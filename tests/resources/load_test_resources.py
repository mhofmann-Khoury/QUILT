"""Module resources for loading resources for tests."""

from importlib import resources


def load_test_resource(test_resource_filename: str) -> str:
    """
    Load data from a resource file in the resources folder of the current module's package.

    Args:
        test_resource_filename (str): Name of the resource file to load (e.g., 'resource.txt', 'config.json')

    Returns:
        str: Content of the resource file

    Raises:
        FileNotFoundError: If the resource file doesn't exist
        ImportError: If the resources package structure is invalid
    """
    # Get the current module's package name using __name__
    current_package = __name__.rsplit('.', 1)[0]  # Remove the module name, keep the package
    sequence_resources_path = resources.files(current_package).joinpath(test_resource_filename)

    if not sequence_resources_path.is_file():
        raise FileNotFoundError(f"Resource file '{test_resource_filename}' not found in {current_package}")
    return str(sequence_resources_path)
