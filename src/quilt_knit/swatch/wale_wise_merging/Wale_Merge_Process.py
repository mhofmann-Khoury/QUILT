"""Module containing the class structure for the Vertical Swatch Merge Process. """
from collections import defaultdict
from typing import cast

from knitout_interpreter.knitout_execution_structures.Carriage_Pass import Carriage_Pass
from knitout_interpreter.knitout_operations.carrier_instructions import (
    Inhook_Instruction,
    Outhook_Instruction,
)
from knitout_interpreter.knitout_operations.Knitout_Line import Knitout_Comment_Line
from knitout_interpreter.knitout_operations.needle_instructions import (
    Drop_Instruction,
    Knit_Instruction,
    Loop_Making_Instruction,
    Tuck_Instruction,
    Xfer_Instruction,
)
from knitout_interpreter.knitout_operations.Rack_Instruction import Rack_Instruction
from virtual_knitting_machine.machine_components.carriage_system.Carriage_Pass_Direction import (
    Carriage_Pass_Direction,
)
from virtual_knitting_machine.machine_components.needles.Needle import Needle
from virtual_knitting_machine.machine_components.yarn_management.Yarn_Carrier import (
    Yarn_Carrier,
)
from virtual_knitting_machine.machine_components.yarn_management.Yarn_Carrier_Set import (
    Yarn_Carrier_Set,
)

from quilt_knit.swatch.Merge_Process import Merge_Process
from quilt_knit.swatch.Seam_Connection import Seam_Connection
from quilt_knit.swatch.Swatch import Swatch
from quilt_knit.swatch.wale_boundary_instructions import (
    Wale_Boundary_Instruction,
    Wale_Side,
)
from quilt_knit.swatch.wale_wise_merging.Wale_Seam_Connection import (
    Wale_Seam_Connection,
)
from quilt_knit.swatch.wale_wise_merging.Wale_Seam_Search_Space import (
    Wale_Seam_Search_Space,
)
from quilt_knit.swatch.wale_wise_merging.Wale_Wise_Connection import (
    Wale_Wise_Connection,
)


class Merge_Comment(Knitout_Comment_Line):
    """Super class of comments added during the merge process."""

    def __init__(self, comment: str | None) -> None:
        super().__init__(comment)


class Pre_Merge_Comment(Merge_Comment):
    def __init__(self) -> None:
        super().__init__("Prior Instructions were from the Bottom Swatch")


class Post_Merge_Comment(Merge_Comment):
    def __init__(self) -> None:
        super().__init__("Following instructions were from the Top Swatch")


