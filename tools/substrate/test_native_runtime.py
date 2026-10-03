import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock
from . import native_runtime
from .native_mjpc import NativeMJPCController
from .aligned_anchor import load_anchor
from .integrity import digest


class SealedNativeRuntimeTests(unittest.TestCase):
    def fixture(self, root):
        for name in (
            "controller",
            "loader",
            "task.xml",
            "canonical.xml",
            "lib/libc.so.6",
        ):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name)
        (root / "controller").chmod(0o700)
        value = {
            "schema": 1,
            "kind": "sealed-go2-native-runtime",
            "binary": "controller",
            "binary_sha256": digest(root / "controller"),
            "workers": 4,
            "loader": "loader",
            "task_xml": "task.xml",
            "canonical_xml": "canonical.xml",
            "library_dir": "lib",
            "libraries": {"libc.so.6": "lib/libc.so.6"},
            "files": {
                p.relative_to(root).as_posix(): digest(p)
                for p in root.rglob("*")
                if p.is_file()
            },
        }
        side = root / native_runtime.SIDECAR
        side.write_text(json.dumps(value))
        return root / "controller", side

    def test_missing_sidecar_fails_in_actual_controller_before_launch(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            binary, side = self.fixture(root)
            side.unlink()
            timing = load_anchor()["controllers"]["mjpc"]["timing"]
            with mock.patch(
                "tools.substrate.native_mjpc.NativeTransport",
                side_effect=AssertionError("native launched"),
            ):
                with self.assertRaises(FileNotFoundError):
                    NativeMJPCController(binary, timing, runtime_identity=side)

    def test_closure_validates_all_libraries_models_and_binary(self):
        with TemporaryDirectory() as temp:
            binary, side = self.fixture(Path(temp))
            self.assertEqual(native_runtime.verify(binary, side)["workers"], 4)
            (Path(temp) / "lib/libc.so.6").unlink()
            with self.assertRaises(ValueError):
                native_runtime.verify(binary, side)

    def test_resource_hash_drift_is_rejected(self):
        with TemporaryDirectory() as temp:
            binary, side = self.fixture(Path(temp))
            (Path(temp) / "task.xml").write_text("changed")
            with self.assertRaises(ValueError):
                native_runtime.verify(binary, side)

    def test_model_path_cannot_escape_package(self):
        with TemporaryDirectory() as temp:
            binary, side = self.fixture(Path(temp))
            value = json.loads(side.read_text())
            value["task_xml"] = "/etc/passwd"
            side.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                native_runtime.verify(binary, side)


if __name__ == "__main__":
    unittest.main()
