import copy
import unittest
from .mjpc_diagnostic import ROOT, load_plan, model_audit, validate_budget_record


class DiagnosticTests(unittest.TestCase):
    def value(self, calls=1):
        return dict(
            policy_id=calls,
            private_step_upper_bound_reserved=calls * 4096,
            private_step_limit=614400,
            rollout_mj_step_count=700 * calls,
            fd_step_upper_bound_count=1801 * calls,
            fd_call_count=37 * calls,
        )

    def test_budget_covers_fd_and_rollouts(self):
        validate_budget_record(self.value(), 0)
        v = self.value(150)
        validate_budget_record(v, 1499)
        v["fd_step_upper_bound_count"] = 614401
        with self.assertRaises(ValueError):
            validate_budget_record(v, 1499)

    def test_feedback_cannot_integrate_or_change_policy(self):
        previous = self.value()
        validate_budget_record(previous, 1, previous)
        for key in (
            "rollout_mj_step_count",
            "fd_step_upper_bound_count",
            "fd_call_count",
        ):
            v = copy.deepcopy(previous)
            v[key] += 1
            with self.assertRaises(ValueError):
                validate_budget_record(v, 1, previous)

    def test_missing_bool_regressed_accounting_rejected(self):
        for key in self.value():
            v = self.value()
            v[key] = True
            with self.assertRaises(ValueError):
                validate_budget_record(v, 0)
        v = self.value()
        v.pop("fd_call_count")
        with self.assertRaises(ValueError):
            validate_budget_record(v, 0)

    def test_two_protocols_have_separate_single_attempt_ownership(self):
        values = [
            load_plan(
                ROOT
                / "tools/substrate/protocols"
                / ("mjpc-adaptation-" + m + "-3s-v1.json")
            )
            for m in ("original", "corrected")
        ]
        self.assertNotEqual(values[0]["raw"]["id"], values[1]["raw"]["id"])
        for p in values:
            self.assertEqual(p["task"].horizon_ticks, 1500)
            self.assertEqual(p["raw"]["scientific_attempts_max"], 1)

    def test_named_joint_and_unnamed_collision_mapping(self):
        v = model_audit()
        self.assertEqual(len(v["joint_map"]), 12)
        self.assertEqual(len(v["collision_map"]), 23)
        self.assertEqual(len({r["canonical_geom"] for r in v["collision_map"]}), 23)
        self.assertNotEqual(*v["optimization_models"].values())
        self.assertEqual(v["canonical_integration_steps"], 0)


if __name__ == "__main__":
    unittest.main()
