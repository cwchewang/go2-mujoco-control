import unittest
import mujoco
from .model import physical_fingerprint
from .specs import ScenarioIntervention, ScenarioSpec


class ScenarioNativeTest(unittest.TestCase):
    def model(self):
        return mujoco.MjModel.from_xml_string(
            '<mujoco><worldbody><geom name="floor" type="plane" size="1 1 .1" '
            'friction=".7 .02 .01" condim="3"/></worldbody></mujoco>'
        )

    def test_compiled_intervention_and_fingerprint(self):
        m = self.model()
        spec = ScenarioSpec(
            "fixtures/floor.xml",
            "home",
            physical_fingerprint(m),
            (
                ScenarioIntervention("floor", "friction", [0.7, 0.02, 0.01]),
                ScenarioIntervention("floor", "condim", 3),
            ),
        )
        self.assertTrue(spec.verify_model(m))
        m.geom_friction[0, 0] = 0.4
        with self.assertRaisesRegex(ValueError, "physical fingerprint"):
            spec.verify_model(m)

    def test_intervention_mismatch_fails_without_source_xml_trust(self):
        m = self.model()
        spec = ScenarioSpec(
            "fixtures/floor.xml",
            "home",
            interventions=(
                ScenarioIntervention("floor", "friction", [0.2, 0.02, 0.01]),
            ),
        )
        with self.assertRaisesRegex(ValueError, "compiled friction"):
            spec.verify_model(m)


if __name__ == "__main__":
    unittest.main()
