"""Module defining the abstract base class for swatch boundary instructions."""

from __future__ import annotations

from dataclasses import dataclass

from knitout_interpreter.knitout_operations.needle_instructions import (
    Needle_Instruction,
)
from virtual_knitting_machine.machine_components.carriage_system.Carriage_Pass_Direction import (
    Carriage_Pass_Direction,
)
from virtual_knitting_machine.machine_components.needles.Needle import Needle
from virtual_knitting_machine.machine_components.yarn_management.Yarn_Carrier_Set import (
    Yarn_Carrier_Set,
)


@dataclass(unsafe_hash=True)
class Swatch_Boundary_Instruction:
    """A class to represent instructions on the boundary of a swatch program."""
    instruction: Needle_Instruction  # The instruction associated with this boundary instruction.
    source_swatch_name: str  # The name of the swatch that this boundary instruction is sourced form.

    @property
    def carrier_set(self) -> Yarn_Carrier_Set | None:
        """
        Returns:
            Yarn_Carrier_Set | None: The carrier set of this boundary instruction or None if the instruction does not use a carrier set.
        """
        return self.instruction.carrier_set

    @property
    def needle(self) -> Needle:
        """
        Returns:
            Needle: The needle that is activated by this boundary instruction.
        """
        return self.instruction.needle

    @property
    def direction(self) -> Carriage_Pass_Direction | None:
        """
        Returns:
            Carriage_Pass_Direction | None: The direction this instruction forms a loop or None if xfer instruction.
        """
        return self.instruction.direction

    @property
    def instruction_index(self) -> int | None:
        """
        Returns:
            int | None: Index of the instruction in the original swatch program. None if the instruction does have a line number defined.
        """
        if self.instruction.original_line_number is None:
            return None
        return int(self.instruction.original_line_number)

    def __repr__(self) -> str:
        """
        Returns:
            str: A string representing this boundary instruction.
        """
        return str(self)

    def __str__(self) -> str:
        """
        Returns:
            str: The string representation of this boundary instruction.
        """
        return str(self.instruction)

    def __lt__(self, other: Needle | Needle_Instruction | Swatch_Boundary_Instruction) -> bool:
        """
        Args:
            other (Needle | Needle_Instruction | Swatch_Boundary_Instruction): The needle or instruction containing a needle to sort these instructions leftward and rightward.

        Returns:
            bool: True if this instruction is on a needle left of the other needle. False, otherwise.
        """
        if isinstance(other, Needle):
            other_needle = other
        else:
            other_needle = other.needle
        return bool(self.needle < other_needle)
