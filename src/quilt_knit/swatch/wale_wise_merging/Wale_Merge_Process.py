"""Module containing the class structure for the Vertical Swatch Merge Process. """
import copy
import warnings
from collections import defaultdict
from typing import cast

from knitout_interpreter.knitout_execution import Knitout_Executer
from knitout_interpreter.knitout_execution_structures.Carriage_Pass import Carriage_Pass
from knitout_interpreter.knitout_operations.carrier_instructions import (
    Hook_Instruction,
    Inhook_Instruction,
    Outhook_Instruction,
    Releasehook_Instruction,
)
from knitout_interpreter.knitout_operations.Header_Line import (
    Knitout_Header_Line,
    get_machine_header,
)
from knitout_interpreter.knitout_operations.Knitout_Line import (
    Knitout_Comment_Line,
    Knitout_Line,
)
from knitout_interpreter.knitout_operations.needle_instructions import (
    Knit_Instruction,
    Loop_Making_Instruction,
    Needle_Instruction,
    Split_Instruction,
    Tuck_Instruction,
    Xfer_Instruction,
)
from knitout_interpreter.knitout_operations.Rack_Instruction import Rack_Instruction
from knitout_to_dat_python.knitout_to_dat import knitout_to_dat
from virtual_knitting_machine.Knitting_Machine import Knitting_Machine
from virtual_knitting_machine.knitting_machine_exceptions.Yarn_Carrier_Error_State import (
    Inserting_Hook_In_Use_Exception,
)
from virtual_knitting_machine.machine_components.carriage_system.Carriage_Pass_Direction import (
    Carriage_Pass_Direction,
)
from virtual_knitting_machine.machine_components.needles.Needle import Needle
from virtual_knitting_machine.machine_components.needles.Slider_Needle import (
    Slider_Needle,
)
from virtual_knitting_machine.machine_components.yarn_management.Yarn_Carrier import (
    Yarn_Carrier,
)
from virtual_knitting_machine.machine_components.yarn_management.Yarn_Carrier_Set import (
    Yarn_Carrier_Set,
)

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


