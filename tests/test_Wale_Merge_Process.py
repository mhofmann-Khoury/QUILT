from unittest import TestCase

from clean_up_tests import cleanup_test_files
from resources.load_ks_resources import load_test_knitscript_to_knitout_to_dat

from quilt_knit.swatch.Swatch import Swatch
from quilt_knit.swatch.wale_wise_merging.Wale_Merge_Process import Wale_Merge_Process
from quilt_knit.swatch.wale_wise_merging.Wale_Wise_Connection import (
    Wale_Wise_Connection,
)


class TestWale_Merge_Process(TestCase):

    def setUp(self):
        cleanup_test_files()

    @staticmethod
    def _make_connection(bottom_swatch_ks, top_swatch_ks,
                         bottom_leftmost_needle_position: int = 0, bottom_rightmost_needle_position: int | None = None,
                         top_leftmost_needle_position: int = 0, top_rightmost_needle_position: int | None = None, **python_vars) -> Wale_Wise_Connection:
        bottom_swatch_k = load_test_knitscript_to_knitout_to_dat(f"{bottom_swatch_ks}.ks", f"{bottom_swatch_ks}.k", f"{bottom_swatch_ks}.dat", **python_vars)
        top_swatch_k = load_test_knitscript_to_knitout_to_dat(f"{top_swatch_ks}.ks", f"{top_swatch_ks}.k", f"{top_swatch_ks}.dat", **python_vars)
        bottom_swatch = Swatch("bottom swatch", bottom_swatch_k)
        top_swatch = Swatch("top swatch", top_swatch_k)
        return Wale_Wise_Connection(bottom_swatch, top_swatch, bottom_leftmost_needle_position, bottom_rightmost_needle_position, top_leftmost_needle_position, top_rightmost_needle_position)

    def test_merge_swatches_single_line(self):
        connection = self._make_connection('single_knit_line', 'single_knit_line', c=1, width=4)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('knit_line_merge')
        self.assertEqual(len(merger.merged_instructions), 26)

    def test_merge_swatches_jersey(self):
        connection = self._make_connection('jersey', 'jersey', c=1, width=4, height=2)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jersey_merge')
        self.assertEqual(len(merger.merged_instructions), 30)

        connection = self._make_connection('jersey', 'jersey', c=1, width=4, height=3)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jersey_merge')
        self.assertEqual(len(merger.merged_instructions), 42)

    def test_merge_swatches_rib(self):
        connection = self._make_connection('rib', 'rib', c=1, width=4, height=2)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('rib_merge')
        self.assertEqual(len(merger.merged_instructions), 32)
        #
        connection = self._make_connection('rib', 'rib', c=1, width=5, height=3)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('rib_merge')
        self.assertEqual(len(merger.merged_instructions), 52)

    def test_merge_swatches_seed(self):
        connection = self._make_connection('seed', 'seed', c=1, width=4, height=2)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('seed_merge')
        self.assertEqual(len(merger.merged_instructions), 44)

        connection = self._make_connection('seed', 'seed', c=1, width=5, height=3)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('seed_merge')
        self.assertEqual(len(merger.merged_instructions), 72)

    def test_merge_lace(self):
        connection = self._make_connection('lace', 'lace', c=1, width=7, height=4)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('lace_merge')
        self.assertEqual(len(merger.merged_instructions), 101)

        connection = self._make_connection('left_lace', 'right_lace', c=1, width=7, height=4)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('lace_dirs_merge')
        self.assertEqual(len(merger.merged_instructions), 97)

    def test_merge_cable(self):
        connection = self._make_connection('cable', 'cable', c=1, width=7, height=4)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('cable_merge')
        self.assertEqual(len(merger.merged_instructions), 125)

        connection = self._make_connection('left_cable', 'right_cable', c=1, width=7, height=4)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('cable_dirs_merge')
        self.assertEqual(len(merger.merged_instructions), 117)

    def test_merge_rib_jersey(self):
        connection = self._make_connection('jersey', 'rib', c=1, width=4, height=2)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jersey_rib')
        self.assertEqual(len(merger.merged_instructions), 32)

        connection = self._make_connection('rib', 'jersey', c=1, width=5, height=3)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('rib_jersey')
        self.assertEqual(len(merger.merged_instructions), 54)

    def test_merge_seed_jersey(self):
        connection = self._make_connection('jersey', 'seed', c=1, width=4, height=2)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jersey_seed')
        self.assertEqual(len(merger.merged_instructions), 36)

        connection = self._make_connection('seed', 'jersey', c=1, width=5, height=3)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('seed_jersey')
        self.assertEqual(len(merger.merged_instructions), 64)

    def test_merge_jacquard(self):
        connection = self._make_connection('jacquard', 'jacquard', white=1, black=2, width=4, height=2)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jacquard_merge')
        self.assertEqual(len(merger.merged_instructions), 61)

        connection = self._make_connection('jacquard', 'jacquard', white=1, black=2, width=5, height=5)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jacquard_merge')
        self.assertEqual(len(merger.merged_instructions), 123)

    def test_merge_seed_jacquard(self):
        connection = self._make_connection('seed', 'jacquard', c=1, white=1, black=2, width=4, height=2)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('seed_jacquard')
        self.assertEqual(len(merger.merged_instructions), 47)

        connection = self._make_connection('jacquard', 'seed', c=1, white=1, black=2, width=3, height=3)
        merger = Wale_Merge_Process(connection)
        merger.merge_swatches()
        merger.compile_to_dat('jacquard_seed')
        self.assertEqual(len(merger.merged_instructions), 55)
