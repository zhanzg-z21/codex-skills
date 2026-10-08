# Execution contract and verification

Create the contract before writing analysis code. It specifies the intended quantity, actual delivery requirements, input fields, runtime and checks. A completed process is one layer of evidence. It does not establish a correct estimand, complete outputs or clinical validation.

## Files and path rules

Use `execution_contract.json`, `provenance.json`, `run_record.json`, `preflight/preflight.json` and `validation/execution_manifest.json` inside a case workspace. A relative `workspace` resolves from the contract file directory. All data, artifact, evidence, preflight, provenance and log paths resolve from that workspace and must remain inside it. Runtime executables may be outside the workspace. Both command output directories are explicitly chosen by the caller. The scripts write reports and probe files there; they never install packages, change system locales or repair packages.

Keep a separate directory and a new contract for an alternative implementation. Preserve original failed attempts. If a compatible implementation exists, inspect and probe it before using it. Do not silently replace the model, covariance estimator, target population or promised outputs.

## Contract structure

The following is an interface example. Replace every example field with the actual task definition before execution. All eight output categories must be present. An empty array means the category is not required. A listed artifact is promised and is checked even when optional. Mark every artifact with `required` and `core`; core artifacts must also be required. Include at least one core artifact.

```json
{
  "schema_version": 1,
  "workspace": ".",
  "analysis_goal": "Fit and deliver the specified analysis",
  "estimand": "State target population, outcome, contrast, scale, time and handling of relevant events",
  "language": {"name": "R", "executable": "C:/Program Files/R/R-4.3.0/bin/Rscript.exe"},
  "required_packages": [{"name": "lme4"}],
  "required_data_fields": {"inputs.csv": ["id", "outcome", "exposure"]},
  "critical_functions": [{"package": "lme4", "name": "lmer"}],
  "critical_probes": [{"id": "fit_and_summary", "required": true, "code": "m <- lme4::lmer(Reaction ~ Days + (1|Subject), lme4::sleepstudy); capture.output(summary(m))"}],
  "environment": {"env": {"LC_ALL": "English_United States.utf8", "LANG": "English_United States.utf8"}},
  "provenance_path": "provenance.json",
  "expected_outputs": {
    "model_object": [{"id": "fit", "path": "outputs/fit.rds", "required": true, "core": true, "kind": "rds", "assertions": [{"type": "execution_evidence", "evidence_path": "outputs/checks.json", "check_id": "model_readable_and_converged"}]}],
    "estimate": [],
    "confidence_interval": [{"id": "contrast", "path": "outputs/contrast.csv", "required": true, "core": true, "kind": "csv", "assertions": [{"type": "csv_rows", "min": 1}, {"type": "csv_columns", "columns": ["estimate", "lower", "upper"]}, {"type": "csv_no_na", "columns": ["estimate", "lower", "upper"]}, {"type": "csv_ci", "estimate": "estimate", "lower": "lower", "upper": "upper"}]}],
    "diagnostics": [],
    "sensitivity_analysis": [],
    "table": [],
    "figure": [],
    "exported_files": []
  },
  "success_criteria": ["All core required artifacts pass and all five layers are verified"]
}
```

The example does not imply that diagnostics or figures are dispensable for a particular study. Populate every promised category. One file can support several categories with different artifact IDs and assertions. A figure promise includes both a readable graphic and an explicit check that it represents the intended quantity. If the task promises a standardized contrast, CI, curve and final image, fitting a model alone cannot satisfy the contract.

Package `version` is an optional exact match, not a compatibility blacklist. Python package records can include `import_name` when the import name differs from the distribution name. `critical_probes` must exercise the operations the delivered code actually needs, including printing, prediction, contrasts and export where relevant. A function-existence check alone does not demonstrate dependency compatibility. Do not require a summary-printing probe when the implementation only needs fitting and prediction.

## Preflight

```text
python environment_preflight.py execution_contract.json preflight
```

The preflight runs the chosen executable in the contract workspace, records package versions, function availability, actual critical calls, locale, encoding, working directory, input paths and input column names. For R it records `R.version.string`, `Sys.getlocale()`, `.libPaths()` and `sessionInfo()`. Input CSVs are read in Python and their paths and headers are probed in the actual R process, which exposes runtime-specific path problems. The process environment inherits the caller's environment; contract `environment.env` applies recorded process-only overrides. Setting these values does not modify system configuration.

`preflight.json` reports `PASS` or `FAIL`. A required probe failure blocks the declared implementation. Optional probes use `required: false` and report `WARNING`. A failed probe process or malformed contract also returns a failed report. The script records alternatives supplied in `compatible_alternatives` but does not choose them automatically. Compatibility is limited to the declared probes, not every possible package operation.

The local development check actually exposed the `reformulas::format_sdvar` missing-function failure in the installed environment. A separate fitting and prediction probe succeeded. This is evidence about the operations tested, not a prohibition on every use of that package.

## Evidence from the actual run