class Wale_Merge_Process:
    """Class to manage the vertical merging of two swatches. """

    def __init__(self, wale_wise_connection: Wale_Wise_Connection,
                 seam_search_space: Wale_Seam_Search_Space | None = None,
                 max_rack: int = 3):
        self.wale_wise_connection: Wale_Wise_Connection = wale_wise_connection
        self.merged_instructions: list[Knitout_Line] = []
        if seam_search_space is None:
            seam_search_space = Wale_Seam_Search_Space(self.bottom_swatch, self.top_swatch, max_rack=max_rack)
        self.seam_search_space: Wale_Seam_Search_Space = seam_search_space
        self.seam_search_space.remove_excluded_boundary(self.wale_wise_connection)
        self._merge_tracking_machine_state: Knitting_Machine = Knitting_Machine()

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

    @property
    def rightmost_needle_positions(self) -> dict[Wale_Side, int]:
        """
        :return: The rightmost needle positions for the top and bottom swatches of the merge
        """
        return self.wale_wise_connection.rightmost_needle_positions

    @property
    def leftmost_needle_positions(self) -> dict[Wale_Side, int]:
        """
        :return: The leftmost needle positions for the top and bottom swatches of the merge.
        """
        return self.wale_wise_connection.leftmost_needle_positions

    @property
    def max_rack(self) -> int:
        """
        :return: The maximum allowed racking to align loops.
        """
        return self.seam_search_space.max_rack

    def _consume_bottom_swatch(self) -> None:
        """
        Add all instructions from the bottom swatch into the new merged program.
        Update the merged tracking machine to the execution point at the end of the swatch.
        Removes all outhook operations from the program that would outhook a needed carrier in the top swatch.
        """
        top_needed_carriers: set[int] = set()
        for wale_entrance in self.top_swatch.wale_entrances:
            if wale_entrance.instruction.has_carrier_set:
                top_needed_carriers.update(wale_entrance.instruction.carrier_set.carrier_ids)
        last_outhook_instruction: dict[int, int] = {}
        for instruction in self.bottom_swatch.knitout_program:
            if isinstance(instruction, Merge_Comment):
                continue  # Skip over comments form prior merges
            if isinstance(instruction, Outhook_Instruction) and instruction.carrier_id in top_needed_carriers:  # record location of an outhook that wale_entrance may remove.
                last_outhook_instruction[instruction.carrier_id] = len(self.merged_instructions)
            elif isinstance(instruction, Inhook_Instruction) and instruction.carrier_id in last_outhook_instruction:  # record the record of the last outhook, because it was reinserted
                del last_outhook_instruction[instruction.carrier_id]
            self.merged_instructions.append(instruction)
            instruction.execute(self._merge_tracking_machine_state)
        if len(last_outhook_instruction) > 0:
            reverse_removal_indices = sorted(last_outhook_instruction.values(), reverse=True)
            for removal_index in reverse_removal_indices:
                del self.merged_instructions[removal_index]
            # restart the merge tracking machine and execute without these outhooks
            self._merge_tracking_machine_state: Knitting_Machine = Knitting_Machine()
            for instruction in self.merged_instructions:
                instruction.execute(self._merge_tracking_machine_state)

    def _reset_knitting_direction_for_top_swatch(self, knit_to_align: bool = True, max_float: int = 4) -> None:
        """
        Adds loop-forming instructions on existing loops in order to align the carriers to continue knitting in the direction expected by the top swatch.

        Args:
            knit_to_align (bool, optional): If True, alignment instructions will be knits. Otherwise, alignment instructions will be tucks.
            max_float (int, optional): The maximum allowed distance for a carrier to float from its current position in the bottom swatch to its first position in the top swatch. Defaults to 4.
        """
        needles_holding_loops = self._merge_tracking_machine_state.all_loops()
        active_carriers: set[Yarn_Carrier] = set(c for c in self._merge_tracking_machine_state.carrier_system.active_carriers)
        carriers_to_cur_direction: dict[Yarn_Carrier, Carriage_Pass_Direction] = {}  # Todo: Update Yarn_insertion_System to track the direction of active carriers
        for instruction in reversed(self.merged_instructions):
            if isinstance(instruction, Hook_Instruction):
                instruction_carrier = instruction.get_carrier(self._merge_tracking_machine_state)
                if instruction_carrier in active_carriers:  # haven't discovered its direction yet.
                    carriers_to_cur_direction[instruction_carrier] = Carriage_Pass_Direction.Leftward  # Hook operation at end means that the next direction will be leftward.
                    # carriers_to_position[instruction_carrier] = None
                    # Outhooks will force a new inhook
                    active_carriers.remove(instruction_carrier)
            elif isinstance(instruction, Loop_Making_Instruction):
                for carrier in instruction.carrier_set.get_carriers(self._merge_tracking_machine_state.carrier_system):
                    if carrier in active_carriers and carrier not in carriers_to_cur_direction:
                        carriers_to_cur_direction[carrier] = instruction.direction
                        # carriers_to_position[carrier] = instruction.needle.position
                        active_carriers.remove(carrier)
            if len(active_carriers) == 0:
                break  # leave for-loop, all directions have been found.
        carriers_to_align: set[Yarn_Carrier] = set(carriers_to_cur_direction.keys())
        for instruction in self.top_swatch.knitout_program:
            if isinstance(instruction, Loop_Making_Instruction):
                for carrier in instruction.carrier_set.get_carriers(self._merge_tracking_machine_state.carrier_system):
                    if carrier in carriers_to_align:
                        if carrier.position is not None and abs(instruction.needle.position - carrier.position) > max_float:  # Float will be required to move the carrier in place
                            if carrier.position < instruction.needle.position:  # current position is to the left of the last instruction
                                next_direction = Carriage_Pass_Direction.Rightward
                                left_pos = carrier.position
                                right_pos = instruction.needle.position
                                if next_direction == carriers_to_cur_direction[carrier]:  # can continue in this direction
                                    left_pos += 1
                            else:  # current position is to the right of the prior position
                                next_direction = Carriage_Pass_Direction.Leftward
                                left_pos = instruction.needle.position
                                right_pos = carrier.position
                                if next_direction == carriers_to_cur_direction[carrier]:
                                    right_pos -= 1
                            aligned_positions = set()
                            for looped_needle in next_direction.sort_needles(needles_holding_loops):
                                if looped_needle.position not in aligned_positions and left_pos <= looped_needle.position <= right_pos:
                                    if knit_to_align:
                                        align_instruction = Knit_Instruction(looped_needle, next_direction, Yarn_Carrier_Set(carrier), "Align carriers for wale-wise merge.")
                                    else:
                                        align_instruction = Tuck_Instruction(looped_needle, next_direction, Yarn_Carrier_Set(carrier), "Align carrier for wale-wise merge.")
                                    self.merged_instructions.append(align_instruction)
                                    aligned_positions.add(looped_needle.position)
                                    align_instruction.execute(self._merge_tracking_machine_state)
                        carriers_to_align.remove(carrier)
            if len(carriers_to_align) == 0:
                break  # all carrier alignment is fixed.
        assert len(carriers_to_align) == 0, f"Carriers to align are not complete: {carriers_to_align}"

    def _consume_top_swatch(self) -> None:
        """
        Consume instructions from the top swatch and extend the merged swatch program and update the merged swatch machine state.
        As instructions are added, releasehook instructions are introduced at opportune moments aligned with the inhook operations for new carriers.
        """
        needed_carriers_by_entrance: set[int] = set()
        for wale_entrance in self.top_swatch.wale_entrances:
            if wale_entrance.instruction.has_carrier_set:
                needed_carriers_by_entrance.update(wale_entrance.instruction.carrier_set.carrier_ids)
        needed_carriers_by_entrance.difference_update(c.carrier_id for c in self._merge_tracking_machine_state.carrier_system.active_carriers)
        carriers_to_release: dict[Carriage_Pass_Direction, list[Releasehook_Instruction]] = defaultdict(list)
        found_entrance = False
        for instruction in self.top_swatch.knitout_program:
            if isinstance(instruction, Merge_Comment):
                continue  # skip over prior merge comments
            if not found_entrance:
                if self.top_swatch.instruction_is_wale_entrance(instruction):
                    found_entrance = True
                elif isinstance(instruction, Inhook_Instruction) and instruction.carrier_id in needed_carriers_by_entrance:
                    needed_carriers_by_entrance.remove(instruction.carrier_id)  # inhook will be added
                    carriers_to_release[self._merge_tracking_machine_state.carriage.last_direction].append(Releasehook_Instruction(instruction.carrier))
                else:  # skip to next instruction.
                    continue
            if len(carriers_to_release) > 0 and isinstance(instruction, Needle_Instruction):  # check for opportunity to release inhooks
                if isinstance(instruction, Xfer_Instruction) or isinstance(instruction, Split_Instruction):  # must release before transfers or splits
                    for releases in carriers_to_release.values():
                        for release in releases:
                            self.merged_instructions.append(release)
                            release.execute(self._merge_tracking_machine_state)
                    carriers_to_release = {}
                elif instruction.direction in carriers_to_release:
                    for release in carriers_to_release[instruction.direction]:
                        self.merged_instructions.append(release)
                        release.execute(self._merge_tracking_machine_state)
                    del carriers_to_release[instruction.direction]
            if isinstance(instruction, Needle_Instruction) and instruction.has_carrier_set:  # Todo, does this every come up?
                assert len(self._merge_tracking_machine_state.carrier_system.missing_carriers(instruction.carrier_set.carrier_ids)) == 0, \
                    f"Adding {str(instruction).strip()} to merged swatch, but carrier set {instruction.carrier_set} is not fully active"
            self.merged_instructions.append(instruction)
            instruction.execute(self._merge_tracking_machine_state)

    def _stratified_connections(self, maximum_stacked_connections: int = 2) -> (
            tuple)[dict[int, list[Xfer_Instruction]], list[Xfer_Instruction], dict[Needle, Wale_Boundary_Instruction], dict[Needle, Wale_Boundary_Instruction]]:
        """
        This method uses a greedy approach to develop a transfer plan for aligning as many exit operations with entrance operations as possible
        while maintaining a relatively balanced set of decreases.

        Args:
            maximum_stacked_connections (int, optional): The maximum number of loops allowed to be stitched into an entrance wale. Defaults to 2.

        Returns:
            tuple[dict[int, list[Xfer_Instruction]], list[Xfer_Instruction], dict[Needle, Wale_Boundary_Instruction], dict[Needle, Wale_Boundary_Instruction]]:
                A tuple containing:
                * Dictionary of racking values mapped to the list of transfer instructions to execute at that racking in order to align exit instructions.
                * List of transfer instructions need to align exit instructions with the slider bed for same side alignments
                * Dictionary of needles that will require an entrance loop mapped to the entrance instruction that expects a loop there.
                * Dictionary of needles that still hold loops to be bound off mapped to the exit instruction that left the loop there.
        """
        boundaries_with_no_alignment = self.seam_search_space.clean_connections()
        exits_with_no_alignment = set(b for b in boundaries_with_no_alignment if b.is_exit)
        exits_need_bo: dict[Needle, Wale_Boundary_Instruction] = {e.needle: e for e in exits_with_no_alignment}
        entrances_with_no_alignment = set(b for b in boundaries_with_no_alignment if b.is_entrance)
        entrances_need_cast_on: dict[Needle, Wale_Boundary_Instruction] = {e.needle: e for e in entrances_with_no_alignment}
        decrease_bias: int = 0  # Amount of accumulated leftward and rightward lean by adding decreases

        def _establish_connection(c: Wale_Seam_Connection) -> None:
            """
            Establish the given connection as part of the transfer planning solution.
            Args:
                c (Wale_Seam_Connection): The connection to establish.
            """
            nonlocal decrease_bias
            self.seam_search_space.remove_boundary(c.exit_instruction)
            c.entrance_instruction.add_connection()
            if connection.entrance_instruction.connections_made >= maximum_stacked_connections:
                self.seam_search_space.remove_boundary(connection.entrance_instruction)
            decrease_bias += connection.required_rack()

        # Find and align all exits that can go directly into an entrance or require only a direct xfer. Remove exits with no possible connections from search space to increase efficiency
        aligned_xfers: list[Xfer_Instruction] = []
        sorted_exits = [*self.seam_search_space.exit_instructions]  # hold current state because exit_instruction will update from within the loop
        for exit_instruction in sorted_exits:
            connections = sorted(self.seam_search_space.available_connections(exit_instruction))
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
        unassigned_entrances = [e for e in self.seam_search_space.entrance_instructions if e.connections_made == 0]  # hold current state because it will be modified within the loop
        for entrance_instruction in unassigned_entrances:
            available_connections = self.seam_search_space.available_connections(entrance_instruction)

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

        sorted_exits = [*self.seam_search_space.exit_instructions]  # hold current state because exit_instruction will update from within the loop
        for exit_instruction in sorted_exits:
            available_connections = self.seam_search_space.available_connections(exit_instruction)
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

        entrances_need_cast_on.update({e.needle: e for e in self.seam_search_space.entrance_instructions})
        exits_need_bo.update({e.needle: e for e in self.seam_search_space.exit_instructions})
        return alignment_transfers_by_racking, slider_transfers, entrances_need_cast_on, exits_need_bo

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
        zero_rack = Rack_Instruction(0, f"Start alignment at racking 0")
        self.merged_instructions.append(zero_rack)
        zero_rack.execute(self._merge_tracking_machine_state)
        if len(slider_transfers) > 0:  # Create a carriage pass of slider transfers
            first_slider_xfer = slider_transfers.pop(0)
            slider_transfer_pass = Carriage_Pass(first_slider_xfer, rack=0, all_needle_rack=False)
            for slider_xfer in slider_transfers:
                added_to_cp = slider_transfer_pass.add_instruction(slider_xfer, rack=0, all_needle_rack=False)
                assert added_to_cp, f"Couldn't add {slider_xfer} to Slider Transfer Pass"
            self.merged_instructions.extend(slider_transfer_pass)
            slider_transfer_pass.execute(self._merge_tracking_machine_state)
        for rack_value, alignment_xfers_at_rack in alignment_transfers_by_racking.items():
            rack_instruction = Rack_Instruction(rack_value, comment="Racking to align exit-entrances.")
            self.merged_instructions.append(rack_instruction)
            rack_instruction.execute(self._merge_tracking_machine_state)
            first_xfer = alignment_xfers_at_rack.pop(0)
            alignment_transfer_pass = Carriage_Pass(first_xfer, rack=rack_value, all_needle_rack=False)
            for xfer in alignment_xfers_at_rack:
                added_to_cp = alignment_transfer_pass.add_instruction(xfer, rack=rack_value, all_needle_rack=False)
                assert added_to_cp, f"Couldn't add {added_to_cp} to Alignment Transfer Pass with rack {rack_value}."
            self.merged_instructions.extend(alignment_transfer_pass)
            alignment_transfer_pass.execute(self._merge_tracking_machine_state)
        rack_instruction = Rack_Instruction(0, comment="Return alignment racking to 0.")
        self.merged_instructions.append(rack_instruction)
        rack_instruction.execute(self._merge_tracking_machine_state)

    def _repair_unaligned_boundaries(self, unconnected_entrances: dict[Needle, Wale_Boundary_Instruction],
                                     unconnected_exits: dict[Needle, Wale_Boundary_Instruction]) -> None:
        """
        Update the merged swatch program and machine state to resolve any remaining unconnected boundary instructions.
        Bind-off the unconnected exits and tuck loops for unconnected entrances.
        If an active carrier is available to complete this, it will be used, otherwise, the extra carrier will be brought in for this task.

        Args:
            unconnected_entrances (dict[Needle, Wale_Boundary_Instruction]: The needles containing loops from unconnected entrance instructions.
            unconnected_exits (dict[Needle, Wale_Boundary_Instruction]: The exits containing loops from unconnected exits instructions.
        """
        if len(unconnected_exits) == 0 and len(unconnected_entrances) == 0:
            return
        looped_needles = Carriage_Pass_Direction.Rightward.sort_needles(self._merge_tracking_machine_state.all_loops())
        cast_on_needles = Carriage_Pass_Direction.Rightward.sort_needles(unconnected_entrances.keys())
        bo_needles = Carriage_Pass_Direction.Rightward.sort_needles(unconnected_exits.keys())
        if len(cast_on_needles) == 0:
            left_most_needle = bo_needles[0]
            right_most_needle = bo_needles[-1]
        elif len(bo_needles) == 0:
            left_most_needle = cast_on_needles[0]
            right_most_needle = cast_on_needles[-1]
        else:
            left_most_needle = min(cast_on_needles[0], bo_needles[0])
            right_most_needle = max(cast_on_needles[-1], bo_needles[-1])
        bo_sections: list[tuple[Needle | None, list[Needle], Needle | None]] = []
        # each section to be bound off is defined by the needle to bind of on the left, the set of needles to bo, and to bind of on the right
        left_needle = None
        current_section: list[Needle] = []
        for needle in looped_needles:
            if needle in unconnected_exits:
                assert needle not in unconnected_entrances
                if len(current_section) == 1 and left_needle is not None and left_needle.position != needle.position - 1:
                    left_needle = None  # left needle is not directly to the left of the new section
                current_section.append(needle)
            else:
                if len(current_section) > 0:  # close up a bo_section
                    if needle.position == current_section[-1].position + 1:  # directly right of section
                        bo_sections.append((left_needle, current_section, needle))
                    else:
                        bo_sections.append((left_needle, current_section, None))
                current_section = []
                left_needle = needle
        no_neighbor_sections_by_right_position: dict[int, list[Needle]] = {}
        no_neighbor_sections_by_left_position: dict[int, list[Needle]] = {}
        left_only_sections: dict[Needle, list[Needle]] = {}
        right_only_sections: dict[Needle, list[Needle]] = {}
        left_flexible_sections: dict[Needle, list[Needle]] = {}
        right_flexible_sections: dict[Needle, list[Needle]] = {}
        for ln, bo_needles, rn in bo_sections:
            if ln is None and rn is None:
                no_neighbor_sections_by_right_position[bo_needles[-1].position + 1] = bo_needles
                no_neighbor_sections_by_left_position[bo_needles[0].position - 1] = bo_needles
            elif ln is None:
                right_only_sections[rn] = bo_needles
            elif rn is None:
                left_only_sections[ln] = bo_needles
            else:
                right_flexible_sections[rn] = bo_needles
                left_flexible_sections[ln] = bo_needles
        relevant_loops = [*cast_on_needles]
        relevant_loops.extend(ln for ln in left_only_sections)
        relevant_loops.extend(ln for ln in left_flexible_sections)
        relevant_loops.extend(rn for rn in right_only_sections)
        relevant_loops.extend(rn for rn in right_flexible_sections)

        def _bind_of_section(section_to_bind: list[Needle], end_needle: Needle, cs: Yarn_Carrier_Set, bo_dir: Carriage_Pass_Direction) -> None:
            section_to_bind = bo_dir.sort_needles(section_to_bind)
            for bo, bo_recipient in zip(section_to_bind[0:-1], section_to_bind[1:]):
                if bo.is_front == bo_recipient.is_front:  # same bed
                    slider_needle = Slider_Needle(not bo.is_front, bo.position)
                    xfer_to_slider = Xfer_Instruction(bo, slider_needle)
                    bo = slider_needle
                    self.merged_instructions.append(xfer_to_slider)
                    xfer_to_slider.execute(self._merge_tracking_machine_state)
                rack_for_bo_transfer = Rack_Instruction(Knitting_Machine.get_transfer_rack(bo, bo_recipient), "prepare to transfer to bind-off")
                self.merged_instructions.append(rack_for_bo_transfer)
                rack_for_bo_transfer.execute(self._merge_tracking_machine_state)
                align_xfer = Xfer_Instruction(bo, bo_recipient, f"Xfer to bind-off")
                self.merged_instructions.append(align_xfer)
                align_xfer.execute(self._merge_tracking_machine_state)
                rack_zero = Rack_Instruction(0)
                self.merged_instructions.append(rack_zero)
                rack_zero.execute(self._merge_tracking_machine_state)
                knit_on_recipient = Knit_Instruction(bo_recipient, bo_dir, cs, "Knit to bind-off")
                self.merged_instructions.append(knit_on_recipient)
                knit_on_recipient.execute(self._merge_tracking_machine_state)
            bo = section_to_bind[-1]
            if bo.is_front == end_needle.is_front:  # same bed
                slider_needle = Slider_Needle(not bo.is_front, bo.position)
                xfer_to_slider = Xfer_Instruction(bo, slider_needle)
                bo = slider_needle
                self.merged_instructions.append(xfer_to_slider)
                xfer_to_slider.execute(self._merge_tracking_machine_state)
            rack_for_bo_transfer = Rack_Instruction(Knitting_Machine.get_transfer_rack(bo, end_needle), "prepare to transfer to bind-off")
            self.merged_instructions.append(rack_for_bo_transfer)
            rack_for_bo_transfer.execute(self._merge_tracking_machine_state)
            align_xfer = Xfer_Instruction(bo, end_needle, f"Xfer to bind-off")
            self.merged_instructions.append(align_xfer)
            align_xfer.execute(self._merge_tracking_machine_state)
            rack_zero = Rack_Instruction(0)
            self.merged_instructions.append(rack_zero)
            rack_zero.execute(self._merge_tracking_machine_state)
            knit_on_recipient = Knit_Instruction(end_needle, bo_dir, cs, "Conclude knitting of bind-off")
            self.merged_instructions.append(knit_on_recipient)
            knit_on_recipient.execute(self._merge_tracking_machine_state)

        active_carriers: list[Yarn_Carrier] = sorted(self._merge_tracking_machine_state.carrier_system.active_carriers, key=lambda c: c.position)  # sorted form left to right positions
        active_carriers_to_position: dict[int, int] = {c.carrier_id: c.position for c in active_carriers}
        right_side_carrier = None
        left_side_carrier = None
        for cid, position in active_carriers_to_position.items():
            if position <= left_most_needle.position:
                left_side_carrier = cid
            if position >= right_most_needle.position:
                right_side_carrier = cid
                break  # found left and right side by now.

        handled_entrances = set()
        handled_exits = set()
        remaining_relevant_loops = []
        if left_side_carrier is not None:  # carrier can be moved in rightward pass to create loops and bind off
            rightward_pass_carrier_set = Yarn_Carrier_Set([left_side_carrier])
            for needle in Carriage_Pass_Direction.Rightward.sort_needles(relevant_loops):
                if needle in right_only_sections:
                    bo_section = right_only_sections[needle]
                    _bind_of_section(bo_section, needle, rightward_pass_carrier_set, Carriage_Pass_Direction.Rightward)
                    handled_exits.update(bo_section)
                elif needle in right_flexible_sections:
                    bo_section = right_flexible_sections[needle]
                    _bind_of_section(bo_section, needle, rightward_pass_carrier_set, Carriage_Pass_Direction.Rightward)
                elif needle in unconnected_entrances:
                    if needle.position in no_neighbor_sections_by_right_position:  # bind-of could result in the needed loop
                        bo_section = no_neighbor_sections_by_right_position[needle.position]
                        _bind_of_section(bo_section, needle, rightward_pass_carrier_set, Carriage_Pass_Direction.Rightward)
                    else:
                        tuck_instruction = Tuck_Instruction(needle, Carriage_Pass_Direction.Rightward, rightward_pass_carrier_set, "Added entrance loop")
                        handled_entrances.add(needle)
                        self.merged_instructions.append(tuck_instruction)
                        tuck_instruction.execute(self._merge_tracking_machine_state)
                else:
                    remaining_relevant_loops.append(needle)
            relevant_loops = remaining_relevant_loops
            new_carrier_position = self._merge_tracking_machine_state.carrier_system[left_side_carrier].position
            if right_most_needle.position <= new_carrier_position:
                if right_side_carrier is None or new_carrier_position <= active_carriers_to_position[right_side_carrier]:  # same position or closer than the right_side carrier
                    right_side_carrier = left_side_carrier
        if right_side_carrier is not None:  # create a leftward pass to handle the remaining loops.
            leftward_carrier_pass_set = Yarn_Carrier_Set([right_side_carrier])
            for needle in Carriage_Pass_Direction.Leftward.sort_needles(relevant_loops):
                if needle in right_only_sections:
                    bo_section = right_only_sections[needle]
                    _bind_of_section(bo_section, needle, leftward_carrier_pass_set, Carriage_Pass_Direction.Leftward)
                    handled_exits.update(bo_section)
                elif needle in right_flexible_sections:
                    bo_section = right_flexible_sections[needle]
                    _bind_of_section(bo_section, needle, leftward_carrier_pass_set, Carriage_Pass_Direction.Leftward)
                elif needle in unconnected_entrances:
                    if needle.position in no_neighbor_sections_by_left_position:  # bind-of could result in the needed loop
                        bo_section = no_neighbor_sections_by_left_position[needle.position]
                        _bind_of_section(bo_section, needle, leftward_carrier_pass_set, Carriage_Pass_Direction.Leftward)
                    else:
                        tuck_instruction = Tuck_Instruction(needle, Carriage_Pass_Direction.Leftward, leftward_carrier_pass_set, "Added entrance loop")
                        handled_entrances.add(needle)
                        self.merged_instructions.append(tuck_instruction)
                        tuck_instruction.execute(self._merge_tracking_machine_state)
                else:
                    remaining_relevant_loops.append(needle)
                relevant_loops = remaining_relevant_loops
        if len(relevant_loops) > 0:
            warnings.warn(f"Loops remain to bind of exits and add entrances: {relevant_loops}")
            # Todo: Add bind off with extra carrier

    def merge_swatches(self) -> None:
        """
        Merges the swatches.
        The resulting program is written to self.merged_instructions and the machine state of the merge program is updated as the merge is completed.
        """
        self._consume_bottom_swatch()
        self.merged_instructions.append(Pre_Merge_Comment())
        self.top_swatch.shift_swatch_rightward_on_needle_bed()
        alignment_transfers_by_racking, slider_transfers, entrance_needles_need_cast_on, exit_needles_need_bo = self._stratified_connections(maximum_stacked_connections=2)
        self._repair_unaligned_boundaries(entrance_needles_need_cast_on, exit_needles_need_bo)
        self._align_by_transfers(alignment_transfers_by_racking, slider_transfers)
        self._reset_knitting_direction_for_top_swatch()
        self.merged_instructions.append(Post_Merge_Comment())
        self._consume_top_swatch()

    def get_merged_instructions(self) -> list[Knitout_Line]:
        """
        Updates the merged instructions with comments specifying the origin swatch and updated line numbers for the merged program.

        Returns:
            list[Knitout_Line]: List of instructions in the merged program.
        """
        updated_merged_instructions = []
        in_bottom_swatch = True
        in_merge = False
        for instruction in self.merged_instructions:
            copy_instruction = copy.copy(instruction)
            if isinstance(instruction, Pre_Merge_Comment):
                assert in_bottom_swatch
                in_bottom_swatch = False
                in_merge = True
            elif isinstance(instruction, Post_Merge_Comment):
                assert in_merge
                in_merge = False
            elif not isinstance(instruction, Knitout_Header_Line):
                if copy_instruction.comment is None:
                    copy_instruction.comment = ""
                if in_bottom_swatch:
                    copy_instruction.comment += f" from bottom swatch <{self.bottom_swatch.name}> line {instruction.original_line_number}"
                elif in_merge:
                    copy_instruction.comment += f" from swatch alignment"
                else:  # assume to be in top swatch
                    copy_instruction.comment += f" from top swatch <{self.top_swatch.name}> line {instruction.original_line_number}"
            updated_merged_instructions.append(copy_instruction)

        merged_re_organized_instructions: list[Knitout_Line] = []
        for instruction in updated_merged_instructions:
            copy_instruction = copy.copy(instruction)
            copy_instruction.original_line_number = len(merged_re_organized_instructions)
            merged_re_organized_instructions.append(copy_instruction)

        merge_execution = Knitout_Executer(merged_re_organized_instructions, Knitting_Machine(), accepted_error_types=[Inserting_Hook_In_Use_Exception])
        merged_executed_instruction = get_machine_header(merge_execution.knitting_machine)
        merged_executed_instruction.extend(merge_execution.executed_instructions)
        return cast(list[Knitout_Line], merged_executed_instruction)

    def write_knitout(self, merge_name: str | None = None) -> None:
        """
        Creates a knitout file of the given merge name of the merged instructions from this merger.

        Args:
            merge_name (str, optional): The name of the merged swatch knitout file. Defaults to cwm_<the bottom_swatch's name>_to_<the top_swatch's name>
        """
        if merge_name is None:
            merge_name = f"wm_{self.bottom_swatch.name}_to_{self.top_swatch.name}"
        with open(f'{merge_name}.k', 'w') as merge_file:
            clean_merged_instructions = [f"{str(i).splitlines()[0]}\n" for i in self.get_merged_instructions()]
            merge_file.writelines(clean_merged_instructions)

    def compile_to_dat(self, merge_name: str | None = None) -> None:
        """
        Creates a knitout file and compiled DAT file of the given merge name of the merged instructions from this merger.

        Args:
            merge_name (str, optional): The name of the merged swatch knitout file. Defaults to cwm_<the bottom_swatch's name>_to_<the top_swatch's name>.
        """
        if merge_name is None:
            merge_name = f"wm_{self.bottom_swatch.name}_to_{self.top_swatch.name}"
        self.write_knitout(merge_name)
        knitout_to_dat(f"{merge_name}.k", f"{merge_name}.dat", knitout_in_file=True)
