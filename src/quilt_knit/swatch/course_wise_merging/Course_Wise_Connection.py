"""Module containing the Course Wise Connection class."""
from __future__ import annotations

from intervaltree import Interval
from virtual_knitting_machine.machine_components.carriage_system.Carriage_Pass_Direction import (
    Carriage_Pass_Direction,
)

from quilt_knit.swatch.course_boundary_instructions import Course_Side
from quilt_knit.swatch.Swatch import Swatch
from quilt_knit.swatch.Swatch_Connection import Swatch_Connection


class Course_Wise_Connection(Swatch_Connection):
    """
        Class representing the course-wise alignment of two swatches in a quilt.
    """

    def __init__(self, left_swatch: Swatch, right_swatch: Swatch,
                 first_carriage_pass_on_left: int = 0, last_carriage_pass_on_left: int | None = None,
                 first_carriage_pass_on_right: int = 0, last_carriage_pass_on_right: int | None = None):
        """
        Args:
            left_swatch (Swatch): The left swatch in the connection.
            right_swatch (Swatch): The right swatch in the connection.
            first_carriage_pass_on_left (int, optional): The first carriage pass to merge from on the left side. Defaults to 0.
            last_carriage_pass_on_left (int, optional): The last carriage pass to merge from on the left side. Defaults to the height of the left swatch.
            first_carriage_pass_on_right (int, optional): The first carriage pass to merge from on the right side. Defaults to 0.
            last_carriage_pass_on_right (int, optional): The last carriage pass to merge from on the right side. Defaults to the height of the right swatch.
        """
        if last_carriage_pass_on_left is None:
            last_carriage_pass_on_left = left_swatch.height
        if last_carriage_pass_on_right is None:
            last_carriage_pass_on_right = right_swatch.height
        first_carriage_pass_on_left = max(0, first_carriage_pass_on_left)  # regulate first carriage passes to be non-negative
        first_carriage_pass_on_right = max(0, first_carriage_pass_on_right)
        last_carriage_pass_on_left = min(last_carriage_pass_on_left, left_swatch.height)  # regulate last carriage passes to top out at the height of the swatch
        last_carriage_pass_on_right = min(last_carriage_pass_on_right, right_swatch.height)
        super().__init__(left_swatch, right_swatch, first_carriage_pass_on_left, last_carriage_pass_on_left, first_carriage_pass_on_right, last_carriage_pass_on_right)
        self.last_courses_by_side: dict[Course_Side, int] = {Course_Side.Left: last_carriage_pass_on_left, Course_Side.Right: last_carriage_pass_on_right}
        self.first_course_by_side: dict[Course_Side, int] = {Course_Side.Left: first_carriage_pass_on_left, Course_Side.Right: first_carriage_pass_on_right}

    @staticmethod
    def connection_by_dict(left_swatch: Swatch, right_swatch: Swatch,
                           first_courses_by_side: dict[Course_Side, int] | None = None,
                           last_courses_by_side: dict[Course_Side, int] | None = None) -> Course_Wise_Connection:
        """
        Args:
            left_swatch (Swatch): The left swatch in the connection.
            right_swatch (Swatch): The right swatch in the connection.
            first_courses_by_side (dict[Course_Side, int], optional): Dictionary of Course_Sides keyed to the starting carriage pass index. Missing course sides default to the 0th course.
            last_courses_by_side (dict[Course_Side, int], optional): Dictionary of Course_Sides keyed to the ending carriage pass index. Missing course sides default to height of the swatch.

        Returns:
            Course_Wise_Connection: The connection formed by the given dictionary definition of the swatch intervals.
        """
        if last_courses_by_side is None:
            last_courses_by_side = {}
        if Course_Side.Left not in last_courses_by_side:
            last_courses_by_side[Course_Side.Left] = left_swatch.height
        if Course_Side.Right not in last_courses_by_side:
            last_courses_by_side[Course_Side.Right] = right_swatch.height
        if first_courses_by_side is None:
            first_courses_by_side = {}
        if Course_Side.Left not in first_courses_by_side:
            first_courses_by_side[Course_Side.Left] = 0
        if Course_Side.Right not in first_courses_by_side:
            first_courses_by_side[Course_Side.Right] = 0
        return Course_Wise_Connection(left_swatch, right_swatch,
                                      first_courses_by_side[Course_Side.Left], last_courses_by_side[Course_Side.Left],
                                      first_courses_by_side[Course_Side.Right], last_courses_by_side[Course_Side.Right])

    @property
    def left_start_direction(self) -> Carriage_Pass_Direction | None:
        """
        Returns:
            Carriage_Pass_Direction | None : The direction of the first carriage pass to merge from on the left side, or None if the first carriage pass is a transfer pass.
        """
        first_cp = self.left_swatch.carriage_passes[self.left_bottom_course]
        if first_cp.xfer_pass:
            return None
        return first_cp.direction

    @property
    def right_start_direction(self) -> Carriage_Pass_Direction | None:
        """
        Returns:
            Carriage_Pass_Direction | None : The direction of the first carriage pass to merge from on the left side, or None if the first carriage pass is a transfer pass.
        """
        first_cp = self.right_swatch.carriage_passes[self.right_bottom_course]
        if first_cp.xfer_pass:
            return None
        return first_cp.direction

    @property
    def consumes_left_side(self) -> bool:
        """
        Returns:
            bool: True if the connection goes all the way to the top of the left swatch. False, otherwise.
        """
        return self.left_top_course >= self.left_swatch.height

    @property
    def consumes_right_side(self) -> bool:
        """
        Returns:
            bool: True if the connection goes all the way to the top of the right swatch. False, otherwise.
        """
        return self.right_top_course >= self.right_swatch.height

    def swap_from_swatch_by_carriage_pass_alignment(self, new_swatch: Swatch, interval_shift: dict[int, int]) -> Course_Wise_Connection:
        """
        Args:
            new_swatch (Swatch): The new from swatch in the resulting swatch connection. This will be the new left swatch.
            interval_shift (dict[int, int]): A dictionary that maps carriage pass indices in the current swatch to new indices in the merged swatch.

        Returns:
            Course_Wise_Connection: The connection formed by swapping the left swatch with the given new swatch and adjusting the interval by the given specification.
        """
        return Course_Wise_Connection(new_swatch, self.right_swatch,
                                      first_carriage_pass_on_left=interval_shift[self.left_bottom_course], last_carriage_pass_on_left=interval_shift[self.left_top_course],
                                      first_carriage_pass_on_right=self.right_bottom_course, last_carriage_pass_on_right=self.right_top_course)

    def swap_to_swatch_by_carriage_pass_alignment(self, new_swatch: Swatch, interval_shift: dict[int, int]) -> Course_Wise_Connection:
        """
        Args:
            new_swatch (Swatch): The new to swatch in the resulting swatch connection. This will be the new right swatch.
            interval_shift (dict[int, int]): A dictionary that maps carriage pass indices in the current swatch to new indices in the merged swatch.

        Returns:
            Course_Wise_Connection: The connection formed by swapping the right swatch with the given new swatch and adjusting the interval by the given specification.
        """
        return Course_Wise_Connection(new_swatch, self.right_swatch,
                                      first_carriage_pass_on_left=self.left_bottom_course, last_carriage_pass_on_left=self.left_top_course,
                                      first_carriage_pass_on_right=interval_shift[self.right_bottom_course], last_carriage_pass_on_right=interval_shift[self.right_top_course])

    def swap_matching_swatch_by_carriage_pass_alignment(self, new_swatch: Swatch, matching_swatch: Swatch, interval_shift: dict[int, int]) -> Course_Wise_Connection:
        """
        Args:
            new_swatch (Swatch): The new swatch to swap into the place of the matching swatch.
            matching_swatch (Swatch): The matching swatch to swap out of the connection.
            interval_shift (dict[int, int]): A dictionary that maps carriage pass indices in the current swatch to new indices in the merged swatch.

        Returns:
            Swatch_Connection:
                The swatch connection formed by swapping the new swatch into place of the matched swatch and shifting it by the given interval.
                If this connection does not contain the matching swatch, this connection is returned unchanged.
        """
        if self.from_swatch is matching_swatch:
            return self.swap_from_swatch_by_carriage_pass_alignment(new_swatch, interval_shift)
        elif self.to_swatch is matching_swatch:
            return self.swap_to_swatch_by_carriage_pass_alignment(new_swatch, interval_shift)
        else:
            return self

    @property
    def left_swatch(self) -> Swatch:
        """
        Returns:
            Swatch: The swatch that is merged from course-wise forming the left side of the connection.
        """
        return self.from_swatch

    @property
    def right_swatch(self) -> Swatch:
        """
        Returns:
            Swatch: The swatch that is merged to course-wise forming the right side of the connection.
        """
        return self.to_swatch

    @property
    def left_bottom_course(self) -> int:
        """
        Returns:
            int: The bottom carriage pass index of the left swatch.
        """
        return self.from_begin

    @property
    def left_top_course(self) -> int:
        """
        Returns:
            int: The top carriage pass index of the left swatch.
        """
        return self.from_end

    @property
    def right_bottom_course(self) -> int:
        """
        Returns:
            int: The bottom carriage pass index of the right swatch.
        """
        return self.to_begin

    @property
    def right_top_course(self) -> int:
        """
        Returns:
            int: The top carriage pass index of the right swatch.
        """
        return self.to_end

    @property
    def left_interval(self) -> Interval:
        """
        Returns:
            Interval: The interval of carriage pass indices of the left swatch.
        """
        return self.from_interval

    @property
    def right_interval(self) -> Interval:
        """
        Returns:
            Interval: The interval of carriage pass indices of the right swatch.
        """
        return self.to_interval
