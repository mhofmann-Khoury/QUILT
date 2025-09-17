"""Module containing structure that define horizontal boundary instructions."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from knitout_interpreter.knitout_operations.needle_instructions import (
    Drop_Instruction,
    Miss_Instruction,
    Split_Instruction,
    Tuck_Instruction,
    Xfer_Instruction,
)
from virtual_knitting_machine.machine_components.needles.Needle import Needle

from quilt_knit.swatch.swatch_boundary_instruction import Swatch_Boundary_Instruction
from quilt_knit.swatch.Swatch_Side import Swatch_Side

if TYPE_CHECKING:
    from knitout_interpreter.knitout_operations.needle_instructions import (
        Needle_Instruction,
    )

class Wale_Side(Swatch_Side, Enum):
    """Enumeration of the wale-wise side of a swatch an instruction exists on. Used to differentiate between entrance-exit seam directions."""
    Top = "Top"  # Indicates that an instruction is on the top boundary of a swatch
    Bottom = "Bottom"  # Indicates that an instruction is on the bottom boundary of a swatch

    def __str__(self) -> str:
        """
        Returns:
            (str): The name of this wale side.
        """
        return self.name

    def __repr__(self) -> str:
        """
        Returns:
            (str): The name of this wale side.
        """
        return str(self)

    @property
    def opposite(self) -> Wale_Side:
        """
        Returns:
            Wale_Side: The opposite of this wale side.
        """
        if self is Wale_Side.Top:
            return Wale_Side.Bottom
        else:
            return Wale_Side.Top

    def __invert__(self) -> Wale_Side:
        """
        Returns:
            Wale_Side: The opposite of this wale side.
        """
        return self.opposite

    def __neg__(self) -> Wale_Side:
        """
        Returns:
            Wale_Side: The opposite of this wale side.
        """
        return self.opposite


@dataclass(unsafe_hash=True)
class Wale_Boundary_Instruction(Swatch_Boundary_Instruction):
    """ A class that represent instructions that process loops on the wale-wise boundary of a swatch program"""
    is_entrance: bool  # If this boundary instruction allows entrance to the swatch program.
    is_exit: bool  # If this boundary instructions allows an exit from the swatch program.
    _connections_made: int = field(default=0, compare=False, hash=False)

    @property
    def connections_made(self) -> int:
        """
        Returns:
            int: The number of reported connections made to this boundary instruction.
        """
        return self._connections_made

    def add_connection(self) -> None:
        """
        Increments the number of connections available to this boundary instruction.
        """
        self._connections_made += 1

    @property
    def swatch_side(self) -> Wale_Side:
        """
        Returns:
            Wale_Side: The side of the wale this instruction belongs to base don if it is an entrance or an exit.
        """
        """
        :return: The side of the swatch that the instruction belongs to.
        """
        if self.is_entrance:
            return Wale_Side.Bottom  # enter into the bottom of a swatch.
        else:
            return Wale_Side.Top  # exit from the top of a swatch.

    @property
    def entrance_needle(self) -> Needle:
        """
        Returns:
            Needle: The needle that the instruction enters.
        """
        return self.needle

    @property
    def exit_needle(self) -> None | Needle | tuple[Needle, Needle]:
        """
        Returns:
            None | Needle | tuple[Needle, Needle]: The needle or needles (split) that loops are left on after the instruction is executed. None if the instruction drops the loops.
        """
        if isinstance(self.instruction, Drop_Instruction) or isinstance(self.instruction, Miss_Instruction):
            return None
        elif isinstance(self.instruction, Split_Instruction):
            assert isinstance(self.instruction.needle_2, Needle)
            return self.needle, self.instruction.needle_2
        elif isinstance(self.instruction, Xfer_Instruction):
            assert isinstance(self.instruction.needle_2, Needle)
            return self.instruction.needle_2
        else:
            return self.needle

    @property
    def front_needle(self) -> None | Needle:
        """
        Returns:
            None | Needle: The front needle involved in this instruction or None if it does not involve a front bed needle.
        """
        if self.needle.is_front:
            return self.needle
        elif self.two_needle_exit:
            return self.instruction.needle_2
        else:
            return None

    @property
    def back_needle(self) -> None | Needle:
        """
        Returns:
            None | Needle: The back needle involved in this instruction or None if it does not involve a back bed needle.
        """
        if self.needle.is_back:
            return self.needle
        elif self.two_needle_exit:
            return self.instruction.needle_2
        else:
            return None

    @property
    def two_needle_exit(self) -> bool:
        """
        Returns:
            bool: True if an exit instruction that splits, leaving loops on two needles. False, otherwise.
        """
        return self.is_exit and isinstance(self.instruction, Split_Instruction)

    @property
    def entrance_requires_loop(self) -> bool:
        """
        Returns:
            bool: True if this is an entrance instruction that requires an input loop at the operating needle. False, otherwise.
        """
        return self.is_entrance and self.entrance_needle is not None

    @property
    def enters_front_needle(self) -> bool:
        """
        Returns:
            bool: True if this is an entrance instruction that must align a front bed needle to form a connection. False, otherwise.
        """
        return self.entrance_requires_loop and self.entrance_needle.is_front

    @property
    def exits_front_needle(self) -> bool:
        """
        Returns:
            bool: True if this is an exit instruction that leaves loops on a front needle. False, otherwise.
        """
        if not self.is_exit:
            return False
        exit_needle = self.exit_needle
        if exit_needle is None:
            return False
        elif isinstance(exit_needle, Needle):
            if exit_needle.is_front:
                return True
            else:
                return False
        else:  # Split front and back bed
            return True

    @property
    def enters_back_needle(self) -> bool:
        """
        Returns:
            bool: True if this is an entrance instruction that must align a back bed needle to form a connection. False, otherwise.
        """
        return self.entrance_requires_loop and self.entrance_needle.is_back

    @property
    def exits_back_needle(self) -> bool:
        """
        Returns:
            bool: True if this is an exit instruction that leaves loops on a back needle. False, otherwise.
        """
        if not self.is_exit:
            return False
        exit_needle = self.exit_needle
        if exit_needle is None:
            return False
        elif isinstance(exit_needle, Needle):
            if exit_needle.is_back:
                return True
            else:
                return False
        else:  # Split front and back bed
            return True

    @property
    def requires_entrance_connection(self) -> bool:
        """
        Returns:
            bool: True if this is an entrance instruction that must be connected (not a tuck). False, otherwise.
        """
        return self.is_entrance and not isinstance(self.instruction, Tuck_Instruction)

    @property
    def required_exit_connections(self) -> int:
        """
        Returns:
            int: The number of connections required to satisfy this exit instruction.
            * 0 if this is not an exit or if the exit drops loops.
            * 1 if this exit leaves loops on one needle.
            * 2 if this exit leaves loops on two needles (split).
        """
        if not self.is_exit or self.exit_needle is None:
            return 0
        elif isinstance(self.exit_needle, tuple):
            return 2
        else:
            return 1

    @property
    def is_top(self) -> bool:
        """
        Returns:
            bool: True if this instruction is on the top boundary of the swatch. False, otherwise.
        """
        return self.swatch_side is Wale_Side.Top

    @property
    def is_bottom(self) -> bool:
        """
        Returns:
            bool: True if this instruction is on the bottom boundary of the swatch. False, otherwise.
        """
        return self.swatch_side is Wale_Side.Bottom

    def __str__(self) -> str:
        """
        Returns:
            str: A string representation of the connection requirements and direction into this instruction.
        """
        string = ""
        if self.is_entrance:
            string += "^"
        string += str(self.instruction).strip()
        if self.is_exit:
            string += f"^{self.required_exit_connections}"
        return string

    def __repr__(self) -> str:
        """
        Returns:
            str: A string representation of the connection requirements and direction into this instruction.
        """
        return str(self)
