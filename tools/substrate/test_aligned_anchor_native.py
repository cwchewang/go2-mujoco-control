import unittest

import mujoco

from .aligned_anchor import load_anchor, validate_canonical_model


class AlignedAnchorNativeTest(unittest.TestCase):
    def test_compiled_canonical_scene_identity(self):
        anchor = load_anchor()
        model = mujoco.MjModel.from_xml_path(anchor["scenario"].scene)
        self.assertTrue(validate_canonical_model(anchor, model))


if __name__ == "__main__":
    unittest.main()
