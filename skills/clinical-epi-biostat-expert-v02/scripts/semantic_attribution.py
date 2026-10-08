"""Enforce auditable attribution decisions, not automatic natural-language entailment."""
import json
import sys
from pathlib import Path

REQUIRED = ["rule_id", "trigger_text", "matched_condition", "rule_scope",
            "current_case_condition", "semantic_match", "attribution_confidence",
            "case_quote", "reason", "requested_action", "used_as_basis"]
RULE_FILES = ["validated_rules.jsonl", "conditional_rules.jsonl", "decision_rules.jsonl",
              "reviewer_checks.jsonl", "reporting_rules.jsonl", "implementation_rules.jsonl",
              "rejected_patterns.jsonl", "hard_stops.jsonl"]


def load_rules(root):
    rules = {}
    for name in RULE_FILES:
        for line in (root / "knowledge" / name).read_text(encoding="utf-8-sig").splitlines():
            record = json.loads(line)
            rid = record.get("rule_id") or record.get("red_flag_rule_id")
            if rid:
                rules[rid] = record
    return rules


def evaluate(payload, skill_root, case_text):
    rules = load_rules(skill_root)
    decisions = []
    for row in payload.get("attributions", []):
        issues = [f"Missing field: {key}" for key in REQUIRED if key not in row or row[key] is None or row[key] == ""]
        rid = row.get("rule_id")
        rule = rules.get(rid)
        if not rule:
            issues.append("Rule is not in active knowledge")
        else:
            serialized = json.dumps(rule, ensure_ascii=False)
            if not row.get("trigger_text") or row["trigger_text"] not in serialized:
                issues.append("trigger_text is not an exact excerpt of the active rule")
            if any(e not in rule.get("evidence_ids", []) for e in row.get("evidence_ids", [])):
                issues.append("Evidence ID is not associated with this rule")
        if not row.get("case_quote") or row["case_quote"] not in case_text:
            issues.append("case_quote is not present in the supplied case")
        match = row.get("semantic_match")
        if match not in {"YES", "PARTIAL", "NO"}:
            issues.append("Invalid semantic_match")
        if row.get("attribution_confidence") not in {"HIGH", "MODERATE", "LOW"}:
            issues.append("Invalid attribution_confidence")
        if not isinstance(row.get("used_as_basis"), bool):
            issues.append("used_as_basis must be a boolean")
        if match == "NO" and row.get("used_as_basis"):
            issues.append("NO semantic match cannot support a conclusion")
        if match == "PARTIAL" and not row.get("limitations"):
            issues.append("PARTIAL semantic match requires limitations")
        action = row.get("requested_action")
        if action not in {"HARD_STOP", "WARNING", "CONDITIONAL_CHECK", "NONE"}:
            issues.append("Invalid requested_action")
        eligible_stop = bool(rule and rule.get("severity") == "HARD_STOP" and match == "YES"
                             and row.get("trigger_matched") is True
                             and row.get("critical_information_missing") is True
                             and row.get("missing_information")
                             and row.get("decision_impact")
                             and row.get("used_as_basis") is True)
        if action == "HARD_STOP" and not eligible_stop:
            issues.append("Hard Stop lacks exact trigger and decision-changing missing-information verification")
        decisions.append({
            "rule_id": rid, "status": "FAIL" if issues else "PASS",
            "semantic_match": match,
            "accepted_as_basis": not issues and match in {"YES", "PARTIAL"} and row.get("used_as_basis") is True,
            "hard_stop_accepted": not issues and action == "HARD_STOP" and eligible_stop,
            "effective_action": action if not issues else "NONE", "issues": issues,
        })
    complete = bool(decisions) and all(x["status"] == "PASS" for x in decisions)
    return {"case_id": payload.get("case_id", "not_available"), "status": "PASS" if complete else "FAIL",
            "decisions": decisions, "accepted_rule_ids": [d["rule_id"] for d in decisions if d["accepted_as_basis"]],
            "hard_stop_triggered": any(d["hard_stop_accepted"] for d in decisions),
            "review_type": payload.get("review_type", "not_available"),
            "automation_scope": "Exact source anchors, rule existence and consistency constraints checked. A reviewer must judge the semantic relationship; this script does not prove the supplied YES judgment."}


def main():
    target = Path(sys.argv[2])
    try:
        source = Path(sys.argv[1]).resolve()
        payload = json.loads(source.read_text(encoding="utf-8-sig"))
        case_path = Path(payload["case_file"])
        if not case_path.is_absolute():
            case_path = source.parent / case_path
        result = evaluate(payload, Path(__file__).resolve().parents[1], case_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        result = {"status": "FAIL", "issues": [str(exc)], "accepted_rule_ids": [], "hard_stop_triggered": False}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
