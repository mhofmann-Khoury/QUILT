"""Module Containing the Seam Search Space class."""

from typing import Any, cast

from knitout_interpreter.knitout_operations.Knitout_Line import Knitout_Line
from networkx import DiGraph

from quilt_knit.swatch.Seam_Connection import Seam_Connection
from quilt_knit.swatch.Swatch import Swatch
from quilt_knit.swatch.swatch_boundary_instruction import Swatch_Boundary_Instruction


class Seam_Search_Space:
    """Super class representing a network of possible connections between two merged swatches.

    Attributes:
        seam_network (DiGraph): The network of boundary instructions that form allowed connections between swatches.
        instructions_to_boundary_instruction (dict[Knitout_line, Swatch_Boundary_Instruction]): Dictionary of Knitout instructions to their corresponding boundary instruction.
    """
    def __init__(self, from_swatch: Swatch, to_swatch: Swatch) -> None:
        self._from_swatch: Swatch = from_swatch
        self._to_swatch: Swatch = to_swatch
        self.seam_network: DiGraph = DiGraph()
        self.instructions_to_boundary_instruction: dict[Knitout_Line, Swatch_Boundary_Instruction] = {}

    def _add_connection(self, connection: Seam_Connection, edge_args: dict[str, Any] | None = None) -> None:
        """
        Add a connection to the search space.

        Args:
            connection (Seam_Connection): The connection to add to the seam-network.
            edge_args (dict[str, Any], optional): Additional keyword arguments to associated with the edge. Defaults to an empty keyword set.
        """
        if edge_args is None:
            edge_args = {}
        self.seam_network.add_edge(connection.seam_exit, connection.seam_entrance, connection=connection, **edge_args)
        self.instructions_to_boundary_instruction[connection.seam_exit.instruction] = connection.seam_exit
        self.instructions_to_boundary_instruction[connection.seam_entrance.instruction] = connection.seam_entrance

    def _remove_connection(self, exit_instruction: Swatch_Boundary_Instruction, entrance_instruction: Swatch_Boundary_Instruction) -> None:
        """
        Remove any connection from the exit instruction to the entrance instruction in the search space.
        Args:
            exit_instruction (Swatch_Boundary_Instruction): The exit instruction in the connection to be removed.
            entrance_instruction (Swatch_Boundary_Instruction): The entrance instruction in the connection to be removed.
        """
        self.seam_network.remove_edge(exit_instruction, entrance_instruction)

    def remove_boundary(self, instruction: Knitout_Line) -> Swatch_Boundary_Instruction | None:
        """
        Removes any boundary instruction associated with the given instruction from the search space.
        If the instruction does not belong to a boundary, nothing happens.

        Args:
            instruction (Knitout_Line): The boundary instruction to remove from the search space.

        Returns:
            Swatch_Boundary_Instruction | None: The boundary instruction that was removed or None, if no boundary was found by that instruction.
        """
        if instruction in self.instructions_to_boundary_instruction:
            boundary = self.instructions_to_boundary_instruction[instruction]
            if self.seam_network.has_node(boundary):
                self.seam_network.remove_node(boundary)
            del self.instructions_to_boundary_instruction[instruction]
            return boundary
        else:
            return None

    def _get_connection(self, exit_instruction: Swatch_Boundary_Instruction, entrance_instruction: Swatch_Boundary_Instruction) -> Seam_Connection | None:
        """
        Args:
            exit_instruction (Swatch_Boundary_Instruction): The exit instruction in the connection.
            entrance_instruction (Swatch_Boundary_Instruction): The entrance instruction in the connection.

        Returns:
            Seam_Connection | None: The connection between the exit instruction and the entrance instruction or None if that connection is not in the search space.
        """
        if self.seam_network.has_edge(exit_instruction, entrance_instruction):
            connection = self.seam_network.edges[exit_instruction, entrance_instruction]['connection']
            assert isinstance(connection, Seam_Connection)
            return connection
        else:
            return None

    def available_connections(self, boundary_instruction: Swatch_Boundary_Instruction) -> set[Seam_Connection]:
        """
        Args:
            boundary_instruction (Wale_Boundary_Instruction): The boundary instruction to find the available connections to.

        Returns:
            set[Seam_Connection]:
                A list of all available connections to the given instruction. If this is an exit, only entrance instructions will be returned. If it is an entrance, only exits will be returned.
        """
        if boundary_instruction not in self.seam_network:
            return set()
        connections = set(self._get_connection(e, boundary_instruction) for e in self.seam_network.predecessors(boundary_instruction))
        connections.update(self._get_connection(boundary_instruction, e) for e in self.seam_network.successors(boundary_instruction))
        return cast(set[Seam_Connection], connections)
