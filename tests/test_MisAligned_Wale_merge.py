import warnings
from unittest import TestCase

from clean_up_tests import cleanup_test_files
from resources.load_ks_resources import load_test_knitscript_to_knitout_to_dat
from virtual_knitting_machine.knitting_machine_warnings.Needle_Warnings import (
    Knit_on_Empty_Needle_Warning,
)

from quilt_knit.swatch.Swatch import Swatch
from quilt_knit.swatch.wale_wise_merging.Wale_Merge_Process import Wale_Merge_Process
from quilt_knit.swatch.wale_wise_merging.Wale_Wise_Connection import (
    Wale_Wise_Connection,
)


class TestWale_Merge_Process(TestCase):

    @staticmethod
    def _make_connection(bottom_swatch_ks, top_swatch_ks, shift: int = 0,
                         **python_vars) -> Wale_Wise_Connection:
        bottom_swatch_k = load_test_knitscript_to_knitout_to_dat(f"{bottom_swatch_ks}.ks", f"{bottom_swatch_ks}.k", f"{bottom_swatch_ks}.dat", **python_vars)
        top_swatch_k = load_test_knitscript_to_knitout_to_dat(f"{top_swatch_ks}.ks", f"{top_swatch_ks}.k", f"{top_swatch_ks}.dat", **python_vars)
        bottom_swatch = Swatch("bottom swatch", bottom_swatch_k)
        top_swatch = Swatch("top swatch", top_swatch_k)
        if shift > 0:  # rightward shift
            top_swatch = top_swatch.shift_swatch_rightward_on_needle_bed(shift)
            bottom_leftmost_needle_position = shift
            top_leftmost_needle_position = 0
        elif shift < 0:  # leftward shift
            bottom_swatch = bottom_swatch.shift_swatch_rightward_on_needle_bed(shift)
            bottom_leftmost_needle_position = 0
            top_leftmost_needle_position = abs(shift)
        else:
            bottom_leftmost_needle_position = 0
            top_leftmost_needle_position = 0
        right_side = min(bottom_swatch.max_needle, top_swatch.max_needle)
        return Wale_Wise_Connection(bottom_swatch, top_swatch, bottom_leftmost_needle_position, right_side, top_leftmost_needle_position, right_side)

    def setUp(self):
        cleanup_test_files()

    def test_merge_swatches_jersey(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            connection = self._make_connection('jersey', 'jersey',
                                               shift=2,
                                               c=1, width=4, height=2)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('jersey_merge')
            self.assertEqual(len(merger.merged_instructions), 30)

            connection = self._make_connection('jersey', 'jersey',
                                               shift=-2,
                                               c=1, width=4, height=2)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('jersey_merge')
            self.assertEqual(len(merger.merged_instructions), 30)

    def test_merge_swatches_rib(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            connection = self._make_connection('rib', 'rib',
                                               shift=-2,
                                               c=1, width=4, height=2)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('rib_merge')
            self.assertEqual(len(merger.merged_instructions), 32)

            connection = self._make_connection('rib', 'rib',
                                               shift=2,
                                               c=1, width=4, height=2)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('rib_merge')
            self.assertEqual(len(merger.merged_instructions), 32)

    def test_merge_swatches_seed(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            connection = self._make_connection('seed', 'seed',
                                               shift=2,
                                                c=1, width=4, height=2)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('seed_merge')
            self.assertEqual(len(merger.merged_instructions), 42)

            connection = self._make_connection('seed', 'seed',
                                               shift=-2,
                                               c=1, width=4, height=2)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('seed_merge')
            self.assertEqual(len(merger.merged_instructions), 42)

    def test_merge_lace(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            connection = self._make_connection('lace', 'lace',
                                               shift=-2,
                                               c=1, width=7, height=2)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('lace_merge')
            self.assertEqual(len(merger.merged_instructions), 59)
            #
            connection = self._make_connection('left_lace', 'right_lace',
                                               shift=2,
                                               c=1, width=7, height=2)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('lace_dirs_merge')
            self.assertEqual(len(merger.merged_instructions), 57)

    def test_merge_cable(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            connection = self._make_connection('cable', 'cable',
                                               shift=2,
                                               c=1, width=7, height=4)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('cable_merge')
            self.assertEqual(len(merger.merged_instructions), 125)

            connection = self._make_connection('left_cable', 'right_cable',
                                               shift=-2,
                                               c=1, width=7, height=4)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('cable_dirs_merge')
            self.assertEqual(len(merger.merged_instructions), 117)

    def test_merge_rib_jersey(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            connection = self._make_connection('jersey', 'rib',
                                               shift=2,
                                               c=1, width=4, height=2)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('jersey_rib')
            self.assertEqual(len(merger.merged_instructions), 31)

            connection = self._make_connection('rib', 'jersey',
                                               shift=-2,
                                               c=1, width=4, height=2)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('rib_jersey')
            self.assertEqual(len(merger.merged_instructions), 33)

    def test_merge_seed_jersey(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            connection = self._make_connection('jersey', 'seed',
                                               shift=2,
                                               c=1, width=4, height=2)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('jersey_seed')
            self.assertEqual(len(merger.merged_instructions), 35)

            connection = self._make_connection('seed', 'jersey',
                                               shift=-2,
                                               c=1, width=4, height=2)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('seed_jersey')
            self.assertEqual(len(merger.merged_instructions), 37)

    def test_merge_jersey_lace(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            connection = self._make_connection('jersey', 'lace',
                                               shift=2,
                                               c=1, width=6, height=4)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('jersey_lace')
            self.assertEqual(len(merger.merged_instructions), 78)

            connection = self._make_connection('lace', 'jersey',
                                               shift=-2,
                                               c=1, width=6, height=4)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('lace_jersey')
            self.assertEqual(len(merger.merged_instructions), 78)

    def test_merge_jersey_cable(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            connection = self._make_connection('jersey', 'cable',
                                               shift=-2,
                                               c=1, width=6, height=4)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('jersey_cable')
            self.assertEqual(len(merger.merged_instructions), 90)

            connection = self._make_connection('cable', 'jersey',
                                               shift=2,
                                               c=1, width=6, height=4)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('cable_jersey')
            self.assertEqual(len(merger.merged_instructions), 90)

    def test_merge_lace_cable(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            connection = self._make_connection('lace', 'cable',
                                               shift=2,
                                               c=1, width=6, height=4)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('lace_cable')
            self.assertEqual(len(merger.merged_instructions), 104)

            connection = self._make_connection('cable', 'lace',
                                               shift=-2,
                                               c=1, width=6, height=4)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('cable_lace')
            self.assertEqual(len(merger.merged_instructions), 104)

    def test_merge_jacquard(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            connection = self._make_connection('jacquard', 'jacquard',
                                               shift=2,
                                               white=1, black=2, width=4, height=2)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('jacquard_merge')
            self.assertEqual(len(merger.merged_instructions), 51)

            connection = self._make_connection('jacquard', 'jacquard',
                                               shift=-2,
                                               white=1, black=2, width=4, height=2)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('jacquard_merge')
            self.assertEqual(len(merger.merged_instructions), 45)

    def test_merge_seed_jacquard(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            connection = self._make_connection('seed', 'jacquard',
                                               shift=2,
                                               c=1, white=1, black=2, width=4, height=4)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('seed_jacquard')
            self.assertEqual(len(merger.merged_instructions), 63)
            connection = self._make_connection('jacquard', 'seed',
                                               shift=-2,
                                               c=1, white=1, black=2, width=4, height=4)
            merger = Wale_Merge_Process(connection)
            merger.merge_swatches()
            merger.compile_to_dat('jacquard_seed')
            self.assertEqual(len(merger.merged_instructions), 75)
