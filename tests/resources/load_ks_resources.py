"""Module provides helper functions to convert Knit Script resources into knitout and dat files for testing."""
from knit_script.knit_script_interpreter.Knit_Script_Interpreter import (
    Knit_Script_Interpreter,
)
from knitout_interpreter.knitout_execution import Knitout_Executer
from knitout_interpreter.knitout_operations.Knitout_Line import Knitout_Comment_Line
from knitout_to_dat_python.knitout_to_dat import knitout_to_dat

from tests.resources.load_test_resources import load_test_resource


def _clean_knitout(executer: Knitout_Executer):
    clean_instructions = []
    for instruction in executer.executed_instructions:
        instruction.comment = None
        if not isinstance(instruction, Knitout_Comment_Line):
            clean_instructions.append(instruction)
    executer.executed_instructions = clean_instructions


def load_test_knitscript_to_knitout(test_knitscript_filename: str, test_knitout_filename: str, **python_variables) -> str:
    """
    Generates a knitout file in the current directory that corresponds to the parameterized run of the given knitscript file.
    Args:
        test_knitscript_filename: The name of the knitscript to run from the test/resources package.
        test_knitout_filename: The name of the knitout file to generate.
        **python_variables: The keyword parameters to pass to the knitscript run.

    Returns: The name of the cleaned knitout file (removing comments and semicolons).
    """
    test_knitscript_filename = load_test_resource(test_knitscript_filename)
    interpreter = Knit_Script_Interpreter()
    knitout, knit_graph, machine_state = interpreter.write_knitout(test_knitscript_filename, test_knitout_filename, pattern_is_file=True, **python_variables)
    knitout_executer = Knitout_Executer(knitout)
    clean_k_name = f"{test_knitout_filename[0:-2]}_clean.k"
    _clean_knitout(knitout_executer)
    knitout_executer.write_executed_instructions(clean_k_name)
    return clean_k_name


def load_test_knitscript_to_knitout_to_dat(test_knitscript_filename: str, test_knitout_filename: str, test_dat_name: str, **python_variables) -> str:
    """
    Generates a knitout file and dat file from the original JS Dat compiler in the current directory that corresponds to the parameterized run of the given knitscript file.
    Args:
        test_dat_name: The name of the dat file to generate with the old js dat compiler.
        test_knitscript_filename: The name of the knitscript to run from the test/resources package.
        test_knitout_filename: The name of the knitout file to generate.
        **python_variables: The keyword parameters to pass to the knitscript run.

    Returns:
        The name of the cleaned knitscript generated knitout file.
    """
    clean_k_name = load_test_knitscript_to_knitout(test_knitscript_filename, test_knitout_filename, **python_variables)
    knitout_to_dat(test_knitout_filename, test_dat_name)
    return clean_k_name
