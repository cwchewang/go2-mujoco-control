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
        ports = preflight.dds_ports(233)
        self.assertGreater(max(ports.values()), 65535)
        self.assertFalse(all(0 <= value <= 65535 for value in ports.values()))

    def test_domain_230_is_legal_and_linux_safe(self) -> None:
        ports = preflight.dds_ports(230)
        self.assertTrue(all(0 <= value <= 65535 for value in ports.values()))
        self.assertTrue(preflight.domain_in_linux_safe_pool(230))

    def test_linux_safe_pool_edges(self) -> None:
        self.assertTrue(preflight.domain_in_linux_safe_pool(0))
        self.assertTrue(preflight.domain_in_linux_safe_pool(101))
        self.assertFalse(preflight.domain_in_linux_safe_pool(102))
        self.assertFalse(preflight.domain_in_linux_safe_pool(214))
        self.assertTrue(preflight.domain_in_linux_safe_pool(215))
        self.assertTrue(preflight.domain_in_linux_safe_pool(232))
        self.assertFalse(preflight.domain_in_linux_safe_pool(233))

    def test_runner_domain_parser_reads_both_cli_forms(self) -> None:
        script = "run_trot.sh --domain-id 230\nother --domain-id=231\n"
        self.assertEqual(preflight.runner_domains(script), [230, 231])
        script = "domain_id=230\nrun_trot.sh --domain-id " + chr(36) + "domain_id\n"
        self.assertEqual(preflight.runner_domains(script), [230])

    def test_runner_domain_parser_ignores_comment_flags(self) -> None:
        script = "# --domain-id 233\nreal --domain-id 230 # --domain-id 231\n"
        self.assertEqual(preflight.runner_domains(script), [230])

    def test_process_matching_uses_argv_basenames_not_arbitrary_text(self) -> None:
        self.assertEqual(
            preflight.process_argv_matches(
                ["python3", "tools/research/preflight.py", "--require-file", "simulate/build/unitree_mujoco"],
                preflight.DEFAULT_PROCESS_NAMES,
            ),
            [],
        )
        self.assertEqual(
            preflight.process_argv_matches(
                ["/usr/bin/bash", "example/cpp/scripts/run_trot.sh", "80", "foo"],
                preflight.DEFAULT_PROCESS_NAMES,
            ),
            ["run_trot.sh"],
        )
        self.assertEqual(
            preflight.process_argv_matches(
                ["/tmp/build/unitree_mujoco", "-i", "230"],
                preflight.DEFAULT_PROCESS_NAMES,
            ),
            ["unitree_mujoco"],
        )
        self.assertEqual(
            preflight.process_argv_matches(
                ["/usr/bin/bash", "-lc", "exec simulate/build/unitree_mujoco -i 230"],
                preflight.DEFAULT_PROCESS_NAMES,
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
