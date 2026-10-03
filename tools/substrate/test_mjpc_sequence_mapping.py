"""No-native checks against the production named-state packet contract."""

import unittest

from tools.substrate import fd_duplicate_diagnostic as d
from tools.substrate import mjpc_short_sequence as sequence
from tools.substrate.contracts import MOTOR_JOINTS
from tools.substrate.native_mjpc import step_packet


class SequenceMappingTests(unittest.TestCase):
    def test_asymmetric_canonical_state_is_permuted_for_native(self):
        anchor = {
            "time_s": 0.02,
            "command": [0.0, 0.0, 0.0],
            "qpos": [1.0, 2.0, 3.0, 1.0, 0.0, 0.0, 0.0, *range(12)],
            "qvel": [101.0, 102.0, 103.0, 104.0, 105.0, 106.0, *range(20, 32)],
        }
        state = sequence.canonical_state(anchor)
        packet = step_packet(state, anchor["command"], MOTOR_JOINTS, replan=True)
        values = [float(x) for x in packet.split()[2:]]
        order = [3, 4, 5, 0, 1, 2, 9, 10, 11, 6, 7, 8]
        self.assertEqual(values[4:11], anchor["qpos"][:7])
        self.assertEqual(values[11:23], [float(i) for i in order])
        self.assertEqual(values[23:29], anchor["qvel"][:6])
        self.assertEqual(values[29:], [float(20 + i) for i in order])
        self.assertNotEqual(packet, d._packet(anchor))

    def test_all_sealed_external_rows_match_production_wire_encoder(self):
        if not d.CAPTURE.exists():
            self.skipTest("sealed Atlas source is absent")
        rows = sequence.load_sequence(d.CAPTURE)["inputs"]
        for row in rows:
            state = sequence.canonical_state(row)
            packet = step_packet(
                state, row["command"], MOTOR_JOINTS, replan=row["replan"]
            )
            values = [float(x) for x in packet.split()[2:]]
            self.assertEqual(values[:4], [row["time_s"], *row["command"]])
            self.assertEqual(values[4:23], state.qpos(MOTOR_JOINTS).tolist())
            self.assertEqual(values[23:], state.qvel(MOTOR_JOINTS).tolist())
        self.assertNotEqual(
            d._packet(rows[1], replan=False),
            step_packet(
                sequence.canonical_state(rows[1]),
                rows[1]["command"],
                MOTOR_JOINTS,
                replan=False,
            ),
        )

    def test_prediction_validator_rejects_legacy_wrong_order_anchor(self):
        path = (
            d.ROOT
            / "_runs/mjpc_short_sequence_observation_launcherfix_20261003/trials/original_repeat1"
        )
        if not path.exists():
            self.skipTest("historical sequence source is absent")
        row = sequence.load_sequence(d.CAPTURE)["inputs"][10]
        state = sequence.canonical_state(row)
        anchor = {
            **row,
            "qpos": state.qpos(MOTOR_JOINTS).tolist(),
            "qvel": state.qvel(MOTOR_JOINTS).tolist(),
        }
        with self.assertRaisesRegex(ValueError, "candidate initial state"):
            sequence._validate_replan_output(path, "original", 2, anchor)