The executor saves a process log, an execution record and specific assertion results from the produced model and outputs. An example assertion file is:

```json
{
  "checks": [
    {"id": "model_readable_and_converged", "passed": true, "rationale": "The saved model was read, its class checked and its applicable convergence diagnostics inspected"},
    {"id": "formula_matches_contract", "passed": true, "rationale": "Actual terms, response, family and random effects were checked"},
    {"id": "target_contrast_matches", "passed": true, "rationale": "The actual contrast, target rows, weights and covariance calculation were checked"}
  ]
}
```

These are example keys, not evidence of an execution. Generate the booleans from the actual fit. Do not write unconditional `true` values or use a file-size check to stand in for model readability. A model-convergence check must inspect the model's applicable diagnostics. A target check should inspect the actual design matrix, contrast, standardization weights and covariance, as appropriate to the contract.

```json
{
  "execution": {"started": true, "completed": true, "exit_code": 0, "log_path": "analysis.log"},
  "preflight_path": "preflight/preflight.json",
  "provenance_gate_path": "provenance_gate.json",
  "statistical_specification": {"status": "PASS", "verification": "programmatic", "evidence_path": "outputs/checks.json", "check_ids": ["formula_matches_contract"], "rationale": "Actual fitted specification checked"},
  "estimand_consistency": {"status": "PASS", "verification": "programmatic", "evidence_path": "outputs/checks.json", "check_ids": ["target_contrast_matches"], "rationale": "Actual estimated quantity checked"}
}
```

`programmatic` requires an existing JSON evidence file and named checks whose `passed` value is the boolean `true`. The manifest labels this as execution-side evidence; it is not independent proof of semantic truth. `internal_model_review` and `human_review` instead require `reviewer`, a nonempty readable `evidence_path`, and `rationale`. Internal model review must not be labeled human review. A human or model review can supply a separately documented semantic judgment, but neither is reclassified as a machine assertion. Bare `status: PASS` without traceable evidence remains `PARTIAL`.

If execution is blocked, record `started: false`, `completed: false`, `exit_code: null` and the blocking reason. Still run the validator and retain its manifest. Do not create empty placeholder artifacts to satisfy promises.

## Output assertions

`execution_validate.py` checks each promised artifact using only `PASS`, `PARTIAL`, `FAIL` or `NOT_REQUIRED`. Artifact kinds are `csv`, `png`, `svg`, `pdf`, `json`, `text`, `rds`, `model` and `binary`.

Supported assertions include `nonempty`; `csv_rows` with `min` and optional `max`; `csv_columns` with `columns`; `csv_no_na` with optional columns and missing tokens; `csv_ci` with lower, upper and optional estimate column names; `csv_numeric` with columns and optional bounds; `csv_unique` with key columns; `png`; `svg`; `pdf`; `json` with required keys; `text_contains` with strings; and `execution_evidence` with an evidence path and check ID. Unknown assertions fail rather than being ignored.

CSV checks parse actual records, reject inconsistent row widths, and inspect declared columns, missing values, finite numeric limits and CI order. `csv_ci` checks that an estimate falls between its limits by default. Set `estimate_within: false` when that property is not appropriate for the specified interval, and document why. Interval structure does not establish correct confidence coverage or the correct contrast; those belong to separate checks.

PNG checks inspect all chunk CRCs, decompress the complete image stream and verify scanline lengths and filters. SVG checks parse XML and require drawing elements. PDF checks require a complete envelope and parse every page and content stream with an already available `pypdf`. If that optional parser is unavailable, PDF readability is `PARTIAL`, not inferred from a signature. None of these mechanical checks proves that a plot shows the requested scientific quantity. Every figure therefore also needs an execution-side target check or `run_record.artifact_evidence[artifact_id]` using the same evidence schema. Opaque model files require an execution-side read or object assertion.

## Five layers and completion claims

```text
python execution_validate.py execution_contract.json validation run_record.json
```

The manifest separates `execution`, `statistical_specification`, `estimand_consistency`, `output_completeness` and `artifact_integrity`. Output completeness describes required files being present. Integrity evaluates actual readability, assertions and labeled target evidence. Both must be reported. Process success must not be presented as a single overall code pass rate.

`analysis completed` requires all five layers to pass, all core required outputs to pass, a passing preflight, and a present, passing and approved provenance gate. The manifest also reports whether all promised artifacts passed, including optional artifacts. A successfully finished process with unmet delivery conditions is `analysis partially executed`. An absent or failed execution is `execution failed`. Validation exceptions still create a manifest and cannot generate a completion claim. Nonzero CLI exit means the declared analysis was not certified complete; it does not by itself distinguish a blocked runtime from an artifact or semantic failure.

Completion never authorizes a clinical-validation claim. The manifest retains the provenance declaration and its gate result, permitted claims, and whether data qualify for the bounded real-patient test. Simulated data can support an approved technical execution test while all clinical claims remain prohibited. Missing provenance prevents a completed designation.
