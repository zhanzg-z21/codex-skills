"""Inspect an existing environment without installing or repairing packages."""
import importlib.metadata
import json
import locale
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import unquote

from execution_common import (inside_path, load_json, read_csv, resolve_workspace,
                              save_json, timestamp, validate_contract)


def r_literal(value):
    return json.dumps(str(value), ensure_ascii=True)


def r_probe_script(contract, root):
    lines = [
        'emit <- function(id, value, status="PASS") {',
        '  cat(id, status, utils::URLencode(paste(value,collapse="\\n"), reserved=TRUE), sep="\\t"); cat("\\n")',
        '}',
        'probe <- function(id, code, required=TRUE) {',
        '  tryCatch({ value <- eval(parse(text=code), envir=.GlobalEnv); emit(id, "Call completed") },',
        '    error=function(e) emit(id, conditionMessage(e), if(required) "FAIL" else "WARNING"))',
        '}',
        'emit("R.version.string", R.version.string)',
        'emit("locale", Sys.getlocale())',
        'emit("encoding", paste(names(l10n_info()), unlist(l10n_info()), sep="="))',
        'emit("working_directory", getwd())',
        'emit("library_paths", .libPaths())',
    ]
    for package in contract.get("required_packages", []):
        if isinstance(package, str):
            package = {"name": package}
        name = package["name"]
        target = package.get("version")
        lines.append('if (requireNamespace(' + r_literal(name) + ', quietly=TRUE)) {')
        lines.append('  pv <- as.character(utils::packageVersion(' + r_literal(name) + '))')
        if target:
            lines.append('  emit(' + r_literal("package:" + name) + ',pv, if (pv == ' + r_literal(target) + ') "PASS" else "FAIL")')
        else:
            lines.append('  emit(' + r_literal("package:" + name) + ',pv)')
        lines.append('} else emit(' + r_literal("package:" + name) + ', "Package unavailable", "FAIL")')
    for function in contract.get("critical_functions", []):
        name, package = function["name"], function.get("package", "base")
        expression = 'stopifnot(exists(' + r_literal(name) + ', envir=asNamespace(' + r_literal(package) + '), mode="function", inherits=FALSE))'
        lines.append('probe(' + r_literal("function:" + package + "::" + name) + ',' + r_literal(expression) + ')')
    for relative in contract.get("required_data_fields", {}):
        path = inside_path(root, relative)
        expression = 'stopifnot(file.exists(' + r_literal(path) + ')); read.csv(' + r_literal(path) + ', nrows=0, check.names=FALSE, fileEncoding="UTF-8-BOM")'
        lines.append('probe(' + r_literal("input_R:" + relative) + ',' + r_literal(expression) + ')')
    for probe in contract.get("critical_probes", []):
        lines.append('probe(' + r_literal("probe:" + probe["id"]) + ',' + r_literal(probe["code"]) + ',' + ("TRUE" if probe.get("required", True) else "FALSE") + ')')
    lines.append('emit("sessionInfo", capture.output(sessionInfo()))')
    return "\n".join(lines) + "\n"


def python_probe_script(contract):
    return '''import importlib, importlib.metadata, json, locale, os, sys, traceback
config = json.loads(''' + repr(json.dumps(contract)) + ''')
result = {"language_version": sys.version, "executable": sys.executable,
          "locale": locale.setlocale(locale.LC_ALL, None),
          "encoding": {"filesystem": sys.getfilesystemencoding(), "preferred": locale.getpreferredencoding(False)},
          "working_directory": os.getcwd(), "checks": []}
for package in config.get("required_packages", []):
    package = {"name": package} if isinstance(package, str) else package
    try:
        version = importlib.metadata.version(package["name"])
        importlib.import_module(package.get("import_name", package["name"]))
        passed = not package.get("version") or version == package["version"]
        result["checks"].append({"id": "package:" + package["name"], "status": "PASS" if passed else "FAIL", "detail": version})
    except Exception as error:
        result["checks"].append({"id": "package:" + package["name"], "status": "FAIL", "detail": repr(error)})
for function in config.get("critical_functions", []):
    try:
        value = importlib.import_module(function["package"])
        for part in function["name"].split("."):
            value = getattr(value, part)
        assert callable(value)
        result["checks"].append({"id": "function:" + function["name"], "status": "PASS"})
    except Exception as error:
        result["checks"].append({"id": "function:" + function["name"], "status": "FAIL", "detail": repr(error)})
for probe in config.get("critical_probes", []):
    try:
        exec(probe["code"], globals())
        result["checks"].append({"id": "probe:" + probe["id"], "status": "PASS"})
    except Exception as error:
        result["checks"].append({"id": "probe:" + probe["id"], "status": "FAIL" if probe.get("required", True) else "WARNING", "detail": repr(error)})
print("PREFLIGHT_JSON=" + json.dumps(result, ensure_ascii=True))
'''


