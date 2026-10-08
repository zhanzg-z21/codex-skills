"""Development controls for provenance claims and attribution state transitions."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from provenance_gate import evaluate as provenance
from semantic_attribution import evaluate as attribution


class GateControls(unittest.TestCase):
    def setUp(self):
        self.data = dict(dataset_id="simulation_control", source="fixed-seed simulation",
                         source_file="data.csv", real_or_simulated="SIMULATED", patient_level=True,
                         derived_or_raw="derived", creation_history="Generated solely for technical testing",
                         known_transformations=[], verification_status="SIMULATED", patient_id_available=True,
                         source_population_known=False, analysis_approved=True)
        self.row = dict(rule_id="HARD_missing_structure", trigger_text="未知缺失模式就机械MI",
                        matched_condition="仅审查给定片段", rule_scope="缺失结构不明时的机械MI选择",
                        current_case_condition="本题只需静态审查", semantic_match="NO",
                        attribution_confidence="HIGH", case_quote="请审查现有代码，不运行模型。",
                        reason="当前任务并非选择唯一插补模型", requested_action="CONDITIONAL_CHECK",
                        used_as_basis=False)
        self.case = self.row["case_quote"]

    def attr(self, row):
        return attribution({"case_id": "control", "review_type": "internal_model_review", "attributions": [row]}, ROOT, self.case)

    def test_simulation_can_be_technical(self):
        out = provenance(self.data)
        self.assertEqual(out["gate_status"], "PASS")
        self.assertFalse(out["real_patient_test_eligible"])

    def test_simulation_cannot_be_real(self):
        self.data["requested_claim"] = "real patient validation"
        self.assertEqual(provenance(self.data)["gate_status"], "FAIL")

    def test_unverified_cannot_be_real(self):
        self.data.update(real_or_simulated="UNKNOWN", verification_status="UNVERIFIED", requested_claim="real-world code validation")
        self.assertEqual(provenance(self.data)["gate_status"], "FAIL")

    def test_inconsistent_relabeling_rejected(self):
        self.data["verification_status"] = "VERIFIED_FOR_TESTING"
        self.assertEqual(provenance(self.data)["record_status"], "FAIL")

    def test_no_match_excluded_without_blocking_static_review(self):
        out = self.attr(self.row)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["accepted_rule_ids"], [])
        self.assertFalse(out["hard_stop_triggered"])

    def test_existing_id_does_not_allow_wrong_basis(self):
        self.row.update(used_as_basis=True, requested_action="HARD_STOP")
        self.assertEqual(self.attr(self.row)["status"], "FAIL")

    def test_partial_needs_limit(self):
        self.row.update(semantic_match="PARTIAL", used_as_basis=True)
        self.assertEqual(self.attr(self.row)["status"], "FAIL")
        self.row["limitations"] = "仅支持检查缺失结构，不能推定当前已经机械MI"
        self.assertEqual(self.attr(self.row)["status"], "PASS")

    def test_hard_stop_requires_both_conditions(self):
        self.case = "不知道缺失模式和模型，请直接指定唯一MI方案。"
        self.row.update(case_quote=self.case, current_case_condition=self.case,
                        semantic_match="YES", used_as_basis=True, trigger_matched=True,
                        critical_information_missing=False, missing_information="缺失结构和分析模型",
                        decision_impact="影响插补模型选择", requested_action="HARD_STOP")
        self.assertEqual(self.attr(self.row)["status"], "FAIL")
        self.row["critical_information_missing"] = True
        self.assertTrue(self.attr(self.row)["hard_stop_triggered"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
