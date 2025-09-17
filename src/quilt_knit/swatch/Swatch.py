""" Module containing the Swatch Class"""
from __future__ import annotations

import warnings
from typing import cast

from knit_graphs.artin_wale_braids.Wale import Wale
from knit_graphs.Knit_Graph import Knit_Graph
from knit_graphs.Loop import Loop
from knitout_interpreter.knitout_execution import Knitout_Executer
from knitout_interpreter.knitout_execution_structures.Carriage_Pass import Carriage_Pass
from knitout_interpreter.knitout_language.Knitout_Context import Knitout_Context
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
    Knitout_Line,
    Knitout_Version_Line,
)
from knitout_interpreter.knitout_operations.needle_instructions import (
    Loop_Making_Instruction,
    Miss_Instruction,
    Needle_Instruction,
    Tuck_Instruction,
    Xfer_Instruction,
)
from knitout_interpreter.knitout_operations.Rack_Instruction import Rack_Instruction
from knitout_to_dat_python.knitout_to_dat import knitout_to_dat
from virtual_knitting_machine.Knitting_Machine import Knitting_Machine
from virtual_knitting_machine.knitting_machine_warnings.Needle_Warnings import (
    Knit_on_Empty_Needle_Warning,
)
from virtual_knitting_machine.machine_components.carriage_system.Carriage_Pass_Direction import (
    Carriage_Pass_Direction,
)
from virtual_knitting_machine.machine_components.needles.Needle import Needle
from virtual_knitting_machine.machine_constructed_knit_graph.Machine_Knit_Loop import (
    Machine_Knit_Loop,
)

from quilt_knit.swatch.course_boundary_instructions import (
    Course_Boundary_Instruction,
    Course_Boundary_Type,
)
from quilt_knit.swatch.wale_boundary_instructions import Wale_Boundary_Instruction


def get_terminal_wales(knit_graph: Knit_Graph) -> dict[Loop, list[Wale]]:
    """Get wale groups organized by their terminal loops.
    # TODO Fix this behavior in knit graphs
    Returns:
        dict[Loop, list[Wale]]: Dictionary mapping terminal loops to list of wales that terminate that wale.
    """
    wale_groups = {}
    for loop in knit_graph:
        if knit_graph.is_terminal_loop(loop):
            wale_groups[loop] = [wale for wale in knit_graph.get_wales_ending_with_loop(loop)]
    return wale_groups


