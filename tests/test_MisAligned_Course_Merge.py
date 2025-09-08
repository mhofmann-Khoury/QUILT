from unittest import TestCase

from resources.load_ks_resources import load_test_knitscript_to_knitout_to_dat

from quilt_knit.swatch.course_wise_merging.Course_Merge_Process import (
    Course_Merge_Process,
)
from quilt_knit.swatch.course_wise_merging.Course_Wise_Connection import (
    Course_Wise_Connection,
)
from quilt_knit.swatch.Swatch import Swatch


class TestCourse_Merge_Process(TestCase):

    @staticmethod
    def _make_connection(left_swatch_ks, right_swatch_ks,
                         first_carriage_pass_on_left: int = 0, last_carriage_pass_on_left: int | None = None,
                         first_carriage_pass_on_right: int = 0, last_carriage_pass_on_right: int | None = None, **python_vars) -> Course_Wise_Connection:
        left_swatch_k = load_test_knitscript_to_knitout_to_dat(f"{left_swatch_ks}.ks", f"{left_swatch_ks}.k", f"{left_swatch_ks}.dat", **python_vars)
        right_swatch_k = load_test_knitscript_to_knitout_to_dat(f"{right_swatch_ks}.ks", f"{right_swatch_ks}.k", f"{right_swatch_ks}.dat", **python_vars)
        left_swatch = Swatch("left swatch", left_swatch_k)
        right_swatch = Swatch("right swatch", right_swatch_k)
        return Course_Wise_Connection(left_swatch, right_swatch, first_carriage_pass_on_left, last_carriage_pass_on_left, first_carriage_pass_on_right, last_carriage_pass_on_right)

    def test_merge_swatches_jersey(self):
        connection = self._make_connection('jersey', 'jersey',
                                           first_carriage_pass_on_left=2, first_carriage_pass_on_right=0,
                                           c=1, width=4, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jersey_merge')
        self.assertEqual(len(merger.merged_instructions), 48)

        connection = self._make_connection('jersey', 'jersey',
                                           first_carriage_pass_on_left=0, first_carriage_pass_on_right=2,
                                           c=1, width=4, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jersey_merge')
        self.assertEqual(len(merger.merged_instructions), 48)

    def test_merge_swatches_rib(self):
        connection = self._make_connection('rib', 'rib',
                                           first_carriage_pass_on_left=2, first_carriage_pass_on_right=0,
                                           c=1, width=4, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('rib_merge')
        self.assertEqual(len(merger.merged_instructions), 52)

        connection = self._make_connection('rib', 'rib',
                                           first_carriage_pass_on_left=0, first_carriage_pass_on_right=2,
                                           c=1, width=4, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('rib_merge')
        self.assertEqual(len(merger.merged_instructions), 52)

    def test_merge_swatches_seed(self):
        connection = self._make_connection('seed', 'seed',
                                           first_carriage_pass_on_left=2, first_carriage_pass_on_right=0,
                                           c=1, width=4, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('seed_merge')
        self.assertEqual(len(merger.merged_instructions), 76)

        connection = self._make_connection('seed', 'seed',
                                           first_carriage_pass_on_left=0, first_carriage_pass_on_right=2,
                                           c=1, width=4, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('seed_merge')
        self.assertEqual(len(merger.merged_instructions), 76)

    def test_merge_lace(self):
        connection = self._make_connection('lace', 'lace',
                                           first_carriage_pass_on_left=0, first_carriage_pass_on_right=2,
                                            c=1, width=7, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('lace_merge')
        self.assertEqual(len(merger.merged_instructions), 103)
        #
        connection = self._make_connection('left_lace', 'right_lace',
                                           first_carriage_pass_on_left=2, first_carriage_pass_on_right=0,
                                             c=1, width=7, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('lace_dirs_merge')
        self.assertEqual(len(merger.merged_instructions), 102)

    def test_merge_cable(self):
        connection = self._make_connection('cable', 'cable',
                                           first_carriage_pass_on_left=0, first_carriage_pass_on_right=2,
                                           c=1, width=7, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('cable_merge')
        self.assertEqual(len(merger.merged_instructions), 120)

        connection = self._make_connection('left_cable', 'right_cable',
                                           first_carriage_pass_on_left=2, first_carriage_pass_on_right=0,
                                           c=1, width=7, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('cable_dirs_merge')
        self.assertEqual(len(merger.merged_instructions), 122)

    def test_merge_rib_jersey(self):
        connection = self._make_connection('jersey', 'rib',
                                           first_carriage_pass_on_left=2, first_carriage_pass_on_right=0,
                                           c=1, width=4, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jersey_rib')
        self.assertEqual(len(merger.merged_instructions), 50)

        connection = self._make_connection('rib', 'jersey',
                                           first_carriage_pass_on_left=0, first_carriage_pass_on_right=2,
                                            c=1, width=4, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('rib_jersey')
        self.assertEqual(len(merger.merged_instructions), 50)

    def test_merge_seed_jersey(self):
        connection = self._make_connection('jersey', 'seed',
                                           first_carriage_pass_on_left=2, first_carriage_pass_on_right=0,
                                            c=1, width=4, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jersey_seed')
        self.assertEqual(len(merger.merged_instructions), 62)

        connection = self._make_connection('seed', 'jersey',
                                           first_carriage_pass_on_left=2, first_carriage_pass_on_right=0,
                                            c=1, width=4, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('seed_jersey')
        self.assertEqual(len(merger.merged_instructions), 62)

    def test_merge_jersey_lace(self):
        connection = self._make_connection('jersey', 'lace',
                                           first_carriage_pass_on_left=2, first_carriage_pass_on_right=0,
                                           c=1, width=6, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jersey_lace')
        self.assertEqual(len(merger.merged_instructions), 82)

        connection = self._make_connection('lace', 'jersey',
                                           first_carriage_pass_on_left=0, first_carriage_pass_on_right=2,
                                           c=1, width=6, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('lace_jersey')
        self.assertEqual(len(merger.merged_instructions), 82)

    def test_merge_jersey_cable(self):
        connection = self._make_connection('jersey', 'cable',
                                           first_carriage_pass_on_left=0, first_carriage_pass_on_right=2,
                                            c=1, width=6, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jersey_cable')
        self.assertEqual(len(merger.merged_instructions), 94)

        connection = self._make_connection('cable', 'jersey',
                                           first_carriage_pass_on_left=2, first_carriage_pass_on_right=0,
                                            c=1, width=6, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('cable_jersey')
        self.assertEqual(len(merger.merged_instructions), 94)

    def test_merge_lace_cable(self):
        connection = self._make_connection('lace', 'cable',
                                           first_carriage_pass_on_left=2, first_carriage_pass_on_right=0,
                                           c=1, width=6, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('lace_cable')
        self.assertEqual(len(merger.merged_instructions), 107)

        connection = self._make_connection('cable', 'lace',
                                           first_carriage_pass_on_left=0, first_carriage_pass_on_right=2,
                                           c=1, width=6, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('cable_lace')
        self.assertEqual(len(merger.merged_instructions), 105)

    def test_merge_jacquard(self):
        connection = self._make_connection('jacquard', 'jacquard',
                                           first_carriage_pass_on_left=2, first_carriage_pass_on_right=0,
                                           white=1, black=2, width=4, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jacquard_merge')
        self.assertEqual(len(merger.merged_instructions), 91)

        connection = self._make_connection('jacquard', 'jacquard',
                                           first_carriage_pass_on_left=0, first_carriage_pass_on_right=2,
                                           white=1, black=2, width=4, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jacquard_merge')
        self.assertEqual(len(merger.merged_instructions), 91)

    def test_merge_seed_jacquard(self):
        connection = self._make_connection('seed', 'jacquard',
                                           first_carriage_pass_on_left=0, first_carriage_pass_on_right=2,
                                           c=1, white=1, black=2, width=4, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('seed_jacquard')
        self.assertEqual(len(merger.merged_instructions), 85)
        connection = self._make_connection('jacquard', 'seed',
                                           first_carriage_pass_on_left=2, first_carriage_pass_on_right=0,
                                           c=1, white=1, black=2, width=4, height=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jacquard_seed')
        self.assertEqual(len(merger.merged_instructions), 85)
