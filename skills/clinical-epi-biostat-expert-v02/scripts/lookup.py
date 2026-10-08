"""Retrieve active rules by words or identifier using only the Python standard library."""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path


BUNDLE = Path(__file__).resolve().parents[1]
KNOWLEDGE = BUNDLE / "knowledge"
MAX_RESULTS = 8
RULE_FILES = (
    "hard_stops.jsonl",
    "rejected_patterns.jsonl",
    "conditional_rules.jsonl",
    "validated_rules.jsonl",
    "decision_rules.jsonl",
    "reviewer_checks.jsonl",
    "reporting_rules.jsonl",
    "implementation_rules.jsonl",
)
NOTICE = (
    "词匹配可能漏检或误匹配，检索结果不构成统计决策。必须阅读完整适用条件、"
    "研究设计和证据范围。同一概念可派生多个操作层规则，命中数不是独立事实数。"
)


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"{path.name}:{number}: expected an object")
                rows.append(row)
    return rows


def inactive(value: object) -> bool:
    """Conservatively exclude an explicit inactive audit marker at any depth."""
    if isinstance(value, dict):
        if value.get("audit_completed") is False:
            return True
        for name in ("status", "audit_status", "validation_status", "gate_status"):
            marker = str(value.get(name, "")).upper()
            if "QUARANTINED" in marker or marker in {
                "UNREVIEWED", "UNRESOLVED", "NOT_AUDITED", "PENDING_REVIEW"
            }:
                return True
        return any(inactive(item) for item in value.values())
    if isinstance(value, list):
        return any(inactive(item) for item in value)
    return False


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in strings(item)]
    if isinstance(value, list):
        return [text for item in value for text in strings(item)]
    return []


def concept_ids(rule: dict) -> list[str]:
    values = rule.get("canonical_claim_ids", [])
    if isinstance(values, str):
        values = [values]
    elif isinstance(values, list):
        values = list(values)
    else:
        values = []
    single = rule.get("canonical_claim_id")
    if isinstance(single, str):
        values.append(single)
    return sorted({item for item in values if isinstance(item, str) and item})


def score_query(query: str, rule: dict) -> tuple[float, list[str]]:
    text = normalize("\n".join(strings(rule)))
    phrase = normalize(query.strip())
    terms = list(dict.fromkeys(re.findall(r"[\w]+(?:-[\w]+)*", phrase)))
    hits = []
    score = 4.0 if phrase and phrase in text else 0.0
    for term in terms:
        chinese = bool(re.search(r"[\u3400-\u9fff]", term))
        exact = term in text if chinese else bool(
            re.search(r"(?<![\w])" + re.escape(term) + r"(?![\w])", text)
        )
        if exact:
            score += 2.0
            hits.append(term)
        elif chinese and len(term) >= 4:
            grams = {term[i:i + 2] for i in range(len(term) - 1)}
            present = {gram for gram in grams if gram in text}
            if len(present) >= 2 and len(present) / len(grams) >= 0.5:
                score += len(present) / len(grams)
                hits.append(term + " [partial character match]")
    return score, hits


def emit(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(arguments: list[str]) -> int:
    if not arguments or arguments[0] not in {"query", "id", "topics"}:
        emit({"error": "Usage: python scripts/lookup.py query 'text' | id 'id' | topics"})
        return 2
    command = arguments[0]
    query = " ".join(arguments[1:]).strip()
    if (command != "topics" and not query) or (command == "topics" and query):
        emit({"error": "query and id require text; topics takes no additional argument"})
        return 2
    missing = [name for name in RULE_FILES if not (KNOWLEDGE / name).is_file()]
    if missing:
        emit({"error": "Knowledge bundle is incomplete", "missing_files": missing})
        return 2
    records = []
    skipped = 0
    for name in RULE_FILES:
        for row in read_jsonl(KNOWLEDGE / name):
            if inactive(row):
                skipped += 1
                continue
            if not row.get("rule_id") or not row.get("audit_status"):
                skipped += 1
                continue
            records.append((name, row))
    evidence_path = KNOWLEDGE / "evidence_catalog.jsonl"
    evidence = {row["evidence_id"]: row for row in read_jsonl(evidence_path)}
    if command == "topics":
        topics = {}
        for filename, rule in records:
            topic = str(rule.get("topic") or rule.get("domain") or "Unspecified")
            item = topics.setdefault(topic, {"rule_records": 0, "canonical_claim_ids": set(), "files": set()})
            item["rule_records"] += 1
            item["canonical_claim_ids"].update(concept_ids(rule))
            item["files"].add(filename)
        output = []
        for topic, counts in sorted(topics.items()):
            output.append({"topic": topic, "rule_records": counts["rule_records"],
                           "distinct_canonical_ids": len(counts["canonical_claim_ids"]),
                           "files": sorted(counts["files"])})
        emit({"notice": NOTICE, "skipped_inactive_or_unmarked": skipped, "topics": output})
        return 0
    hits = []
    for filename, rule in records:
        if command == "id":
            exact = normalize(query) in {
                normalize(str(rule["rule_id"])),
                *(normalize(item) for item in concept_ids(rule)),
            }
            score, matched = (1.0, [query]) if exact else (0.0, [])
        else:
            score, matched = score_query(query, rule)
        if score > 0:
            hits.append((score, filename, rule, matched))
    hits.sort(key=lambda item: (-item[0], RULE_FILES.index(item[1]), item[2]["rule_id"]))
    selected = hits[:MAX_RESULTS]
    results = []
    for score, filename, rule, matched in selected:
        ids = rule.get("evidence_ids", [])
        absent = [item for item in ids if item not in evidence]
        if absent:
            raise ValueError(f"Rule {rule['rule_id']} has unresolved evidence: {absent}")
        results.append({"file": "knowledge/" + filename, "lexical_score": score,
                        "matched_terms": matched, "rule": rule,
                        "evidence": [evidence[item] for item in ids]})
    emit({"command": command, "query": query, "notice": NOTICE,
          "total_matching_records": len(hits), "returned_records": len(results),
          "more_matches_omitted": len(hits) > MAX_RESULTS,
          "distinct_canonical_claim_ids_returned": sorted({item for hit in selected for item in concept_ids(hit[2])}),
          "skipped_inactive_or_unmarked": skipped, "results": results})
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, KeyError, TypeError) as error:
        emit({"error": str(error)})
        raise SystemExit(2)
