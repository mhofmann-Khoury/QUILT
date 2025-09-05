from unittest import TestCase

from resources.load_ks_resources import load_test_knitscript_to_knitout_to_dat

from quilt_knit.quilt.Quilt import Quilt
from quilt_knit.swatch.Swatch import Swatch


class TestQuilt(TestCase):

    @staticmethod
    def _swatch(ks: str, swatch_name: str, **python_vars) -> Swatch:
        swatch_k = load_test_knitscript_to_knitout_to_dat(f"{ks}.ks", f"{ks}.k", f"{ks}.dat", **python_vars)
        return Swatch(swatch_name, swatch_k)

    @staticmethod
    def _quad_quilt(left_bottom_ks: str, right_bottom_ks: str, left_top_ks: str, right_top_ks: str, **python_vars) -> Quilt:
        left_bottom = TestQuilt._swatch(left_bottom_ks, "left bottom", **python_vars)
        right_bottom = TestQuilt._swatch(right_bottom_ks, "right bottom", **python_vars)
        left_top = TestQuilt._swatch(left_top_ks, "left top", **python_vars)
        right_top = TestQuilt._swatch(right_top_ks, "right top", **python_vars)
        quilt = Quilt()
        quilt.connect_swatches_wale_wise(left_bottom, left_top)
        quilt.connect_swatches_wale_wise(right_bottom, right_top)
        quilt.connect_swatches_course_wise(left_bottom, right_bottom)
        quilt.connect_swatches_course_wise(left_top, right_top)
        return quilt

    def test_jersey_quad_quilt(self):
        quilt = self._quad_quilt("jersey", "jersey", "jersey", "jersey", c=1, width=4, height=2)
        # quilt.print_bottom_up_leftward_traversal()
        swatches = quilt.merge_quilt()
        self.assertEqual(len(swatches), 1)
        for swatch in swatches:
            swatch.compile_to_dat('jersey_merge')
            self.assertEqual(len(swatch.carriage_passes), 6)
            self.assertEqual(len(swatch.knitout_program), 53)

    def test_rib_quad_quilt(self):
        quilt = self._quad_quilt("rib", "rib", "rib", "rib", c=1, width=4, height=2)
        # quilt.print_bottom_up_leftward_traversal()
        swatches = quilt.merge_quilt()
        self.assertEqual(len(swatches), 1)
        for swatch in swatches:
            swatch.compile_to_dat('rib_merge')
            self.assertEqual(len(swatch.carriage_passes), 7)
            self.assertEqual(len(swatch.knitout_program), 57)

    def test_seed_quad_quilt(self):
        quilt = self._quad_quilt("seed", "seed", "seed", "seed", c=1, width=4, height=2)
        # quilt.print_bottom_up_leftward_traversal()
        swatches = quilt.merge_quilt()
        self.assertEqual(len(swatches), 1)
        for swatch in swatches:
            swatch.compile_to_dat('seed_merge')
            self.assertEqual(len(swatch.carriage_passes), 10)
            self.assertEqual(len(swatch.knitout_program), 81)

    def test_lace_quad_quilt(self):
        quilt = self._quad_quilt("lace", "left_lace", "right_lace", "lace", c=1, width=7, height=4)
        # quilt.print_bottom_up_leftward_traversal()
        swatches = quilt.merge_quilt()
        self.assertEqual(len(swatches), 1)
        for swatch in swatches:
            swatch.compile_to_dat('lace_merge')
            self.assertEqual(len(swatch.carriage_passes), 30)
            self.assertEqual(len(swatch.knitout_program), 189)

    def test_cable_quad_quilt(self):
        quilt = self._quad_quilt("cable", "left_cable", "right_cable", "cable", c=1, width=7, height=2)
        # quilt.print_bottom_up_leftward_traversal()
        swatches = quilt.merge_quilt()
        self.assertEqual(len(swatches), 1)
        for swatch in swatches:
            swatch.compile_to_dat('cable_merge')
            self.assertEqual(len(swatch.carriage_passes), 17)
            self.assertEqual(len(swatch.knitout_program), 126)

    def test_jacquard_quad_quilt(self):
        quilt = self._quad_quilt("jacquard", "jacquard", "jacquard", "jacquard", white=1, black=2, c=1, width=4, height=2)
        # quilt.print_bottom_up_leftward_traversal()
        swatches = quilt.merge_quilt()
        self.assertEqual(len(swatches), 1)
        for swatch in swatches:
            swatch.compile_to_dat('jacquard_merge')
            self.assertEqual(len(swatch.carriage_passes), 10)
            self.assertEqual(len(swatch.knitout_program), 99)
