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
    """ Network of potential linking instructions between swatches to form a horizontal seam."""
    _NEEDED_INSTRUCTIONS = "needed_instructions"

    def __init__(self, bottom_swatch: Swatch, top_swatch: Swatch, max_rack: int = 2):
        super().__init__(bottom_swatch, top_swatch)
        self.max_rack: int = max_rack
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

    def remove_excluded_exits(self, connection: Wale_Wise_Connection) -> None:
        """
        Remove the exit instructions in the search space that fall outside the boundary interval defined by the given Wale Wise connection.
        Args:
            connection (Wale_Seam_Connection): The wale wise connection interval to exclude exits outside its connection interval.
        """
        sorted_exits = sorted(self.exit_instructions)
        for exit_instruction in sorted_exits:
            if exit_instruction.needle.position < connection.bottom_left_needle_position:
                self.remove_boundary(exit_instruction.instruction)
            else:
                break  # Exit instructions are sorted from left to right, so skip over the middle section that is going to be included
        for exit_instruction in reversed(sorted_exits):
            if exit_instruction.needle.position > connection.bottom_right_needle_position:
                self.remove_boundary(exit_instruction.instruction)
            else:
                break

    def remove_excluded_entrances(self, connection: Wale_Wise_Connection) -> None:
        """
        Remove the entrance instructions in the search space that fall outside the boundary interval defined by the given Wale Wise connection.
        Args:
            connection (Wale_Seam_Connection): The wale wise connection interval to exclude entrances outside its connection interval.
        """
        sorted_entrances = sorted(self.entrance_instructions)
        for entrance_instruction in sorted_entrances:
            if entrance_instruction.needle.position < connection.top_left_needle_position:
                self.remove_boundary(entrance_instruction.instruction)
            else:
                break  # Exit instructions are sorted from left to right, so skip over the middle section that is going to be included
        for entrance_instruction in reversed(sorted_entrances):
            if entrance_instruction.needle.position > connection.top_right_needle_position:
                self.remove_boundary(entrance_instruction.instruction)
            else:
                break

    def remove_excluded_boundary(self, connection: Wale_Wise_Connection) -> None:
        """
        Remove the boundary instructions in the search space that fall outside the boundary interval defined by the given Wale Wise connection.
        Args:
            connection (Wale_Seam_Connection): The wale wise connection interval to exclude boundary instructions outside its connection interval.
        """
        self.remove_excluded_entrances(connection)
        self.remove_excluded_exits(connection)

    def choose_best_connection(self, boundary_instruction: Wale_Boundary_Instruction, preferred_rack_values: set[int] | None = None) -> Wale_Seam_Connection | None:
        """
        Args:
            boundary_instruction (Wale_Boundary_Instruction): The boundary instruction to choose the best connection to.
            preferred_rack_values (set[int], optional): The rack values preferred as a tie-breaker for aligning instructions that require a racking. By default, there is no preference.

        Returns:
            Wale_Seam_Connection | None: The connection between the exit instruction and the entrance instruction.

        Notes:
            * If rackings have already been assigned to form other connections, these racking should be included in the preferred_rack_values set.
        """
        sorted_potential_connections = cast(list[Wale_Seam_Connection], sorted(self.available_connections(boundary_instruction)))
        if len(sorted_potential_connections) == 0:
            return None
        if preferred_rack_values is None:  # no preferred racking, so take the shortest connection
            return sorted_potential_connections[0]
        else:
            best_0_racking_option = None
            best_racking_match = None
            best_non_match = None
            for connection in sorted_potential_connections:
                minimum_connection_instructions = connection.minimum_instructions_to_connect_to_entrance()
                assert isinstance(minimum_connection_instructions, list)
                instruction_count = len(minimum_connection_instructions)
                if instruction_count == 0:  # alignment possible without xfers so just take that
                    return connection
                required_rack = connection.required_rack()
                if required_rack == 0 and best_0_racking_option is None:  # first match found that requires no special alignment.
                    best_0_racking_option = connection
                elif best_0_racking_option is not None:
                    if best_racking_match is None and required_rack in preferred_rack_values:  # first match found that requires no additional alignment
                        best_racking_match = connection
                    elif best_non_match is None:  # First match found that requires a non-preferred rack value
                        best_non_match = connection
            if isinstance(best_0_racking_option, Wale_Seam_Connection):
                return best_0_racking_option
            elif isinstance(best_racking_match, Wale_Seam_Connection):
                return best_0_racking_option
            else:
                assert isinstance(best_non_match, Wale_Seam_Connection)
                return best_non_match

    def needed_instructions(self, exit_instruction: Wale_Boundary_Instruction, entrance_instruction: Wale_Boundary_Instruction) -> int:
        """
        Args:
            exit_instruction (Wale_Boundary_Instruction): The exit instruction forming a connection in the search space.
            entrance_instruction (Wale_Boundary_Instruction): The entrance instruction forming a connection in the search space.

        Returns:
            int: The number of instructions needed to connect the exit and entrance instructions.
        """
        return int(self.seam_network.edges[exit_instruction, entrance_instruction][self._NEEDED_INSTRUCTIONS])

    def print_search_space(self) -> None:
        """
        Prints out the search space for debugging purposes.
        """
        print(f"Exits from Bottom Swatch {self.bottom_swatch.name}")
        for bottom_exit in self.bottom_swatch.wale_exits:
            if self.seam_network.has_node(bottom_exit):
                print(f"\texit {bottom_exit.instruction}")
                for potential_top_entrance in self.seam_network.successors(bottom_exit):
                    print(f"\t\t{self.needed_instructions(bottom_exit, potential_top_entrance)} instructions align to {potential_top_entrance.instruction}")
            else:
                print(f"\tNo entrances align with exit {bottom_exit.instruction}")
        print(f"Entrances to Top Swatch {self.top_swatch.name}")
        for top_entrance in self.top_swatch.wale_entrances:
            if self.seam_network.has_node(top_entrance):
                print(f"\tEnter {top_entrance.instruction}")
                for potential_bottom_exit in self.seam_network.predecessors(top_entrance):
                    print(f"\t\t{self.needed_instructions(potential_bottom_exit, top_entrance)} instructions align to {potential_bottom_exit.instruction}")
            else:
                print(f"\tNo exits align with entrance {top_entrance.instruction}")
