"""Module containing the Wale_Seam_Search_Space class."""
from typing import cast

from knitout_interpreter.knitout_operations.Knitout_Line import Knitout_Line
from networkx import DiGraph

from quilt_knit.swatch.Swatch import Swatch
from quilt_knit.swatch.wale_boundary_instructions import Wale_Boundary_Instruction
from quilt_knit.swatch.wale_wise_merging.Wale_Seam_Connection import (
    Wale_Seam_Connection,
)


class Wale_Seam_Search_Space:
    """ Network of potential linking instructions between swatches to form a horizontal seam."""

    def __init__(self, bottom_swatch: Swatch, top_swatch: Swatch, max_rack: int = 2):
        self.max_rack: int = max_rack
        self.top_swatch: Swatch = top_swatch
        self.bottom_swatch: Swatch = bottom_swatch
        self.seam_network: DiGraph = DiGraph()
        self.instructions_to_boundary_instruction: dict[Knitout_Line, Wale_Boundary_Instruction] = {}
        sorted_bottom_exits: list[Wale_Boundary_Instruction] = sorted(self.bottom_swatch.wale_exits)
        self.exit_instructions: list[Wale_Boundary_Instruction] = [*sorted_bottom_exits]
        for exit_instruction in sorted_bottom_exits:
            self.instructions_to_boundary_instruction[exit_instruction.instruction] = exit_instruction
            self.seam_network.add_node(exit_instruction)
        sorted_top_entrances: list[Wale_Boundary_Instruction] = sorted(self.top_swatch.wale_entrances)
        self.entrance_instructions: list[Wale_Boundary_Instruction] = [*sorted_top_entrances]
        for entrance_instruction in sorted_top_entrances:
            self.instructions_to_boundary_instruction[entrance_instruction.instruction] = entrance_instruction
            self.seam_network.add_node(entrance_instruction)
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
                    _connected, _connection = self._add_connection(next_exit, next_entrance)
                else:  # The next entrance is too far to align with this exit, move on to next exit in list.
                    break

    def _add_connection(self, exit_instruction: Wale_Boundary_Instruction, entrance_instruction: Wale_Boundary_Instruction) -> tuple[bool, Wale_Seam_Connection]:
        """
        Add a connection to the search space from the exit instruction to the entrance instruction.
        The connection is only added if the connection can be formed between these instructions.

        Args:
            exit_instruction (Wale_Boundary_Instruction): The exit instruction in the connection.
            entrance_instruction (Wale_Boundary_Instruction): The entrance instruction in the connection.

        Returns:
            tuple[bool, Wale_Seam_Connection]:
                A tuple containing:
                * True if the connection was formed. False, otherwise.
                * The connection between instructions.
        """
        connection = Wale_Seam_Connection(exit_instruction, entrance_instruction)
        instructions_to_form_connection = connection.minimum_instructions_to_connect_to_entrance()
        if instructions_to_form_connection is not None:
            self.seam_network.add_edge(exit_instruction, entrance_instruction, connection=connection, needed_instructions=len(instructions_to_form_connection))
            return True, connection
        else:
            return False, connection

    def _get_connection(self, exit_instruction: Wale_Boundary_Instruction, entrance_instruction: Wale_Boundary_Instruction) -> Wale_Seam_Connection | None:
        """
        Args:
            exit_instruction (Wale_Boundary_Instruction): The exit instruction in the connection.
            entrance_instruction (Wale_Boundary_Instruction): The entrance instruction in the connection.

        Returns:
            Wale_Seam_Connection | None: The connection between the exit instruction and the entrance instruction or None if that connection is not in the search space.
        """
        if self.seam_network.has_edge(exit_instruction, entrance_instruction):
            connection = self.seam_network.edges[exit_instruction, entrance_instruction]['connection']
            assert isinstance(connection, Wale_Seam_Connection)
            return connection
        else:
            return None

    def available_connections(self, boundary_instruction: Wale_Boundary_Instruction) -> list[Wale_Seam_Connection]:
        """
        Args:
            boundary_instruction (Wale_Boundary_Instruction): The boundary instruction to find the available connections to.

        Returns:
            list[Wale_Seam_Connection]:
                A list of all available connections to the given instruction. If this is an exit, only entrance instructions will be returned. If it is an entrance, only exits will be returned.
        """
        if boundary_instruction not in self.seam_network:
            return []
        if boundary_instruction.is_entrance:  # potential exits to entrance
            return cast(list[Wale_Seam_Connection], [self._get_connection(e, boundary_instruction) for e in self.seam_network.predecessors(boundary_instruction)])
        else:  # exit to potential entrances
            return cast(list[Wale_Seam_Connection], [self._get_connection(boundary_instruction, e) for e in self.seam_network.successors(boundary_instruction)])

    def _remove_connection(self, exit_instruction: Wale_Boundary_Instruction, entrance_instruction: Wale_Boundary_Instruction) -> None:
        """
        Remove any connection from the exit instruction to the entrance instruction in the search space.
        Args:
            exit_instruction (Wale_Boundary_Instruction): The exit instruction in the connection to be removed.
            entrance_instruction (Wale_Boundary_Instruction): The entrance instruction in the connection to be removed.
        """
        self.seam_network.remove_edge(exit_instruction, entrance_instruction)

    def remove_boundary(self, instruction: Knitout_Line) -> None:
        """
        Removes any boundary instruction associated with the given instruction from the search space.

        Args:
            instruction (Knitout_Line): An instruction to remove from the search space.
        """
        if instruction in self.instructions_to_boundary_instruction:
            boundary = self.instructions_to_boundary_instruction[instruction]
            if self.seam_network.has_node(boundary):
                self.seam_network.remove_node(boundary)
            if boundary.is_exit:
                self.exit_instructions.remove(boundary)
            elif boundary.is_entrance:
                self.entrance_instructions.remove(boundary)
            del self.instructions_to_boundary_instruction[instruction]

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
        sorted_potential_connections = sorted(self.available_connections(boundary_instruction))
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

    def print_search_space(self) -> None:
        """
        Prints out the search space for debugging purposes.
        """
        print(f"Exits from Bottom Swatch {self.bottom_swatch.name}")
        for bottom_exit in self.bottom_swatch.wale_exits:
            if self.seam_network.has_node(bottom_exit):
                print(f"\texit {bottom_exit.instruction}")
                for potential_top_entrance in self.seam_network.successors(bottom_exit):
                    print(f"\t\t{self.seam_network.edges[bottom_exit, potential_top_entrance]['needed_instructions']} instructions align to {potential_top_entrance.instruction}")
            else:
                print(f"\tNo entrances align with exit {bottom_exit.instruction}")
        print(f"Entrances to Top Swatch {self.top_swatch.name}")
        for top_entrance in self.top_swatch.wale_entrances:
            if self.seam_network.has_node(top_entrance):
                print(f"\tEnter {top_entrance.instruction}")
                for potential_bottom_exit in self.seam_network.predecessors(top_entrance):
                    print(f"\t\t{self.seam_network.edges[potential_bottom_exit, top_entrance]['needed_instructions']} instructions align to {potential_bottom_exit.instruction}")
            else:
                print(f"\tNo exits align with entrance {top_entrance.instruction}")
