import unittest
import mujoco
from .model import physical_fingerprint
from .specs import ScenarioIntervention, ScenarioSpec


class ScenarioNativeTest(unittest.TestCase):
    def model(self):
        return mujoco.MjModel.from_xml_string(
            "<mujoco><worldbody>"
            '<geom name="floor" type="plane" size="1 1 .1" friction=".2 .02 .01" condim="3" priority="0"/>'
            '<body pos="0 0 .04"><freejoint/><geom name="foot" type="sphere" size=".05" '
            'friction=".8 .03 .02" condim="6" priority="1"/></body>'
            "</worldbody></mujoco>"
        )

    def state(self):
        m = self.model()
        d = mujoco.MjData(m)
        mujoco.mj_forward(m, d)
        self.assertEqual(d.ncon, 1)
        return m, d

    def test_effective_contact_semantics_respect_priority(self):
        m, d = self.state()
        spec = ScenarioSpec(
            "fixtures/contact.xml",
            "home",
            physical_fingerprint(m),
            (
                ScenarioIntervention(
                    ("floor", "foot"), "contact_friction", [0.8, 0.8, 0.03, 0.02, 0.02]
                ),
                ScenarioIntervention(("floor", "foot"), "contact_dim", 6),
            ),
        )
        self.assertTrue(spec.verify_model(m, d))

    def test_geom_edit_does_not_masquerade_as_effective_intervention(self):
        m, d = self.state()
        spec = ScenarioSpec(
            "fixtures/contact.xml",
            "home",
            interventions=(
                ScenarioIntervention(
                    ("floor", "foot"), "contact_friction", [0.2, 0.2, 0.02, 0.01, 0.01]
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "effective contact friction"):
            spec.verify_model(m, d)

    def test_intervention_requires_active_contact_data(self):
        m, _ = self.state()
        spec = ScenarioSpec(
            "fixtures/contact.xml",
            "home",
            interventions=(ScenarioIntervention(("floor", "foot"), "contact_dim", 6),),
        )
        with self.assertRaisesRegex(ValueError, "contact data required"):
            spec.verify_model(m)


if __name__ == "__main__":
    unittest.main()