class Swatch:
    """
        Class that associates a knitout program with the resulting knit graph.
        Used for linking swatches to form Quilts.

        Attributes:
            carriage_passes (list[Carriage_Pass]): An ordered list of carriage passes in the swatch.
            wale_entrances (list[Wale_Boundary_Instruction]): The instructions on the bottom boundary of the swatch.
            wale_exits (list[Wale_Boundary_Instruction]): The instructions on the top boundary of the swatch.
    """

    def __init__(self, name: str, knitout_program: str | list[Knitout_Line], prior_machine_state: Knitting_Machine | None = None):
        self._name: str = name
        knitout_context: Knitout_Context = Knitout_Context()
        if isinstance(knitout_program, str):
            knitout_program, _knitting_machine, _knit_graph = knitout_context.process_knitout_file(knitout_program)
            self.knitout_program: list[Knitout_Line] = cast(list[Knitout_Line], knitout_program)
        else:
            self.knitout_program: list[Knitout_Line] = knitout_program
        if prior_machine_state is None:
            prior_machine_state = Knitting_Machine()
        self._execute_knitout(prior_machine_state)
        self._course_boundary_instructions: dict[Course_Boundary_Instruction, Carriage_Pass] = {}
        self._instructions_on_course_boundary: dict[Needle_Instruction, Course_Boundary_Instruction] = {}
        self._instruction_to_carriage_pass: dict[Needle_Instruction, Carriage_Pass] = {}
        self._carriage_pass_to_index: dict[Carriage_Pass, int] = {}
        self.carriage_passes: list[Carriage_Pass] = self._knitout_execution.carriage_passes
        for i, cp in enumerate(self.carriage_passes):
            self._carriage_pass_to_index[cp] = i
            for instruction in cp:
                self._instruction_to_carriage_pass[instruction] = cp
        self._process_course_boundaries()
        self._terminal_wales: dict[Loop, list[Wale]] = get_terminal_wales(self.execution_knit_graph)  # Todo update knitgraph to handle this
        self.wale_entrances: list[Wale_Boundary_Instruction] = self._get_wale_entrances()
        self.wale_exits: list[Wale_Boundary_Instruction] = self._get_wale_exits()
        self._instructions_on_wale_boundary: dict[Needle_Instruction, Wale_Boundary_Instruction] = {wb.instruction: wb for wb in self.wale_entrances}
        exits_from_entrances = {}
        updated_exits: list[Wale_Boundary_Instruction] = []
        for exit_instruction in self.wale_exits:
            if exit_instruction.instruction in self._instructions_on_wale_boundary:  # instruction was also an entrance
                entrance = self.get_wale_boundary_instruction(exit_instruction.instruction)
                entrance.is_exit = True
                exits_from_entrances[exit_instruction] = entrance
                updated_exits.append(entrance)
            else:
                updated_exits.append(exit_instruction)
        self.wale_exits: list[Wale_Boundary_Instruction] = updated_exits
        self._instructions_on_wale_boundary.update({wb.instruction: wb for wb in self.wale_exits if wb not in exits_from_entrances})

    def _process_course_boundaries(self) -> None:
        """
        Processes all the carriage passes in the program into data structures for efficient reference.
        """
        for carriage_pass, cp_index in self._carriage_pass_to_index.items():
            blocked_pass = len(carriage_pass) > 1  # True if the carriage pass has multiple operations blocking it from one side or the other.
            if not blocked_pass:  # Only one xfer instruction, so it can merge from either direction
                if carriage_pass.xfer_pass:
                    self._add_boundary_instruction(Course_Boundary_Instruction(instruction=carriage_pass.first_instruction, source_swatch_name=self.name,
                                                                               left_boundary_type=Course_Boundary_Type.entrance_exit, right_boundary_type=Course_Boundary_Type.entrance_exit,
                                                                               carriage_pass_rack=carriage_pass.rack, carriage_pass_is_all_needle=carriage_pass.all_needle_rack,
                                                                               carriage_pass_index=cp_index))
                elif carriage_pass.direction is Carriage_Pass_Direction.Rightward:
                    self._add_boundary_instruction(Course_Boundary_Instruction(instruction=carriage_pass.first_instruction, source_swatch_name=self.name,
                                                                               left_boundary_type=Course_Boundary_Type.entrance, right_boundary_type=Course_Boundary_Type.exit_boundary,
                                                                               carriage_pass_rack=carriage_pass.rack, carriage_pass_is_all_needle=carriage_pass.all_needle_rack,
                                                                               carriage_pass_index=cp_index))
                else:
                    assert carriage_pass.direction is Carriage_Pass_Direction.Leftward
                    self._add_boundary_instruction(Course_Boundary_Instruction(instruction=carriage_pass.first_instruction, source_swatch_name=self.name,
                                                                               left_boundary_type=Course_Boundary_Type.exit_boundary, right_boundary_type=Course_Boundary_Type.entrance,
                                                                               carriage_pass_rack=carriage_pass.rack, carriage_pass_is_all_needle=carriage_pass.all_needle_rack,
                                                                               carriage_pass_index=cp_index))

            elif carriage_pass.xfer_pass:
                left_instruction = carriage_pass.first_instruction
                right_instruction = carriage_pass.last_instruction
                self._add_boundary_instruction(Course_Boundary_Instruction(instruction=left_instruction, source_swatch_name=self.name,
                                                                           left_boundary_type=Course_Boundary_Type.entrance_exit, right_boundary_type=Course_Boundary_Type.blocked,
                                                                           carriage_pass_rack=carriage_pass.rack, carriage_pass_is_all_needle=carriage_pass.all_needle_rack,
                                                                           carriage_pass_index=cp_index))
                self._add_boundary_instruction(Course_Boundary_Instruction(instruction=right_instruction, source_swatch_name=self.name,
                                                                           left_boundary_type=Course_Boundary_Type.blocked, right_boundary_type=Course_Boundary_Type.entrance_exit,
                                                                           carriage_pass_rack=carriage_pass.rack, carriage_pass_is_all_needle=carriage_pass.all_needle_rack,
                                                                           carriage_pass_index=cp_index))
            elif carriage_pass.direction is Carriage_Pass_Direction.Rightward:
                self._add_boundary_instruction(Course_Boundary_Instruction(instruction=carriage_pass.first_instruction, source_swatch_name=self.name,
                                                                           left_boundary_type=Course_Boundary_Type.entrance, right_boundary_type=Course_Boundary_Type.blocked,
                                                                           carriage_pass_rack=carriage_pass.rack, carriage_pass_is_all_needle=carriage_pass.all_needle_rack,
                                                                           carriage_pass_index=cp_index))
                self._add_boundary_instruction(Course_Boundary_Instruction(instruction=carriage_pass.last_instruction, source_swatch_name=self.name,
                                                                           left_boundary_type=Course_Boundary_Type.blocked, right_boundary_type=Course_Boundary_Type.exit_boundary,
                                                                           carriage_pass_rack=carriage_pass.rack, carriage_pass_is_all_needle=carriage_pass.all_needle_rack,
                                                                           carriage_pass_index=cp_index))
            else:
                assert carriage_pass.direction is Carriage_Pass_Direction.Leftward
                self._add_boundary_instruction(Course_Boundary_Instruction(instruction=carriage_pass.first_instruction, source_swatch_name=self.name,
                                                                           left_boundary_type=Course_Boundary_Type.blocked, right_boundary_type=Course_Boundary_Type.entrance,
                                                                           carriage_pass_rack=carriage_pass.rack, carriage_pass_is_all_needle=carriage_pass.all_needle_rack,
                                                                           carriage_pass_index=cp_index))
                self._add_boundary_instruction(Course_Boundary_Instruction(instruction=carriage_pass.last_instruction, source_swatch_name=self.name,
                                                                           left_boundary_type=Course_Boundary_Type.exit_boundary, right_boundary_type=Course_Boundary_Type.blocked,
                                                                           carriage_pass_rack=carriage_pass.rack, carriage_pass_is_all_needle=carriage_pass.all_needle_rack,
                                                                           carriage_pass_index=cp_index))

    def _execute_knitout(self, prior_machine_state: Knitting_Machine) -> None:
        """
        Sets the _knitout_execution property.
        If the set to inject missing carriers, this will modify the knitout program to avoid Use_Inactive_Carrier_Exceptions.
        Args:
            prior_machine_state (Knitting_Machine): The machine state prior to execution of the Swatch
        """
        original_prior = prior_machine_state
        first_pass_prior_machine_state = original_prior
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            self._knitout_execution: Knitout_Executer = Knitout_Executer(self.knitout_program, first_pass_prior_machine_state)
        self.knitout_program = self._knitout_execution.executed_instructions  # set the knitout program to be the program that is produced by successful execution.

    def _get_wale_entrances(self) -> list[Wale_Boundary_Instruction]:
        if len(self._terminal_wales) == 0:  # the program does not result in any courses to form wales.
            return []
        entrance_loops: set[Loop] = set()
        wales_to_find_entrances = set()
        for wales in self._terminal_wales.values():
            wales_to_find_entrances.update(wales)
        while len(wales_to_find_entrances) > 0:
            wale = wales_to_find_entrances.pop()
            if wale.first_loop.has_parent_loops():
                wales_to_find_entrances.update(self.execution_knit_graph.get_wales_ending_with_loop(wale.first_loop))
            else:
                entrance_loops.add(wale.first_loop)
        entrance_needles: set[Needle] = set(l.source_needle for l in entrance_loops if isinstance(l, Machine_Knit_Loop))
        locked_needles: set[Needle] = set()
        entrances_to_needles: dict[Needle, Wale_Boundary_Instruction] = {}
        for carriage_pass in self.carriage_passes:
            carriage_pass_is_locked = False
            needles_in_cp: set[Needle] = set()
            for instruction in carriage_pass:
                if not carriage_pass_is_locked and not isinstance(instruction, Miss_Instruction):
                    needles_in_cp.add(instruction.needle)
                if (not isinstance(instruction, Miss_Instruction) and  # ignores misses since they don't result in loop actions
                        instruction.needle not in locked_needles and  # ignored locked needles since their entrance has already been decided
                        instruction.needle in entrance_needles):  # only consider needles that are entrances to the knitgraph.
                    entrance = Wale_Boundary_Instruction(is_entrance=True, is_exit=False, instruction=instruction, source_swatch_name=self.name)
                    entrances_to_needles[instruction.needle] = entrance  # overrides unlocked tuck instructions on this location
                    if carriage_pass_is_locked or entrance.entrance_requires_loop:  # This instruction requires a prior instruction to place a loop either by tucked cast on or form prior swatch.
                        carriage_pass_is_locked = True
                        locked_needles.add(instruction.needle)
                        locked_needles.update(needles_in_cp)
                        needles_in_cp = set()  # cleans up set since it will get updated to end of carriage pass.
                        entrance_needles.remove(instruction.needle)  # This entrance is no longer worth looking for.
                        if len(entrance_needles) == 0:
                            return [*entrances_to_needles.values()]
        # assert len(entrance_needles) == 0, f"Entrance needles is not empty: {entrance_needles}"
        return [*entrances_to_needles.values()]

    def _get_wale_exits(self) -> list[Wale_Boundary_Instruction]:
        if len(self._terminal_wales) == 0:  # the program does not result in any courses to form wales.
            return []
        exit_needles: set[Needle] = set(l.last_needle for l in self._terminal_wales if isinstance(l, Machine_Knit_Loop))
        exits: list[Wale_Boundary_Instruction] = []
        for instruction in reversed(self.knitout_program):
            if isinstance(instruction, Needle_Instruction) and not isinstance(instruction, Miss_Instruction):
                exit_boundary = Wale_Boundary_Instruction(is_entrance=False, is_exit=True, instruction=instruction, source_swatch_name=self.name)
                include_exit = False
                if exit_boundary.front_needle is not None and exit_boundary.front_needle in exit_needles:
                    exit_needles.remove(exit_boundary.front_needle)
                    include_exit = True
                if exit_boundary.back_needle is not None and exit_boundary.back_needle in exit_needles:
                    exit_needles.remove(exit_boundary.back_needle)
                    include_exit = True
                if include_exit:
                    exits.append(exit_boundary)
                    if len(exit_needles) == 0:
                        return exits
        return exits

    def get_instruction_pass(self, instruction: Knitout_Line) -> Carriage_Pass | None:
        """
        Args:
            instruction (Knitout_Line): The instruction to find the owning carriage pass.

        Returns:
            Carriage_Pass | None: None if the instruction does not belong to a carriage pass. Otherwise, the carriage pass that owns the instruction.
        """
        if instruction not in self._instruction_to_carriage_pass:
            return None
        else:
            assert isinstance(instruction, Needle_Instruction)
            return self._instruction_to_carriage_pass[instruction]

    def get_cp_index_of_instruction(self, instruction: Knitout_Line) -> int | None:
        """

        Args:
            instruction (Knitout_Line): The instruction to find the carriage pass index.

        Returns:
            int | None: None if the instruction does not belong to a carriage pass. Otherwise, the index of the carriage pass that owns the instruction.
        """
        cp = self.get_instruction_pass(instruction)
        if cp is None:
            return None
        else:
            return self._carriage_pass_to_index[cp]

    def get_cp_by_index(self, index: int) -> Carriage_Pass:
        """
        Args:
            index (int): The index of the carriage pass.
        Returns:
            Carriage_Pass: The carriage pass at the given index.
        """
        """
        :param index:
        :return: The carriage pass in the swatch at the given index.
        """
        return self.carriage_passes[index]

    def _add_boundary_instruction(self, boundary_instruction: Course_Boundary_Instruction) -> None:
        """
        Adds the given course boundary instruction belonging to the given carriage pass.

        Args:
            boundary_instruction (Course_Boundary_Instruction): The course boundary instruction to add.
        """
        cp = self.get_instruction_pass(boundary_instruction.instruction)
        self._course_boundary_instructions[boundary_instruction] = cp
        self._instructions_on_course_boundary[boundary_instruction.instruction] = boundary_instruction

    @property
    def execution_knitting_machine(self) -> Knitting_Machine:
        """
        Returns:
            Knitting_Machine: The knitting machine state after knitout execution.
        """
        return self._knitout_execution.knitting_machine

    @property
    def execution_knit_graph(self) -> Knit_Graph:
        """
        Returns:
            Knit_Graph: The knitgraph that results from the execution of the knitout program.
        """
        return self.execution_knitting_machine.knit_graph

    def instruction_on_course_boundary(self, instruction: Knitout_Line) -> bool:
        """
        Args:
            instruction (Knitout_Line): The instruction to determine if it lies on the course boundary of the swatch.

        Returns:
            bool: True if the instruction is on the course boundary of the swatch, False otherwise.
        """
        return instruction in self._instructions_on_course_boundary

    def instruction_on_wale_boundary(self, instruction: Knitout_Line) -> bool:
        """
        Args:
            instruction (Knitout_Line): The instruction to determine if it lies on the wale boundary of the swatch.

        Returns:
            bool: True if the instruction is on the wale boundary of the swatch, False otherwise.
        """
        return instruction in self._instructions_on_wale_boundary

    def get_course_boundary_instruction(self, instruction: Knitout_Line) -> None | Course_Boundary_Instruction:
        """
        Args:
            instruction (Knitout_Line): The instruction owned by a boundary instruction.

        Returns:
            None | Course_Boundary_Instruction: The course boundary instruction that owns the given instruction or None if the instruction is not on the course boundary.
        """
        if self.instruction_on_course_boundary(instruction):
            assert isinstance(instruction, Needle_Instruction)
            return self._instructions_on_course_boundary[instruction]
        else:
            return None

    def get_wale_boundary_instruction(self, instruction: Knitout_Line) -> Wale_Boundary_Instruction:
        """
        Args:
            instruction (Knitout_Line): The instruction owned by a boundary instruction.

        Returns:
            Wale_Boundary_Instruction: The wale boundary instruction that owns the given instruction.

        Raises:
            KeyError: If the given instruction is not on the wale boundary.
        """
        if self.instruction_on_wale_boundary(instruction):
            assert isinstance(instruction, Needle_Instruction)
            return self._instructions_on_wale_boundary[instruction]
        else:
            raise KeyError(f'The instruction {instruction} is not on the wale boundary.')

    def instruction_is_left_exit(self, instruction: Knitout_Line) -> bool:
        """
        Args:
            instruction (Knitout_Line): The instruction owned by a boundary instruction.

        Returns:
            bool: True if the instruction is an exit to the left boundary. False, otherwise.
        """
        return self.instruction_on_course_boundary(instruction) and cast(Course_Boundary_Instruction, self.get_course_boundary_instruction(instruction)).is_left_exit

    def instruction_is_left_entrance(self, instruction: Knitout_Line) -> bool:
        """
        Args:
            instruction (Knitout_Line): The instruction owned by a boundary instruction.

        Returns:
            bool: True if the instruction is an entrance to the left boundary. False, otherwise.
        """
        return self.instruction_on_course_boundary(instruction) and cast(Course_Boundary_Instruction, self.get_course_boundary_instruction(instruction)).is_left_entrance

    def instruction_is_right_exit(self, instruction: Knitout_Line) -> bool:
        """
        Args:
            instruction (Knitout_Line): The instruction owned by a boundary instruction.

        Returns:
            bool: True if the instruction is an exit from the right boundary. False, otherwise.
        """
        return self.instruction_on_course_boundary(instruction) and cast(Course_Boundary_Instruction, self.get_course_boundary_instruction(instruction)).is_right_exit

    def instruction_is_right_entrance(self, instruction: Knitout_Line) -> bool:
        """
        Args:
            instruction (Knitout_Line): The instruction owned by a boundary instruction.

        Returns:
            bool: True if the instruction is an entrance to the right boundary. False, otherwise.
        """
        return self.instruction_on_course_boundary(instruction) and cast(Course_Boundary_Instruction, self.get_course_boundary_instruction(instruction)).is_right_entrance

    @property
    def name(self) -> str:
        """
        Returns:
            str: The name of the swatch.
        """
        return self._name

    @property
    def min_needle(self) -> int:
        """
        Returns:
            int: The position of the leftmost needle used in swatch construction.
        """
        return int(self._knitout_execution.left_most_position)

    @property
    def max_needle(self) -> int:
        """
        Returns:
            int: The position of the rightmost needle used in swatch construction.
        """
        return int(self._knitout_execution.right_most_position)

    @property
    def width(self) -> int:
        """
        Returns:
            int: The number of needles used in the swatch at its greatest width.
        """
        return self.max_needle - self.min_needle + 1

    @property
    def height(self) -> int:
        """
        Returns:
            int: The number of carriage passes in the swatch.
        """
        return len(self._carriage_pass_to_index)

    @property
    def constructed_height(self) -> int:
        """
        Returns:
            int: The number of carriage passes in the swatch that create new loops. This excludes xfer passes.
        """
        loop_construction_passes = [cp for cp in self.carriage_passes if not cp.xfer_pass]
        return len(loop_construction_passes)

    @property
    def left_entrances(self) -> list[Course_Boundary_Instruction]:
        """
        Returns:
            list[Course_Boundary_Instruction]: The boundary entrances of the left side of the swatch.
        """
        return [b for b in self._course_boundary_instructions if b.is_left_entrance]

    @property
    def left_exits(self) -> list[Course_Boundary_Instruction]:
        """
        Returns:
            list[Course_Boundary_Instruction]: The boundary exits of the left side of the swatch.
        """
        return [b for b in self._course_boundary_instructions if b.is_left_exit]

    @property
    def left_boundary(self) -> list[Course_Boundary_Instruction]:
        """
        Returns:
            list[Course_Boundary_Instruction]: The boundary instructions of the left side of the swatch.
        """
        return [b for b in self._course_boundary_instructions if b.is_left]

    @property
    def right_entrances(self) -> list[Course_Boundary_Instruction]:
        """
        Returns:
            list[Course_Boundary_Instruction]: The boundary entrances of the right side of the swatch.
        """
        return [b for b in self._course_boundary_instructions if b.is_right_entrance]

    @property
    def right_exits(self) -> list[Course_Boundary_Instruction]:
        """
        Returns:
            list[Course_Boundary_Instruction]: The boundary exits of the right side of the swatch.
        """
        return [b for b in self._course_boundary_instructions if b.is_right_exit]

    @property
    def right_boundary(self) -> list[Course_Boundary_Instruction]:
        """
        Returns:
            list[Course_Boundary_Instruction]: The boundary instructions of the right side of the swatch.
        """
        return [b for b in self._course_boundary_instructions if b.is_right]

    def get_carriage_pass_index_of_instruction(self, instruction: Knitout_Line) -> int | None:
        """

        Args:
            instruction: The instruction to find the index of its owning carriage pass.

        Returns:
            int | None: The index of the carriage pass that executes the instruction or None if the instruction does not belong to a carriage pass.
        """
        if instruction not in self._instruction_to_carriage_pass:
            return None
        else:
            assert isinstance(instruction, Needle_Instruction)
            cp = self._instruction_to_carriage_pass[instruction]
            return self._carriage_pass_to_index[cp]

    def split_swatch_at_carriage_pass(self, carriage_pass_index: int, bottom_swatch_name: str, top_swatch_name: str) -> tuple[Swatch | None, Swatch | None, bool]:
        """

        Args:
            carriage_pass_index (int): The carriage pass to start the top swatch on.
            bottom_swatch_name (str): The name to give the bottom swatch.
            top_swatch_name (str): The name to give the top swatch

        Returns:
            tuple[Swatch | None, Swatch | None, bool]: A tuple containing the following:
            * The bottom swatch created by the split or None if the split did not create a bottom swatch.
            * The top swatch created by the split or None if the split did not create a top swatch.
            * True if the top swatch has initial transfer pass carriage passes removed. False, otherwise.

        Notes:
            * If the carriage pass index is less than or equal to 0, then the swatch is not split. The bottom swatch will be None and the top swatch will be this swatch.
            * If the carriage pass index is greater than the height of the swatch, then teh swatch is not split. The bottom swatch will be this swatch and the top swatch will be None.
        """
        if carriage_pass_index <= 0:
            return None, self, False
        elif carriage_pass_index >= self.height:
            return self, None, False
        bottom_program = get_machine_header(self.execution_knitting_machine)
        top_program = get_machine_header(self.execution_knitting_machine)
        header_len = len(top_program)
        in_bottom = True
        excluding_xfers = True
        lost_starting_xfers = False
        for instruction in self.knitout_program:
            if isinstance(instruction, Knitout_Header_Line) or isinstance(instruction, Knitout_Version_Line):
                continue  # skip header lines since these are added to the start of both programs based on the machine state
            cp = self.get_carriage_pass_index_of_instruction(instruction)
            if cp is None:
                if in_bottom:
                    bottom_program.append(instruction)
                else:
                    top_program.append(instruction)
            elif cp < carriage_pass_index:
                bottom_program.append(instruction)
                in_bottom = True
            else:  # cp >= carriage_pass_index, move to the top program
                in_bottom = False
                if excluding_xfers and isinstance(instruction, Needle_Instruction):
                    if isinstance(instruction, Xfer_Instruction):  # still first set of xfers which can be excluded
                        lost_starting_xfers = True
                        continue
                    else:  # Found a non-xfer instruction in the top swatch, stop excluding xfers
                        excluding_xfers = False
                top_program.append(instruction)
        bottom_swatch = Swatch(bottom_swatch_name, bottom_program)
        for carrier in bottom_swatch.execution_knitting_machine.carrier_system.active_carriers:
            top_program.insert(header_len, Inhook_Instruction(carrier.carrier_id, f"Inject carrier from lower swatch"))
            top_program.insert(header_len + 1, Releasehook_Instruction(carrier.carrier_id, "Inject release from lower swatch"))
        top_program.insert(header_len, Rack_Instruction(bottom_swatch.execution_knitting_machine.rack, f"Injected Rack to start at state of upper swatch"))
        top_swatch = Swatch(top_swatch_name, top_program)
        return bottom_swatch, top_swatch, lost_starting_xfers

    def compile_to_knitout(self, knitout_name: str | None = None) -> None:
        """
        Writes a knitout file of the given name that executes this swatch program.
        Args:
            knitout_name (str, option): The name of the knitout file to write. Defaults to the name of the swatch.
        """
        if knitout_name is None:
            knitout_name = self.name
        context = Knitout_Context()
        executed_instructions, execution_machine, _knitgraph = context.execute_knitout_instructions(self.knitout_program)
        self.knitout_program = get_machine_header(self.execution_knitting_machine)
        self.knitout_program.extend(executed_instructions)
        for cid in execution_machine.carrier_system.active_carriers:
            self.knitout_program.append(Outhook_Instruction(cid, f"Take out remaining carriers from {self.name}"))
        with open(f'{knitout_name}.k', 'w') as knitout_file:
            clean_instructions = [f"{str(i).splitlines()[0]}\n" for i in self.knitout_program]
            knitout_file.writelines(clean_instructions)

    def compile_to_dat(self, dat_name: str | None = None) -> None:
        """
        Writes a shima-seiki dat file of the given name that executes this swatch program.

        Args:
            dat_name (str, optional): The name of the dat to write. Defaults to the name of the swatch.
        """
        if dat_name is None:
            dat_name = self.name
        self.compile_to_knitout(dat_name)
        knitout_to_dat(f"{dat_name}.k", f"{dat_name}.dat", knitout_in_file=True)

    def __hash__(self) -> int:
        """
        Returns:
            int: The hash value of this swatch's name.
        """
        return hash(self.name)

    def __repr__(self) -> str:
        """
        Returns:
            str: A string representation of this swatch based on its name.
        """
        return self.name

    def __eq__(self, other: Swatch) -> bool:
        """
        Args:
            other (Swatch): The other swatch to compare to this swatch.

        Returns:
            bool: True if this and the other swatch, share the same name. False, otherwise.
        """
        return self.name == other.name

    def shift_swatch_rightward_on_needle_bed(self, shift_needle_count: int = 0) -> Swatch:
        """
        Args:
            shift_needle_count (int, optional): The number of needles to shift this swatch program rightward by. Defaults to 0.

        Returns:
            Swatch: The shifted swatch program. All needle operations will have their needle slot shifted over by the shift value.

        Notes:
            * If the shifted needle count is 0, then this returns this swatch.
        """
        if shift_needle_count == 0:
            return self
        shift_needle_count = abs(shift_needle_count)  # ensures a rightward, increasing shift

        def shift_swatch_instruction(instruction: Knitout_Line) -> Knitout_Line:
            """
            Args:
                instruction (Knitout_Line): The instruction to shift.

            Returns:
                Knitout_Line: A copy of the instruction with all needle values shifted rightward by the given value.
            """
            if isinstance(instruction, Needle_Instruction):
                shifted_needle = instruction.needle + shift_needle_count
                if instruction.needle_2 is None:
                    shifted_needle_2 = None
                else:
                    shifted_needle_2 = instruction.needle_2 + shift_needle_count
                return build_instruction(instruction.instruction_type, shifted_needle, instruction.direction, instruction.carrier_set, shifted_needle_2)
            else:
                return instruction

        return Swatch(f"{self.name}_shifted_right_{shift_needle_count}", [shift_swatch_instruction(i) for i in self.knitout_program])

    def find_carriage_pass_from_course_passes(self, course_pass_count: int) -> int:
        """
        Args:
            course_pass_count (int): The target number of carriage passes that form courses by creating new loops.

        Returns:
            int: The number of carriage passes required to reach the target number of courses. If that course target is not reached, this will be the full height of the swatch.
        """
        if course_pass_count == 0:
            return 0
        course_passes = 0

        for total_passes, cp in enumerate(self.carriage_passes):
            if not cp.xfer_pass:
                course_passes += 1
            if course_passes == course_pass_count:
                return total_passes + 1  # Note: Add 1 to ensure this passes is captured in the count.
        # If we didn't reach the requested course_pass_count, return height of this swatch.
        return self.height

    def remove_cast_on_boundary(self) -> None:
        """
        Re-initializes this swatch without the tuck operations at the bottom of each wale.
        """
        new_knitout = []
        knit_needles = set()
        for k_index, knitout_line in enumerate(self.knitout_program):
            if isinstance(knitout_line, Needle_Instruction):
                if knitout_line.needle in knit_needles:  # includes tucks on marked needles
                    if isinstance(knitout_line.needle_2, Needle):  # Xfers and Splits from a marked needle.
                        knit_needles.add(knitout_line.needle_2)
                    new_knitout.append(knitout_line)
                elif isinstance(knitout_line, Loop_Making_Instruction) and not isinstance(knitout_line, Tuck_Instruction):
                    knit_needles.add(knitout_line.needle)
                    if isinstance(knitout_line.needle_2, Needle):  # splits from a newly marked needle
                        knit_needles.add(knitout_line.needle_2)
                    new_knitout.append(knitout_line)
            else:  # Non needle instructions get added
                new_knitout.append(knitout_line)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            self.__init__(self.name, new_knitout)
