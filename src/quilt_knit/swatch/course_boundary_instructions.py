"""Module containing structure that define course-wise boundary instructions of swatch programs."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from virtual_knitting_machine.machine_components.carriage_system.Carriage_Pass_Direction import (
    Carriage_Pass_Direction,
)

from quilt_knit.swatch.swatch_boundary_instruction import Swatch_Boundary_Instruction


class Course_Side(Enum):
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

    def __hash__(self) -> int:
        """
        Returns:
            int: The hash value of the name of this Course_Side
        """
        return hash(self.name)

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


@dataclass(unsafe_hash=True)
class Course_Boundary_Instruction(Swatch_Boundary_Instruction):
    """ A class to represent instructions on the course-wise boundary of a swatch program."""
    is_exit: bool  # If this boundary instruction allows an exit from this carriage pass. Note that is_entrance and is_exit are not mutually exclusive in single instruction carriage passes.
    course_side: Course_Side  # The side of the course that the instruction is on.
    carriage_pass_index: int  # The index of the carriage pass in the swatch program that formed this boundary instruction.
    blocked_on_left: bool  # If true, this instruction cannot be merged with a carriage pass coming from the left side.
    blocked_on_right: bool  # If true, this instruction cannot be merged with a carriage pass coming from the right side.

    @property
    def is_left(self) -> bool:
        """
        Returns:
            bool: True if this instruction is on the left boundary of the swatch. False otherwise.
        """
        return self.course_side is Course_Side.Left

    @property
    def is_right(self) -> bool:
        """
        Returns:
            bool: True if this instruction is on the right boundary of the swatch. False otherwise.
        """
        return self.course_side is Course_Side.Right

    def has_potential_connection(self, other_boundary_instruction: Course_Boundary_Instruction) -> bool:
        """

        Args:
            other_boundary_instruction (Course_Boundary_Instruction): The other boundary instruction to check for possible connections to.

        Returns:
            bool: True if the boundaries are on opposite course sides, proceed in the same carriage pass direction, and are an entrance exit pair. False, otherwise.

        """
        if self.course_side != other_boundary_instruction.course_side and self.direction == other_boundary_instruction.direction:
            if self.is_entrance:
                return other_boundary_instruction.is_exit
            else:
                assert self.is_exit
                return other_boundary_instruction.is_entrance
        else:
            return False

    def __str__(self) -> str:
        """
        Returns:
            str: A string expressing the entrance-exit direction and blocked status of this boundary instruction.
        """
        if self.course_side is Course_Side.Left:
            if self.is_entrance:
                if self.blocked_on_left:
                    left = "-\\>"
                else:
                    left = "->"
                if self.is_exit:  # both entrance and exit
                    if self.blocked_on_right:
                        right = "-\\>"
                    else:
                        right = "->"
                else:
                    right = ""
            else:
                assert self.is_exit
                right = ""
                if self.blocked_on_left:
                    left = "<\\-"
                else:
                    left = "<-"
        else:
            if self.is_entrance:
                if self.blocked_on_right:
                    right = "<\\-"
                else:
                    right = "<-"
                if self.is_exit:  # both entrance and exit
                    if self.blocked_on_left:
                        left = "<\\-"
                    else:
                        left = "<-"
                else:
                    left = ""
            else:
                assert self.is_exit
                left = ""
                if self.blocked_on_right:
                    right = "-\\>"
                else:
                    right = "->"
        i_str = str(self.instruction)[:-1]
        return f"{left}{i_str}{right}"
