from unittest import TestCase

from clean_up_tests import cleanup_test_files
from resources.load_ks_resources import load_test_knitscript_to_knitout_to_dat

from quilt_knit.quilt.Quilt import Quilt
from quilt_knit.swatch.Swatch import Swatch


class TestQuilt(TestCase):
    def setUp(self):
        cleanup_test_files()

    @staticmethod
    def _swatch(ks: str, swatch_name: str, **python_vars) -> Swatch:
        swatch_k = load_test_knitscript_to_knitout_to_dat(f"{ks}.ks", f"{ks}.k", f"{ks}.dat", **python_vars)
        return Swatch(swatch_name, swatch_k)

    @staticmethod
    def _interlock_quilt(left_bottom_ks: str, right_bottom_ks: str, left_top_ks: str, right_top_ks: str, center_ks: str,
                         width: tuple[int, int], height: tuple[int, int], **python_vars) -> Quilt:
        wide_vars = {"width": width[1], "height": height[0]}
        wide_vars.update(python_vars)
        tall_vars = {"width": width[0], "height": height[1]}
        tall_vars.update(python_vars)
        square_vars = {"width": width[0], "height": height[0]}
        square_vars.update(python_vars)
        left_bottom = TestQuilt._swatch(left_bottom_ks, "left bottom", **wide_vars)
        right_bottom = TestQuilt._swatch(right_bottom_ks, "right bottom", **tall_vars)
        center = TestQuilt._swatch(center_ks, "center", **square_vars)
        center.remove_cast_on_boundary()
        left_top = TestQuilt._swatch(left_top_ks, "left top", **tall_vars)
        left_top.remove_cast_on_boundary()
        right_top = TestQuilt._swatch(right_top_ks, "right top", **wide_vars)
        right_top.remove_cast_on_boundary()
        quilt = Quilt()
        quilt.connect_swatches_wale_wise(left_bottom, left_top, bottom_rightmost_needle_position=left_top.max_needle)
        quilt.connect_swatches_wale_wise(left_bottom, center, bottom_leftmost_needle_position=left_top.max_needle + 1)
        quilt.connect_swatches_wale_wise(center, right_top, top_rightmost_needle_position=center.max_needle)
        quilt.connect_swatches_wale_wise(right_bottom, right_top, top_leftmost_needle_position=center.max_needle + 1)

        right_bottom_split = right_bottom.find_carriage_pass_from_course_passes(left_bottom.constructed_height)
        quilt.connect_swatches_course_wise(left_bottom, right_bottom, last_carriage_pass_on_right=right_bottom_split)
        left_top_split = left_top.find_carriage_pass_from_course_passes(center.constructed_height)
        quilt.connect_swatches_course_wise(left_top, center, last_carriage_pass_on_left=left_top_split)
        quilt.connect_swatches_course_wise(center, right_bottom, first_carriage_pass_on_right=right_bottom_split + 1)
        quilt.connect_swatches_course_wise(left_top, right_top, first_carriage_pass_on_left=left_top_split + 1)
        return quilt

    def test_jersey_quilt(self):
        quilt = self._interlock_quilt("jersey", "jersey", "jersey", "jersey", "jersey",
                                      width=(4, 8), height=(4, 8), c=1)
        # quilt.print_bottom_up_leftward_traversal()
        swatches = quilt.merge_quilt()
        self.assertEqual(len(swatches), 1)
        for swatch in swatches:
            swatch.compile_to_dat('jersey_merge')
            self.assertEqual(swatch.width, 12)
            self.assertEqual(swatch.height, 14)
            self.assertEqual(len(swatch.knitout_program), 169)

    def test_rib_quilt(self):
        quilt = self._interlock_quilt("rib", "rib", "rib", "rib", "rib",
                                      width=(4, 8), height=(4, 8), c=1)
        swatches = quilt.merge_quilt()
        self.assertEqual(len(swatches), 1)
        for swatch in swatches:
            swatch.compile_to_dat('rib_merge')
            self.assertEqual(swatch.width, 12)
            self.assertEqual(swatch.height, 15)
            self.assertEqual(swatch.constructed_height, 14)
            self.assertEqual(len(swatch.knitout_program), 175)

    def test_seed_quilt(self):
        quilt = self._interlock_quilt("seed", "seed", "seed", "seed", "seed",
                                      width=(4, 8), height=(4, 8), c=1)
        swatches = quilt.merge_quilt()
        self.assertEqual(len(swatches), 1)
        for swatch in swatches:
            swatch.compile_to_dat('seed_merge')
            self.assertEqual(swatch.width, 12)
            self.assertEqual(swatch.height, 26)
            self.assertEqual(swatch.constructed_height, 14)
            self.assertEqual(len(swatch.knitout_program), 307)

    def test_lace_quilt(self):
        quilt = self._interlock_quilt("lace", "left_lace", "left_lace", "lace", "left_lace",
                                      width=(4, 7), height=(4, 8), c=1)
        swatches = quilt.merge_quilt()
        self.assertEqual(len(swatches), 1)
        for swatch in swatches:
            swatch.compile_to_dat('lace_merge')
            self.assertEqual(swatch.width, 12)
            self.assertEqual(swatch.height, 34)
            self.assertEqual(swatch.constructed_height, 14)
            self.assertEqual(len(swatch.knitout_program), 218)

    def test_cable_quilt(self):
        quilt = self._interlock_quilt("cable", "left_cable", "left_cable", "cable", "left_cable",
                                      width=(4, 7), height=(4, 8), c=1)
        swatches = quilt.merge_quilt()
        self.assertEqual(len(swatches), 1)
        for swatch in swatches:
            swatch.compile_to_dat('cable_merge')
            self.assertEqual(swatch.width, 12)
            self.assertEqual(swatch.height, 46)
            self.assertEqual(swatch.constructed_height, 14)
            self.assertEqual(len(swatch.knitout_program), 266)

    def test_jacquard_quilt(self):
        quilt = self._interlock_quilt("jacquard", "jacquard", "jacquard", "jacquard", "jacquard",
                                      width=(4, 8), height=(4, 8), white=1, black=1)
        swatches = quilt.merge_quilt()
        self.assertEqual(len(swatches), 1)
        for swatch in swatches:
            swatch.compile_to_dat('jacquard_merge')
            # self.assertEqual(swatch.width, 12)
            # self.assertEqual(swatch.height, 46)
            # self.assertEqual(swatch.constructed_height, 14)
            # self.assertEqual(len(swatch.knitout_program), 266)
