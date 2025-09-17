"""Module containing the Course_Seam_Connection class."""
from __future__ import annotations

from knitout_interpreter.knitout_operations.needle_instructions import Xfer_Instruction

from quilt_knit.swatch.course_boundary_instructions import Course_Boundary_Instruction
from quilt_knit.swatch.Seam_Connection import Seam_Connection


class Course_Seam_Connection(Seam_Connection):
    """ A Class representing the effects of connecting an exit and entrance instruction between two swatches."""

    @property
    def exit_instruction(self) -> Course_Boundary_Instruction:
        """
        Returns:
            Course_Boundary_Instruction: The instruction that exits a course boundary.
        """
        assert isinstance(self._exit_instruction, Course_Boundary_Instruction)
        return self._exit_instruction

    @property
    def entrance_instruction(self) -> Course_Boundary_Instruction:
        """
        Returns:
            Course_Boundary_Instruction: The instruction that enters a course boundary.
        """
        assert isinstance(self._entrance_instruction, Course_Boundary_Instruction)
        return self._entrance_instruction

    @property
    def left_instruction(self) -> Course_Boundary_Instruction:
        """
        Returns:
            Course_Boundary_Instruction: The instruction on the left swatch of the seam connection.
        """
        if self.exit_instruction.is_right_exit:  # exits the right side of the left swatch
            return self.exit_instruction
        else:
            assert self.entrance_instruction.is_right_entrance  # enters the right side fo the left swatch
            return self.entrance_instruction

    @property
    def right_instruction(self) -> Course_Boundary_Instruction:
        """
        Returns:
            Course_Boundary_Instruction: The instruction on the right swatch of the seam connection.
        """
        if self.exit_instruction.is_left_exit:  # exits the left side of the right swatch
            return self.exit_instruction
        else:
            assert self.entrance_instruction.is_left_entrance  # enters the left side of the right swatch
            return self.entrance_instruction

    @property
    def leftward_connection(self) -> bool:
        """
        Returns:
            bool: True if the connection moves from the right to left swatch, False otherwise.
        """
        return self.entrance_instruction.is_left_entrance and self.exit_instruction.is_right_exit

    @property
    def rightward_connection(self) -> bool:
        """
        Returns:
            bool: True if the connection moves from the left to right swatch, False otherwise.
        """
        return self.exit_instruction.is_left_exit and self.entrance_instruction.is_right_entrance

    @property
    def xfer_connection(self) -> bool:
        """
        Returns:
            bool: True if this is a connection between transfer carriage passes. False otherwise.
        """
        return isinstance(self.exit_instruction.instruction, Xfer_Instruction)

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
    def different_carriers(self) -> int:
        """
        Returns:
            int: The number of carriers that differ between the entrance and exit instructions. Differences include different positions in the carrier set and different lengths of carrier sets.
        """
        exit_carrier_set = self.exit_instruction.carrier_set
        if exit_carrier_set is None:
            exit_carrier_set = []
        entrance_carrier_set = self.entrance_instruction.carrier_set
        if entrance_carrier_set is None:
            entrance_carrier_set = []
        differences = len([True for exit_cid, entrance_cid in zip(exit_carrier_set, entrance_carrier_set) if exit_cid != entrance_cid])
        if len(exit_carrier_set) != len(entrance_carrier_set):
            differences += abs(len(exit_carrier_set) - len(entrance_carrier_set))
        return differences

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

    def __lt__(self, other: Course_Seam_Connection) -> bool:
        """
        Args:
            other (Course_Seam_Connection): The other connection to compare with.

        Returns:
            bool: True if this connection has fewer different carriers between instructions that the other connection.

        """
        return self.different_carriers < other.different_carriers
