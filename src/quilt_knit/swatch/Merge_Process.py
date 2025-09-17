"""Module containing the Merge_Process class"""
import warnings
from typing import cast

from knitout_interpreter.knitout_execution import Knitout_Executer
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
    Knitout_Version_Line,
)
from knitout_interpreter.knitout_operations.needle_instructions import (
    Loop_Making_Instruction,
    Miss_Instruction,
    Needle_Instruction,
    Tuck_Instruction,
)
from knitout_interpreter.knitout_operations.Rack_Instruction import Rack_Instruction
from knitout_to_dat_python.knitout_to_dat import knitout_to_dat
from virtual_knitting_machine.Knitting_Machine import Knitting_Machine
from virtual_knitting_machine.knitting_machine_exceptions.Knitting_Machine_Exception import (
    Knitting_Machine_Exception,
)
from virtual_knitting_machine.knitting_machine_warnings.carrier_operation_warnings import (
    Mismatched_Releasehook_Warning,
)
from virtual_knitting_machine.knitting_machine_warnings.Needle_Warnings import (
    Knit_on_Empty_Needle_Warning,
)
from virtual_knitting_machine.knitting_machine_warnings.Yarn_Carrier_System_Warning import (
    In_Active_Carrier_Warning,
    Out_Inactive_Carrier_Warning,
)
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

from quilt_knit.swatch.course_boundary_instructions import Course_Side
from quilt_knit.swatch.Seam_Search_Space import Seam_Search_Space
from quilt_knit.swatch.Swatch import Swatch
from quilt_knit.swatch.Swatch_Connection import Swatch_Connection
from quilt_knit.swatch.Swatch_Side import Swatch_Side
from quilt_knit.swatch.wale_boundary_instructions import Wale_Side


class Failed_Merge_Release_Exception(Knitting_Machine_Exception):
    """ Exception raised when a release required by the merge program cannot be executed."""

    def __init__(self, release: Releasehook_Instruction):
        super().__init__(f"Cannot execute required release {release} from current merge state.")


