import unittest

import mujoco

from .aligned_anchor import (
    load_anchor,
    validate_canonical_model,
    validate_canonical_reset,
)


class AlignedAnchorNativeTest(unittest.TestCase):
    def test_compiled_canonical_scene_identity(self):
        anchor = load_anchor()
        model = mujoco.MjModel.from_xml_path(anchor["scenario"].scene)
        self.assertTrue(validate_canonical_model(anchor, model))

    def test_home_heading_is_explicitly_locked_to_world_x(self):
        anchor = load_anchor()
        model = mujoco.MjModel.from_xml_path(anchor["scenario"].scene)
        self.assertTrue(validate_canonical_reset(model))
        model.key_qpos[0, 3:7] = [2**-0.5, 0.0, 0.0, 2**-0.5]
        with self.assertRaisesRegex(ValueError, "world \\+x"):
            validate_canonical_reset(model)


if __name__ == "__main__":
    unittest.main()
