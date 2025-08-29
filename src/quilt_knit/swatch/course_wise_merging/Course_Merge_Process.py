"""Module for linking Swatches by vertical seams"""
import warnings

from knitout_interpreter.knitout_execution_structures.Carriage_Pass import Carriage_Pass
from knitout_interpreter.knitout_operations.carrier_instructions import (
    Inhook_Instruction,
    Outhook_Instruction,
    Releasehook_Instruction,
)
from knitout_interpreter.knitout_operations.Header_Line import (
    Knitout_Header_Line,
    get_machine_header,
)
from knitout_interpreter.knitout_operations.knitout_instruction_factory import (
    build_instruction,
)
from knitout_interpreter.knitout_operations.Knitout_Line import (
    Knitout_Comment_Line,
    Knitout_Line,
    Knitout_Version_Line,
)
from knitout_interpreter.knitout_operations.needle_instructions import (
    Loop_Making_Instruction,
    Miss_Instruction,
    Needle_Instruction,
    Xfer_Instruction,
)
from knitout_interpreter.knitout_operations.Rack_Instruction import Rack_Instruction
from knitout_to_dat_python.knitout_to_dat import knitout_to_dat
from virtual_knitting_machine.Knitting_Machine import Knitting_Machine
from virtual_knitting_machine.knitting_machine_warnings.carrier_operation_warnings import (
    Mismatched_Releasehook_Warning,
)
from virtual_knitting_machine.knitting_machine_warnings.Yarn_Carrier_System_Warning import (
    In_Active_Carrier_Warning,
    Out_Inactive_Carrier_Warning,
)
from virtual_knitting_machine.machine_components.carriage_system.Carriage_Pass_Direction import (
    Carriage_Pass_Direction,
)
from virtual_knitting_machine.machine_components.yarn_management.Yarn_Carrier import (
    Yarn_Carrier,
)
from virtual_knitting_machine.machine_components.yarn_management.Yarn_Carrier_Set import (
    Yarn_Carrier_Set,
)

from quilt_knit.swatch.course_boundary_instructions import (
    Course_Boundary_Instruction,
    Course_Side,
)
from quilt_knit.swatch.course_wise_merging.Course_Seam_Connection import (
    Course_Seam_Connection,
)
from quilt_knit.swatch.course_wise_merging.Course_Seam_Search_Space import (
    Course_Seam_Search_Space,
)
from quilt_knit.swatch.course_wise_merging.Course_Wise_Connection import (
    Course_Wise_Connection,
)
from quilt_knit.swatch.Swatch import Swatch


