"""Module containing the Wale_Wise_Connection class."""
from __future__ import annotations

from intervaltree import Interval

from quilt_knit.swatch.Swatch import Swatch
from quilt_knit.swatch.Swatch_Connection import Swatch_Connection


class Wale_Wise_Connection(Swatch_Connection):
    """
        A Class for tracking the needle ranges between two swatches to be merged wale-wise (bottom to top).
    """

    def __init__(self, bottom_swatch: Swatch, top_swatch: Swatch,
                 bottom_leftmost_needle_position: int = 0, bottom_rightmost_needle_position: int | None = None,
                 top_leftmost_needle_position: int = 0, top_rightmost_needle_position: int | None = None,
                 remove_cast_ons: bool = True):
        """
        Args:
            bottom_swatch (Swatch): The bottom swatch in the connection.
            top_swatch (Swatch): The top swatch in the connection.
            bottom_leftmost_needle_position (int, optional): The leftmost needle position to merge from the bottom swatch. Defaults to 0.
            bottom_rightmost_needle_position (int, optional): The rightmost needle position to merge from the bottom swatch. Defaults to the width of the bottom swatch.
            top_leftmost_needle_position (int, optional): The leftmost needle position to merge into the top swatch. Defaults to 0.
            top_rightmost_needle_position (int, optional): The rightmost needle position to merge into the top swatch. Defaults to the width of the top swatch.
            remove_cast_ons (bool, optional): Whether to remove cast-on operations from the top swatch before merging. Defaults to True.
        """
        if bottom_rightmost_needle_position is None:
            bottom_rightmost_needle_position = bottom_swatch.width - 1
        if top_rightmost_needle_position is None:
            top_rightmost_needle_position = top_swatch.width - 1
        bottom_leftmost_needle_position = max(bottom_swatch.min_needle, bottom_leftmost_needle_position)  # regulate left side of the connection
        top_leftmost_needle_position = max(top_swatch.min_needle, top_leftmost_needle_position)
        bottom_rightmost_needle_position = min(bottom_rightmost_needle_position, bottom_swatch.max_needle)  # regulate right side of the connection
        top_rightmost_needle_position = min(top_rightmost_needle_position, top_swatch.max_needle)
        if remove_cast_ons:
            top_swatch.remove_cast_on_boundary()
        super().__init__(bottom_swatch, top_swatch,
                         bottom_leftmost_needle_position, bottom_rightmost_needle_position,
                         top_leftmost_needle_position, top_rightmost_needle_position,
                         connection_symbol="^")

    @property
    def top_swatch(self) -> Swatch:
        """
        Returns:
            Swatch: The top swatch merged into by this connection.
        """
        return self.to_swatch

    @property
    def bottom_swatch(self) -> Swatch:
        """
        Returns:
            Swatch: The bottom swatch merged from by this connection.
        """
        return self.from_swatch

    @property
    def bottom_interval(self) -> Interval:
        """
        Returns:
            Interval: The interval of needle slots to merge from the bottom swatch.
        """
        return self.from_interval

    @property
    def top_interval(self) -> Interval:
        """
        Returns:
            Interval: The interval of needle slots to merge to the top swatch.
        """
        return self.to_interval

    @property
    def bottom_left_needle_position(self) -> int:
        """
        Returns:
            int: The bottom left needle slot to merge from.
        """
        return self.from_begin

    @property
    def bottom_right_needle_position(self) -> int:
        """
        Returns:
            int: The bottom right needle slot to merge from.
        """
        return self.from_end

    @property
    def top_left_needle_position(self) -> int:
        """
        Returns:
            int: The top left needle slot to merge to.
        """
        return self.to_begin

    @property
    def top_right_needle_position(self) -> int:
        """
        Returns:
            int: The top right needle slot to merge to.
        """
        return self.to_end
