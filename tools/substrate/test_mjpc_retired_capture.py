import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.substrate import mjpc_diagnostic_capture as capture_module


class RetiredCaptureTests(unittest.TestCase):
    def test_empty_worktree_cannot_reopen_either_retired_scope(self):
        for mode in ("original", "corrected"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                task_id = "mjpc-adaptation-" + mode + "-3s-v1"
                with (
                    patch.object(capture_module, "ROOT", root),
                    patch.object(
                        capture_module,
                        "experiment_lock",
                        return_value=contextlib.nullcontext(),
                    ),
                    patch.object(
                        capture_module,
                        "verify_bundle",
                        return_value={"task_id": task_id},
                    ),
                    patch.object(capture_module.spec, "load_plan") as plan,
                    patch.object(capture_module, "identity") as identity,
                    patch.object(capture_module, "NativeMJPCController") as native,
                ):
                    with self.assertRaisesRegex(ValueError, "permanently closed"):
                        capture_module.capture(
                            root / "prepared",
                            root / "review",
                            root / "start",
                            root / "out",
                        )
                    plan.assert_not_called()
                    identity.assert_not_called()
                    native.assert_not_called()
                    self.assertEqual(list(root.iterdir()), [])