class Course_Merge_Process:
    """Class to manage a horizontal merge process between two swatches."""

    def __init__(self, courseWise_connection: Course_Wise_Connection,
                 seam_search_space: Course_Seam_Search_Space | None = None):
        self.course_wise_connection: Course_Wise_Connection = courseWise_connection
        if seam_search_space is None:
            seam_search_space = Course_Seam_Search_Space(self.left_swatch, self.right_swatch)
        self.seam_search_space: Course_Seam_Search_Space = seam_search_space
        self.seam_search_space.remove_boundaries_beyond_course_connections(self.course_wise_connection)
        self._next_instruction_index_by_side: dict[Course_Side, int | None] = {Course_Side.Left: 0, Course_Side.Right: 0}
        self.current_swatch_side: Course_Side = Course_Side.Left
        self._set_merge_direction()
        self.merged_program_machine_state: Knitting_Machine = Knitting_Machine()
        self.source_machine_states: dict[Course_Side, Knitting_Machine] = {Course_Side.Left: Knitting_Machine(), Course_Side.Right: Knitting_Machine()}
        self.merged_instructions: list[tuple[Knitout_Line, Course_Side]] = [(i, self.current_swatch_side) for i in get_machine_header(self.current_swatch.execution_knitting_machine)]

    @property
    def starting_course_aligned(self) -> bool:
        """
        Returns:
            bool: True if the starting courses of both swatches are executed in the same carriage pass direction. False, otherwise.
        """
        return self.course_wise_connection.left_start_direction == self.course_wise_connection.right_start_direction

    def _set_merge_direction(self) -> None:
        """
        Determine the direction to start merging from. If the carriage passes are aligned, start knitting from the one that feeds into the next.
        """
        if self.starting_course_aligned:  # Courses are aligned, so we can smoothly merge in the direction of the first set of carriage passes
            if self.course_wise_connection.right_start_direction is Carriage_Pass_Direction.Leftward:
                self.current_swatch_side: Course_Side = Course_Side.Right
            else:  # leftward direction or xfer
                self.current_swatch_side: Course_Side = Course_Side.Left
        elif self.course_wise_connection.right_start_direction is Carriage_Pass_Direction.Leftward:
            self.current_swatch_side: Course_Side = Course_Side.Right
        elif self.course_wise_connection.left_start_direction is Carriage_Pass_Direction.Rightward:
            self.current_swatch_side: Course_Side = Course_Side.Left

    # def get_source_carriage_pass_index(self, instruction: Knitout_Line) -> int | None:
    #     """
    #     Args:
    #         instruction (Knitout_Line): The instruction to find the carriage pass index of.
    #
    #     Returns:
    #         int | None: Get the carriage pass index of the given instruction in its originating swatch or None if the instruction is not in either swatch.
    #     """
    #     if instruction in self.merged_instruction_to_course_side:
    #         course_side = self.merged_instruction_to_course_side[instruction]
    #         if course_side is Course_Side.Left:
    #             return self.left_swatch.get_cp_index_of_instruction(instruction)
    #         else:
    #             assert course_side is Course_Side.Right
    #             return self.right_swatch.get_cp_index_of_instruction(instruction)
    #     else:
    #         return None

    @property
    def right_swatch(self) -> Swatch:
        """
        Returns:
            Swatch: The right swatch in the connection being merged.
        """
        return self.course_wise_connection.right_swatch

    @property
    def left_swatch(self) -> Swatch:
        """
        Returns:
            Swatch: The left swatch in the connection being merged.
        """
        return self.course_wise_connection.left_swatch

    @property
    def first_courses_by_side(self) -> dict[Course_Side, int]:
        """
        Returns:
            dict[Course_Side, int]: Dictionary mapping left and right course sides to the first course on that side to be merged.
        """
        return self.course_wise_connection.first_course_by_side

    @property
    def last_courses_by_side(self) -> dict[Course_Side, int]:
        """
        Returns:
            dict[Course_Side, int]: Dictionary mapping left and right course sides to the last course on that side to be merged.
        """
        return self.course_wise_connection.last_courses_by_side

    @property
    def next_index(self) -> int | None:
        """
        Returns:
            int | None: The next index of instructions to consume from the current swatch or None if the current swatch is fully consumed.
        """
        return self._next_instruction_index_by_side[self.current_swatch_side]

    def increment_next_index(self) -> None:
        """
            Increments the index pointing to the next instruction in the current swatch.
        """
        next_index = self.next_index
        if isinstance(next_index, int):
            if next_index + 1 >= len(self.current_swatch.knitout_program):
                self._next_instruction_index_by_side[self.current_swatch_side] = None
            else:
                self._next_instruction_index_by_side[self.current_swatch_side] = next_index + 1

    @next_index.setter
    def next_index(self, next_index_of_current_swatch: int) -> None:
        """
        Sets the next index of instructions to consume from the current swatch. If that index moves beyond the length of the current swatch, next index is set to None.

        Args:
            next_index_of_current_swatch (int): The next index of instructions to consume from the current swatch.
        """
        if next_index_of_current_swatch >= len(self.current_swatch.knitout_program):
            self._next_instruction_index_by_side[self.current_swatch_side] = None
        else:
            self._next_instruction_index_by_side[self.current_swatch_side] = next_index_of_current_swatch

    @property
    def next_left_index(self) -> int | None:
        """
        Returns:
            int | None: The next index of instructions to consume from the left swatch or None if the left swatch is fully consumed.
        """
        return self._next_instruction_index_by_side[Course_Side.Left]

    @property
    def next_right_index(self) -> int | None:
        """
        Returns:
            int | None: The next index of instructions to consume from the right swatch or None if the right swatch is fully consumed.
        """
        return self._next_instruction_index_by_side[Course_Side.Right]

    def get_left_instruction_at_index(self, index: int) -> Knitout_Line | None:
        """
        Args:
            index (int): The index of the instruction in the left swatch.

        Returns:
            Knitout_Line | None: The instruction at the given index in the left swatch or None if that index is not in the left swatch.
        """
        if index >= len(self.left_swatch.knitout_program):
            return None
        else:
            return self.left_swatch.knitout_program[index]

    def get_right_instruction_at_index(self, index: int) -> Knitout_Line | None:
        """
        Args:
            index (int): The index of the instruction in the right swatch.

        Returns:
            Knitout_Line | None: The instruction at the given index in the right swatch or None if that index is not in the right swatch.
        """
        if index >= len(self.right_swatch.knitout_program):
            return None
        else:
            return self.right_swatch.knitout_program[index]

    def get_instruction_at_index(self, index: int, swatch_side: Course_Side) -> Knitout_Line | None:
        """
        Args:
            index (int): The index of the instruction.
            swatch_side (Course_Side): The swatch side to source the instruction from

        Returns:
            Knitout_Line | None: The instruction at the given index in the specified swatch or None if that index is not in that swatch.
        """
        if swatch_side is Course_Side.Left:
            return self.get_left_instruction_at_index(index)
        else:
            return self.get_right_instruction_at_index(index)

    @property
    def next_left_instruction(self) -> Knitout_Line | None:
        """
        Returns:
            Knitout_Line | None: The next instruction on the left swatch or None if there are no instructions to consume from the left.
        """
        if self.next_left_index is None:
            return None
        else:
            return self.left_swatch.knitout_program[self.next_left_index]

    @property
    def next_right_instruction(self) -> Knitout_Line | None:
        """
        Returns:
            Knitout_Line | None: The next instruction on the right swatch or None if there are no instructions to consume from the right.
        """
        if self.next_right_index is None:
            return None
        else:
            return self.right_swatch.knitout_program[self.next_right_index]

    @property
    def next_left_needle_instruction(self) -> Needle_Instruction | None:
        """
        Returns:
            Needle_Instruction | None: The next needle instruction that will be encountered in the left swatch program or None if no more needle instructions exist.
        """
        if self.next_left_index is None:
            return None
        next_instruction = self.next_left_instruction
        next_index = self.next_left_index + 1
        while not isinstance(next_instruction, Needle_Instruction):
            if next_index >= len(self.left_swatch.knitout_program):
                return None
            next_instruction = self.get_left_instruction_at_index(next_index)
            next_index += 1
        return next_instruction

    @property
    def cp_index_of_next_left_needle_instruction(self) -> int | None:
        """
        Returns:
            int | None: The index of the carriage pass of the next needle instruction in the left swatch or None if there are no more needle instructions in the swatch.
        """
        next_instruction = self.next_left_needle_instruction
        if next_instruction is None:
            return None
        return self.left_swatch.get_cp_index_of_instruction(next_instruction)

    @property
    def next_right_needle_instruction(self) -> Needle_Instruction | None:
        """
        Returns:
            Needle_Instruction | None: The next needle instruction that will be encountered in the right swatch program or None if no more needle instructions exist.
        """
        if self.next_right_index is None:
            return None
        next_instruction = self.next_right_instruction
        next_index = self.next_right_index + 1
        while not isinstance(next_instruction, Needle_Instruction):
            if next_index >= len(self.right_swatch.knitout_program):
                return None
            next_instruction = self.get_right_instruction_at_index(next_index)
            next_index += 1
        return next_instruction

    @property
    def cp_index_of_next_right_needle_instruction(self) -> int | None:
        """
        Returns:
            int | None: The index of the carriage pass of the next needle instruction in the right swatch or None if there are no more needle instructions in the swatch.
        """
        next_instruction = self.next_right_needle_instruction
        if next_instruction is None:
            return None
        return self.right_swatch.get_cp_index_of_instruction(next_instruction)

    @property
    def next_needle_instruction_in_next_swatch(self) -> Needle_Instruction | None:
        """
        Returns:
            Needle_Instruction | None: The next needle instruction that will be encountered in the next (non-current) swatch program or None if no more needle instructions exist in that swatch.
        """
        if self.current_swatch_side is Course_Side.Left:
            return self.next_right_needle_instruction
        else:
            return self.next_left_needle_instruction

    @property
    def cp_index_of_next_needle_instruction_in_next_swatch(self) -> int | None:
        """
        Returns:
            int | None: The index of the carriage pass of the next needle instruction in the next (non-current) swatch or None if there are no more needle instructions in the swatch.
        """
        next_instruction = self.next_needle_instruction_in_next_swatch
        if next_instruction is None:
            return None
        return self.next_swatch.get_cp_index_of_instruction(next_instruction)

    @property
    def next_needle_instruction_in_current_swatch(self) -> Needle_Instruction | None:
        """
        Returns:
            Needle_Instruction | None: The next needle instruction that will be encountered in the current swatch program or None if no more needle instructions exist in that swatch.
        """
        if self.current_swatch_side is Course_Side.Left:
            return self.next_left_needle_instruction
        else:
            return self.next_right_needle_instruction

    @property
    def cp_index_of_next_needle_instruction_in_current_swatch(self) -> int | None:
        """
        Returns:
            int | None: The index of the carriage pass of the next needle instruction in the current swatch or None if there are no more needle instructions in the swatch.
        """
        next_instruction = self.next_needle_instruction_in_current_swatch
        if next_instruction is None:
            return None
        return self.current_swatch.get_cp_index_of_instruction(next_instruction)

    @property
    def current_swatch(self) -> Swatch:
        """
        Returns:
            Swatch: The current swatch to consume instructions from.
        """
        if self.current_swatch_side is Course_Side.Left:
            return self.left_swatch
        else:
            return self.right_swatch

    @property
    def next_swatch(self) -> Swatch:
        """
        Returns:
            Swatch: The next swatch to consume instructions from. This will be the opposite of the current swatch.
        """
        if self.current_swatch_side is Course_Side.Left:
            return self.right_swatch
        else:
            return self.left_swatch

    @property
    def current_swatch_rack(self) -> int:
        """
        Returns:
            int: The rack value of the machine state of the current swatch.
        """
        return int(self.source_machine_states[self.current_swatch_side].rack)

    @property
    def current_swatch_all_needle_rack(self) -> bool:
        """
        Returns:
            bool: True if the machine state of the current swatch is set to all needle rack. False, otherwise.
        """
        return bool(self.source_machine_states[self.current_swatch_side].all_needle_rack)

    def swap_swatch_sides(self) -> None:
        """
        Swaps which swatch is the current swatch vs the next swatch to consume from.
        """
        self.current_swatch_side = ~self.current_swatch_side

    @property
    def current_boundary_side(self) -> Course_Side:
        """
        Returns:
            Course_Side: The boundary of the current swatch to merge from.
        """
        return self.current_swatch_side.opposite

    @property
    def next_instruction_on_boundary(self) -> bool:
        """
        Returns:
            bool: True if the next instruction is on the boundary of the current swatch. False, otherwise.
        """
        if self.next_instruction is None:
            return False
        elif self.current_boundary_side is Course_Side.Left:
            return self.current_swatch.instruction_on_left_boundary(self.next_instruction)
        elif self.current_boundary_side is Course_Side.Right:
            return self.current_swatch.instruction_on_right_boundary(self.next_instruction)

    @property
    def next_instruction_is_boundary_entrance(self) -> bool:
        """
        Returns:
            bool: True if the next instruction is on the relevant boundary entrance of the current swatch. False, otherwise
        """
        return self.next_instruction_on_boundary and self.current_swatch.instruction_is_course_entrance(self.next_instruction)

    @property
    def next_instruction_is_boundary_exit(self) -> bool:
        """
        Returns:
            bool: True if the next instruction is on the relevant boundary exit of the current swatch. False, otherwise
        """
        return self.next_instruction_on_boundary and self.current_swatch.instruction_is_course_exit(self.next_instruction)

    @property
    def current_swatch_is_consumed(self) -> bool:
        """
        Returns:
            bool: True if the current swatch is consumed, False otherwise.
        """
        return self.next_index is None

    @property
    def left_swatch_is_consumed(self) -> bool:
        """
        Returns:
            bool: True if the left swatch is consumed, False otherwise.
        """
        return self._next_instruction_index_by_side[Course_Side.Left] is None

    @property
    def right_swatch_is_consumed(self) -> bool:
        """
        Returns:
            bool: True if the right swatch is consumed, False otherwise.
        """
        return self._next_instruction_index_by_side[Course_Side.Right] is None

    def needle_instruction_in_merged_swatch(self, needle_instruction: Needle_Instruction, source_swatch_side: Course_Side) -> Needle_Instruction:
        """
        Args:
            needle_instruction (Needle_Instruction): The needle instruction to copy for the merged program.
            source_swatch_side (Course_Side): The source swatch of the given needle instruction.

        Returns:
            Needle_Instruction:
                The needle instruction adjusted for the position in the merged program.
                This is the same instruction from the left swatch and a copy shifted by the width of the left swatch for instructions from the right swatch.

        """
        if source_swatch_side is Course_Side.Left:
            return needle_instruction
        else:
            shifted_needle = needle_instruction.needle + self.left_swatch.width
            if needle_instruction.needle_2 is None:
                shifted_needle_2 = None
            else:
                shifted_needle_2 = needle_instruction.needle_2 + self.left_swatch.width
            shifted_instruction = build_instruction(needle_instruction.instruction_type, shifted_needle,
                                                    needle_instruction.direction, needle_instruction.carrier_set, shifted_needle_2,
                                                    comment="Right Shifted for Merge")
            assert isinstance(shifted_instruction, Needle_Instruction)
            shifted_instruction.original_line_number = needle_instruction.original_line_number
            return shifted_instruction

    def instruction_requires_release(self, next_instruction: Knitout_Line) -> bool:
        """
        Args:
            next_instruction (Knitout_Line): The next instruction to test if it requires a releasehook.

        Returns:
            bool: True if the specified next instruction would trigger a releasehook from the current merged program machine state.
        """
        if self.merged_program_machine_state.carrier_system.inserting_hook_available:
            return False
        elif isinstance(next_instruction, Inhook_Instruction) or isinstance(next_instruction, Outhook_Instruction):
            return True
        elif isinstance(next_instruction, Needle_Instruction):
            if next_instruction.has_second_needle:
                return True
        return False

    def _get_floats_to_instruction(self, merge_instruction: Loop_Making_Instruction) -> dict[Yarn_Carrier: tuple[int, Carriage_Pass_Direction]]:
        """
        Args:
            merge_instruction (Loop_Making_Instruction): The instruction that would be executed in the merged program.

        Returns:
            dict[Yarn_Carrier, tuple[int, Carriage_Pass_Direction]]:
                Dictionary mapping yarn carriers to tuples of the float lengths and directions for the float that would be formed by executing the given instruction. Only non-zero floats are returned.
        """
        if isinstance(merge_instruction, Miss_Instruction):
            return {}  # Miss instructions do not form floats.

        def _float_direction(current_carrier_position: int | None) -> Carriage_Pass_Direction:
            """
            Args:
                current_carrier_position (int | None): The current needle slot position of the carrier.

            Returns:
                Carriage_Pass_Direction:
                    The direction that a float will be formed from the given carrier position to the instruction's position.
                    * If the float is of zero length, this direction is determined by the direction of the instruction.
                    * If the current carrier is not active (position is None), then the direction is determined by the direction of the instruction.

            Notes:
                * A carrier cannot be inserted in a rightward direction, so a None-position carrier followed by a rightward instruction should be excluded as an allowable merge.
            """
            if current_carrier_position is None:
                return merge_instruction.direction
            elif merge_instruction.needle.position < current_carrier_position:
                return Carriage_Pass_Direction.Leftward
            elif merge_instruction.needle.position > current_carrier_position:
                return Carriage_Pass_Direction.Rightward
            else:
                return merge_instruction.direction

        def _float_length(current_carrier_position: int | None) -> int:
            """
            Args:
                current_carrier_position (int | None): The current needle slot position of the carrier.

            Returns:
                int: The length of the float formed between the current carrier position and the given instruction.

            """
            if current_carrier_position is None:  # Carrier is not active
                return 0
            return abs(int(merge_instruction.needle.position) - current_carrier_position)

        def _float(current_carrier_position: int | None) -> tuple[int, Carriage_Pass_Direction]:
            return _float_length(current_carrier_position), _float_direction(current_carrier_position)

        floats = {carrier: _float(carrier.position) for carrier in merge_instruction.carrier_set.get_carriers(self.merged_program_machine_state.carrier_system)}
        return {c: f for c, f in floats.items() if f[0] > 0}

    def _add_instruction_to_merge(self, merge_instruction: Knitout_Line, instruction_source: Course_Side, instruction: Knitout_Line | None = None) -> bool:
        """
        Adds the given merge instruction to the merged instruction program and updates the corresponding machine states.
        Args:
            merge_instruction (Knitout_Line): The instruction to add to the merged program.
            instruction_source (Course_Side): Specifies the source swatch of the merged instruction.
            instruction (Knitout_Line, optional): The instruction from the original swatch to execute on its corresponding machine state. Defaults to the merged_instruction.

        Returns:
            bool: True if the given merged instruction updates the machine state and is added to the merged program. False otherwise.
        """
        if instruction is None:
            instruction = merge_instruction
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=In_Active_Carrier_Warning)
            warnings.filterwarnings("ignore", category=Out_Inactive_Carrier_Warning)
            warnings.filterwarnings("ignore", category=Mismatched_Releasehook_Warning)
            instruction.execute(self.source_machine_states[instruction_source])
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=Out_Inactive_Carrier_Warning)
            warnings.filterwarnings("ignore", category=Mismatched_Releasehook_Warning)
            updates_merge = merge_instruction.execute(self.merged_program_machine_state)
            if not updates_merge:
                return False  # No update to the merged machine state, so this isn't added to the merged program.
        self.merged_instructions.append((merge_instruction, instruction_source))
        return True

    def _release_to_merge_instruction(self, instruction: Knitout_Line, instruction_source: Course_Side) -> None:
        """
        Inserts a necessary releasehook in order to execute the given instruction in the merged program. If a release is not needed, nothing happens.
        Args:
            instruction (Knitout_Line): The instruction that may trigger a release.
            instruction_source (Course_Side): Specifies the source swatch of the given instruction.
        """
        if self.instruction_requires_release(instruction):
            assert isinstance(self.merged_program_machine_state.carrier_system.hooked_carrier, Yarn_Carrier)
            release = Releasehook_Instruction(self.merged_program_machine_state.carrier_system.hooked_carrier, "Required release between merges")
            self._add_instruction_to_merge(release, instruction_source)

    @property
    def merged_and_current_racks_match(self) -> bool:
        """
        Returns:
            bool: True if the racking values of the merged program state and the current swatch state match. False, otherwise.
        """
        return bool(self.merged_program_machine_state.rack == self.current_swatch_rack and self.merged_program_machine_state.all_needle_rack == self.current_swatch_all_needle_rack)

    def _rack_to_current_swatch(self, instruction_source: Course_Side) -> None:
        """
        Injects a rack instruction into the merged program to align the merged program racking with the current swatch. If they are already aligned, nothing happens.

        Args:
            instruction_source (Course_Side): Specifies the source swatch of the instruction that triggered the need for an aligning merge.
        """
        if not self.merged_and_current_racks_match:
            rack_to_match_current = Rack_Instruction.rack_instruction_from_int_specification(self.current_swatch_rack, self.current_swatch_all_needle_rack,
                                                                                             "Racking introduced to realign between merged courses")
            self._add_instruction_to_merge(rack_to_match_current, instruction_source)

    def _cut_and_reinsert_carrier(self, carrier: Yarn_Carrier, instruction_source: Course_Side) -> None:
        """
        Cuts the given yarn carrier and reinserts it to avoid a long float formed in the merge process.

        Args:
            carrier (Yarn_Carrier): The carrier to cut and reinsert.
            instruction_source (Course_Side): Specifies the source swatch of the instruction that triggered long float.
        """
        cut_float = Outhook_Instruction(carrier, "Cut for long float in merge")
        self._release_to_merge_instruction(cut_float, instruction_source)
        self._add_instruction_to_merge(cut_float, instruction_source)
        insert_float_yarn = Inhook_Instruction(carrier, 'Bring in for merge alignment')
        self._add_instruction_to_merge(insert_float_yarn, instruction_source)

    def _inhook_missing_carriers(self, instruction: Loop_Making_Instruction, instruction_source: Course_Side) -> None:
        """
        Adds inhook operations for any carrier used in the given instruction that is not currently active on the merged machine.
        Args:
            instruction (Loop_Making_Instruction): The instruction that may require carriers to be activated.
            instruction_source (Course_Side): Specifies the source swatch of the instruction that triggered inhooks.
        """
        assert isinstance(instruction.carrier_set, Yarn_Carrier_Set)
        for missing_carrier in self.merged_program_machine_state.carrier_system[self.merged_program_machine_state.carrier_system.missing_carriers(instruction.carrier_set.carrier_ids)]:
            assert instruction.direction is not Carriage_Pass_Direction.Rightward, f"Inserting a carrier before a rightward loop is formed by {instruction}"
            insert_float_yarn = Inhook_Instruction(missing_carrier, 'Bring in carrier from merge')
            self._release_to_merge_instruction(insert_float_yarn, instruction_source)
            self._add_instruction_to_merge(insert_float_yarn, instruction_source)

    def _instruction_is_no_op_in_merged_program(self, instruction: Knitout_Line) -> bool:
        """
        Args:
            instruction (Knitout_Line): The instruction to test for a no-op.

        Returns:
            bool: True if the given instruction has no effect on merged program. False, otherwise.
        """
        if isinstance(instruction, Inhook_Instruction):  # Inhook an active carrier
            return bool(instruction.carrier in self.merged_program_machine_state.carrier_system.active_carriers)
        elif isinstance(instruction, Releasehook_Instruction):  # release free hook or wrong carrier on that hook
            return bool(self.merged_program_machine_state.carrier_system.inserting_hook_available or
                        self.merged_program_machine_state.carrier_system.hooked_carrier.carrier_id != instruction.carrier_id)
        elif isinstance(instruction, Outhook_Instruction):  # cut inactive carrier
            return bool(self.merged_program_machine_state.carrier_system[instruction.carrier].is_active)
        else:
            return False

    def _consume_instruction(self, instruction: Knitout_Line, instruction_source: Course_Side, remove_connections: bool = False, max_float: int = 15) -> None:
        """
        Consumes the given instruction in the specified swatch.
        This will update the merged program and merged program machine state and inject any necessary operations to keep the merged program aligned.
        The source swatch's machine state is also updated by the consumption of the instruction.

        Args:
            instruction (Knitout_Line): The instruction to add to the merged program.
            instruction_source (Course_Side): Specifies the source swatch for this instruction.
            remove_connections (bool, optional): If True, any connections found in the consumed instruction are removed from the search space. Defaults to False.
            max_float (int, optional): Maximum number yarn-floating distances allowed between operations without introducing a cut and reinsert. Defaults to 15.
        """
        if (isinstance(instruction, Knitout_Header_Line) or isinstance(instruction, Knitout_Version_Line)
                or (isinstance(instruction, Knitout_Comment_Line) and "No-Op:" in str(instruction))):  # Todo: Update knitout interpreter to have subclass of comments for no-ops
            return  # Do not consume header, version lines, or no-op comments
        if self._instruction_is_no_op_in_merged_program(instruction):  # No op inhook or releasehook in the merged program.
            instruction.execute(self.source_machine_states[instruction_source])  # update carrier in the swatch's machine, but ignore its addition to the merged program
            return
        if remove_connections:
            self.seam_search_space.remove_boundary(instruction)
        self._release_to_merge_instruction(instruction, instruction_source)  # Add any necessary releases before the instruction is merged in.
        if not isinstance(instruction, Rack_Instruction):  # Inject a racking instruction to get the merged machine state aligned with the current swatch
            self._rack_to_current_swatch(instruction_source)
        if isinstance(instruction, Needle_Instruction):
            # update instruction to align with needle slots based on origin swatch
            merge_instruction = self.needle_instruction_in_merged_swatch(instruction, instruction_source)
            if isinstance(merge_instruction, Loop_Making_Instruction):  # Long floats may be created by this operation
                for carrier, float_values in self._get_floats_to_instruction(merge_instruction).items():
                    float_len = float_values[0]
                    float_direction = float_values[1]
                    if float_len >= max_float:
                        assert float_direction is not Carriage_Pass_Direction.Rightward, f"Cutting a Rightward float to consume instruction {instruction}"
                        self._cut_and_reinsert_carrier(carrier, instruction_source)
                self._inhook_missing_carriers(merge_instruction, instruction_source)  # Inject any remaining carriers that will be needed by this instruction.
        else:
            merge_instruction = instruction  # There is no difference between the merged instruction and its source.
        self._add_instruction_to_merge(merge_instruction, instruction_source, instruction)

    def _consume_next_instruction(self, remove_connections: bool = False, max_float: int = 15) -> None:
        """
        Consumes the next instruction in the current swatch.
        This will update the merged program and merged program machine state and inject any necessary operations to keep the merged program aligned.

        Args:
            remove_connections (bool, optional): If True, any connections found in the consumed instruction are removed from the search space. Defaults to False.
            max_float (int, optional): Maximum number yarn-floating distances allowed between operations without introducing a cut and reinsert. Defaults to 15.
        """
        assert self.next_instruction is not None, f"Cannot consume instruction from empty swatch: {self.current_swatch}"
        self._consume_instruction(self.next_instruction, self.current_swatch_side, remove_connections, max_float)
        self.increment_next_index()

    # def _merge_in_consumed_instructions(self, consumed_instructions: list[Knitout_Line]) -> None:
    #     """
    #     Consumes the given instructions, presuming they are from the current swatch.
    #     Args:
    #         consumed_instructions (list[Knitout_Line]): The instructions to consume.
    #     """
    #     for instruction in consumed_instructions:
    #         self._consume_instruction(instruction, self.current_swatch_side)

    @property
    def next_instruction(self) -> Knitout_Line | None:
        """
        Returns:
            Knitout_Line | None: The next instruction to consume from the current swatch or None if the current swatch is fully consumed.
        """
        if self.current_swatch_is_consumed:
            return None
        assert isinstance(self.next_index, int)
        return self.current_swatch.knitout_program[self.next_index]

    @property
    def cp_index_of_next_instruction(self) -> int | None:
        """
        Returns:
            int | None: The course index of the next instruction in the current swatch or None if the current swatch is fully consumed.
        """
        if self.next_instruction is None:
            return None
        return self.current_swatch.get_carriage_pass_index_of_instruction(self.next_instruction)

    def _consume_from_current_swatch(self, end_on_entrances: bool = True, end_on_exits: bool = True,
                                     end_on_carriage_pass_index: int | None = None,
                                     remove_connections: bool = True) -> None:
        """
        Consumes instructions from the current swatch up to the specified stopping points.

        Args:
            end_on_entrances (bool, optional): If true, stops consuming before any entrances found on the swatch boundary.
            end_on_exits (bool, optional): If true, stops consuming before any exits found on the swatch boundary.
            end_on_carriage_pass_index (int, optional): Stops consuming before reaching the indicated carriage pass. Defaults to consuming all carriage passes.
            remove_connections (bool, optional): If true, removes any possible connections between swatches using the consumed instructions. Defaults to True.
        """
        while self.next_instruction is not None:
            if end_on_carriage_pass_index is not None:
                cp_index = self.current_swatch.get_carriage_pass_index_of_instruction(self.next_instruction)
                if cp_index is not None and cp_index >= end_on_carriage_pass_index:
                    return  # Do not consume next instruction.
            if end_on_entrances and self.next_instruction_is_boundary_entrance:
                return  # Do not consume next Instruction.
            if end_on_exits and self.next_instruction_is_boundary_exit:
                return  # DO not consume next Instruction
            self._consume_next_instruction(remove_connections=remove_connections)

    def _consume_to_instruction(self, target_instruction: Knitout_Line, remove_connections: bool = True) -> None:
        """
        Consumes from the current swatch until the target instruction is found or the swatch is fully consumed.
        Args:
            target_instruction (Knitout_Line): The instruction to consume up to.
            remove_connections (bool, optional): If true, removes any possible connections between swatches using the consumed instructions. Defaults to True.
        """
        while self.next_instruction is not None and self.next_instruction != target_instruction:
            self._consume_next_instruction(remove_connections)

    def _consume_up_to_first_courses(self) -> None:
        """
        Consumes up to the starting carriage passes of each swatch based on the interval of the course-wise swatch connection.
        """
        self._consume_from_current_swatch(end_on_entrances=False, end_on_exits=False, end_on_carriage_pass_index=self.first_courses_by_side[self.current_swatch_side], remove_connections=True)
        self.swap_swatch_sides()
        self._consume_from_current_swatch(end_on_entrances=False, end_on_exits=False, end_on_carriage_pass_index=self.first_courses_by_side[self.current_swatch_side], remove_connections=True)
        self.swap_swatch_sides()  # return to first swatch for merging process

    def _available_connections(self, boundary_instruction: Course_Boundary_Instruction,
                               excluded_boundaries: set[Course_Boundary_Instruction] | None = None, max_cp_jumps: int = 4) -> set[Course_Seam_Connection]:
        """
        Args:
            boundary_instruction (Course_Boundary_Instruction): The boundary instruction to find connections from.
            excluded_boundaries (set[Course_Boundary_Instruction], optional: The set of boundary instructions to exclude from the available connections. Defaults to the empty set.
            max_cp_jumps (int, optional): The maximum number carriage passes allowed to be jumped to form a connection. Defaults to 4.

        Returns:
            set[Course_Seam_Connection]:
                The set of available connections in the seam search space from the given boundary instruction.
                * Available connections will be refined to those that do not require carriage pass jumps greater than the specified amount.
                * If there are connections that will not require long floats to be cut, only those connections will be returned. Otherwise, connections that require cut-floats will be returned.

        """
        if boundary_instruction not in self.seam_search_space.seam_network:
            return set()
        if excluded_boundaries is None:
            excluded_boundaries = set()
        if isinstance(boundary_instruction.instruction, Xfer_Instruction):
            max_cp_jumps = 0  # Never jump ahead just to connect xfers
        next_left_cp = self.cp_index_of_next_left_needle_instruction
        if next_left_cp is None:
            next_left_cp = -1
        next_right_cp = self.cp_index_of_next_right_needle_instruction
        if next_right_cp is None:
            next_right_cp = -1
        max_cp = max(next_left_cp, next_right_cp)
        max_cp += max_cp_jumps
        if boundary_instruction.is_entrance:
            potential_connections = set(self.seam_search_space.get_connection(e, boundary_instruction)
                                        for e in self.seam_search_space.seam_network.predecessors(boundary_instruction)
                                        if e.carriage_pass_index <= max_cp)
        else:
            potential_connections = set(self.seam_search_space.get_connection(boundary_instruction, e)
                                        for e in self.seam_search_space.seam_network.successors(boundary_instruction)
                                        if e.carriage_pass_index <= max_cp)
        potential_connections = set(c for c in potential_connections if c.exit_instruction not in excluded_boundaries and c.entrance_instruction not in excluded_boundaries)

        def _safe_connection(c: Course_Seam_Connection) -> bool:
            """
            Args:
                c (Course_Seam_Connection): The connection to safety check.

            Returns:
                bool:
                    True if the connection is safe, False otherwise.
                    A connection is safe if it meets the following criteria:
                    * The jump distance is less than the specified maximum number of carriage pass jumps (defaults to 4)
                    * The floats created by the connection do not supersede the maximum float length.

            """
            jump_distance = self._get_distance_to_connection_jump(c)
            if jump_distance >= max_cp_jumps:
                return False
            return not self._has_dangerous_float(c)

        safe_connections = set(c for c in potential_connections if _safe_connection(c))
        return safe_connections

    def _connection_cost(self, connection: Course_Seam_Connection) -> tuple[int, int, int]:
        """
        Args:
            connection (Course_Seam_Connection): The connection to identify the cost of.

        Returns:
            tuple[int, int, int]:
                A tuple specifying different costs of forming the given connection. The tuple contains:
                * The differences between the carrier sets of the connection.
                * The number of long floats that must be cut to form this connection.
                * The number of carriage passes that must be jumped to form this connection.

        """
        jump_distance = self._get_distance_to_connection_jump(connection)
        floats_cut = self.floats_requires_cut(connection)
        return connection.different_carriers, floats_cut, jump_distance

    def best_connection(self, boundary_instruction: Course_Boundary_Instruction) -> Course_Seam_Connection | None:
        """
        Args:
            boundary_instruction (Course_Boundary_Instruction): The boundary instruction to find the best connection from.

        Returns:
            Course_Seam_Connection | None: The best available connection from the given boundary instruction or None if there are no connections available.

        """
        preference = self.preferred_connection(boundary_instruction)
        if isinstance(preference, Course_Seam_Connection) and self._connection_is_stable(preference):
            return preference
        return None

    def preferred_connection(self, boundary_instruction: Course_Boundary_Instruction, excluded_boundaries: set[Course_Boundary_Instruction] | None = None) -> Course_Seam_Connection | None:
        """
        Args:
            boundary_instruction (boundary_instruction): The boundary instruction to find the best connection from.
            excluded_boundaries (set[Course_Boundary_Instruction], optional): The set of boundary instructions to exclude from potential connections. Defaults to the empty set.

        Returns:
            Course_Seam_Connection | None: The lowest cost connection from the given boundary instruction or None if there are no connections available.

        """
        potential_connections = self._available_connections(boundary_instruction, excluded_boundaries=excluded_boundaries)
        if len(potential_connections) == 0:
            return None
        return min(potential_connections, key=self._connection_cost)  # Note: Min of tuple will compare elements step wise (first element < first element then second element < second element)

    def _get_boundaries_upto_connection(self, connection: Course_Seam_Connection) -> list[Course_Boundary_Instruction]:
        """
        Args:
            connection (Course_Seam_Connection): The connection that may skip over existing boundaries.

        Returns:
            list[Course_Boundary_Instruction]: Boundary instruction in the non-current (next) swatch that will be skipped by the given connection.
        """
        next_swatch_current_cp, target_cp = self._get_carriage_pass_range_upto_connection(connection)
        if self.current_swatch_side is Course_Side.Right:  # look at left swatch
            return [self.seam_search_space.left_swatch_boundaries_by_course_index[i] for i in range(next_swatch_current_cp, target_cp)]
        else:  # look at right swatch
            return [self.seam_search_space.right_swatch_boundaries_by_course_index[i] for i in range(next_swatch_current_cp, target_cp)]

    def _connection_is_stable(self, connection: Course_Seam_Connection) -> bool:
        """
        Args:
            connection (Course_Seam_Connection): The connection to check for stability.

        Returns:
            bool:
            True if the connection is stable, False otherwise. A connection is stable if there are no other boundaries that will be skipped by forming this connection that would have a lower cost.


        """
        c_cost = self._connection_cost(connection)
        for alternate_boundary in self._get_boundaries_upto_connection(connection):
            alternate_connection = self.preferred_connection(alternate_boundary, excluded_boundaries={connection.exit_instruction, connection.entrance_instruction})
            if alternate_connection is not None:
                a_cost = self._connection_cost(alternate_connection)
                if a_cost < c_cost:
                    return False
        return True

    def floats_requires_cut(self, connection: Course_Seam_Connection, max_float_length: int = 10) -> int:
        """
        Args:
            connection (Course_Seam_Connection): The connection to identify the find the number of floats from.
            max_float_length (int, optional): The maximum length of allowed floats. Defaults to 10.

        Returns:
            int: The number of floats that will need to be cut if the given connection is formed.
        """
        floats_by_cid = self._get_floats_upto_connection(connection)
        long_floats = [f for f, _ in floats_by_cid.values() if f >= max_float_length]
        return len(long_floats)

    def _has_dangerous_float(self, connection: Course_Seam_Connection, max_float_length: int = 10) -> bool:
        """
        Args:
            connection (Course_Seam_Connection): The connection to test for dangerous long floats.
            max_float_length (int, optional): The maximum length of allowed floats. Defaults to 10.

        Returns:
            bool: True if there are any dangerous floats formed by the connection. False, otherwise.
            A float is dangerous if it would need to be cut and requires yarn-insertion in an invalid rightward direction.
        """
        floats_by_cid = self._get_floats_upto_connection(connection)
        return any(float_len >= max_float_length and float_dir == Carriage_Pass_Direction.Rightward
                   for float_len, float_dir in floats_by_cid.values())

    def _get_floats_upto_connection(self, connection: Course_Seam_Connection) -> dict[Yarn_Carrier, tuple[int, Carriage_Pass_Direction]]:
        """
        Args:
            connection (Course_Seam_Connection): The connection that may form floats.

        Returns:
            dict[Yarn_Carrier, tuple[int, Carriage_Pass_Direction]:
                A dictionary that maps carriers to a tuple containing the required float length and direction that the float will be formed by the connection.
                Only non-zero floats will be included.
        """
        carriage_passes_to_instruction = self._get_carriage_passes_upto_connection(connection)
        floats_by_carrier: dict[Yarn_Carrier, tuple[int, Carriage_Pass_Direction]] = {}
        found_carriers: set[Yarn_Carrier] = set()
        for cp in carriage_passes_to_instruction:
            next_instruction = cp.first_instruction
            if isinstance(next_instruction, Loop_Making_Instruction):
                new_floats = self._instruction_creates_float(next_instruction, ignore_carriers=found_carriers)
                if not isinstance(next_instruction, Miss_Instruction):
                    found_carriers.update(next_instruction.get_carriers(self.merged_program_machine_state).values())  # Any carriers that have formed loops can be ignored from now on
                floats_by_carrier.update(new_floats)
                if len(floats_by_carrier) >= len(self.merged_program_machine_state.carrier_system.active_carriers):
                    return floats_by_carrier  # All possible floats found.
        if connection.exit_instruction.source_swatch_name == self.current_swatch.name and isinstance(connection.entrance_instruction.instruction, Loop_Making_Instruction):  # exiting current swatch
            floats_by_carrier.update(self._instruction_creates_float(connection.entrance_instruction.instruction, ignore_carriers=found_carriers))
        return floats_by_carrier

    def _instruction_creates_float(self, instruction: Loop_Making_Instruction, ignore_carriers: set[Yarn_Carrier]) -> dict[Yarn_Carrier, tuple[int, Carriage_Pass_Direction]]:
        """
        Args:
            instruction (Loop_Making_Instruction): An instruction that may form a float.
            ignore_carriers (set[Yarn_Carrier]): The set of carriers to ignore floats from.

        Returns:
            dict[Yarn_Carrier, tuple[int, Carriage_Pass_Direction]:
                A dictionary that maps carriers to a tuple containing the required float length and direction that the float will be formed by the given instruction.
                Only non-zero length floats and floats of carriers that were not ignored are included.
        """
        if len(instruction.carrier_set) == 0:  # No floats formed by the instruction
            return {}
        merge_instruction = self.needle_instruction_in_merged_swatch(instruction, self.current_swatch_side)
        assert isinstance(merge_instruction, Loop_Making_Instruction)
        carriers_to_floats = self._get_floats_to_instruction(merge_instruction)
        return {carrier: float_value for carrier, float_value in carriers_to_floats.items() if carrier not in ignore_carriers}

    def _get_carriage_pass_range_upto_connection(self, connection: Course_Seam_Connection) -> tuple[int, int]:
        """
        Args:
            connection (Course_Seam_Connection): The connection to find the range of carriage passes jumped in the next (non-current) swatch.

        Returns:
            tuple[int, int]: The range of carriage pass indices jumped by the given connection.
        """
        next_swatch_current_cp = self.cp_index_of_next_needle_instruction_in_next_swatch
        assert isinstance(next_swatch_current_cp, int), f"Expected connection {connection} to jump into at least one operation in the next swatch"
        target_cp = self._get_cp_index_of_connection_jump(connection)
        return next_swatch_current_cp, target_cp

    def _get_carriage_passes_upto_connection(self, connection: Course_Seam_Connection) -> list[Carriage_Pass]:
        """
        Args:
            connection (Course_Seam_Connection): The connection to find all carriage passes from the current instruction to the instruction in the connection that belongs to the next swatch.

        Returns:
            list[Carriage_Pass]: The list of carriage passes that will be executed on the next swatch in order to form this connection.
        """
        next_swatch_current_cp, target_cp = self._get_carriage_pass_range_upto_connection(connection)
        return self.next_swatch.carriage_passes[next_swatch_current_cp: target_cp]

    def _get_distance_to_connection_jump(self, connection: Course_Seam_Connection, count_xfer_passes: bool = False) -> int:
        """
        Args:
            connection (connection): The connection that may cause a jump in carriage passes in the non-current (next) swatch.
            count_xfer_passes (bool, optional): If True, xfer passes are counted towards the distance. Otherwise, they are excluded from the distance. Defaults to False.

        Returns:
            int: The number of carriage passes jumped in the non-current swatch in order to form the given connection.
        """
        if count_xfer_passes:
            current_cp, target_cp = self._get_carriage_pass_range_upto_connection(connection)
            return target_cp - current_cp
        else:
            return len([cp for cp in self._get_carriage_passes_upto_connection(connection) if not cp.xfer_pass])

    def _get_cp_index_of_connection_jump(self, connection: Course_Seam_Connection) -> int:
        """
        Args:
            connection (Course_Seam_Connection): The connection to find the jump carriage pass of.

        Returns:
            int: The index of the carriage pass that owns the instruction on the jump side of the connection. The jump is from the current swatch to the next swatch.

        """
        cp_index = self.next_swatch.get_cp_index_of_instruction(self._get_jump_of_connection(connection).instruction)
        assert cp_index is not None, f"Expected {connection} to jump to a valid carriage pass."
        return cp_index

    def _get_jump_of_connection(self, connection: Course_Seam_Connection) -> Course_Boundary_Instruction:
        """
        Args:
            connection (Course_Seam_Connection): The connection to determine which side of the connection is being jumped to.

        Returns:
            Course_Boundary_Instruction: The exit of this connection if the exit belongs to the next swatch or the entrance if te entrance belongs to the next swatch.
        """
        if connection.exit_instruction.source_swatch_name == self.next_swatch.name:
            return connection.exit_instruction
        else:
            return connection.entrance_instruction

    def _get_cp_index_of_instruction(self, instruction: Needle_Instruction) -> int:
        """
        Args:
            instruction (Needle_Instruction): The needle instruction to find the carriage pass index of in its owning swatch.

        Returns:
            int: The index of the carriage pass that owns the instruction in the swatch that owns the instruction.

        """
        cp_index = self.left_swatch.get_cp_index_of_instruction(instruction)
        if cp_index is None:
            cp_index = self.right_swatch.get_cp_index_of_instruction(instruction)
        if cp_index is None:
            raise ValueError(f"Could not find {instruction} in left or right swatch")
        return cp_index

    def merge_swatches(self, xfer_exit_buffer: int = 5) -> [Knitout_Line]:
        """
        Merges the left and right swatch and forms a merged swatch program and updates the machine state according to that merged program.

        Args:
            xfer_exit_buffer (int, optional): The distance in needles of that a xfer instruction must be within to allow for a connection to be formed. Defaults to 5.

        Returns:
            list[Knitout_Line]: A list of instructions in the merged program.
        """
        self._consume_up_to_first_courses()
        # Start Merge process
        while not self.left_swatch_is_consumed and not self.right_swatch_is_consumed:
            # Consume up to next boundary instruction or until reaching top course to merge.
            self._consume_from_current_swatch(end_on_exits=True, end_on_entrances=True, end_on_carriage_pass_index=self.last_courses_by_side[self.current_swatch_side], remove_connections=False)
            if self.next_instruction is None:  # Swatch is fully consumed.
                self.swap_swatch_sides()
                break  # end the merge process and continue into the next swatch.
            if self._current_swatch_consumed():
                # Swatch was consumed up to target course
                break  # end merge process without swapping. The remainder of the courses will be consumed before completing the next swatch.
            elif self.next_instruction_is_boundary_exit:
                exit_instruction = self.current_swatch.get_course_boundary_instruction(self.next_instruction)
                assert isinstance(exit_instruction, Course_Boundary_Instruction)
                assert exit_instruction.is_exit
                if isinstance(exit_instruction.instruction, Xfer_Instruction) and exit_instruction.needle.position < (self.current_swatch.width - xfer_exit_buffer):  # Todo: what is the buffer for?
                    best_connection = None
                else:
                    best_connection = self.best_connection(exit_instruction)
                self._consume_next_instruction(remove_connections=True)  # Consumes the exit instruction
                if best_connection is not None:  # Otherwise continue in the current swatch, ignoring that possible connection
                    self.swap_swatch_sides()
                    self._consume_to_instruction(best_connection.entrance_instruction.instruction)
                    self._consume_next_instruction(remove_connections=True)  # consumes the entrance
            elif self.next_instruction_is_boundary_entrance:
                entrance_instruction = self.current_swatch.get_course_boundary_instruction(self.next_instruction)
                assert isinstance(entrance_instruction, Course_Boundary_Instruction)
                assert entrance_instruction.is_entrance
                best_connection = self.best_connection(entrance_instruction)
                if best_connection is not None:  # Otherwise continue in the current swatch, ignoring that possible connection.
                    self.swap_swatch_sides()
                    self._consume_to_instruction(best_connection.exit_instruction.instruction)  # Consume up from the other swatch to the exit that aligns with the found entrance.
                    self._consume_next_instruction(remove_connections=True)  # Consume the exit before the entrance connection is formed.
                    self.swap_swatch_sides()  # swap back to the current swatch and continue from the found entrance instruction.
                self._consume_next_instruction(remove_connections=True)

        # Consume remainder of current swatch
        self._consume_from_current_swatch(end_on_entrances=False, end_on_exits=False, remove_connections=True)
        self.swap_swatch_sides()
        # Consume remainder of last swatch
        self._consume_from_current_swatch(end_on_entrances=False, end_on_exits=False, remove_connections=True)
        for active_carrier in self.merged_program_machine_state.carrier_system.active_carriers:
            outhook = Outhook_Instruction(active_carrier, 'Outhook remaining active carriers')
            self._release_to_merge_instruction(outhook, self.current_swatch_side)
            self._add_instruction_to_merge(outhook, self.current_swatch_side)
        self._specify_sources_in_merged_instructions()
        return [instruction for instruction, _source in self.merged_instructions]

    def _specify_sources_in_merged_instructions(self) -> None:
        """
        Updates the line numbers and comments of the instructions in the merged program. Instructions copied from a swatch will include source information in the comment.
        """
        for line_number, instruction_info in enumerate(self.merged_instructions):
            instruction = instruction_info[0]
            if instruction.original_line_number is not None:
                if instruction.comment is None:
                    instruction.comment = ""
                instruction.comment += f" from line {instruction.original_line_number} of {instruction_info[1]} swatch"
            instruction.original_line_number = line_number

    def _current_swatch_consumed(self) -> bool:
        """
        Returns:
            bool: True if the current swatch is consumed through the last course of the Course Wise Connection interval. False, otherwise.
        """
        cp_index = self.cp_index_of_next_needle_instruction_in_current_swatch
        return cp_index is not None and (self.last_courses_by_side[self.current_swatch_side] <= cp_index)

    def write_knitout(self, merge_name: str | None = None) -> None:
        """
        Creates a knitout file of the given merge name of the merged instructions from this merger.

        Args:
            merge_name (str, optional): The name of the merged swatch knitout file. Defaults to cwm_<the left_swatch's name>_to_<the right_swatch's name>.
        """
        if merge_name is None:
            merge_name = f"cwm_{self.left_swatch.name}_to_{self.right_swatch.name}"
        with open(f'{merge_name}.k', 'w') as merge_file:
            clean_merged_instructions = [f"{str(instruction).splitlines()[0]}\n" for instruction, _side in self.merged_instructions]
            merge_file.writelines(clean_merged_instructions)

    def compile_to_dat(self, merge_name: str | None = None) -> None:
        """
        Creates a knitout file and compiled DAT file of the given merge name of the merged instructions from this merger.

        Args:
            merge_name (str, optional): The name of the merged swatch knitout file. Defaults to cwm_<the left_swatch's name>_to_<the right_swatch's name>.
        """
        if merge_name is None:
            merge_name = f"cwm_{self.left_swatch.name}_to_{self.right_swatch.name}"
        self.write_knitout(merge_name)
        knitout_to_dat(f"{merge_name}.k", f"{merge_name}.dat")
