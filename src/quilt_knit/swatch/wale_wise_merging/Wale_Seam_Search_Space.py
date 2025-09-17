"""Module containing the Wale_Seam_Search_Space class."""
from typing import cast

from knitout_interpreter.knitout_operations.Knitout_Line import Knitout_Line

from quilt_knit.swatch.Seam_Search_Space import Seam_Search_Space
from quilt_knit.swatch.Swatch import Swatch
from quilt_knit.swatch.swatch_boundary_instruction import Swatch_Boundary_Instruction
from quilt_knit.swatch.wale_boundary_instructions import Wale_Boundary_Instruction
from quilt_knit.swatch.wale_wise_merging.Wale_Seam_Connection import (
    Wale_Seam_Connection,
)
from quilt_knit.swatch.wale_wise_merging.Wale_Wise_Connection import (
    Wale_Wise_Connection,
)


class Wale_Seam_Search_Space(Seam_Search_Space):
    """ Network of potential linking instructions between swatches to form a horizontal seam.

    Attributes:
        exit_instructions (set[Wale_Boundary_Instruction]): The set of wale boundary instructions that exit the bottom swatch.
        entrance_instructions (set[Wale_Boundary_Instruction]): The set of wale boundary instructions that enter the top swatch.

    """
    _NEEDED_INSTRUCTIONS = "needed_instructions"

    def __init__(self, bottom_swatch: Swatch, top_swatch: Swatch, max_rack: int = 2) -> None:
        """
        Initializes the Wale_Seam_Search_Space between the bottom and top swatches.
        Args:
            bottom_swatch (Swatch): The bottom swatch to be merged from.
            top_swatch (Swatch): The top swatch to be merged to.
            max_rack (int, optional): The maximum racking alignment allowed to form a connection. Defaults to 2.
        """
        super().__init__(bottom_swatch, top_swatch)
        sorted_bottom_exits: list[Wale_Boundary_Instruction] = sorted(self.bottom_swatch.wale_exits, key=lambda wb: wb.needle.position)
        self.exit_instructions: set[Wale_Boundary_Instruction] = set(sorted_bottom_exits)
        sorted_top_entrances: list[Wale_Boundary_Instruction] = sorted(self.top_swatch.wale_entrances, key=lambda wb: wb.needle.position)
        self.entrance_instructions: set[Wale_Boundary_Instruction] = set(sorted_top_entrances)
        while len(sorted_bottom_exits) > 0 and len(sorted_top_entrances) > 0:
            next_exit = sorted_bottom_exits.pop(0)
            minimum_entrance_position = next_exit.needle.position - max_rack
            maximum_entrance_position = next_exit.needle.position + max_rack
            next_entrance = sorted_top_entrances[0]
            while next_entrance.needle.position < minimum_entrance_position:
                sorted_top_entrances.pop(0)  # This entrance will be too far away from all future exits to form a connection and can be ignored.
                if len(sorted_top_entrances) == 0:  # No more entrances
                    break
                next_entrance = sorted_top_entrances[0]
            for next_entrance in sorted_top_entrances:  # sorted entrances now excludes all those with lower needle values than alignment with this and all further exits.
                if next_entrance.needle.position < maximum_entrance_position:
                    connection = Wale_Seam_Connection(next_exit, next_entrance)
                    instructions_to_form_connection = connection.minimum_instructions_to_connect_to_entrance()
                    if instructions_to_form_connection is not None:
                        self._add_connection(connection, {self._NEEDED_INSTRUCTIONS: len(instructions_to_form_connection)})
                else:  # The next entrance is too far to align with this exit, move on to next exit in list.
                    break

    @property
    def bottom_swatch(self) -> Swatch:
        """
        Returns:
            Swatch: The bottom swatch in the merge.
        """
        return self._from_swatch

    @property
    def top_swatch(self) -> Swatch:
        """
        Returns:
            Swatch: The top swatch in the merge.
        """
        return self._to_swatch

    def clean_connections(self) -> set[Wale_Boundary_Instruction]:
        """
        Remove all boundary instructions from the search space that cannot form a connection.

        Returns:
            list[Wale_Boundary_Instruction]: All boundary instructions that were removed by this process.
        """
        bad_instructions = set(boundary for boundary in self.instructions_to_boundary_instruction.values() if len(self.available_connections(boundary)) == 0)
        for bad_instruction in bad_instructions:
            self.remove_boundary(bad_instruction.instruction)
        return cast(set[Wale_Boundary_Instruction], bad_instructions)

    def remove_boundary(self, instruction: Knitout_Line) -> Swatch_Boundary_Instruction | None:
        """
        Removes any boundary instruction associated with the given instruction from the search space.
        If the instruction does not belong to a boundary, nothing happens.

        Args:
            instruction (Knitout_Line): The boundary instruction to remove from the search space.

        Returns:
            Swatch_Boundary_Instruction | None: The boundary instruction that was removed or None, if no boundary was found by that instruction.
        """
        boundary = super().remove_boundary(instruction)
        if isinstance(boundary, Wale_Boundary_Instruction):
            if boundary in self.exit_instructions:
                self.exit_instructions.remove(boundary)
            elif boundary in self.entrance_instructions:
                self.entrance_instructions.remove(boundary)
        return boundary

    def remove_excluded_boundary(self, connection: Wale_Wise_Connection) -> None:
        """
        Remove the boundary instructions in the search space that fall outside the boundary interval defined by the given Wale Wise connection.
        Args:
            connection (Wale_Seam_Connection): The wale wise connection interval to exclude boundary instructions outside its connection interval.
        """
        excluded_boundary = set(e.instruction for e in self.entrance_instructions
                                if connection.top_left_needle_position > e.needle.position or e.needle.position > connection.top_right_needle_position)
        excluded_boundary.update(e.instruction for e in self.exit_instructions
                                 if connection.bottom_left_needle_position > e.needle.position or e.needle.position > connection.bottom_right_needle_position)
        for boundary in excluded_boundary:
            self.remove_boundary(boundary)

    def needed_instructions(self, exit_instruction: Wale_Boundary_Instruction, entrance_instruction: Wale_Boundary_Instruction) -> int:
        """
        Args:
            exit_instruction (Wale_Boundary_Instruction): The exit instruction forming a connection in the search space.
            entrance_instruction (Wale_Boundary_Instruction): The entrance instruction forming a connection in the search space.

        Returns:
            int: The number of instructions needed to connect the exit and entrance instructions.
        """
        return int(self.seam_network.edges[exit_instruction, entrance_instruction][self._NEEDED_INSTRUCTIONS])
