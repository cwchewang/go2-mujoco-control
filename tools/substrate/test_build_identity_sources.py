"""Generated sources and compiled dependency bytes are admission inputs."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from .build_identity import compilation_files


class CompilationIdentityTest(unittest.TestCase):
    def test_generated_translation_unit_and_actual_header_are_byte_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "generated.cc"
            header = root / "real_dependency.h"
            source.write_text("source-one")
            header.write_text("header-one")
            (root / "compile_commands.json").write_text(
                json.dumps([{"directory": str(root), "file": str(source)}])
            )
            with patch(
                "tools.substrate.build_identity.subprocess.check_output",
                return_value="object: #deps 1\n    " + str(header) + "\n",
            ):
                before = compilation_files(root)
                source.write_text("source-two")
                changed = compilation_files(root)
                self.assertNotEqual(
                    before["translation_units"], changed["translation_units"]
                )
                self.assertEqual(
                    before["actual_dependencies"], changed["actual_dependencies"]
                )
                header.write_text("header-two")
                self.assertNotEqual(
                    changed["actual_dependencies"],
                    compilation_files(root)["actual_dependencies"],
                )

    def test_planned_compiler_dependencies_handle_make_continuations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "generated/unit.cc"
            source.parent.mkdir()
            source.write_text("unit")
            header = root / "header.h"
            header.write_text("header")
            (root / "compile_commands.json").write_text(
                json.dumps(
                    [
                        {
                            "directory": str(root),
                            "file": str(source),
                            "arguments": [
                                "c++",
                                "-MD",
                                "-MF",
                                "unit.d",
                                "-o",
                                "unit.o",
                                "-c",
                                str(source),
                            ],
                        }
                    ]
                )
            )
            calls = []

            def output(argv, **kwargs):
                calls.append(argv)
                if argv[0] == "ninja":
                    return "object: #deps 1" + chr(10) + "    " + str(header)
                return (
                    "identity: "
                    + str(source)
                    + " "
                    + chr(92)
                    + chr(10)
                    + " "
                    + str(header)
                )

            with patch(
                "tools.substrate.build_identity.subprocess.check_output",
                side_effect=output,
            ):
                identity = compilation_files(root)
            self.assertIn(str(header), identity["planned_native_dependencies"])
            self.assertIn(str(source), identity["translation_units"])
            self.assertNotIn("-o", calls[0])
            self.assertNotIn("-MD", calls[0])

    def test_missing_dependency_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "compile_commands.json").write_text("[]")
            with patch(
                "tools.substrate.build_identity.subprocess.check_output",
                return_value="object:\n    missing.h\n",
            ):
                with self.assertRaises(FileNotFoundError):
                    compilation_files(root)


if __name__ == "__main__":
    unittest.main()
