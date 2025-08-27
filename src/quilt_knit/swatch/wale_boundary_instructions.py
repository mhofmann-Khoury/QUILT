"""Module containing structure that define horizontal boundary instructions."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from knitout_interpreter.knitout_operations.needle_instructions import (
    Drop_Instruction,
    Knit_Instruction,
    Miss_Instruction,
    Split_Instruction,
    Tuck_Instruction,
)
from virtual_knitting_machine.machine_components.needles.Needle import Needle

from quilt_knit.swatch.swatch_boundary_instruction import Swatch_Boundary_Instruction


class Wale_Side(Enum):
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

    def __hash__(self) -> int:
        """
        Returns:
            int: The hash value of the name of this wale side
        """
        return hash(self.name)

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

    def entrance_replaced_with_tuck(self) -> None | Tuck_Instruction:
        """
        Returns:
            None | Tuck_Instruction: None iff this not an entrance or is not a knit instruction that can be replaced by a tuck. Otherwise, the tuck instruction that replaces the knit.
        """
        if self.is_entrance and isinstance(self.instruction, Knit_Instruction):
            return Tuck_Instruction(self.instruction.needle, self.instruction.direction, self.instruction.carrier_set, "Replaced unaligned knit with tuck")
        else:
            return None

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
    def is_exit(self) -> bool:
        """
        Indicates if this instruction exits from a wale.
        Returns:
            bool: True if this not an entrance instruction. False, otherwise.
        """
        return not self.is_entrance

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
        if self.is_exit:
            return False
        else:
            return not isinstance(self.instruction, Tuck_Instruction) and not isinstance(self.instruction, Miss_Instruction)

    @property
    def exit_drops_loop(self) -> bool:
        """
        Returns:
            bool: True if this is an exit instruction that drops a loop. False, otherwise.
        """
        return self.is_exit and isinstance(self.instruction, Drop_Instruction)

    @property
    def requires_front_needle_alignment(self) -> bool:
        """
        Returns:
            bool: True if the boundary instruction must align a front bed needle to form a connection. False, otherwise.
        """
        if self.is_entrance:
            if self.entrance_requires_loop:
                return bool(self.needle.is_front)
            else:
                return False  # Tuck operation requires no alignment
        else:
            assert self.is_exit
            if self.exit_drops_loop:
                return False
            else:
                return self.front_needle is not None

    @property
    def requires_back_needle_alignment(self) -> bool:
        """
        Returns:
            bool: True if the boundary instruction must align a back bed needle to form a connection. False, otherwise.
        """
        if self.is_entrance:
            if self.entrance_requires_loop:
                return bool(self.needle.is_back)
            else:
                return False  # tuck operation requires no alignment
        else:
            assert self.is_exit
            if self.exit_drops_loop:
                return False
            else:
                return self.back_needle is not None

    @property
    def required_connections(self) -> int:
        """
        Returns:
            int: The number of connections required to satisfy alignment to this instruction.
            * 0 Connections means that no connections are required (exit that drops loop or entrance that does not require alignment).
            * 1 Connection means that the exit leaves one loop or an entrance requires one loop.
            * 2 Connections means that this is a split exit that requires both loops to be aligned.
        """
        return sum([self.requires_front_needle_alignment, self.requires_back_needle_alignment])

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
        if self.is_entrance:
            return f"{self.required_connections}^{self.instruction}"
        else:
            return f"{self.instruction}^{self.required_connections}"
