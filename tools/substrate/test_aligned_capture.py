import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from .aligned_capture import (
    capture,
    load_capture_plan,
    prepare,
    validate_capture_plan,
    validate_external_start,
)
from .integrity import digest, verify_bundle


class AlignedCaptureTest(unittest.TestCase):
    def test_plan_is_self_unauthorized_and_bounded(self):
        plan = load_capture_plan()
        raw = plan["raw"]
        self.assertFalse(raw["self_authorizes_physics"])
        self.assertEqual(raw["self_authorized_scientific_attempts"], 0)
        self.assertEqual(raw["capture_order"], ["rl", "mjpc"])
        self.assertEqual(raw["planned_attempts_per_controller"], 1)
        self.assertEqual(raw["max_attempts"], 2)

    def test_plan_authorization_or_attempt_drift_fails_closed(self):
        plan = load_capture_plan()
        for key, value in (
            ("self_authorizes_physics", True),
            ("self_authorized_scientific_attempts", 2),
            ("max_attempts", 3),
        ):
            raw = copy.deepcopy(plan["raw"])
            raw[key] = value
            with self.assertRaises(ValueError):
                validate_capture_plan(raw)

    def test_external_start_requires_distinct_exact_head_reviews_and_user_record(self):
        head = "a" * 40
        manifest = "b" * 64
        protocol = "c" * 64
        prepared = {
            "readiness": "AWAITING_EXACT_HEAD_REVIEWS_AND_USER_START",
            "head": head,
            "protocol_sha256": protocol,
            "max_attempts": 2,
        }
        review = {
            "head": head,
            "science": {
                "verdict": "APPROVED",
                "reviewer": "science-reviewer",
                "evidence": "science.md",
            },
            "execution": {
                "verdict": "APPROVED",
                "reviewer": "execution-reviewer",
                "evidence": "execution.md",
            },
        }
        auth = {
            "action": "START_FORMAL_CAPTURE",
            "head": head,
            "protocol_sha256": protocol,
            "prepared_manifest_sha256": manifest,
            "max_attempts": 2,
            "authorized_by": "user",
            "user_instruction": "start capture",
        }
        self.assertTrue(validate_external_start(prepared, review, auth, head, manifest))
        bad = copy.deepcopy(review)
        bad["execution"]["reviewer"] = "science-reviewer"
        with self.assertRaisesRegex(ValueError, "reviewers must differ"):
            validate_external_start(prepared, bad, auth, head, manifest)
        bad = copy.deepcopy(auth)
        bad["authorized_by"] = "assistant"
        with self.assertRaisesRegex(ValueError, "actual user instruction"):
            validate_external_start(prepared, review, bad, head, manifest)

    def test_prepare_seals_zero_step_identity_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "prepared"
            lock = Path(temp) / "experiment.lock"
            with (
                mock.patch("tools.substrate.integrity.LOCK_PATH", lock),
                mock.patch(
                    "tools.substrate.aligned_capture.current_head",
                    return_value="d" * 40,
                ),
            ):
                result = prepare(output)
            self.assertEqual(result["physics_steps"], 0)
            self.assertEqual(result["scientific_attempts"], 0)
            admitted = verify_bundle(output)
            self.assertEqual(admitted["max_attempts"], 2)
            self.assertEqual(admitted["planned_arms"], ["rl", "mjpc"])
            self.assertEqual(admitted["physics_steps"], 0)
            self.assertEqual(admitted["scientific_attempts"], 0)
            self.assertEqual(
                admitted["protocol_sha256"],
                digest(Path("tools/substrate/protocols/aligned_flat_capture_v1.json")),
            )

    def test_invalid_review_blocks_capture_before_plant_creation(self):
        head = "d" * 40
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prepared_dir = root / "prepared"
            with mock.patch(
                "tools.substrate.aligned_capture.current_head", return_value=head
            ):
                prepare(prepared_dir)

            prepared = verify_bundle(prepared_dir)
            manifest = digest(prepared_dir / "manifest.json")
            review = {
                "head": head,
                "science": {"verdict": "APPROVED", "reviewer": "same", "evidence": "s"},
                "execution": {
                    "verdict": "APPROVED",
                    "reviewer": "same",
                    "evidence": "e",
                },
            }
            auth = {
                "action": "START_FORMAL_CAPTURE",
                "head": head,
                "protocol_sha256": prepared["protocol_sha256"],
                "prepared_manifest_sha256": manifest,
                "max_attempts": 2,
                "authorized_by": "user",
                "user_instruction": "start capture",
            }
            review_path = root / "review.json"
            review_path.write_text(__import__("json").dumps(review))
            auth_path = root / "auth.json"
            auth_path.write_text(__import__("json").dumps(auth))
            with (
                mock.patch(
                    "tools.substrate.aligned_capture.current_head", return_value=head
                ),
                mock.patch(
                    "tools.substrate.aligned_capture.MujocoPlant",
                    side_effect=AssertionError("plant created before review gate"),
                ),
            ):
                with self.assertRaisesRegex(ValueError, "reviewers must differ"):
                    capture(prepared_dir, review_path, auth_path, root / "unused")


if __name__ == "__main__":
    unittest.main()