def run_preflight(contract_path, output_dir):
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result = {"schema_version": 1, "created_at": timestamp(), "status": "FAIL",
              "contract_path": str(Path(contract_path).resolve()), "checks": [],
              "environment_changed": False, "packages_installed": False,
              "compatibility_scope": "Only declared functions and actual probes were tested"}
    try:
        contract = load_json(contract_path)
        root = resolve_workspace(contract, contract_path)
        result["workspace"] = str(root)
        errors = validate_contract(contract)
        for error in errors:
            result["checks"].append({"id": "contract", "status": "FAIL", "detail": error})
        result["checks"].append({"id": "working_directory", "status": "PASS" if root.is_dir() else "FAIL", "detail": str(root)})
        for category in contract.get("expected_outputs", {}).values():
            for artifact in category:
                try:
                    path = inside_path(root, artifact["path"])
                    result["checks"].append({"id": "output_path:" + artifact["id"], "status": "PASS", "detail": str(path)})
                except (ValueError, TypeError, KeyError) as error:
                    result["checks"].append({"id": "output_path", "status": "FAIL", "detail": str(error)})
        for relative, required in contract.get("required_data_fields", {}).items():
            check = {"id": "input:" + relative, "status": "FAIL"}
            try:
                path = inside_path(root, relative)
                header, rows = read_csv(path)
                missing = sorted(set(required) - set(header))
                check.update({"path": str(path), "rows": len(rows), "columns": header, "missing_fields": missing,
                              "status": "FAIL" if missing else "PASS"})
            except (OSError, ValueError, TypeError) as error:
                check["detail"] = str(error)
            result["checks"].append(check)
        language = contract["language"]
        candidate = language.get("executable", "Rscript" if language["name"] == "R" else sys.executable)
        executable = shutil.which(candidate)
        if not executable and Path(candidate).is_file():
            executable = str(Path(candidate).resolve())
        if not executable:
            raise ValueError("Requested language executable is unavailable: " + candidate)
        result["executable"] = executable
        environment = os.environ.copy()
        overrides = contract.get("environment", {}).get("env", {})
        environment.update({str(key): str(value) for key, value in overrides.items()})
        result["process_environment_overrides"] = overrides
        script_path = output_dir / ("preflight_probe.R" if language["name"] == "R" else "preflight_probe.py")
        script_path.write_text(r_probe_script(contract, root) if language["name"] == "R" else python_probe_script(contract), encoding="utf-8")
        timeout = min(max(int(contract.get("preflight_timeout_seconds", 60)), 1), 300)
        completed = subprocess.run([executable, str(script_path)], cwd=root, env=environment,
                                   capture_output=True, timeout=timeout)
        stdout = completed.stdout.decode("utf-8", errors="replace")
        stderr = completed.stderr.decode("utf-8", errors="replace")
        (output_dir / "preflight_stdout.log").write_text(stdout, encoding="utf-8")
        (output_dir / "preflight_stderr.log").write_text(stderr, encoding="utf-8")
        result["process_exit_code"] = completed.returncode
        result["stderr"] = stderr
        if language["name"] == "R":
            metadata = {}
            for line in stdout.splitlines():
                parts = line.split("\t", 2)
                if len(parts) != 3 or parts[1] not in ("PASS", "FAIL", "WARNING"):
                    continue
                key, status, payload = parts[0], parts[1], unquote(parts[2])
                if key in ("R.version.string", "locale", "encoding", "working_directory", "library_paths", "sessionInfo"):
                    metadata[key] = payload
                else:
                    result["checks"].append({"id": key, "status": status, "detail": payload})
            result["runtime"] = metadata
            for required in ("R.version.string", "locale", "encoding", "sessionInfo"):
                if required not in metadata:
                    result["checks"].append({"id": "runtime_record:" + required, "status": "FAIL", "detail": "Record not produced"})
            expected_ids = ["package:" + (p if isinstance(p, str) else p["name"]) for p in contract.get("required_packages", [])]
            expected_ids += ["probe:" + p["id"] for p in contract.get("critical_probes", [])]
            actual_ids = {check["id"] for check in result["checks"]}
            for expected_id in expected_ids:
                if expected_id not in actual_ids:
                    result["checks"].append({"id": expected_id, "status": "FAIL", "detail": "Declared probe did not produce a result"})
        else:
            records = [line.partition("=")[2] for line in stdout.splitlines() if line.startswith("PREFLIGHT_JSON=")]
            if not records:
                raise ValueError("Python runtime did not produce its preflight record")
            payload = json.loads(records[-1])
            result["checks"].extend(payload.pop("checks"))
            result["runtime"] = payload
        if completed.returncode:
            result["checks"].append({"id": "probe_process", "status": "FAIL", "detail": "Nonzero process exit code"})
        result["status"] = "FAIL" if any(check["status"] == "FAIL" for check in result["checks"]) else "PASS"
        result["incompatibility_detected"] = any(check["status"] == "FAIL" and check["id"].startswith(("package:", "function:", "probe:")) for check in result["checks"])
        result["declared_compatible_alternatives"] = contract.get("compatible_alternatives", [])
        result["alternative_policy"] = "Alternatives require their own contract and actual probes; no automatic switch"
    except Exception as error:
        result["checks"].append({"id": "preflight_exception", "status": "FAIL", "detail": repr(error)})
        result["status"] = "FAIL"
    save_json(output_dir / "preflight.json", result)
    return result


def main():
    if len(sys.argv) != 3:
        print("Usage: python environment_preflight.py CONTRACT.json OUTPUT_DIR")
        return 2
    result = run_preflight(sys.argv[1], sys.argv[2])
    print(json.dumps({"status": result["status"], "path": str(Path(sys.argv[2]).resolve() / "preflight.json")}, ensure_ascii=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
