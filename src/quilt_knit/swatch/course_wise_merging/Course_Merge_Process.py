"""Module for linking Swatches by vertical seams"""
import warnings

from knitout_interpreter.knitout_execution import Knitout_Executer
from knitout_interpreter.knitout_execution_structures.Carriage_Pass import Carriage_Pass
from knitout_interpreter.knitout_operations.carrier_instructions import (
    Inhook_Instruction,
    Outhook_Instruction,
)
from knitout_interpreter.knitout_operations.knitout_instruction_factory import (
    build_instruction,
)
from knitout_interpreter.knitout_operations.Knitout_Line import Knitout_Line
from knitout_interpreter.knitout_operations.needle_instructions import (
    Loop_Making_Instruction,
    Miss_Instruction,
    Needle_Instruction,
    Xfer_Instruction,
)
from virtual_knitting_machine.knitting_machine_warnings.carrier_operation_warnings import (
    Mismatched_Releasehook_Warning,
)
from virtual_knitting_machine.knitting_machine_warnings.Needle_Warnings import (
    Knit_on_Empty_Needle_Warning,
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
from quilt_knit.swatch.Merge_Process import Merge_Process
from quilt_knit.swatch.Swatch import Swatch
from quilt_knit.swatch.Swatch_Connection import Swatch_Connection


class Course_Merge_Process(Merge_Process):
    """Class to manage a horizontal merge process between two swatches."""

    def __init__(self, swatch_connection: Course_Wise_Connection,
                 seam_search_space: Course_Seam_Search_Space | None = None):
        if seam_search_space is None:
            seam_search_space = Course_Seam_Search_Space(swatch_connection.left_swatch, swatch_connection.right_swatch)
        super().__init__(swatch_connection, Course_Side.Left, seam_search_space)
        self.seam_search_space.remove_boundaries_beyond_course_connections(self.course_wise_connection)
        self._next_instruction_index_by_side: dict[Course_Side, int | None] = {Course_Side.Left: 0, Course_Side.Right: 0}
        self._set_merge_direction()

    @property
    def course_wise_connection(self) -> Course_Wise_Connection:
        """
        Returns:
            Course_Wise_Connection: The connection between the two swatches being merged.
        """
        assert isinstance(self._swatch_connection, Course_Wise_Connection)
        return self._swatch_connection

    @property
    def seam_search_space(self) -> Course_Seam_Search_Space:
        """
        Returns:
            Course_Seam_Search_Space: The seam search space between entrance-exit instructions along the swatch boundaries being merged.
        """
        assert isinstance(self._seam_search_space, Course_Seam_Search_Space)
        return self._seam_search_space

    @property
    def current_course_merge_side(self) -> Course_Side:
        """
        Returns:
            Course_Side: The side of the merge that the program is currently consuming from.
        """
        assert isinstance(self._current_merge_side, Course_Side)
        return self._current_merge_side

    @current_course_merge_side.setter
    def current_course_merge_side(self, course_side: Course_Side) -> None:
        self._current_merge_side = course_side

    def get_original_cp_index(self, carriage_pass: Carriage_Pass) -> tuple[None | int, None | int]:
        """
        Args:
            carriage_pass (Carriage_Pass): A carriage pass in the swatch resulting from this merge.

        Returns:
            tuple[None | int, None | int]:
                A tuple containing the carriage pass indices in the original left and right swatches that created this carriage pass.
                These indices are None if the carriage pass does not contain instructions from a given side.

        Raises
            KeyError: If the carriage pass does not belong to the merged swatch.
        """
        left_index = None
        right_index = None
        for instruction in carriage_pass:
            if instruction not in self._merged_instructions_to_source:
                raise KeyError(f"Instruction {instruction} not found in merged swatch")
            source = self._merged_instructions_to_source[instruction]
            if source is not None:
                if left_index is None and source[0] is Course_Side.Left:
                    left_index = self.left_swatch.get_cp_index_of_instruction(source[1])
                elif right_index is None and source[0] is Course_Side.Right:
                    right_index = self.right_swatch.get_cp_index_of_instruction(source[1])
            if left_index is not None and right_index is not None:
                break
        return left_index, right_index

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
                self.current_course_merge_side: Course_Side = Course_Side.Right
            else:  # leftward direction or xfer
                self.current_course_merge_side: Course_Side = Course_Side.Left
        elif self.course_wise_connection.right_start_direction is Carriage_Pass_Direction.Leftward:
            self.current_course_merge_side: Course_Side = Course_Side.Right
        elif self.course_wise_connection.left_start_direction is Carriage_Pass_Direction.Rightward:
            self.current_course_merge_side: Course_Side = Course_Side.Left

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
    def current_swatch(self) -> Swatch:
        """
        Returns:
            Swatch: The current swatch to consume instructions from.
        """
        if self.current_course_merge_side is Course_Side.Left:
            return self.left_swatch
        else:
            return self.right_swatch

    @property
    def next_swatch(self) -> Swatch:
        """
        Returns:
            Swatch: The next swatch to consume instructions from. This will be the opposite of the current swatch.
        """
        if self.current_course_merge_side is Course_Side.Left:
            return self.right_swatch
        else:
            return self.left_swatch

    def boundary_in_left_swatch(self, boundary_instruction: Course_Boundary_Instruction) -> bool:
        """
        Args:
            boundary_instruction (Course_Boundary_Instruction): The boundary instruction to check which swatch it belongs to.

        Returns:
            bool: True if the boundary instruction belongs to the left swatch, False otherwise.
        """
        return boundary_instruction.source_swatch_name == self.left_swatch.name

    def boundary_in_right_swatch(self, boundary_instruction: Course_Boundary_Instruction) -> bool:
        """
        Args:
            boundary_instruction (Course_Boundary_Instruction): The boundary instruction to check which swatch it belongs to.

        Returns:
            bool: True if the boundary instruction belongs to the right swatch, False otherwise.
        """
        return boundary_instruction.source_swatch_name == self.right_swatch.name

    @property
    def first_course_on_current_side(self) -> int:
        """
        Returns:
            int: The index of the first course to be merged on the current working swatch.
        """
        if self._current_merge_side is Course_Side.Left:
            return self.course_wise_connection.left_bottom_course
        else:
            return self.course_wise_connection.right_bottom_course

    @property
    def last_course_on_current_side(self) -> int:
        """
        Returns:
            int: The index of the last course to be merged on the current working swatch.
        """
        if self._current_merge_side is Course_Side.Left:
            return self.course_wise_connection.left_top_course
        else:
            return self.course_wise_connection.right_top_course

    @property
    def next_index(self) -> int | None:
        """
        Returns:
            int | None: The next index of instructions to consume from the current swatch or None if the current swatch is fully consumed.
        """
        return self._next_instruction_index_by_side[self.current_course_merge_side]

    @property
    def next_index_in_next_swatch(self) -> int | None:
        """
        Returns:
            int | None: The next index of instructions to consume from the swatch not being consumed or None if that swatch is fully consumed.

        """
        return self._next_instruction_index_by_side[~self.current_course_merge_side]

    def increment_next_index(self) -> None:
        """
            Increments the index pointing to the next instruction in the current swatch.
        """
        next_index = self.next_index
        if isinstance(next_index, int):
            if next_index + 1 >= len(self.current_swatch.knitout_program):
                self._next_instruction_index_by_side[self.current_course_merge_side] = None
            else:
                self._next_instruction_index_by_side[self.current_course_merge_side] = next_index + 1

    @next_index.setter
    def next_index(self, next_index_of_current_swatch: int) -> None:
        """
        Sets the next index of instructions to consume from the current swatch. If that index moves beyond the length of the current swatch, next index is set to None.

        Args:
            next_index_of_current_swatch (int): The next index of instructions to consume from the current swatch.
        """
        if next_index_of_current_swatch >= len(self.current_swatch.knitout_program):
            self._next_instruction_index_by_side[self.current_course_merge_side] = None
        else:
            self._next_instruction_index_by_side[self.current_course_merge_side] = next_index_of_current_swatch

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
        if self.current_course_merge_side is Course_Side.Left:
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
        if self.current_course_merge_side is Course_Side.Left:
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

    def swap_swatch_sides(self) -> None:
        """
        Swaps which swatch is the current swatch vs the next swatch to consume from.
        """
        self.current_course_merge_side = ~self.current_course_merge_side

    @property
    def current_boundary_side(self) -> Course_Side:
        """
        Returns:
            Course_Side: The boundary of the current swatch to merge from.
        """
        return self.current_course_merge_side.opposite

    @property
    def next_instruction_is_boundary_entrance(self) -> bool:
        """
        Returns:
            bool: True if the next instruction is on the relevant boundary entrance of the current swatch. False, otherwise
        """
        if self.next_instruction is None:
            return False
        elif self.current_boundary_side is Course_Side.Left:
            return self.current_swatch.instruction_is_left_entrance(self.next_instruction)
        else:  # self.current_boundary_side is Course_Side.Right:
            return self.current_swatch.instruction_is_right_entrance(self.next_instruction)

    @property
    def next_instruction_is_boundary_exit(self) -> bool:
        """
        Returns:
            bool: True if the next instruction is on the relevant boundary exit of the current swatch. False, otherwise
        """
        if self.next_instruction is None:
            return False
        elif self.current_boundary_side is Course_Side.Left:
            return self.current_swatch.instruction_is_left_exit(self.next_instruction)
        else:  # self.current_boundary_side is Course_Side.Right:
            return self.current_swatch.instruction_is_right_exit(self.next_instruction)

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

    def _needle_instruction_in_merged_swatch(self, needle_instruction: Needle_Instruction, source_swatch_side: Course_Side) -> Needle_Instruction:
        """
        Args:
            needle_instruction (Needle_Instruction): The needle instruction to copy for the merged program.
            source_swatch_side (Course_Side): The source swatch of the given needle instruction.

        Returns:
            Needle_Instruction:
                The needle instruction adjusted for the position in the merged program.
                This is the same instruction from the left swatch and a copy shifted by the width of the left swatch for instructions from the right swatch.

        """
        if source_swatch_side is None or source_swatch_side is Course_Side.Left:
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

    def _consume_next_instruction(self, remove_connections: bool = False, max_float: int = 15) -> None:
        """
        Consumes the next instruction in the current swatch.
        This will update the merged program and merged program machine state and inject any necessary operations to keep the merged program aligned.

        Args:
            remove_connections (bool, optional): If True, any connections found in the consumed instruction are removed from the search space. Defaults to False.
            max_float (int, optional): Maximum number yarn-floating distances allowed between operations without introducing a cut and reinsert. Defaults to 15.
        """
        assert self.next_instruction is not None, f"Cannot consume instruction from empty swatch: {self.current_swatch}"
        next_instruction = self.next_instruction
        if isinstance(next_instruction, Outhook_Instruction) and self._other_swatch_expects_carrier(next_instruction.carrier_id):
            self.increment_next_index()
            return
        if isinstance(next_instruction, Inhook_Instruction):
            self.increment_next_index()
            return  # Skip inhooks form the original swatches. Only use the inhooks that are injected as needed.
        self._consume_instruction(self.next_instruction, self.current_course_merge_side, remove_connections, max_float)
        self.increment_next_index()

    def _other_swatch_expects_carrier(self, carrier_id: int) -> bool:
        for instruction in self.next_swatch.knitout_program[self.next_index_in_next_swatch:]:
            if isinstance(instruction, Inhook_Instruction) and instruction.carrier_id == carrier_id:
                return False  # found inhook in next swatch
            elif isinstance(instruction, Needle_Instruction) and instruction.carrier_set is not None and carrier_id in instruction.carrier_set:
                return True
        return False

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
        self._consume_from_current_swatch(end_on_entrances=False, end_on_exits=False, end_on_carriage_pass_index=self.first_course_on_current_side, remove_connections=True)
        self.swap_swatch_sides()
        self._consume_from_current_swatch(end_on_entrances=False, end_on_exits=False, end_on_carriage_pass_index=self.first_course_on_current_side, remove_connections=True)
        self.swap_swatch_sides()  # return to first swatch for merging process

    def _available_connections(self, boundary_instruction: Course_Boundary_Instruction,
                               excluded_boundaries: set[Course_Boundary_Instruction] | None = None, max_cp_jumps: int = 4) -> set[Course_Seam_Connection]:
        """
        Args:
            boundary_instruction (Course_Boundary_Instruction): The boundary instruction to find connections from.
            excluded_boundaries (set[Course_Boundary_Instruction], optional): The set of boundary instructions to exclude from the available connections. Defaults to the empty set.
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
            return set()  # No Connections because we are at the end of the left swatch
        next_right_cp = self.cp_index_of_next_right_needle_instruction
        if next_right_cp is None:
            return set()  # No connections because we are at the en dof the right swatch
        max_cp = max(next_left_cp, next_right_cp)
        max_cp += max_cp_jumps

        def _potential_connection(c: Course_Seam_Connection) -> bool:
            """
            Args:
                c (Swatch_Connection): The current swatch connection to check.

            Returns:
                bool: True if the connection is a valid connection in the carriage pass range. False, otherwise.
            """
            return (c.exit_instruction.carriage_pass_index <= max_cp and c.entrance_instruction.carriage_pass_index <= max_cp
                    and c.exit_instruction not in excluded_boundaries and c.entrance_instruction not in excluded_boundaries)

        potential_connections: set[Course_Seam_Connection] = set(c for c in self.seam_search_space.available_connections(boundary_instruction)
                                                                 if isinstance(c, Course_Seam_Connection) and _potential_connection(c))

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
            if jump_distance > max_cp_jumps:
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
        if self.current_course_merge_side is Course_Side.Right:  # look at left swatch
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

    def floats_requires_cut(self, connection: Course_Seam_Connection, max_float_length: int = 15) -> int:
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

    def _has_dangerous_float(self, connection: Course_Seam_Connection, max_float_length: int = 15) -> bool:
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
                    found_carriers.update(next_instruction.get_carriers(self._merged_program_machine_state).values())  # Any carriers that have formed loops can be ignored from now on
                floats_by_carrier.update(new_floats)
                if len(floats_by_carrier) >= len(self._merged_program_machine_state.carrier_system.active_carriers):
                    return floats_by_carrier  # All possible floats found.
        if connection.exit_instruction.source_swatch_name == self.current_swatch.name and isinstance(connection.entrance_instruction.instruction, Loop_Making_Instruction):  # exiting current swatch
            floats_by_carrier.update(self._instruction_creates_float(connection.entrance_instruction.instruction, ignore_carriers=found_carriers))
        return floats_by_carrier

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

    def _consume_connection(self, connection: Course_Seam_Connection) -> None:
        """
        Consumes instructions from both swatches to form the given connection. Removes any possible connections consumed in this process.
        Args:
            connection (Course_Seam_Connection): The connection to merge into the swatch.
        """
        if connection.xfer_connection:
            if self.current_course_merge_side == Course_Side.Right:
                self.swap_swatch_sides()
            if self.boundary_in_left_swatch(connection.exit_instruction):
                left_boundary = connection.exit_instruction
                assert self.boundary_in_right_swatch(connection.entrance_instruction)
                right_boundary = connection.entrance_instruction
            else:
                assert self.boundary_in_left_swatch(connection.entrance_instruction)
                assert self.boundary_in_right_swatch(connection.exit_instruction)
                left_boundary = connection.entrance_instruction
                right_boundary = connection.exit_instruction
            self._consume_to_instruction(left_boundary.instruction, remove_connections=True)
            self._consume_next_instruction(remove_connections=True)
            self.swap_swatch_sides()
            self._consume_to_instruction(right_boundary.instruction, remove_connections=True)
            self._consume_next_instruction(remove_connections=True)
        else:
            if self.current_swatch.name != connection.exit_instruction.source_swatch_name:
                self.swap_swatch_sides()
            assert self.current_swatch.name == connection.exit_instruction.source_swatch_name
            self._consume_to_instruction(connection.exit_instruction.instruction, remove_connections=True)
            self._consume_next_instruction(remove_connections=True)  # Consume the exit instruction.
            self.swap_swatch_sides()
            self._consume_to_instruction(connection.entrance_instruction.instruction, remove_connections=True)
            self._consume_next_instruction(remove_connections=True)  # Consume the entrance instruction.

    def merge_swatches(self) -> [Knitout_Line]:
        """
        Merges the left and right swatch and forms a merged swatch program and updates the machine state according to that merged program.

        Returns:
            list[Knitout_Line]: A list of instructions in the merged program.
        """
        self._consume_up_to_first_courses()
        # Start Merge process
        while not self.left_swatch_is_consumed and not self.right_swatch_is_consumed:
            # Consume up to next boundary instruction or until reaching top course to merge.
            self._consume_from_current_swatch(end_on_exits=True, end_on_entrances=True, end_on_carriage_pass_index=self.last_course_on_current_side, remove_connections=False)
            if self.next_instruction is None:  # Swatch is fully consumed.
                self.swap_swatch_sides()
                break  # end the merge process and continue into the next swatch.
            if self._current_swatch_consumed():  # Swatch was consumed up to target course
                break  # end merge process without swapping. The remainder of the courses will be consumed before completing the next swatch.
            if self.next_instruction_is_boundary_entrance or self.next_instruction_is_boundary_exit:
                boundary_instruction = self.current_swatch.get_course_boundary_instruction(self.next_instruction)
                assert isinstance(boundary_instruction, Course_Boundary_Instruction)
                best_connection = self.best_connection(boundary_instruction)
                if best_connection is not None:  # Otherwise continue in the current swatch, ignoring that possible connection.
                    self._consume_connection(best_connection)
                    continue
            self._consume_next_instruction(remove_connections=True)  # Skip over this instruction and continue iterating through the current swatch

        # Consume remainder of current swatch
        self._consume_from_current_swatch(end_on_entrances=False, end_on_exits=False, remove_connections=True)
        self.swap_swatch_sides()
        # Consume remainder of last swatch
        self._consume_from_current_swatch(end_on_entrances=False, end_on_exits=False, remove_connections=True)
        for active_carrier in self._merged_program_machine_state.carrier_system.active_carriers:
            outhook = Outhook_Instruction(active_carrier, 'Outhook remaining active carriers')
            self._release_to_merge_instruction(outhook, self.current_course_merge_side)
            self._add_instruction_to_merge(outhook, self.current_course_merge_side)
        self._specify_sources_in_merged_instructions()
        # Clean and reorganize instructions
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=In_Active_Carrier_Warning)
            warnings.filterwarnings("ignore", category=Out_Inactive_Carrier_Warning)
            warnings.filterwarnings("ignore", category=Mismatched_Releasehook_Warning)
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            executer = Knitout_Executer(self.merged_instructions)
        self.merged_instructions = executer.executed_instructions
        return self.merged_instructions

    def _current_swatch_consumed(self) -> bool:
        """
        Returns:
            bool: True if the current swatch is consumed through the last course of the Course Wise Connection interval. False, otherwise.
        """
        cp_index = self.cp_index_of_next_needle_instruction_in_current_swatch
        return cp_index is not None and (self.last_course_on_current_side <= cp_index)
