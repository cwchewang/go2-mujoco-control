import unittest
from unittest.mock import patch

from .native.patch_mjpc_utilities import EXPECTED_SHA256, NEW, OLD, hardened_text


class MJPCPatchTest(unittest.TestCase):
    def test_exact_block_replacement_preserves_surrounding_source(self):
        source = ("before\n" + OLD + "after\n").encode()
        with patch("tools.substrate.native.patch_mjpc_utilities.hashlib.sha256") as sha:
            sha.return_value.hexdigest.return_value = EXPECTED_SHA256
            self.assertEqual(hardened_text(source), "before\n" + NEW + "after\n")

    def test_missing_or_duplicate_ground_block_fails_closed(self):
        with patch("tools.substrate.native.patch_mjpc_utilities.hashlib.sha256") as sha:
            sha.return_value.hexdigest.return_value = EXPECTED_SHA256
            for source in (b"missing", (OLD + OLD).encode()):
                with self.assertRaisesRegex(ValueError, "exactly once"):
                    hardened_text(source)

    def test_patch_contract_is_narrow_and_source_locked(self):
        self.assertEqual(
            EXPECTED_SHA256,
            "1924b6cea946cbac517abc1808e9433ddc8c1a390aee5e5c570d5aeab8fbd118",
        )
        self.assertIn('mju_error("no group 0 geom detected by raycast")', OLD)
        self.assertIn("mjWARN_BADQPOS", NEW)
        self.assertIn("Trajectory::CheckWarnings", NEW)
        self.assertNotIn("mju_error", NEW)
        with self.assertRaisesRegex(ValueError, "identity drifted"):
            hardened_text(b"not the pinned source")


if __name__ == "__main__":
    unittest.main()
