"""Shared contract and evidence utilities. Standard library only."""
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_TYPES = (
    "model_object", "estimate", "confidence_interval", "diagnostics",
    "sensitivity_analysis", "table", "figure", "exported_files",
)
STATUSES = {"PASS", "PARTIAL", "FAIL", "NOT_REQUIRED"}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    def reject_nonfinite(value):
        raise ValueError("Nonfinite JSON constant is not allowed: " + value)
    with Path(path).open(encoding="utf-8-sig") as handle:
        return json.load(handle, parse_constant=reject_nonfinite)


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def resolve_workspace(contract, contract_path):
    root = Path(contract.get("workspace", "."))
    if not root.is_absolute():
        root = Path(contract_path).resolve().parent / root
    return root.resolve()


def inside_path(root, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("A nonempty workspace path is required")
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError("Path is outside the contract workspace: " + str(path)) from error
    return path


def validate_contract(contract):
    errors = []
    for key in ("analysis_goal", "estimand", "language", "required_packages",
                "required_data_fields", "success_criteria", "expected_outputs"):
        if key not in contract:
            errors.append("Missing contract field: " + key)
    if not contract.get("analysis_goal") or not contract.get("estimand"):
        errors.append("Analysis goal and estimand must be specified")
    language = contract.get("language", {})
    if not isinstance(language, dict) or language.get("name") not in ("R", "Python"):
        errors.append("language.name must be R or Python")
    if not isinstance(contract.get("required_data_fields"), dict):
        errors.append("required_data_fields must map input paths to field lists")
    expected = contract.get("expected_outputs", {})
    if not isinstance(expected, dict):
        errors.append("expected_outputs must be an object")
        return errors
    unknown_categories = set(expected) - set(OUTPUT_TYPES)
    if unknown_categories:
        errors.append("Unknown output categories cannot be ignored: " + ", ".join(sorted(unknown_categories)))
    ids = set()
    for category in OUTPUT_TYPES:
        if category not in expected:
            errors.append("Missing expected output category: " + category)
            continue
        items = expected[category]
        if not isinstance(items, list):
            errors.append(category + " must be an array; use [] for not required")
            continue
        for item in items:
            if not isinstance(item, dict):
                errors.append(category + " artifacts must be objects")
                continue
            for key in ("id", "path", "required", "core", "kind", "assertions"):
                if key not in item:
                    errors.append(category + " artifact lacks " + key)
            ident = item.get("id")
            if not isinstance(ident, str) or not ident or ident in ids:
                errors.append("Artifact ids must be nonempty and globally unique")
            ids.add(ident)
            if not isinstance(item.get("required"), bool) or not isinstance(item.get("core"), bool):
                errors.append(str(ident) + " requires boolean required and core")
            if item.get("core") and not item.get("required"):
                errors.append(str(ident) + " cannot be core without being required")
            if not isinstance(item.get("assertions"), list):
                errors.append(str(ident) + " assertions must be an array")
    if not any(isinstance(items, list) and any(isinstance(i, dict) and i.get("core")
               for i in items) for items in expected.values()):
        errors.append("At least one core required artifact must be declared")
    return errors


def aggregate(statuses, empty="NOT_REQUIRED"):
    values = list(statuses)
    if not values:
        return empty
    if "FAIL" in values:
        return "FAIL"
    if "PARTIAL" in values:
        return "PARTIAL"
    if "PASS" in values:
        return "PASS"
    return "NOT_REQUIRED"


def read_csv(path, delimiter=","):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError("CSV header is missing")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("CSV has duplicate column names")
        rows = list(reader)
        if any(None in row or any(value is None for value in row.values()) for row in rows):
            raise ValueError("CSV row width differs from its header")
        return reader.fieldnames, rows


def finite_number(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Nonfinite numeric value")
    return result


def check_evidence(root, description):
    """Validate traceable execution-side or human evidence, never infer semantics."""
    if not isinstance(description, dict):
        return {"status": "PARTIAL", "reason": "No review evidence was supplied"}
    claimed = description.get("status", "PARTIAL")
    if claimed not in STATUSES:
        return {"status": "FAIL", "reason": "Invalid evidence status"}
    if claimed == "FAIL":
        return {"status": "FAIL", "reason": description.get("rationale", "Reported failure")}
    if claimed != "PASS":
        return {"status": "PARTIAL", "reason": description.get("rationale", "Review incomplete")}
    verification = description.get("verification")
    if verification not in ("programmatic", "human_review", "internal_model_review"):
        return {"status": "PARTIAL", "reason": "Evidence verification type is missing"}
    try:
        path = inside_path(root, description.get("evidence_path"))
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError("Evidence file is missing or empty")
        if not description.get("rationale"):
            raise ValueError("Evidence rationale is missing")
        if verification == "programmatic":
            payload = load_json(path)
            checks = payload.get("checks", [])
            indexed = {item["id"]: item for item in checks if isinstance(item, dict) and "id" in item}
            ids = description.get("check_ids", [])
            if not ids:
                raise ValueError("Programmatic evidence must name actual check_ids")
            failures = [ident for ident in ids if ident not in indexed or indexed[ident].get("passed") is not True]
            if failures:
                return {"status": "FAIL", "reason": "Execution-side checks failed or absent: " + ", ".join(failures),
                        "verification": verification, "evidence_path": str(path)}
            return {"status": "PASS", "verification": "execution_side_programmatic_evidence",
                    "independent_semantic_proof": False, "check_ids": ids,
                    "evidence_path": str(path), "reason": description["rationale"]}
        if not description.get("reviewer"):
            raise ValueError("A review must identify its reviewer")
        return {"status": "PASS", "verification": verification,
                "independent_semantic_proof": False, "reviewer": description["reviewer"],
                "independent_human_review": verification == "human_review",
                "evidence_path": str(path), "reason": description["rationale"]}
    except (OSError, ValueError, TypeError, KeyError) as error:
        return {"status": "PARTIAL", "reason": str(error), "verification": verification}
