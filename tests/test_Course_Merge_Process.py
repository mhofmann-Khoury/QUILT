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

    def test_merge_swatches_single_line(self):
        connection = self._make_connection('tuck_line', 'tuck_line', c=1, width=4)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('tuck_line_merge')
        self.assertEqual(len(merger.merged_instructions), 16)

    def test_merge_swatches_jersey(self):
        connection = self._make_connection('jersey', 'jersey', c=1, width=4, height=2)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jersey_merge')
        self.assertEqual(len(merger.merged_instructions), 32)

        connection = self._make_connection('jersey', 'jersey', c=1, width=4, height=3)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jersey_merge')
        self.assertEqual(len(merger.merged_instructions), 40)

    def test_merge_swatches_rib(self):
        connection = self._make_connection('rib', 'rib', c=1, width=4, height=2)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('rib_merge')
        self.assertEqual(len(merger.merged_instructions), 36)
        #
        connection = self._make_connection('rib', 'rib', c=1, width=5, height=3)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('rib_merge')
        self.assertEqual(len(merger.merged_instructions), 52)

    def test_merge_swatches_seed(self):
        connection = self._make_connection('seed', 'seed', c=1, width=4, height=2)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('seed_merge')
        self.assertEqual(len(merger.merged_instructions), 44)

        connection = self._make_connection('seed', 'seed', c=1, width=5, height=3)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('seed_merge')
        self.assertEqual(len(merger.merged_instructions), 72)

    def test_merge_rib_jersey(self):
        connection = self._make_connection('jersey', 'rib', c=1, width=4, height=2)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jersey_rib')
        self.assertEqual(len(merger.merged_instructions), 34)

        connection = self._make_connection('rib', 'jersey', c=1, width=5, height=3)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('rib_jersey')
        self.assertEqual(len(merger.merged_instructions), 50)

    def test_merge_seed_jersey(self):
        connection = self._make_connection('jersey', 'seed', c=1, width=4, height=2)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jersey_seed')
        self.assertEqual(len(merger.merged_instructions), 38)

        connection = self._make_connection('seed', 'jersey', c=1, width=5, height=3)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('seed_jersey')
        self.assertEqual(len(merger.merged_instructions), 60)

    def test_merge_jacquard(self):
        connection = self._make_connection('jacquard', 'jacquard', white=1, black=2, width=4, height=2)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jacquard_merge')
        self.assertEqual(len(merger.merged_instructions), 75)

    def test_merge_seed_jacquard(self):
        connection = self._make_connection('seed', 'jacquard', c=1, white=1, black=2, width=4, height=2)
        merger = Course_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('seed_jacquard')
        # self.assertEqual(len(merger.merged_instructions), 38)
