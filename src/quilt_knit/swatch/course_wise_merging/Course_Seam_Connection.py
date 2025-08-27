"""Module containing the Course_Seam_Connection class."""
from __future__ import annotations

from dataclasses import dataclass, field

from quilt_knit.swatch.course_boundary_instructions import (
    Course_Boundary_Instruction,
    Course_Side,
)


@dataclass
class Course_Seam_Connection:
    """ A Class representing the effects of connecting an exit and entrance instruction between two swatches."""
    exit_instruction: Course_Boundary_Instruction = field(compare=False)  # The exit instruction connecting the swatches course-wise
    entrance_instruction: Course_Boundary_Instruction = field(compare=False)  # The entrance instruction connecting the swatches course-wise.

    def __eq__(self, other: Course_Seam_Connection) -> bool:
        """
        Args:
            other (Course_Seam_Connection): The other connection to compare to.

        Returns:
            bool: True if both connections connect the same entrance-exit pairs.
        """
        return self.exit_instruction == other.exit_instruction and self.entrance_instruction == other.entrance_instruction

    def __str__(self) -> str:
        """
        Returns:
            str: A string representation of the Course_Seam_Connection.
        """
        exit_instruction = str(self.exit_instruction.instruction).rstrip()
        entrance_instruction = str(self.entrance_instruction.instruction).rstrip()
        exit_str = f"{self.exit_instruction.source_swatch_name}:{self.exit_instruction.carriage_pass_index}:{exit_instruction}"
        entrance_str = f"{self.entrance_instruction.source_swatch_name}:{self.entrance_instruction.carriage_pass_index}:{entrance_instruction}"
        if self.exit_instruction.is_left:
            return f"<-{entrance_str}<-{exit_str}<-"
        else:
            return f"->{exit_str}->{entrance_str}->"

    def __repr__(self) -> str:
        """
        Returns:
            str: A string representation of the Course_Seam_Connection.
        """
        return str(self)

    @property
    def distance(self) -> int:
        """
        Returns:
            int: The distances between the carriage passes linked by this connection.
        """
        return abs(self.exit_instruction.carriage_pass_index - self.entrance_instruction.carriage_pass_index)

    @property
    def shared_carriers(self) -> set[int]:
        """
        Returns:
            set[int]: The set of carrier ids that are shared between the linked instructions.
        """
        exit_set = self.exit_carrier_ids
        entrance_set = self.entrance_carrier_ids
        return exit_set.intersection(entrance_set)

    @property
    def entrance_carrier_ids(self) -> set[int]:
        """
        Returns:
            set[int]: The set of carrier ids involved in the entrance instruction.
        """
        if self.entrance_instruction.carrier_set is None:
            return set()
        else:
            return set(self.entrance_instruction.carrier_set)

    @property
    def exit_carrier_ids(self) -> set[int]:
        """
        Returns:
            set[int]: The set of carrier ids involved in the exit instruction.
        """
        if self.exit_instruction.carrier_set is None:
            return set()
        else:
            return set(self.exit_instruction.carrier_set)

    @property
    def requires_cut(self) -> bool:
        """
        Returns:
            bool: True if creating this connection will require a cut operation on exit carriers not passed over the connection.
        """
        return len(self.shared_carriers) < len(self.exit_carrier_ids)

    def __hash__(self) -> int:
        """
        Returns:
            int: Hash of the tuple of the exit and entrance instruction.
        """
        return hash((self.exit_instruction, self.entrance_instruction))

    def __contains__(self, item: Course_Boundary_Instruction) -> bool:
        """
        Args:
            item (Course_Boundary_Instruction): The instruction to find in the connection.

        Returns:
            bool: True if the given item is one of the boundary instructions involved in the connection. False, otherwise.
        """
        return item == self.exit_instruction or item == self.entrance_instruction

    def __getitem__(self, item: Course_Side) -> Course_Boundary_Instruction:
        """
        Args:
            item (Course_Side): The course side that references the desired boundary instruction

        Returns:
            Course_Boundary_Instruction: The boundary instruction that matches the given course side.
        """
        if self.exit_instruction.course_side == item:
            return self.exit_instruction
        else:
            return self.entrance_instruction
