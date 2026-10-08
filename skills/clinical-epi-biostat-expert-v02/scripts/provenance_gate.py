"""Validate a declared data provenance record without certifying its truth."""
import json
import sys
from pathlib import Path

FIELDS = ["dataset_id", "source", "source_file", "real_or_simulated", "patient_level",
          "derived_or_raw", "creation_history", "known_transformations", "verification_status",
          "patient_id_available", "source_population_known", "analysis_approved"]
STATUSES = {"VERIFIED_FOR_TESTING", "PARTIALLY_VERIFIED", "UNVERIFIED", "SIMULATED", "UNKNOWN"}


def evaluate(record):
    issues = []
    for field in FIELDS:
        if field not in record or record[field] is None or record[field] == "":
            issues.append(f"Missing provenance field: {field}")
    status = record.get("verification_status", "UNKNOWN")
    if status not in STATUSES:
        issues.append("Invalid verification_status")
    for field in ("patient_level", "patient_id_available", "source_population_known", "analysis_approved"):
        if not isinstance(record.get(field), bool):
            issues.append(f"{field} must be a boolean")
    kind = str(record.get("real_or_simulated", "UNKNOWN")).upper()
    if kind not in {"REAL", "SIMULATED", "MIXED", "UNKNOWN"}:
        issues.append("real_or_simulated must be REAL, SIMULATED, MIXED or UNKNOWN")
    if kind == "SIMULATED" and status != "SIMULATED":
        issues.append("Simulation cannot be relabeled as verified real observations")
    if status == "SIMULATED" and kind != "SIMULATED":
        issues.append("Simulation status conflicts with declared data origin")
    if status == "VERIFIED_FOR_TESTING":
        if kind != "REAL" or not record.get("verification_evidence") or not record.get("verification_scope"):
            issues.append("Verified testing requires REAL origin, evidence and a bounded verification scope")
    if status == "PARTIALLY_VERIFIED" and not record.get("verification_scope"):
        issues.append("Partial verification requires explicit limits")
    real_allowed = (not issues and status == "VERIFIED_FOR_TESTING" and kind == "REAL"
                    and record.get("patient_level") is True
                    and record.get("source_population_known") is True
                    and record.get("analysis_approved") is True)
    allowed = []
    if not issues and record.get("analysis_approved") is True:
        allowed.append("simulation test" if kind == "SIMULATED" else "technical execution test")
        if kind == "SIMULATED":
            allowed.append("technical execution test")
        if real_allowed:
            allowed.extend(["real patient validation", "real-world code validation"])
    prohibited = [x for x in ["real patient validation", "real-world code validation", "clinical validation"] if x not in allowed]
    requested = record.get("requested_claim", "technical execution test")
    claim_allowed = requested in allowed
    return {
        "dataset_id": record.get("dataset_id", "not_available"),
        "verification_status": status,
        "record_status": "PASS" if not issues else "FAIL",
        "gate_status": "PASS" if not issues and claim_allowed else "FAIL",
        "analysis_approved": record.get("analysis_approved") is True,
        "allowed_claims": allowed, "prohibited_claims": prohibited,
        "requested_claim": requested, "requested_claim_allowed": claim_allowed,
        "real_patient_test_eligible": real_allowed,
        "issues": issues,
        "verification_scope": record.get("verification_scope", "not_available"),
        "limits": "This checks provenance declarations and claim eligibility. Source truth needs documented inspection. Clinical validation cannot be inferred from a data record or successful code run.",
    }


def main():
    target = Path(sys.argv[2])
    try:
        source = Path(sys.argv[1])
        record = json.loads(source.read_text(encoding="utf-8-sig"))
        result = evaluate(record)
        result["record_path"] = str(source.resolve())
    except Exception as exc:
        result = {"record_status": "FAIL", "gate_status": "FAIL", "issues": [str(exc)],
                  "requested_claim_allowed": False, "real_patient_test_eligible": False}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["gate_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