class Wale_Merge_Process(Merge_Process):
    """Class to manage the vertical merging of two swatches. """

    def __init__(self, swatch_connection: Wale_Wise_Connection,
                 seam_search_space: Wale_Seam_Search_Space | None = None,
                 max_rack: int = 3):
        if seam_search_space is None:
            seam_search_space = Wale_Seam_Search_Space(swatch_connection.bottom_swatch, swatch_connection.top_swatch, max_rack=max_rack)
        super().__init__(swatch_connection, Wale_Side.Bottom, seam_search_space)
        self.seam_search_space.remove_excluded_boundary(self.wale_wise_connection)

    @property
    def wale_wise_connection(self) -> Wale_Wise_Connection:
        """
        Returns:
            Wale_Wise_Connection: The connection between the two swatches being merged.
        """
        assert isinstance(self._swatch_connection, Wale_Wise_Connection)
        return self._swatch_connection

    @property
    def seam_search_space(self) -> Wale_Seam_Search_Space:
        """
        Returns:
            Wale_Seam_Search_Space: The seam search space between entrance-exit instructions along the swatch boundaries being merged.
        """
        assert isinstance(self._seam_search_space, Wale_Seam_Search_Space)
        return self._seam_search_space

    @property
    def top_swatch(self) -> Swatch:
        """
        :return: The top swatch of the merge.
        """
        return self.wale_wise_connection.top_swatch

    @property
    def bottom_swatch(self) -> Swatch:
        """
        :return: The bottom swatch of the merge.
        """
        return self.wale_wise_connection.bottom_swatch

    def _consume_bottom_swatch(self) -> None:
        """
        Add all instructions from the bottom swatch into the new merged program.
        Update the merged tracking machine to the execution point at the end of the swatch.
        Removes all outhook operations from the program that would outhook a needed carrier in the top swatch.
        """
        top_needed_carriers = self._top_needed_carriers()
        last_outhook_instruction: dict[int, int] = {}
        for instruction in self.bottom_swatch.knitout_program:
            if isinstance(instruction, Outhook_Instruction) and instruction.carrier_id in top_needed_carriers:  # record location of an outhook that wale_entrance may remove.
                last_outhook_instruction[instruction.carrier_id] = len(self.merged_instructions)
            elif isinstance(instruction, Inhook_Instruction) and instruction.carrier_id in last_outhook_instruction:  # record the record of the last outhook, because it was reinserted
                del last_outhook_instruction[instruction.carrier_id]
            self._consume_instruction(instruction, Wale_Side.Bottom, remove_connections=False)
        if len(last_outhook_instruction) > 0:
            reverse_removal_indices = sorted(last_outhook_instruction.values(), reverse=True)
            for removal_index in reverse_removal_indices:
                del self.merged_instructions[removal_index]
            self._restart_merge_machine()

    def _top_needed_carriers(self) -> set[int]:
        """
        Returns:
            The set of carriers IDs that will be needed in the top swatch program.
        """
        found_outhooks = set()
        top_needed_carriers: set[int] = set()
        for instruction in self.top_swatch.knitout_program:
            if isinstance(instruction, Outhook_Instruction):
                found_outhooks.add(instruction.carrier_id)
            elif isinstance(instruction, Inhook_Instruction) and instruction.carrier_id not in found_outhooks:
                top_needed_carriers.add(instruction.carrier_id)
        return top_needed_carriers

    def _set_carriers_for_top_swatch(self, max_float: int = 4, max_reverse: int = 2) -> tuple[dict[Yarn_Carrier, set[Needle]], set[Yarn_Carrier]]:
        carriers_to_align: set[Yarn_Carrier] = set(c for c in self._merged_program_machine_state.carrier_system.active_carriers)
        carriers_to_cut: set[Yarn_Carrier] = set()
        carriers_to_reverse: dict[Yarn_Carrier, set[Needle]] = {}
        reverse_found: set[Yarn_Carrier] = set()
        reverse_carrier_is_all_needle: set[Yarn_Carrier] = set()
        for instruction in self.top_swatch.knitout_program:
            if isinstance(instruction, Loop_Making_Instruction):
                for carrier in instruction.carrier_set.get_carriers(self._merged_program_machine_state.carrier_system):
                    if carrier in carriers_to_align:
                        assert carrier.position is not None
                        float_length = abs(instruction.needle.position - carrier.position)
                        if float_length > max_float:  # Long Float will be required to move the carrier in place
                            carriers_to_cut.add(carrier)
                        elif float_length > max_reverse and carrier.direction_to_needle(instruction.needle) != carrier.last_direction:
                            carriers_to_reverse[carrier] = {instruction.needle}
                        carriers_to_align.remove(carrier)
                    elif carrier in carriers_to_reverse and carrier not in reverse_found:
                        if carrier.last_direction == instruction.direction:
                            if instruction.needle.opposite() in carriers_to_reverse[carrier]:
                                reverse_carrier_is_all_needle.add(carrier)
                            carriers_to_reverse[carrier].add(instruction.needle)
                        else:
                            reverse_found.add(carrier)
            if len(carriers_to_align) == 0 and len(reverse_found) == len(carriers_to_reverse):
                break  # all carrier alignment is found
        assert len(carriers_to_align) == 0, f"Carriers to align are not complete: {carriers_to_align}"
        for carrier_to_cut in carriers_to_cut:
            self._consume_instruction(Outhook_Instruction(carrier_to_cut, "Cut to prevent long float after merge"))
        return carriers_to_reverse, reverse_carrier_is_all_needle

    def _reset_knitting_direction_for_top_swatch(self, knit_to_align: bool = True, max_float: int = 4, max_reverse: int = 2) -> None:
        """
        Adds loop-forming instructions on existing loops in order to align the carriers to continue knitting in the direction expected by the top swatch.

        Args:
            knit_to_align (bool, optional): If True, alignment instructions will be knits. Otherwise, alignment instructions will be tucks.
            max_float (int, optional): The maximum allowed distance for a carrier to float from its current position in the bottom swatch to its first position in the top swatch. Defaults to 4.
            max_reverse (int, optional): The maximum allow distances for a float to reverse course after the merge. Defaults to 2.
        """
        carriers_to_reverse, reverse_carrier_is_all_needle = self._set_carriers_for_top_swatch(max_float, max_reverse)
        self._consume_instruction(Rack_Instruction(0, "Re-Zero Rack for Top Swatch"))
        for carrier, reverse_needles in carriers_to_reverse.items():
            assert carrier in self._merged_program_machine_state.carrier_system.active_carriers
            # Set all Needle racking for the carrier reverse course
            if carrier in reverse_carrier_is_all_needle:
                self._consume_instruction(Rack_Instruction.rack_instruction_from_int_specification(0, all_needle_rack=True))
            else:
                self._consume_instruction(Rack_Instruction.rack_instruction_from_int_specification(0, all_needle_rack=False))
            reverse_dir = carrier.last_direction.opposite()
            reverse_needles = reverse_dir.sort_needles(reverse_needles)
            if knit_to_align:
                instructions = [Knit_Instruction(n, reverse_dir, Yarn_Carrier_Set(carrier), comment="Align Carrier for Merge") for n in reverse_needles]
            else:
                instructions = [Tuck_Instruction(n, reverse_dir, Yarn_Carrier_Set(carrier), comment="Align Carrier for Merge") for n in reverse_needles]
            cp = Carriage_Pass(instructions[0], rack=0, all_needle_rack=carrier in reverse_carrier_is_all_needle)
            for instruction in instructions[1:]:
                cp.add_instruction(instruction, rack=0, all_needle_rack=carrier in reverse_carrier_is_all_needle)
            for instruction in cp:
                self._consume_instruction(instruction)
        self._consume_instruction(Rack_Instruction(0, "Re-Zero Rack for Top Swatch"))

    def _consume_top_swatch(self) -> None:
        """
        Consume instructions from the top swatch and extend the merged swatch program and update the merged swatch machine state.
        As instructions are added, releasehook instructions are introduced at opportune moments aligned with the inhook operations for new carriers.
        """
        self._current_merge_side = Wale_Side.Top
        for instruction in self.top_swatch.knitout_program:
            self._consume_instruction(instruction, Wale_Side.Top, remove_connections=False)

    def _stratified_connections(self, maximum_stacked_connections: int = 2) -> tuple[dict[int, list[Xfer_Instruction]], list[Xfer_Instruction], set[Needle]]:
        """
        This method uses a greedy approach to develop a transfer plan for aligning as many exit operations with entrance operations as possible
        while maintaining a relatively balanced set of decreases.

        Args:
            maximum_stacked_connections (int, optional): The maximum number of loops allowed to be stitched into an entrance wale. Defaults to 2.

        Returns:
            tuple[dict[int, list[Xfer_Instruction]], list[Xfer_Instruction], dict[Needle, Wale_Boundary_Instruction], dict[Needle, Wale_Boundary_Instruction]]:
                A tuple containing:
                * Dictionary of racking values mapped to the list of transfer instructions to execute at that racking in order to align exit instructions.
                * List of transfer instructions need to align exit instructions with the slider bed for same side alignments.
                * Set of needles that still hold loops to be bound off.
        """
        boundaries_with_no_alignment = self.seam_search_space.clean_connections()
        exits_with_no_alignment = set(b for b in boundaries_with_no_alignment if b.is_exit)
        exits_need_bo: set[Needle] = set(e.needle for e in exits_with_no_alignment)
        decrease_bias: int = 0  # Amount of accumulated leftward and rightward lean by adding decreases

        def _establish_connection(c: Wale_Seam_Connection) -> None:
            """
            Establish the given connection as part of the transfer planning solution.
            Args:
                c (Wale_Seam_Connection): The connection to establish.
            """
            nonlocal decrease_bias
            self.seam_search_space.remove_boundary(c.exit_instruction.instruction)
            c.entrance_instruction.add_connection()
            if connection.entrance_instruction.connections_made >= maximum_stacked_connections:
                self.seam_search_space.remove_boundary(connection.entrance_instruction.instruction)
            decrease_bias += connection.required_rack()

        # Find and align all exits that can go directly into an entrance or require only a direct xfer. Remove exits with no possible connections from search space to increase efficiency
        aligned_xfers: list[Xfer_Instruction] = []
        sorted_exits = sorted(self.seam_search_space.exit_instructions)  # hold current state because exit_instruction will update from within the loop
        for exit_instruction in sorted_exits:
            connections = cast(list[Wale_Seam_Connection], Seam_Connection.sort_connections(self.seam_search_space.available_connections(exit_instruction)))
            assert len(connections) > 0
            for connection in connections:
                minimum_instructions = connection.minimum_instructions_to_connect_to_entrance()
                assert isinstance(minimum_instructions, list)
                if len(minimum_instructions) == 0:  # Already aligned, definitely want this one
                    _establish_connection(connection)
                    break  # Skip the remaining connections with this exit
                elif len(minimum_instructions) == 1:  # Just requires a direct transfer to form an alignment. Since there wasn't an already aligned option, take this.
                    _establish_connection(connection)
                    alignment_xfer = minimum_instructions.pop()
                    assert isinstance(alignment_xfer, Xfer_Instruction)
                    aligned_xfers.append(alignment_xfer)
                    break

        assert decrease_bias == 0, "Expected no bias to accumulate from established connections without racking"
        alignment_transfers_by_racking: dict[int, list[Xfer_Instruction]] = defaultdict(list)
        alignment_transfers_by_racking[0] = aligned_xfers
        # Greedily attach remainder to other rackings
        slider_transfers: list[Xfer_Instruction] = []
        unassigned_entrances = sorted(e for e in self.seam_search_space.entrance_instructions if e.connections_made == 0)  # hold current state because it will be modified within the loop
        for entrance_instruction in unassigned_entrances:
            available_connections = cast(set[Wale_Seam_Connection], self.seam_search_space.available_connections(entrance_instruction))
            if len(available_connections) == 0:  # Prior connections formed in this loop may have made this entrance impossible to connect
                continue
            connection = min(available_connections, key=lambda c: abs(decrease_bias + c.required_rack()))  # Connection that adds the least decrease bias to the current bias.
            _establish_connection(connection)
            alignment_instructions = connection.minimum_instructions_to_connect_to_entrance()
            assert isinstance(alignment_instructions, list)
            if len(alignment_instructions) == 3:  # slider transfer
                slider_xfer = alignment_instructions.pop(0)
                assert isinstance(slider_xfer, Xfer_Instruction)
                slider_transfers.append(slider_xfer)
            assert len(alignment_instructions) == 2
            racking = connection.required_rack()
            transfer = alignment_instructions[-1]
            assert isinstance(transfer, Xfer_Instruction)
            alignment_transfers_by_racking[racking].append(transfer)

        sorted_exits = sorted(self.seam_search_space.exit_instructions)  # hold current state because exit_instruction will update from within the loop
        for exit_instruction in sorted_exits:
            available_connections = cast(set[Wale_Seam_Connection], self.seam_search_space.available_connections(exit_instruction))
            if len(available_connections) == 0:  # Prior connections formed in this loop may have made this exit impossible to connect
                continue
            connection = min(available_connections, key=lambda c: abs(decrease_bias + c.required_rack()))  # Connection that adds the least decrease bias to the current bias
            _establish_connection(connection)
            alignment_instructions = connection.minimum_instructions_to_connect_to_entrance()
            assert isinstance(alignment_instructions, list)
            if len(alignment_instructions) == 3:  # slider transfer
                slider_xfer = alignment_instructions.pop(0)
                assert isinstance(slider_xfer, Xfer_Instruction)
                slider_transfers.append(slider_xfer)
            assert len(alignment_instructions) == 2
            racking = connection.required_rack()
            transfer = alignment_instructions[-1]
            assert isinstance(transfer, Xfer_Instruction)
            alignment_transfers_by_racking[racking].append(transfer)

        exits_need_bo.update(e.needle for e in self.seam_search_space.exit_instructions)
        return alignment_transfers_by_racking, slider_transfers, exits_need_bo

    def _align_by_transfers(self, alignment_transfers_by_racking: dict[int, list[Xfer_Instruction]], slider_transfers: list[Xfer_Instruction]) -> None:
        """
        Update the merged swatch program and machine state with the specified alignments between boundary instructions.
        Align the wales from the bottom swatch to wales in the top swatch using the given instructions.
        After execution of the alignment, the racking of the machine state is returned to 0.

        Args:
            alignment_transfers_by_racking (dict[int, list[Xfer_Instruction]]): Dictionary mapping racking values to the transfer instructions to execute at the racking.
            slider_transfers (list[Xfer_Instruction]): List of transfer instructions at racking 0 to align loops with the opposite bed before alignment.
        """
        alignment_transfers_by_racking = {r: xfers for r, xfers in alignment_transfers_by_racking.items() if len(xfers) > 0}
        if len(alignment_transfers_by_racking) == 0:
            assert len(slider_transfers) == 0
            return
        self._consume_instruction(Rack_Instruction(0, f"Start alignment at racking 0"))
        if len(slider_transfers) > 0:  # Create a carriage pass of slider transfers
            first_slider_xfer = slider_transfers.pop(0)
            slider_transfer_pass = Carriage_Pass(first_slider_xfer, rack=0, all_needle_rack=False)
            for slider_xfer in slider_transfers:
                added_to_cp = slider_transfer_pass.add_instruction(slider_xfer, rack=0, all_needle_rack=False)
                assert added_to_cp, f"Couldn't add {slider_xfer} to Slider Transfer Pass"
            for slider_xfer in slider_transfer_pass:
                self._consume_instruction(slider_xfer)
        for rack_value, alignment_xfers_at_rack in alignment_transfers_by_racking.items():
            self._consume_instruction(Rack_Instruction(rack_value, comment="Racking to align exit-entrances."))
            first_xfer = alignment_xfers_at_rack.pop(0)
            alignment_transfer_pass = Carriage_Pass(first_xfer, rack=rack_value, all_needle_rack=False)
            for xfer in alignment_xfers_at_rack:
                added_to_cp = alignment_transfer_pass.add_instruction(xfer, rack=rack_value, all_needle_rack=False)
                assert added_to_cp, f"Couldn't add {added_to_cp} to Alignment Transfer Pass with rack {rack_value}."
            for xfer in alignment_transfer_pass:
                self._consume_instruction(xfer)
        self._consume_instruction(Rack_Instruction(0, comment="Return alignment racking to 0."))

    def _repair_unaligned_boundaries(self, unconnected_exits: set[Needle]) -> None:
        """
        Drop the loops that could not be connected to entrance instructions before knitting the top swatch.

        Args:
            unconnected_exits (set[Needle]): The exits containing loops from unconnected exits instructions.
        """
        if len(unconnected_exits) > 0:
            drops = Carriage_Pass_Direction.Rightward.sort_needles(unconnected_exits)
            drop_pass = Carriage_Pass(Drop_Instruction(drops[0]), rack=0, all_needle_rack=False)
            for drop in drops[1:]:
                drop_pass.add_instruction(Drop_Instruction(drop), rack=0, all_needle_rack=False)
            for drop in drop_pass:
                self._consume_instruction(drop)

    def merge_swatches(self) -> None:
        """
        Merges the swatches.
        The resulting program is written to self.merged_instructions and the machine state of the merge program is updated as the merge is completed.
        """
        self._consume_bottom_swatch()
        self._consume_instruction(Pre_Merge_Comment())
        alignment_transfers_by_racking, slider_transfers, exit_needles_need_bo = self._stratified_connections(maximum_stacked_connections=2)
        self._repair_unaligned_boundaries(exit_needles_need_bo)
        self._align_by_transfers(alignment_transfers_by_racking, slider_transfers)
        self._reset_knitting_direction_for_top_swatch()
        self._consume_instruction(Post_Merge_Comment())
        self._consume_top_swatch()
