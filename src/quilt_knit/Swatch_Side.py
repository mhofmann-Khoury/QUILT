"""Super Class for enumeration defining the side of swatch being merged."""


class Swatch_Side:
    """Super Class for specifying the boundaries of swatches"""

    def __init__(self, *args: tuple) -> None:
        assert len(args) > 0
        self._side = args[0]

    def __hash__(self) -> int:
        """
        Returns:
            int: The hash value of the name of this Swatch Side
        """
        return hash(self._side)
