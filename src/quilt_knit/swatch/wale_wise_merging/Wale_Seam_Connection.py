"""Module containing the Wale_Seam_Connection class."""
from __future__ import annotations

from typing import cast

from knitout_interpreter.knitout_operations.knitout_instruction import (
    Knitout_Instruction,
)
from knitout_interpreter.knitout_operations.needle_instructions import Xfer_Instruction
from knitout_interpreter.knitout_operations.Rack_Instruction import Rack_Instruction
from virtual_knitting_machine.Knitting_Machine import Knitting_Machine
from virtual_knitting_machine.machine_components.needles.Needle import Needle
from virtual_knitting_machine.machine_components.needles.Slider_Needle import (
    Slider_Needle,
)

from quilt_knit.swatch.Seam_Connection import Seam_Connection
from quilt_knit.swatch.wale_boundary_instructions import Wale_Boundary_Instruction


class Wale_Seam_Connection(Seam_Connection):
    """ A Class representing the effects of connecting an exit and entrance instruction between two swatches."""

    @property
    def exit_instruction(self) -> Wale_Boundary_Instruction:
        """
        Returns:
            Wale_Boundary_Instruction: The instruction that exits a wale boundary.
        """
        assert isinstance(self._exit_instruction, Wale_Boundary_Instruction)
        return self._exit_instruction

    @property
    def entrance_instruction(self) -> Wale_Boundary_Instruction:
        """
        Returns:
            Wale_Boundary_Instruction: The instruction that enters a wale boundary.
        """
        assert isinstance(self._entrance_instruction, Wale_Boundary_Instruction)
        return self._entrance_instruction

    @property
    def can_satisfy_connection(self) -> bool:
        """
        Returns:
            bool: True if this connection can satisfy alignment of loops. False, otherwise.
        """
        return self.exit_instruction.required_exit_connections > 0 and self.entrance_instruction.requires_entrance_connection

    def minimum_instructions_to_connect_to_entrance(self, max_rack: int = 3) -> list[Knitout_Instruction] | None:
        """
        Args:
            max_rack (int, optional): Maximum racking distance allowed to form a connection. Defaults to 3.

        Returns:
            list[Knitout_Instruction]:
                List knitout instructions needed to form this connection or None if the connection cannot be formed. An empty list indicates that the connection is already aligned.
                Otherwise, instructions will be returned in teh following order:

                1. An optional transfer to a slider needle to hold loops on opposite bed for transfer.
                2. An optional racking instruction to align loops on the opposite bed of the entrance with the entrance instruction.
                3. A transfer from the opposite bed to the entrance instruction to place the exit loop on the entrance needle.
        """
        if not self.can_satisfy_connection:
            return None
        connect_to_front = self.minimum_instructions_required_to_front_entrance(max_rack)
        if connect_to_front is None:
            return self.minimum_instructions_required_to_back_entrance(max_rack)
        else:
            return connect_to_front

    def minimum_instructions_required_to_front_entrance(self, max_rack: int = 3) -> list[Knitout_Instruction] | None:
        """
        Args:
            max_rack (int, optional): Maximum racking distance allowed to form a connection. Defaults to 3.

        Returns:
            list[Knitout_Instruction]:
                List knitout instructions needed to form this connection for the front needle or None if that connection cannot be formed.
                An empty list indicates that the connection is already aligned.
                Otherwise, instructions will be returned in teh following order:

                1. An optional transfer to a slider needle to hold loops on opposite bed for transfer.
                2. An optional racking instruction to align loops on the opposite bed of the entrance with the entrance instruction.
                3. A transfer from the opposite bed to the entrance instruction to place the exit loop on the entrance needle.
        """
        if self.entrance_instruction.enters_front_needle:  # Find alignment instruction to front bed entrance.
            if self.exit_instruction.exits_front_needle and self.entrance_instruction.front_needle == self.exit_instruction.front_needle:
                return []  # The exit and entrance are already aligned. No Instructions required.
            alignment_instructions = []
            if not self.exit_instruction.exits_back_needle:  # No exit on back to transfer onto front bed entrance
                exit_back_needle: Needle = Slider_Needle(is_front=False, position=cast(Needle, self.exit_instruction.front_needle).position)
                alignment_instructions.append(Xfer_Instruction(self.exit_instruction.front_needle, exit_back_needle,
                                                               comment=f"Hold exit on {self.exit_instruction.front_needle} on back slider"))
            else:
                exit_back_needle: Needle = self.exit_instruction.back_needle
            required_rack = Knitting_Machine.get_rack(front_pos=cast(Needle, self.entrance_instruction.front_needle).position, back_pos=exit_back_needle.position)
            if abs(required_rack) >= max_rack:
                return None  # Cannot make this connection without exceeding the given maximum racking.
            elif required_rack != 0:
                alignment_instructions.append(Rack_Instruction(required_rack, f"Align exit on {exit_back_needle} to entrance on {self.entrance_instruction.needle}"))
            alignment_instructions.append(Xfer_Instruction(exit_back_needle, self.entrance_instruction.needle,
                                                           comment=f"Align exit loop from  {self.exit_instruction.needle} to entrance on {self.entrance_instruction.needle}"))
            return alignment_instructions
        else:
            return None

    def minimum_instructions_required_to_back_entrance(self, max_rack: int = 3) -> list[Knitout_Instruction] | None:
        """
        Args:
            max_rack (int, optional): Maximum racking distance allowed to form a connection. Defaults to 3.

        Returns:
            list[Knitout_Instruction]:
                List knitout instructions needed to form this connection for the back needle or None if that connection cannot be formed.
                An empty list indicates that the connection is already aligned.
                Otherwise, instructions will be returned in teh following order:

                1. An optional transfer to a slider needle to hold loops on opposite bed for transfer.
                2. An optional racking instruction to align loops on the opposite bed of the entrance with the entrance instruction.
                3. A transfer from the opposite bed to the entrance instruction to place the exit loop on the entrance needle.
        """
        if self.entrance_instruction.enters_back_needle:  # Find alignment instruction to back bed entrance
            if self.exit_instruction.exits_back_needle and self.entrance_instruction.back_needle == self.exit_instruction.back_needle:
                return []
            alignment_instructions = []
            if not self.exit_instruction.exits_front_needle:  # No exit on front to transfer onto back bed entrance:
                exit_front_needle = Slider_Needle(is_front=True, position=cast(Needle, self.exit_instruction.back_needle).position)
                alignment_instructions.append(Xfer_Instruction(self.exit_instruction.back_needle, exit_front_needle,
                                                               comment=f"Hold exit on {self.exit_instruction.needle} on front slider"))
            else:
                exit_front_needle = self.exit_instruction.front_needle
            required_rack = Knitting_Machine.get_rack(front_pos=exit_front_needle.position, back_pos=cast(Needle, self.entrance_instruction.back_needle).position)
            if abs(required_rack) >= max_rack:
                return None  # Cannot make this connection without exceeding the given maximum racking.
            elif required_rack != 0:
                alignment_instructions.append(Rack_Instruction(required_rack, f"Align exit on {exit_front_needle} to entrance on {self.entrance_instruction.needle}"))
            alignment_instructions.append(Xfer_Instruction(exit_front_needle, self.entrance_instruction.needle,
                                                           comment=f"Align exit loop from  {self.exit_instruction.needle} to entrance on {self.entrance_instruction.needle}"))
            return alignment_instructions
        else:
            return None

    def required_rack(self) -> int:
        """
        Returns:
            int: The racking required to perform the minimum alignment between this exit and entrance instruction.

        Notes:
            * This does not check that the instructions require alignment (e.g., exit drops or entrance tucks).
        """
        if self.entrance_instruction.enters_front_needle:
            if self.exit_instruction.two_needle_exit:
                if self.entrance_instruction.needle == self.exit_instruction.front_needle:
                    return 0
                else:
                    return int(Knitting_Machine.get_rack(front_pos=cast(Needle, self.entrance_instruction.front_needle).position, back_pos=cast(Needle, self.exit_instruction.back_needle).position))
            else:
                return int(Knitting_Machine.get_rack(front_pos=cast(Needle, self.entrance_instruction.front_needle).position, back_pos=cast(Needle, self.exit_instruction.needle).position))
        else:  # back needle alignment
            if self.exit_instruction.two_needle_exit:
                if self.entrance_instruction.needle == self.exit_instruction.back_needle:
                    return 0
                else:
                    return int(Knitting_Machine.get_rack(front_pos=cast(Needle, self.exit_instruction.front_needle).position, back_pos=cast(Needle, self.entrance_instruction.back_needle).position))
            else:
                return int(Knitting_Machine.get_rack(front_pos=cast(Needle, self.exit_instruction.needle).position, back_pos=cast(Needle, self.entrance_instruction.back_needle).position))

    def better_connection(self, other: Wale_Seam_Connection) -> bool:
        """
        Args:
            other (Wale_Seam_Connection): The other connection to compare to.

        Returns:
            bool: True if this connection is better than the other connection. Connections are better if they can form a connection and do so with fewer operations.
        """
        minimum_instructions_for_self = self.minimum_instructions_to_connect_to_entrance()
        minimum_instructions_for_other = other.minimum_instructions_to_connect_to_entrance()
        if minimum_instructions_for_self is None:
            return False  # This is equal to (no alignment solution) or worse than an aligned solution.
        elif minimum_instructions_for_other is None:
            return False  # The other connection is worse because it has no alignment
        else:
            return len(minimum_instructions_for_self) < len(minimum_instructions_for_other)

    def __lt__(self, other: Wale_Seam_Connection) -> bool:
        """
        Args:
            other (Wale_Seam_Connection): The other connection to compare to.

        Returns:
            bool: True if this connection is strictly better than the other connection. A connection is better if it can form a connection in fewer operations.
        """
        return self.better_connection(other)
