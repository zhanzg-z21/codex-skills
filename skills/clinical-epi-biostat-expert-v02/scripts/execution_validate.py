"""Validate delivered artifacts and retain five separate code-to-claim layers."""
import csv
import json
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET
import zlib

from execution_common import (OUTPUT_TYPES, aggregate, check_evidence, finite_number,
                              inside_path, load_json, read_csv, resolve_workspace,
                              save_json, timestamp, validate_contract)


def inspect_png(path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("PNG signature is invalid")
    offset, chunks, compressed, header = 8, [], bytearray(), None
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("PNG chunk header is truncated")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(data):
            raise ValueError("PNG chunk body is truncated")
        payload = data[offset + 8:offset + 8 + length]
        actual_crc = struct.unpack(">I", data[offset + 8 + length:end])[0]
        if zlib.crc32(kind + payload) & 0xffffffff != actual_crc:
            raise ValueError("PNG chunk CRC mismatch")
        chunks.append(kind)
        if kind == b"IHDR":
            if header is not None or length != 13 or len(chunks) != 1:
                raise ValueError("PNG IHDR is malformed")
            header = struct.unpack(">IIBBBBB", payload)
        if kind == b"IDAT":
            compressed.extend(payload)
        offset = end
        if kind == b"IEND":
            if length != 0 or offset != len(data):
                raise ValueError("PNG end marker is malformed or trailing bytes exist")
            break
    if not header or not chunks or chunks[-1] != b"IEND" or not compressed:
        raise ValueError("PNG required chunks are missing")
    width, height, depth, color, compression, filtering, interlace = header
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
    legal_depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
    if not width or not height or not channels or depth not in legal_depths[color] or compression or filtering or interlace not in (0, 1):
        raise ValueError("PNG image header values are invalid")
    if width * height > 100_000_000:
        raise ValueError("PNG exceeds the validator pixel limit")
    decompressor = zlib.decompressobj()
    raw = decompressor.decompress(bytes(compressed), width * height * 9 + height + 4096)
    if not decompressor.eof or decompressor.unused_data:
        raise ValueError("PNG compressed stream is truncated or has trailing data")
    passes = [(0, 0, 1, 1)] if interlace == 0 else [
        (0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
        (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2)]
    cursor = 0
    for x0, y0, dx, dy in passes:
        pass_width = max(0, (width - x0 + dx - 1) // dx)
        pass_height = max(0, (height - y0 + dy - 1) // dy)
        if not pass_width or not pass_height:
            continue
        row_bytes = (pass_width * channels * depth + 7) // 8
        for _ in range(pass_height):
            if cursor >= len(raw) or raw[cursor] > 4:
                raise ValueError("PNG row filter or row data is invalid")
            cursor += row_bytes + 1
    if cursor != len(raw):
        raise ValueError("PNG decoded row length differs from image dimensions")
    return {"width": width, "height": height, "decoded": True,
            "scope": "CRC, decompression and scanline structure; scientific content needs separate evidence"}


def inspect_svg(path):
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ValueError("Root element is not SVG")
    drawing = {"path", "rect", "line", "polyline", "polygon", "circle", "ellipse", "text", "image", "use"}
    count = sum(node.tag.rsplit("}", 1)[-1] in drawing for node in root.iter())
    if count == 0:
        raise ValueError("SVG contains no drawing elements")
    return {"drawing_elements": count, "scope": "XML and drawing structure, not a rendering or scientific review"}


def inspect_pdf(path):
    data = path.read_bytes()
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-1024:]:
        raise ValueError("PDF header or end marker is missing")
    try:
        from pypdf import PdfReader
    except ImportError:
        return {"status": "PARTIAL", "reason": "PDF envelope exists but a PDF parser is unavailable; readability is not certified"}
    reader = PdfReader(str(path), strict=True)
    if reader.is_encrypted or len(reader.pages) == 0:
        raise ValueError("PDF has no readable unencrypted pages")
    for page in reader.pages:
        float(page.mediabox.width)
        float(page.mediabox.height)
        contents = page.get_contents()
        if contents is not None:
            contents.get_data()
    return {"pages": len(reader.pages), "scope": "Parsed pages and content streams; target semantics need separate evidence"}


def assertion_result(path, assertion, root):
    kind = assertion.get("type")
    result = {"type": kind, "status": "PASS"}
    try:
        if kind == "nonempty":
            if not path.is_file() or path.stat().st_size <= 0:
                raise ValueError("File does not exist or is empty")
            result["bytes"] = path.stat().st_size
        elif kind in ("csv_columns", "csv_rows", "csv_no_na", "csv_ci", "csv_numeric", "csv_unique"):
            header, rows = read_csv(path, assertion.get("delimiter", ","))
            if kind == "csv_rows":
                if len(rows) < assertion.get("min", 1) or len(rows) > assertion.get("max", float("inf")):
                    raise ValueError("CSV row count does not meet the contract")
                result["rows"] = len(rows)
            elif kind == "csv_columns":
                missing = set(assertion["columns"]) - set(header)
                if missing:
                    raise ValueError("CSV columns missing: " + ", ".join(sorted(missing)))
                result["columns_checked"] = assertion["columns"]
            elif kind == "csv_no_na":
                columns = assertion.get("columns", header)
                missing_tokens = {str(value).strip().lower() for value in assertion.get("missing_tokens", ["", "NA", "NaN", "null", "None", "N/A"])}
                for column in columns:
                    if column not in header:
                        raise ValueError("Column missing: " + column)
                failures = [(index + 1, column) for index, row in enumerate(rows) for column in columns
                            if str(row[column]).strip().lower() in missing_tokens]
                if failures:
                    raise ValueError("Unexpected missing values: " + str(failures[:10]))
                result["rows_checked"] = len(rows)
            elif kind == "csv_ci":
                if not rows:
                    raise ValueError("Confidence interval CSV has no data rows")
                lower = assertion["lower"]
                upper = assertion["upper"]
                estimate = assertion.get("estimate")
                for index, row in enumerate(rows):
                    lo, hi = finite_number(row[lower]), finite_number(row[upper])
                    if lo > hi:
                        raise ValueError("Reversed confidence limits at row " + str(index + 1))
                    if estimate and assertion.get("estimate_within", True):
                        value = finite_number(row[estimate])
                        if not lo <= value <= hi:
                            raise ValueError("Estimate is outside declared interval at row " + str(index + 1))
                result["rows_checked"] = len(rows)
                result["scope"] = "Interval structure and declared relation only; coverage and contrast require semantic evidence"
            elif kind == "csv_numeric":
                for row in rows:
                    for column in assertion["columns"]:
                        value = finite_number(row[column])
                        if value < assertion.get("min", float("-inf")) or value > assertion.get("max", float("inf")):
                            raise ValueError("Numeric value is outside declared bounds")
                result["rows_checked"] = len(rows)
            elif kind == "csv_unique":
                keys = [tuple(row[column] for column in assertion["columns"]) for row in rows]
                if len(keys) != len(set(keys)):
                    raise ValueError("CSV key is not unique")
                result["rows_checked"] = len(rows)
        elif kind == "png":
            result.update(inspect_png(path))
        elif kind == "svg":
            result.update(inspect_svg(path))
        elif kind == "pdf":
            result.update(inspect_pdf(path))
        elif kind == "json":
            value = load_json(path)
            for key in assertion.get("required_keys", []):
                if key not in value:
                    raise ValueError("JSON key missing: " + key)
        elif kind == "text_contains":
            text = path.read_text(encoding="utf-8-sig")
            for needle in assertion["strings"]:
                if needle not in text:
                    raise ValueError("Required text is absent: " + needle)
        elif kind == "execution_evidence":
            evidence = {
                "status": "PASS", "verification": "programmatic",
                "evidence_path": assertion["evidence_path"], "check_ids": [assertion["check_id"]],
                "rationale": assertion.get("rationale", "Declared execution-side artifact check")}
            result.update(check_evidence(root, evidence))
        else:
            raise ValueError("Unsupported assertion: " + str(kind))
    except Exception as error:
        result.update({"status": "FAIL", "reason": str(error)})
    return result


def inspect_artifact(item, root, record):
    result = {key: item.get(key) for key in ("id", "path", "required", "core", "kind")}
    result.update({"status": "FAIL", "assertions": []})
    try:
        path = inside_path(root, item["path"])
        result["resolved_path"] = str(path)
        result["assertions"].append(assertion_result(path, {"type": "nonempty"}, root))
        if result["assertions"][-1]["status"] == "FAIL":
            result["reason"] = "Promised artifact is absent or empty"
            return result
        kind = item["kind"]
        if kind == "csv":
            read_csv(path)
        elif kind in ("png", "svg", "pdf", "json"):
            result["assertions"].append(assertion_result(path, {"type": kind}, root))
        elif kind == "text":
            path.read_text(encoding="utf-8-sig")
        elif kind not in ("rds", "model", "binary"):
            raise ValueError("Unsupported artifact kind: " + str(kind))
        for assertion in item["assertions"]:
            result["assertions"].append(assertion_result(path, assertion, root))
        if kind in ("rds", "model", "binary") and not any(a.get("type") == "execution_evidence" for a in item["assertions"]):
            result["assertions"].append({"type": "model_object_readability", "status": "PARTIAL",
                                         "reason": "A nonempty opaque model file needs an actual execution-side read or object check"})
        if kind in ("png", "svg", "pdf") and not any(a.get("type") == "execution_evidence" for a in item["assertions"]):
            evidence = record.get("artifact_evidence", {}).get(item["id"])
            checked = check_evidence(root, evidence)
            checked["type"] = "figure_target_consistency"
            result["assertions"].append(checked)
        result["status"] = aggregate(a["status"] for a in result["assertions"])
        result["scope"] = "Mechanical checks plus explicitly labelled execution-side or human evidence"
    except Exception as error:
        result["assertions"].append({"type": "artifact_exception", "status": "FAIL", "reason": str(error)})
        result["status"] = "FAIL"
    return result


def validate_execution(contract_path, output_dir, run_record_path=None):
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": 1, "created_at": timestamp(),
                "contract_path": str(Path(contract_path).resolve()),
                "completion_claim": "execution failed", "analysis_completed": False,
                "clinical_validation_claim_allowed": False,
                "clinical_claim_note": "Analysis completion does not establish clinical validation",
                "expected_outputs": {}, "layers": {}, "validation_errors": []}
    for category in OUTPUT_TYPES:
        manifest["expected_outputs"][category] = {"status": "NOT_REQUIRED", "artifacts": []}
    try:
        contract = load_json(contract_path)
        root = resolve_workspace(contract, contract_path)
        manifest.update({"workspace": str(root), "analysis_goal": contract.get("analysis_goal"),
                         "estimand": contract.get("estimand"), "success_criteria": contract.get("success_criteria")})
        errors = validate_contract(contract)
        manifest["validation_errors"].extend(errors)
        record = load_json(run_record_path) if run_record_path else {}
        manifest["run_record_path"] = str(Path(run_record_path).resolve()) if run_record_path else None
        execution = record.get("execution", {})
        executed = execution.get("started") is True
        ran_successfully = executed and execution.get("completed") is True and execution.get("exit_code") == 0
        if not executed:
            execution_status, reason = "FAIL", "Analysis execution was not demonstrated"
        elif not ran_successfully:
            execution_status, reason = "FAIL", "Analysis process did not complete successfully"
        else:
            execution_status, reason = "PASS", "Successful execution is recorded"
            log = execution.get("log_path")
            if not log or not inside_path(root, log).is_file():
                execution_status, reason = "PARTIAL", "Successful execution was asserted without its readable log"
        manifest["layers"]["execution"] = {"status": execution_status, "reason": reason, "record": execution}
        preflight_path = record.get("preflight_path", contract.get("preflight_path"))
        if preflight_path:
            path = inside_path(root, preflight_path)
            preflight = load_json(path)
            manifest["preflight"] = {"path": str(path), "status": preflight.get("status", "FAIL")}
        else:
            manifest["preflight"] = {"status": "PARTIAL", "reason": "Preflight record is missing"}
        provenance_path = contract.get("provenance_path", record.get("provenance_path"))
        if provenance_path:
            path = inside_path(root, provenance_path)
            provenance = load_json(path)
            manifest["data_provenance"] = {"path": str(path), "record": provenance,
                                            "verification_status": provenance.get("verification_status", "UNKNOWN")}
        else:
            manifest["data_provenance"] = {"verification_status": "UNKNOWN", "reason": "Provenance record is missing"}
        gate_path = record.get("provenance_gate_path", contract.get("provenance_gate_path"))
        if gate_path:
            gate = load_json(inside_path(root, gate_path))
            manifest["data_provenance"]["gate_result"] = gate
            manifest["data_provenance"]["gate_path"] = str(inside_path(root, gate_path))
            manifest["approved_test_kind"] = gate.get("requested_claim", "technical execution test")
            manifest["allowed_claims"] = gate.get("allowed_claims", [])
            manifest["real_patient_test_eligible"] = gate.get("real_patient_test_eligible", False)
        else:
            manifest["approved_test_kind"] = "Not classified by provenance gate"
        for layer in ("statistical_specification", "estimand_consistency"):
            manifest["layers"][layer] = check_evidence(root, record.get(layer))
        for category in OUTPUT_TYPES:
            artifacts = [inspect_artifact(item, root, record) for item in contract.get("expected_outputs", {}).get(category, [])]
            manifest["expected_outputs"][category] = {"status": aggregate(item["status"] for item in artifacts), "artifacts": artifacts}
        artifacts = [item for value in manifest["expected_outputs"].values() for item in value["artifacts"]]
        required = [item for item in artifacts if item.get("required")]
        core = [item for item in required if item.get("core")]
        missing = [item["id"] for item in required if any(check.get("type") == "nonempty" and check["status"] == "FAIL" for check in item["assertions"])]
        manifest["layers"]["output_completeness"] = {
            "status": "FAIL" if missing else ("PASS" if required else "PARTIAL"),
            "required_artifact_count": len(required), "missing_required_artifacts": missing,
            "scope": "Presence of required output files, with correctness evaluated separately"}
        manifest["layers"]["artifact_integrity"] = {
            "status": aggregate((item["status"] for item in required), empty="PARTIAL"),
            "scope": "Readability, assertions and labelled target-consistency evidence"}
        manifest["core_required_outputs_pass"] = bool(core) and all(item["status"] == "PASS" for item in core)
        manifest["all_promised_outputs_pass"] = bool(artifacts) and all(item["status"] == "PASS" for item in artifacts)
        provenance_present = bool(provenance_path and gate_path)
        gate_result = manifest["data_provenance"].get("gate_result", {})
        approved = (gate_result.get("analysis_approved") is True and gate_result.get("gate_status") == "PASS"
                    and gate_result.get("record_status") == "PASS" and gate_result.get("requested_claim_allowed") is True)
        all_layers_pass = all(layer.get("status") == "PASS" for layer in manifest["layers"].values())
        can_complete = (not errors and manifest["core_required_outputs_pass"] and all_layers_pass
                        and manifest["preflight"]["status"] == "PASS" and provenance_present and approved)
        manifest["analysis_completed"] = can_complete
        manifest["completion_claim"] = "analysis completed" if can_complete else ("analysis partially executed" if executed and ran_successfully else "execution failed")
        manifest["execution_success"] = execution_status == "PASS"
        manifest["output_integrity_success"] = manifest["layers"]["artifact_integrity"]["status"] == "PASS"
        if not provenance_present:
            manifest["validation_errors"].append("Explicit provenance and its gate record are required before completion")
    except Exception as error:
        manifest["validation_errors"].append(repr(error))
        manifest["analysis_completed"] = False
        manifest["completion_claim"] = "execution failed"
    for layer in ("execution", "statistical_specification", "estimand_consistency", "output_completeness", "artifact_integrity"):
        manifest["layers"].setdefault(layer, {"status": "FAIL", "reason": "Validation could not establish this layer"})
    save_json(output_dir / "execution_manifest.json", manifest)
    return manifest


def main():
    if len(sys.argv) not in (3, 4):
        print("Usage: python execution_validate.py CONTRACT.json OUTPUT_DIR [RUN_RECORD.json]")
        return 2
    result = validate_execution(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None)
    print(json.dumps({"completion_claim": result["completion_claim"], "path": str(Path(sys.argv[2]).resolve() / "execution_manifest.json")}, ensure_ascii=True))
    return 0 if result["analysis_completed"] else 1


if __name__ == "__main__":
    sys.exit(main())
