"""Module containing structure that define course-wise boundary instructions of swatch programs."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from knitout_interpreter.knitout_operations.needle_instructions import Xfer_Instruction
from virtual_knitting_machine.machine_components.carriage_system.Carriage_Pass_Direction import (
    Carriage_Pass_Direction,
)

from quilt_knit.swatch.swatch_boundary_instruction import Swatch_Boundary_Instruction
from quilt_knit.swatch.Swatch_Side import Swatch_Side

if TYPE_CHECKING:
    from knitout_interpreter.knitout_operations.needle_instructions import (
        Needle_Instruction,
    )


class Course_Side(Swatch_Side, Enum):
    """Enumeration of the side of a swatch an instruction exists on. Used to differentiate between entrance-exit seam directions."""

    Left = "Left"  # Indicates that an instruction is on the left side of the swatch
    Right = "Right"  # Indicates that an instruction is on the right side of the swatch

    @staticmethod
    def entrance_by_direction(direction: Carriage_Pass_Direction) -> Course_Side:
        """
        Args:
            direction (Carriage_Pass_Direction): The direction of a carriage pass to find the entrance side of a course.

        Returns:
            Course_Side: The side of the course that would be entered by the given carriage pass direction
        """
        if direction is Carriage_Pass_Direction.Leftward:
            return Course_Side.Right
        else:
            return Course_Side.Left

    @staticmethod
    def exit_by_direction(direction: Carriage_Pass_Direction) -> Course_Side:
        """
        Args:
            direction (Carriage_Pass_Direction): The direction of a carriage pass to find the exit side of a course.

        Returns:
            Course_Side: The side of the course that would be exited by the given carriage pass direction
        """
        if direction is Carriage_Pass_Direction.Leftward:
            return Course_Side.Left
        else:
            return Course_Side.Right

    def __str__(self) -> str:
        """
        Returns:
            (str): The name of this course side.
        """
        return self.name

    def __repr__(self) -> str:
        """
        Returns:
            (str): The name of this course side.
        """
        return str(self)

    @property
    def opposite(self) -> Course_Side:
        """
        Returns:
            Course_Side: The opposite of this course side.
        """
        if self is Course_Side.Left:
            return Course_Side.Right
        else:
            return Course_Side.Left

    def __invert__(self) -> Course_Side:
        """
        Returns:
            Course_Side: The opposite of this course side.
        """
        return self.opposite

    def __neg__(self) -> Course_Side:
        """
        Returns:
            Course_Side: The opposite of this course side.
        """
        return self.opposite


class Course_Boundary_Type(Enum):
    """Enumeration of the course-wise boundary entrance/exit types."""
    exit_boundary = "exit"  # Implies that this boundary can exit the carriage pass.
    entrance = "entrance"  # Implies that this boundary can enter the carriage pass.
    entrance_exit = "entrance-exit"  # Implies that this boundary can enter or exit the carriage pass.
    blocked = "blocked"  # Implies that this boundary is neither an exit nor entrance to the carriage pass.

    def is_exit(self) -> bool:
        """
        Returns:
            True if the boundary is an exit. False, otherwise.
        """
        return self in {Course_Boundary_Type.exit_boundary, Course_Boundary_Type.entrance_exit}

    def is_entrance(self) -> bool:
        """
        Returns:
            True if the boundary is an entrance. False, otherwise.
        """
        return self in {Course_Boundary_Type.entrance, Course_Boundary_Type.entrance_exit}

    def __str__(self) -> str:
        """
        Returns:
            (str): The name of this boundary type.
        """
        return self.name

    def __repr__(self) -> str:
        """
        Returns:
            (str): The name of this boundary type.
        """
        return str(self)

    def __hash__(self) -> int:
        """
        Returns:
            int: The hash value of the name of this boundary type
        """
        return hash(self.name)

    @property
    def opposite(self) -> Course_Boundary_Type:
        """
        Returns:
            Course_Boundary_Type: The opposite of this boundary type. Entrance-Exits and blocked boundaries remain unchanged.
        """
        if self is Course_Boundary_Type.exit_boundary:
            return Course_Boundary_Type.entrance
        elif self is Course_Boundary_Type.entrance:
            return Course_Boundary_Type.exit_boundary
        else:  # Entrance Exits and Blocked boundaries
            return self

    def __invert__(self) -> Course_Boundary_Type:
        """
        Returns:
            Course_Boundary_Type: The opposite of this boundary type.
        """
        return self.opposite

    def __neg__(self) -> Course_Boundary_Type:
        """
        Returns:
            Course_Boundary_Type: The opposite of this boundary type.
        """
        return self.opposite


@dataclass(unsafe_hash=True)
class Course_Boundary_Instruction(Swatch_Boundary_Instruction):
    """ A class to represent instructions on the course-wise boundary of a swatch program."""
    left_boundary_type: Course_Boundary_Type  # The boundary type from the left side of the swatch.
    right_boundary_type: Course_Boundary_Type  # The boundary type from the right side of the swatch.
    carriage_pass_rack: int  # The racking alignment of the carriage pass of this instruction
    carriage_pass_is_all_needle: bool  # True if the carriage pass is racked for all-needle knitting
    carriage_pass_index: int  # The index of the carriage pass in the swatch program that formed this boundary instruction.

    @property
    def is_left(self) -> bool:
        """
        Returns:
            bool: True if the boundary instruction can enter or exit the left side of its carriage pass.
        """
        return self.left_boundary_type is not Course_Boundary_Type.blocked

    @property
    def is_right(self) -> bool:
        """
        Returns:
            bool: True if the boundary instruction can enter or exit the right side of its carriage pass.
        """
        return self.right_boundary_type is not Course_Boundary_Type.blocked

    @property
    def is_left_exit(self) -> bool:
        """
        Returns:
            bool: True if the boundary instruction can exit the left side of its carriage pass.
        """
        return self.left_boundary_type.is_exit()

    @property
    def is_right_exit(self) -> bool:
        """
        Returns:
            bool: True if the boundary instruction can exit the right side of its carriage pass.
        """
        return self.right_boundary_type.is_exit()

    @property
    def is_left_entrance(self) -> bool:
        """
        Returns:
            bool: True if the boundary instruction can enter the left side of its carriage pass.
        """
        return self.left_boundary_type.is_entrance()

    @property
    def is_right_entrance(self) -> bool:
        """
        Returns:
            bool: True if the boundary instruction can enter the right side of its carriage pass.
        """
        return self.right_boundary_type.is_entrance()

    def has_potential_left_to_right_connection(self, right_boundary_instruction: Course_Boundary_Instruction) -> bool:
        """

        Args:
            right_boundary_instruction (Course_Boundary_Instruction): The boundary instruction to find potential connection to, presuming it is on the right side of the boundary.

        Returns:
            bool: True if the boundaries are on opposite course sides, proceed in the same carriage pass direction, and are an entrance exit pair. False, otherwise.

        """
        if not self._matching_carriage_pass_types(right_boundary_instruction):
            return False
        if self.is_left_exit:
            return right_boundary_instruction.is_right_entrance
        elif self.is_left_entrance:
            return right_boundary_instruction.is_right_exit
        return False

    def _matching_carriage_pass_types(self, other_boundary_instruction: Course_Boundary_Instruction) -> bool:
        """
        Carriage passes can be connected if they are in the same direction, occur at the same racking, and if they are both loop-forming or xfer passes.

        Args:
            other_boundary_instruction (Course_Boundary_Instruction): The boundary instruction to check for possible connections to.

        Returns:
            bool: True if the two instructions are of similar enough types for a valid connection of their carriage passes.
        """
        if self.direction != other_boundary_instruction.direction:
            return False
        elif isinstance(self.instruction, Xfer_Instruction) and not isinstance(other_boundary_instruction.instruction, Xfer_Instruction):
            return False
        return self.carriage_pass_rack == other_boundary_instruction.carriage_pass_rack and self.carriage_pass_is_all_needle == other_boundary_instruction.carriage_pass_is_all_needle

    def __str__(self) -> str:
        """
        Returns:
            str: A string expressing the entrance-exit direction and blocked status of this boundary instruction.
        """
        left = "\\"
        right = "\\"
        if self.is_left_entrance:
            if self.is_left_exit:
                left = "<>"
            else:
                left = "->"
        elif self.is_left_exit:
            left = "<-"

        if self.is_right_entrance:
            if self.is_right_exit:
                right = "<>"
            else:
                right = "<-"
        elif self.is_right_exit:
            left = "->"
        i_str = str(self.instruction)[:-1]
        return f"{left}{i_str}{right}"
