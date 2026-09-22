#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).with_name("preflight.py")
SPEC = importlib.util.spec_from_file_location("research_preflight", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


class PreflightRegressionTest(unittest.TestCase):
    def test_domain_233_exceeds_rtps_udp_range(self) -> None:
        self.assertGreater(max(preflight.dds_ports(233).values()), 65535)
        self.assertFalse(preflight.domain_in_linux_safe_pool(233))

    def test_domain_230_is_legal_and_linux_safe(self) -> None:
        self.assertTrue(
            all(0 <= value <= 65535 for value in preflight.dds_ports(230).values())
        )
        self.assertTrue(preflight.domain_in_linux_safe_pool(230))

    def test_linux_safe_pool_edges(self) -> None:
        self.assertTrue(preflight.domain_in_linux_safe_pool(0))
        self.assertTrue(preflight.domain_in_linux_safe_pool(101))
        self.assertFalse(preflight.domain_in_linux_safe_pool(102))
        self.assertFalse(preflight.domain_in_linux_safe_pool(214))
        self.assertTrue(preflight.domain_in_linux_safe_pool(215))
        self.assertTrue(preflight.domain_in_linux_safe_pool(232))

    def test_runner_domain_parser(self) -> None:
        self.assertEqual(preflight.runner_domains("run --domain-id 230\n"), [230])
        self.assertEqual(
            preflight.runner_domains("domain_id=230\nrun --domain-id $domain_id\n"),
            [230],
        )
        self.assertEqual(
            preflight.runner_domains(
                "domain_id=229\n"
                "domain_id=230\n"
                "run --domain-id " + chr(36) + "domain_id\n"
            ),
            [],
        )
        self.assertEqual(
            preflight.runner_domains(
                "# --domain-id 233\nrun --domain-id=230 # ignored\n"
            ),
            [230],
        )

    def test_process_matching_uses_real_executable_or_script(self) -> None:
        self.assertEqual(
            preflight.process_argv_matches(
                ["python3", "preflight.py", "unitree_mujoco"],
                preflight.DEFAULT_PROCESS_NAMES,
            ),
            [],
        )
        self.assertEqual(
            preflight.process_argv_matches(
                ["/usr/bin/bash", "example/cpp/scripts/run_trot.sh", "80"],
                preflight.DEFAULT_PROCESS_NAMES,
            ),
            ["run_trot.sh"],
        )
        self.assertEqual(
            preflight.process_argv_matches(
                ["/usr/bin/bash", "-lc", "exec unitree_mujoco"],
                preflight.DEFAULT_PROCESS_NAMES,
            ),
            [],
        )

    def test_analyzer_changes_require_a_no_live_test(self) -> None:
        self.assertIn("analyzer", preflight.AUTO_TEST_SURFACES)

    def test_changed_surface_inference(self) -> None:
        paths = [
            "example/cpp/gait/cartesian_world_trot.h",
            "example/cpp/scripts/run_x.sh",
            "example/cpp/trot/trot_experiment_diagnostics.cpp",
            "example/cpp/tools/analysis/analyze_x.py",
            "unitree_robots/go2/scene.xml",
            "docs/research/TASK_X.md",
        ]
        self.assertEqual(
            preflight.infer_changed_surfaces(paths),
            {"runtime", "runner", "schema", "analyzer", "scene"},
        )

    def test_logger_schema_file_not_double_counted_as_runtime(self) -> None:
        self.assertEqual(
            preflight.infer_changed_surfaces(
                ["example/cpp/trot/trot_experiment_diagnostics.cpp"]
            ),
            {"schema"},
        )


if __name__ == "__main__":
    unittest.main()
