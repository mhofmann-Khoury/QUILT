"""Module containing the Seam_Connection class."""
from __future__ import annotations

from dataclasses import dataclass, field

from quilt_knit.swatch.swatch_boundary_instruction import Swatch_Boundary_Instruction


@dataclass
class Seam_Connection:
    """Super class of the connections between exit-entrance instruction boundaries for merging swatches."""
    _exit_instruction: Swatch_Boundary_Instruction = field(compare=False)  # The exit instruction connecting the swatches
    _entrance_instruction: Swatch_Boundary_Instruction = field(compare=False)  # The entrance instruction connecting the swatches

    @property
    def seam_exit(self) -> Swatch_Boundary_Instruction:
        """
        Returns:
            Swatch_Boundary_Instruction: The instruction that exits the merging swatch.
        """
        assert isinstance(self._exit_instruction, Swatch_Boundary_Instruction)
        return self._exit_instruction

    @property
    def seam_entrance(self) -> Swatch_Boundary_Instruction:
        """
        Returns:
            Swatch_Boundary_Instruction: The instruction that enters the merging swatch
        """
        assert isinstance(self._entrance_instruction, Swatch_Boundary_Instruction)
        return self._entrance_instruction

    def __lt__(self, other: Seam_Connection) -> bool:
        """
        Args:
            other (Seam_Connection): The other seam connection to compare to.

        Returns:
            bool: True if the other seam connection's exit instruction comes after this exit instruction in their original swatch programs.

        Notes:
            This is reimplemented in the subclasses for more nuanced comparison of connections.
        """
        if self._exit_instruction.instruction_index is None:
            return True
        elif other._exit_instruction.instruction_index is None:
            return False
        return self._exit_instruction.instruction_index < other._exit_instruction.instruction_index

    @staticmethod
    def sort_connections(connections: set[Seam_Connection]) -> list[Seam_Connection]:
        """
        Args:
            connections (set[Seam_Connection]): The list of connections to sort.

        Returns:
            List[Seam_Connection]: The sorted list of connections.
        """
        return sorted(connections)

    def __eq__(self, other: Seam_Connection) -> bool:
        """
        Args:
            other (Course_Seam_Connection): The other connection to compare to.

        Returns:
            bool: True if both connections connect the same entrance-exit pairs.
        """
        return self._exit_instruction == other._exit_instruction and self._entrance_instruction == other._entrance_instruction

    def __hash__(self) -> int:
        """
        Returns:
            int: Hash of the tuple of the exit and entrance instruction.
        """
        return hash((self._exit_instruction, self._entrance_instruction))

    def __contains__(self, item: Swatch_Boundary_Instruction) -> bool:
        """
        Args:
            item (Swatch_Boundary_Instruction): The instruction to find in the connection.

        Returns:
            bool: True if the given item is one of the boundary instructions involved in the connection. False, otherwise.
        """
        return item == self._exit_instruction or item == self._entrance_instruction