class Merge_Process:
    """Super class for swatch merging processes that tracks the merged machine state.

    Attributes:
        merged_instructions (list[Knitout_Line]): The ordered list of knitout instructions that result from the merge.
    """

    def __init__(self, swatch_connection: Swatch_Connection, starting_swatch_side: Swatch_Side, seam_search_space: Seam_Search_Space) -> None:
        self._swatch_connection: Swatch_Connection = swatch_connection
        self._merged_program_machine_state: Knitting_Machine = Knitting_Machine()
        self._seam_search_space: Seam_Search_Space = seam_search_space
        self.merged_instructions: list[Knitout_Line] = [i for i in get_machine_header(self._merged_program_machine_state)]
        if isinstance(starting_swatch_side, Course_Side):
            self._source_machine_states: dict[Swatch_Side, Knitting_Machine] = {Course_Side.Left: Knitting_Machine(), Course_Side.Right: Knitting_Machine()}
        else:
            self._source_machine_states: dict[Swatch_Side, Knitting_Machine] = {Wale_Side.Top: Knitting_Machine(), Wale_Side.Bottom: Knitting_Machine()}
        self._merged_instructions_to_source: dict[Knitout_Line, tuple[Swatch_Side, Knitout_Line] | None] = {i: None for i in self.merged_instructions}
        self._current_merge_side: Swatch_Side = starting_swatch_side

    @property
    def from_swatch(self) -> Swatch:
        """
        Returns:
            Swatch: The first swatch in the connection.
        """
        return self._swatch_connection.from_swatch

    @property
    def to_swatch(self) -> Swatch:
        """

        Returns:
            Swatch: The second swatch in the connection.
        """
        return self._swatch_connection.to_swatch

    @property
    def current_swatch_rack(self) -> int:
        """
        Returns:
            int: The rack value of the machine state of the current swatch.
        """
        return int(self._source_machine_states[self._current_merge_side].rack)

    @property
    def current_swatch_all_needle_rack(self) -> bool:
        """
        Returns:
            bool: True if the machine state of the current swatch is set to all needle rack. False, otherwise.
        """
        return bool(self._source_machine_states[self._current_merge_side].all_needle_rack)

    @property
    def merged_and_current_racks_match(self) -> bool:
        """
        Returns:
            bool: True if the racking values of the merged program state and the current swatch state match. False, otherwise.
        """
        return bool(self._merged_program_machine_state.rack == self.current_swatch_rack and self._merged_program_machine_state.all_needle_rack == self.current_swatch_all_needle_rack)

    def _rack_to_current_swatch(self, instruction_source: Swatch_Side | None = None) -> None:
        """
        Injects a rack instruction into the merged program to align the merged program racking with the current swatch. If they are already aligned, nothing happens.

        Args:
            instruction_source (Swatch_Side, optional): Specifies the source swatch of the instruction that triggered the need for an aligning merge.
        """
        if not self.merged_and_current_racks_match:
            rack_to_match_current = Rack_Instruction.rack_instruction_from_int_specification(self.current_swatch_rack, self.current_swatch_all_needle_rack,
                                                                                             "Racking introduced to realign between merged courses")
            self._add_instruction_to_merge(rack_to_match_current, instruction_source)

    def instruction_requires_release(self, next_instruction: Knitout_Line) -> bool:
        """
        Args:
            next_instruction (Knitout_Line): The next instruction to test if it requires a releasehook.

        Returns:
            bool: True if the specified next instruction would trigger a releasehook from the current merged program machine state.
        """
        if self._merged_program_machine_state.carrier_system.inserting_hook_available:
            return False
        elif isinstance(next_instruction, Hook_Instruction):
            return True
        elif isinstance(next_instruction, Needle_Instruction) and next_instruction.has_second_needle:
            return True
        return False

    def _release_to_merge_instruction(self, instruction: Knitout_Line, instruction_source: Swatch_Side | None) -> None:
        """
        Inserts a necessary releasehook in order to execute the given instruction in the merged program. If a release is not needed, nothing happens.

        Args:
            instruction (Knitout_Line): The instruction that may trigger a release.
            instruction_source (Swatch_Side): Specifies the source swatch of the given instruction.

        Raises:
            Failed_Merge_Release_Exception: If the release is required, but it is not allowed in the given program state.
        """
        if self.instruction_requires_release(instruction):
            assert isinstance(self._merged_program_machine_state.carrier_system.hooked_carrier, Yarn_Carrier)
            release = Releasehook_Instruction(self._merged_program_machine_state.carrier_system.hooked_carrier, "Required release between merges")
            if self._will_execute_release(release):
                self._add_instruction_to_merge(release, instruction_source)
            elif isinstance(self._merged_program_machine_state.carrier_system.hooked_carrier, Yarn_Carrier) and self._merged_program_machine_state.carrier_system.hooked_carrier.position is None:
                bad_inhook_index = next(-1 - i for i, bad_instruction in enumerate(reversed(self.merged_instructions)) if isinstance(bad_instruction, Inhook_Instruction))
                self.merged_instructions.pop(bad_inhook_index)
                carrier_id = self._merged_program_machine_state.carrier_system.hooked_carrier.carrier_id
                self._merged_program_machine_state.carrier_system.releasehook()
                self._merged_program_machine_state.carrier_system.outhook(carrier_id)
            else:
                raise Failed_Merge_Release_Exception(release)

    def _will_execute_release(self, release_instruction: Releasehook_Instruction) -> bool:
        """

        Args:
            release_instruction (Releasehook_Instruction): The releasehook instruction to test if it can be executed on the merged program machine state.

        Returns:
            bool: True if the release instruction will successfully execute on the current merged program machine state. False, otherwise.
        """
        if self._merged_program_machine_state.carrier_system.inserting_hook_available:
            return False  # No-op, release isn't needed if the inserting is available
        assert isinstance(self._merged_program_machine_state.carrier_system.hooked_carrier, Yarn_Carrier)
        if self._merged_program_machine_state.carrier_system.hooked_carrier.carrier_id != release_instruction.carrier_id:
            return False  # No-op, the currently hooked carrier does not match the given release instruction
        if self._merged_program_machine_state.carrier_system.hooked_carrier.position is None:
            return False  # Inserting Hook holds un-positioned yarn, so the release cannot happen yet.
        return True

    def _cut_and_reinsert_carrier(self, carrier: Yarn_Carrier, instruction_source: Swatch_Side | None = None) -> None:
        """
        Cuts the given yarn carrier and reinserts it to avoid a long float formed in the merge process.

        Args:
            carrier (Yarn_Carrier): The carrier to cut and reinsert.
            instruction_source (Swatch_Side, optional): Specifies the source swatch of the instruction that triggered long float.
        """
        cut_float = Outhook_Instruction(carrier, "Cut for long float in merge")
        self._release_to_merge_instruction(cut_float, instruction_source)
        self._add_instruction_to_merge(cut_float, instruction_source)
        insert_float_yarn = Inhook_Instruction(carrier, 'Bring in for merge alignment')
        self._add_instruction_to_merge(insert_float_yarn, instruction_source)

    def _inhook_missing_carriers(self, instruction: Loop_Making_Instruction, instruction_source: Swatch_Side | None, original_instruction: Loop_Making_Instruction | None) -> None:
        """
        Adds inhook operations for any carrier used in the given instruction that is not currently active on the merged machine.
        Args:
            instruction (Loop_Making_Instruction): The instruction that may require carriers to be activated.
            instruction_source (Swatch_Side, optional): Specifies the source swatch of the instruction that triggered inhooks.
            original_instruction (Loop_Making_Instruction | None): The original instruction from the swatch being merged from. If None, the given instruction does not belong to an original swatch.
        """
        assert isinstance(instruction.carrier_set, Yarn_Carrier_Set)
        missing_carriers = self._merged_program_machine_state.carrier_system[self._merged_program_machine_state.carrier_system.missing_carriers(instruction.carrier_set.carrier_ids)]
        if not isinstance(missing_carriers, list):
            missing_carriers = [missing_carriers]
        rightward_carriers = []
        for missing_carrier in missing_carriers:
            if instruction.direction is Carriage_Pass_Direction.Rightward:
                rightward_carriers.append(missing_carrier)
            insert_float_yarn = Inhook_Instruction(missing_carrier, 'Bring in carrier from merge')
            self._release_to_merge_instruction(insert_float_yarn, instruction_source)
            self._add_instruction_to_merge(insert_float_yarn, instruction_source)
        if len(rightward_carriers) > 0:
            self._tuck_float_leftward(Yarn_Carrier_Set(rightward_carriers), instruction.needle)
        if instruction_source is not None:
            assert original_instruction is not None
            source_machine = self._source_machine_states[instruction_source]
            missing_carriers = source_machine.carrier_system[source_machine.carrier_system.missing_carriers(instruction.carrier_set.carrier_ids)]
            if not isinstance(missing_carriers, list):
                missing_carriers = [missing_carriers]
            if len(missing_carriers) > 0 and not source_machine.carrier_system.inserting_hook_available:
                source_machine.carrier_system.releasehook()
            for missing_carrier in missing_carriers:
                Inhook_Instruction(missing_carrier).execute(source_machine)
            if original_instruction.direction is Carriage_Pass_Direction.Rightward:
                self._tuck_float_leftward(Yarn_Carrier_Set(missing_carriers), original_instruction.needle, source_machine)

    def _tuck_float_leftward(self, carrier_set: Yarn_Carrier_Set, start_needle: Needle, machine: Knitting_Machine | None = None, tuck_spacing: int = 3) -> None:
        """
        Adds tuck instructions in a leftward direction onto existing loops to move cut yarns into place to prevent rightward insertions of yarns.
        Args:
            carrier_set (Yarn_Carrier_Set): The set of carriers to tuck with.
            start_needle (Needle): The needle that the next knit instruction will be executed on. The tucks are added up to this location.
            machine (Knitting_Machine, optional): The machine to add the tucked loops to. Default to the Merged-Program knitting machine.
            tuck_spacing (int, optional): The spacing of between tucks on existing loops. Defaults to 3.
        """
        if machine is None:
            machine = self._merged_program_machine_state
        tuck_needles = Carriage_Pass_Direction.Leftward.sort_needles(machine.all_loops(), machine.rack)
        tuck_needles = [n for n in tuck_needles if n.position >= start_needle.position]
        tuck_needles = tuck_needles[0::tuck_spacing]
        for needle in tuck_needles:
            self._add_instruction_to_merge(Tuck_Instruction(needle, Carriage_Pass_Direction.Leftward, carrier_set, "Leftward Insertion after long float"), instruction_source=None)

    def _instruction_is_no_op_in_merged_program(self, instruction: Knitout_Line) -> bool:
        """
        Args:
            instruction (Knitout_Line): The instruction to test for a no-op.

        Returns:
            bool: True if the given instruction has no effect on merged program. False, otherwise.
        """
        if isinstance(instruction, Inhook_Instruction):  # Inhook an active carrier
            return bool(instruction.carrier in self._merged_program_machine_state.carrier_system.active_carriers)
        elif isinstance(instruction, Releasehook_Instruction):  # release free hook or wrong carrier on that hook
            return not self._will_execute_release(instruction)
        elif isinstance(instruction, Outhook_Instruction):  # cut inactive carrier
            return bool(not self._merged_program_machine_state.carrier_system[instruction.carrier].is_active)
        else:
            return False

    def _add_instruction_to_merge(self, merge_instruction: Knitout_Line, instruction_source: Swatch_Side | None = None, instruction: Knitout_Line | None = None) -> bool:
        """
        Adds the given merge instruction to the merged instruction program and updates the corresponding machine states.

        Args:
            merge_instruction (Knitout_Line): The instruction to add to the merged program.
            instruction_source (Swatch_Side, optional): Specifies the source swatch of the merged instruction. If this isn't provided, this is assumed to be a merge-only instruction.
            instruction (Knitout_Line, optional): The instruction from the original swatch to execute on its corresponding machine state. Defaults to the merged_instruction.

        Returns:
            bool: True if the given merged instruction updates the machine state and is added to the merged program. False otherwise.
        """
        if instruction is None:
            instruction = merge_instruction
        if instruction_source is not None:

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=In_Active_Carrier_Warning)
                warnings.filterwarnings("ignore", category=Out_Inactive_Carrier_Warning)
                warnings.filterwarnings("ignore", category=Mismatched_Releasehook_Warning)
                warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
                source_machine = self._source_machine_states[instruction_source]
                if isinstance(instruction, Hook_Instruction) and not source_machine.carrier_system.inserting_hook_available:
                    source_machine.carrier_system.releasehook()
                if isinstance(instruction, Loop_Making_Instruction) and instruction.direction is Carriage_Pass_Direction.Rightward and source_machine.carrier_system.searching_for_position:
                    source_machine.carrier_system._hook_position = instruction.needle.position + 1  # Position yarn inserting hook at the needle slot to the right of the needle.
                    source_machine.carrier_system.hook_input_direction = Carriage_Pass_Direction.Leftward
                    source_machine.carrier_system._searching_for_position = False
                instruction.execute(source_machine)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=In_Active_Carrier_Warning)
            warnings.filterwarnings("ignore", category=Out_Inactive_Carrier_Warning)
            warnings.filterwarnings("ignore", category=Mismatched_Releasehook_Warning)
            warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
            updates_merge = merge_instruction.execute(self._merged_program_machine_state)
            if not updates_merge:
                return False  # No update to the merged machine state, so this isn't added to the merged program.
        if isinstance(merge_instruction, Rack_Instruction) and isinstance(self.merged_instructions[-1], Rack_Instruction):  # Undo extra rack
            del self._merged_instructions_to_source[self.merged_instructions[-1]]
            self.merged_instructions[-1] = merge_instruction
        else:
            self.merged_instructions.append(merge_instruction)
        if instruction_source is not None:
            source = (instruction_source, instruction)
        else:
            source = None
        self._merged_instructions_to_source[merge_instruction] = source
        return True

    def _needle_instruction_in_merged_swatch(self, needle_instruction: Needle_Instruction, source_swatch_side: Swatch_Side | None) -> Needle_Instruction:
        """
        Args:
            needle_instruction (Needle_Instruction): The needle instruction to copy for the merged program.
            source_swatch_side (Swatch_Side): The source swatch of the given needle instruction.

        Returns:
            Needle_Instruction: The needle instruction adjusted for the position in the merged program.

        """
        return needle_instruction

    def _get_floats_to_instruction(self, merge_instruction: Loop_Making_Instruction) -> dict[Yarn_Carrier: tuple[int, Carriage_Pass_Direction]]:
        """
        Args:
            merge_instruction (Loop_Making_Instruction): The instruction that would be executed in the merged program.

        Returns:
            dict[Yarn_Carrier, tuple[int, Carriage_Pass_Direction]]:
                Dictionary mapping yarn carriers to tuples of the float lengths and directions for the float that would be formed by executing the given instruction. Only non-zero floats are returned.
        """
        if isinstance(merge_instruction, Miss_Instruction):
            return {}  # Miss instructions do not form floats.

        def _float_direction(current_carrier_position: int | None) -> Carriage_Pass_Direction:
            """
            Args:
                current_carrier_position (int | None): The current needle slot position of the carrier.

            Returns:
                Carriage_Pass_Direction:
                    The direction that a float will be formed from the given carrier position to the instruction's position.
                    * If the float is of zero length, this direction is determined by the direction of the instruction.
                    * If the current carrier is not active (position is None), then the direction is determined by the direction of the instruction.

            Notes:
                * A carrier cannot be inserted in a rightward direction, so a None-position carrier followed by a rightward instruction should be excluded as an allowable merge.
            """
            if current_carrier_position is None:
                return merge_instruction.direction
            elif merge_instruction.needle.position < current_carrier_position:
                return Carriage_Pass_Direction.Leftward
            elif merge_instruction.needle.position > current_carrier_position:
                return Carriage_Pass_Direction.Rightward
            else:
                return merge_instruction.direction

        def _float_length(current_carrier_position: int | None) -> int:
            """
            Args:
                current_carrier_position (int | None): The current needle slot position of the carrier.

            Returns:
                int: The length of the float formed between the current carrier position and the given instruction.

            """
            if current_carrier_position is None:  # Carrier is not active
                return 0
            return abs(int(merge_instruction.needle.position) - current_carrier_position)

        def _float(current_carrier_position: int | None) -> tuple[int, Carriage_Pass_Direction]:
            return _float_length(current_carrier_position), _float_direction(current_carrier_position)

        floats = {carrier: _float(carrier.position) for carrier in merge_instruction.carrier_set.get_carriers(self._merged_program_machine_state.carrier_system)}
        return {c: f for c, f in floats.items() if f[0] > 0}

    def _instruction_creates_float(self, instruction: Loop_Making_Instruction, ignore_carriers: set[Yarn_Carrier]) -> dict[Yarn_Carrier, tuple[int, Carriage_Pass_Direction]]:
        """
        Args:
            instruction (Loop_Making_Instruction): An instruction that may form a float.
            ignore_carriers (set[Yarn_Carrier]): The set of carriers to ignore floats from.

        Returns:
            dict[Yarn_Carrier, tuple[int, Carriage_Pass_Direction]:
                A dictionary that maps carriers to a tuple containing the required float length and direction that the float will be formed by the given instruction.
                Only non-zero length floats and floats of carriers that were not ignored are included.
        """
        if len(instruction.carrier_set) == 0:  # No floats formed by the instruction
            return {}
        merge_instruction = self._needle_instruction_in_merged_swatch(instruction, self._current_merge_side)
        assert isinstance(merge_instruction, Loop_Making_Instruction)
        carriers_to_floats = self._get_floats_to_instruction(merge_instruction)
        return {carrier: float_value for carrier, float_value in carriers_to_floats.items() if carrier not in ignore_carriers}

    def _consume_instruction(self, instruction: Knitout_Line, instruction_source: Swatch_Side | None = None, remove_connections: bool = False, max_float: int = 15) -> None:
        """
        Consumes the given instruction in the specified swatch.
        This will update the merged program and merged program machine state and inject any necessary operations to keep the merged program aligned.
        The source swatch's machine state is also updated by the consumption of the instruction.

        Args:
            instruction (Knitout_Line): The instruction to add to the merged program.
            instruction_source (Swatch_Side, optional): Specifies the source swatch for this instruction.
            remove_connections (bool, optional): If True, any connections found in the consumed instruction are removed from the search space. Defaults to False.
            max_float (int, optional): Maximum number yarn-floating distances allowed between operations without introducing a cut and reinsert. Defaults to 15.
        """
        if (isinstance(instruction, Knitout_Header_Line) or isinstance(instruction, Knitout_Version_Line)
                or (isinstance(instruction, Knitout_Comment_Line) and "No-Op:" in str(instruction))):  # Todo: Update knitout interpreter to have subclass of comments for no-ops
            return  # Do not consume header, version lines, or no-op comments
        if self._instruction_is_no_op_in_merged_program(instruction) and instruction_source is not None:  # No op inhook or releasehook in the merged program.
            if (isinstance(instruction, Hook_Instruction) and not isinstance(instruction, Releasehook_Instruction)
                    and not self._source_machine_states[instruction_source].carrier_system.inserting_hook_available):
                self._source_machine_states[instruction_source].carrier_system.releasehook()
            if isinstance(instruction_source, Swatch_Side):
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', category=Knit_on_Empty_Needle_Warning)
                    warnings.filterwarnings('ignore', category=Mismatched_Releasehook_Warning)
                    instruction.execute(self._source_machine_states[instruction_source])  # update carrier in the swatch's machine, but ignore its addition to the merged program
            return
        if remove_connections:
            self._seam_search_space.remove_boundary(instruction)
        try:
            self._release_to_merge_instruction(instruction, instruction_source)  # Add any necessary releases before the instruction is merged in.
        except Failed_Merge_Release_Exception as e:
            if isinstance(instruction, Hook_Instruction):
                return  # Skip invalid hooks
            raise e
        if not isinstance(instruction, Rack_Instruction) and instruction_source is not None:  # Inject a racking instruction to get the merged machine state aligned with the current swatch
            self._rack_to_current_swatch(instruction_source)
        if isinstance(instruction, Needle_Instruction):
            # update instruction to align with needle slots based on origin swatch
            merge_instruction = self._needle_instruction_in_merged_swatch(instruction, instruction_source)
            if isinstance(merge_instruction, Loop_Making_Instruction):  # Long floats may be created by this operation
                for carrier, float_values in self._get_floats_to_instruction(merge_instruction).items():
                    float_len = float_values[0]
                    if float_len >= max_float:
                        self._cut_and_reinsert_carrier(carrier, instruction_source)
                assert isinstance(instruction, Loop_Making_Instruction)
                self._inhook_missing_carriers(merge_instruction, instruction_source, instruction)  # Inject any remaining carriers that will be needed by this instruction.
        else:
            merge_instruction = instruction  # There is no difference between the merged instruction and its source.
        self._add_instruction_to_merge(merge_instruction, instruction_source, instruction)

    def _restart_merge_machine(self) -> None:
        """
        Restarts the merged tracking knitting machine and re-executes the current merged program.
        """
        self._merged_program_machine_state: Knitting_Machine = Knitting_Machine()
        for instruction in self.merged_instructions:
            instruction.execute(self._merged_program_machine_state)

    def _specify_sources_in_merged_instructions(self) -> None:
        """
        Updates the line numbers and comments of the instructions in the merged program. Instructions copied from a swatch will include source information in the comment.
        """
        for line_number, instruction in enumerate(self.merged_instructions):
            source = self._merged_instructions_to_source[instruction]
            if source is not None and instruction.original_line_number is not None:
                if instruction.comment is None:
                    instruction.comment = ""
                instruction.comment += f" from line {instruction.original_line_number} of {source[0]} swatch"
            instruction.original_line_number = line_number

    def get_merged_instructions(self) -> list[Knitout_Line]:
        """
        Updates the merged instructions with comments specifying the origin swatch and updated line numbers for the merged program.

        Returns:
            list[Knitout_Line]: List of instructions in the merged program.
        """
        self._specify_sources_in_merged_instructions()
        merge_execution = Knitout_Executer(self.merged_instructions, Knitting_Machine())
        return cast(list[Knitout_Line], merge_execution.executed_instructions)

    def write_knitout(self, merge_name: str | None = None) -> None:
        """
        Creates a knitout file of the given merge name of the merged instructions from this merger.

        Args:
            merge_name (str, optional): The name of the merged swatch knitout file. Defaults to cwm_<the left_swatch's name>_to_<the right_swatch's name>.
        """
        if merge_name is None:
            merge_name = f"{self.from_swatch.name}_{self.to_swatch.name}"
        with open(f'{merge_name}.k', 'w') as merge_file:
            clean_merged_instructions = [f"{str(instruction).splitlines()[0]}\n" for instruction in self.merged_instructions]
            merge_file.writelines(clean_merged_instructions)

    def compile_to_dat(self, merge_name: str | None = None) -> None:
        """
        Creates a knitout file and compiled DAT file of the given merge name of the merged instructions from this merger.

        Args:
            merge_name (str, optional): The name of the merged swatch knitout file. Defaults to cwm_<the left_swatch's name>_to_<the right_swatch's name>.
        """
        if merge_name is None:
            merge_name = f"{self.from_swatch.name}_{self.to_swatch.name}"
        self.write_knitout(merge_name)
        knitout_to_dat(f"{merge_name}.k", f"{merge_name}.dat")
