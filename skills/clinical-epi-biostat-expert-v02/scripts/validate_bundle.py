"""Check bundle structure and provenance without evaluating statistical correctness."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

from lookup import BUNDLE, RULE_FILES, concept_ids, inactive, read_jsonl


REQUIRED_DIRS = ("knowledge", "modes", "tests", "examples", "provenance", "scripts")
REQUIRED_KNOWLEDGE = RULE_FILES + ("terminology.json", "problem_method_map.csv")
REQUIRED_FIELDS = (
    "rule_id", "canonical_claim_ids", "source_article_ids", "evidence_ids",
    "audit_status", "version", "last_reviewed", "origin",
)
EXPECTED_QUARANTINED = 387


def quarantine_record(row: dict) -> bool:
    return any("QUARANTINED" in str(row.get(key, "")).upper()
               for key in ("status", "audit_status", "validation_status", "gate_status"))


def manifest_entries(data: object) -> list[tuple[str, str]]:
    if isinstance(data, dict):
        for key in ("files", "sha256_by_path", "file_hashes"):
            if key in data:
                return manifest_entries(data[key])
        entries = []
        for name, value in data.items():
            if isinstance(value, str) and len(value) == 64:
                entries.append((name, value))
            elif isinstance(value, dict) and value.get("sha256"):
                entries.append((name, value["sha256"]))
        return entries
    if isinstance(data, list):
        return [(str(row.get("path") or row.get("relative_path")), row["sha256"])
                for row in data if isinstance(row, dict) and row.get("sha256")]
    return []


def main() -> int:
    errors = []
    warnings = []
    counts = {}
    if len(sys.argv) != 1:
        errors.append("Usage: python scripts/validate_bundle.py")
    for name in REQUIRED_DIRS:
        if not (BUNDLE / name).is_dir():
            errors.append(f"Missing directory: {name}")
    for name in ("SKILL.md", "README.md", "provenance/excluded_registry.jsonl"):
        if not (BUNDLE / name).is_file():
            errors.append(f"Missing file: {name}")
    for name in REQUIRED_KNOWLEDGE + ("evidence_catalog.jsonl",):
        if not (BUNDLE / "knowledge" / name).is_file():
            errors.append(f"Missing knowledge file: {name}")

    def rows(name: str) -> list[dict]:
        path = BUNDLE / name
        if not path.is_file():
            return []
        try:
            result = read_jsonl(path)
            counts[name] = len(result)
            return result
        except (OSError, ValueError) as error:
            errors.append(f"{name}: {error}")
            return []

    evidence_rows = rows("knowledge/evidence_catalog.jsonl")
    evidence_ids = set()
    for row in evidence_rows:
        key = row.get("evidence_id")
        if not isinstance(key, str) or not key:
            errors.append("Evidence entry missing evidence_id")
        elif key in evidence_ids:
            errors.append(f"Duplicate evidence_id: {key}")
        else:
            evidence_ids.add(key)
    if not evidence_ids:
        errors.append("Evidence catalog has no usable records")

    all_rule_ids = set()
    active_claim_ids = set()
    for name in RULE_FILES:
        records = rows("knowledge/" + name)
        if not records and (BUNDLE / "knowledge" / name).is_file():
            errors.append(f"Empty rule file: {name}")
        for index, rule in enumerate(records, 1):
            location = f"{name}:{index}"
            missing = [field for field in REQUIRED_FIELDS if field not in rule]
            if missing:
                errors.append(f"{location} missing fields: {missing}")
            if inactive(rule):
                errors.append(f"{location} contains an inactive audit marker")
            key = rule.get("rule_id")
            if not isinstance(key, str) or not key.strip():
                errors.append(f"{location} has no valid rule_id")
            elif key in all_rule_ids:
                errors.append(f"Duplicate rule_id: {key}")
            else:
                all_rule_ids.add(key)
            for field in ("canonical_claim_ids", "source_article_ids", "evidence_ids"):
                values = rule.get(field)
                if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
                    errors.append(f"{location} {field} must be a list of nonempty strings")
                elif field != "source_article_ids" and not values:
                    errors.append(f"{location} {field} must not be empty")
            for field in ("audit_status", "version", "origin"):
                if not isinstance(rule.get(field), str) or not rule.get(field, "").strip():
                    errors.append(f"{location} {field} must be nonempty")
            try:
                date.fromisoformat(rule.get("last_reviewed", ""))
            except (TypeError, ValueError):
                errors.append(f"{location} last_reviewed must be an ISO date")
            references = rule.get("evidence_ids", [])
            if isinstance(references, list):
                for evidence_id in references:
                    if isinstance(evidence_id, str) and evidence_id not in evidence_ids:
                        errors.append(f"{location} unresolved evidence_id: {evidence_id}")
            if isinstance(rule.get("canonical_claim_ids"), list):
                active_claim_ids.update(value for value in concept_ids(rule) if value)

    excluded = rows("provenance/excluded_registry.jsonl")
    quarantined_ids = set()
    quarantined_records = 0
    for index, row in enumerate(excluded, 1):
        if quarantine_record(row):
            quarantined_records += 1
            ids = concept_ids(row)
            if not ids:
                errors.append(f"excluded_registry.jsonl:{index} lacks a quarantined concept identifier")
            for key in ids:
                if key in quarantined_ids:
                    errors.append(f"Duplicate quarantined canonical id: {key}")
                quarantined_ids.add(key)
    if len(quarantined_ids) != EXPECTED_QUARANTINED:
        errors.append(f"Expected {EXPECTED_QUARANTINED} quarantined canonical groups, found {len(quarantined_ids)}")
    for key in sorted(active_claim_ids & quarantined_ids):
        errors.append(f"Quarantined concept is active: {key}")

    terminology = BUNDLE / "knowledge" / "terminology.json"
    if terminology.is_file():
        try:
            value = json.loads(terminology.read_text(encoding="utf-8-sig"))
            if not isinstance(value, (dict, list)) or not value:
                errors.append("terminology.json must contain a nonempty object or list")
        except (OSError, ValueError) as error:
            errors.append(f"terminology.json: {error}")
    mapping = BUNDLE / "knowledge" / "problem_method_map.csv"
    if mapping.is_file():
        try:
            with mapping.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                records = list(reader)
                if not reader.fieldnames or not records:
                    errors.append("problem_method_map.csv must contain a header and data")
                counts["knowledge/problem_method_map.csv"] = len(records)
        except (OSError, csv.Error) as error:
            errors.append(f"problem_method_map.csv: {error}")

    manifest_count = 0
    for filename in ("freeze_manifest.json", "skill_freeze_manifest.json"):
        path = BUNDLE / "provenance" / filename
        if not path.is_file():
            continue
        manifest_count += 1
        try:
            entries = manifest_entries(json.loads(path.read_text(encoding="utf-8-sig")))
            if not entries:
                errors.append(f"{filename} has no recognized SHA-256 entries")
            for relative, expected in entries:
                target = (BUNDLE / relative).resolve()
                try:
                    target.relative_to(BUNDLE)
                except ValueError:
                    errors.append(f"{filename} target escapes bundle: {relative}")
                    continue
                if not target.is_file():
                    errors.append(f"Frozen file missing: {relative}")
                elif hashlib.sha256(target.read_bytes()).hexdigest() != str(expected).lower():
                    errors.append(f"Frozen file changed: {relative}")
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors.append(f"{filename}: {error}")
    if manifest_count == 0:
        warnings.append("No optional freeze manifest found; freeze verification was not performed")
    result = {
        "structural_validation_passed": not errors,
        "scope": "Structure, explicit audit gates, provenance references and optional freeze integrity only; statistical correctness and clinical validity are not tested.",
        "active_rule_records": len(all_rule_ids),
        "distinct_active_canonical_ids": len(active_claim_ids),
        "count_note": "Multiple operational layers can derive from one concept; rule records are not independent facts.",
        "quarantined_records": quarantined_records,
        "quarantined_canonical_groups": len(quarantined_ids),
        "freeze_manifests_checked": manifest_count,
        "file_counts": counts, "errors": errors, "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
