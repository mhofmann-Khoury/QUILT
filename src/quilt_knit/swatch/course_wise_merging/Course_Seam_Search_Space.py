"""Module containing the Course_Seam_Search_Space class."""

from quilt_knit.swatch.course_boundary_instructions import Course_Boundary_Instruction
from quilt_knit.swatch.course_wise_merging.Course_Seam_Connection import (
    Course_Seam_Connection,
)
from quilt_knit.swatch.course_wise_merging.Course_Wise_Connection import (
    Course_Wise_Connection,
)
from quilt_knit.swatch.Seam_Search_Space import Seam_Search_Space
from quilt_knit.swatch.Swatch import Swatch


class Course_Seam_Search_Space(Seam_Search_Space):
    """
        Network of potential linking instructions between swatches to form a vertical seam along the courses.

        Attributes:
            left_swatch_boundaries_by_course_index (dict[int, Course_Boundary_Instruction]): Left-swatch course indices keyed to the boundary of that course.
            right_swatch_boundaries_by_course_index (dict[int, Course_Boundary_Instruction]): Right-swatch boundaries keyed to the boundary of that course.
    """

    def __init__(self, left_swatch: Swatch, right_swatch: Swatch):
        super().__init__(left_swatch, right_swatch)
        for left_exit in self.right_swatch.left_exits:
            for right_entrance in self.left_swatch.right_entrances:
                if left_exit.has_potential_left_to_right_connection(right_entrance):
                    connection = Course_Seam_Connection(left_exit, right_entrance)
                    self._add_connection(connection)
        for right_exit in self.left_swatch.right_exits:
            for left_entrance in self.right_swatch.left_entrances:
                if left_entrance.has_potential_left_to_right_connection(right_exit):
                    connection = Course_Seam_Connection(right_exit, left_entrance)
                    self._add_connection(connection)
        self.left_swatch_boundaries_by_course_index: dict[int, Course_Boundary_Instruction] = {}
        for boundary in self.left_swatch.right_boundary:
            self.left_swatch_boundaries_by_course_index[boundary.carriage_pass_index] = boundary
        self.right_swatch_boundaries_by_course_index: dict[int, Course_Boundary_Instruction] = {}
        for boundary in self.right_swatch.left_boundary:
            self.right_swatch_boundaries_by_course_index[boundary.carriage_pass_index] = boundary

    @property
    def left_swatch(self) -> Swatch:
        """
        Returns:
            Swatch: The left swatch in the merge.
        """
        return self._from_swatch

    @property
    def right_swatch(self) -> Swatch:
        """
        Returns:
            Swatch: The right swatch in the merge.
        """
        return self._to_swatch

    def remove_boundaries_beyond_course_connections(self, course_wise_connection: Course_Wise_Connection,
                                                    remove_left_swatch: bool = True, remove_right_swatch: bool = True) -> None:
        """
        Removes boundary instructions  from the search space that occur outside the range of courses in the course-wise connection.

        Args:
            course_wise_connection (Course_Wise_Connection): The connection to narrow the search space to.
            remove_left_swatch (bool, optional): Whether to remove boundary instructions in left swatch from the search space. Defaults to True.
            remove_right_swatch (bool, optional): Whether to remove boundary instructions in right swatch from the search space. Defaults to True.
        """
        if remove_left_swatch:
            for i in range(course_wise_connection.left_bottom_course):
                self.seam_network.remove_node(self.left_swatch_boundaries_by_course_index[i])
            for i in range(course_wise_connection.left_top_course, self.left_swatch.height):
                self.seam_network.remove_node(self.left_swatch_boundaries_by_course_index[i])
        if remove_right_swatch:
            for i in range(course_wise_connection.right_bottom_course):
                self.seam_network.remove_node(self.right_swatch_boundaries_by_course_index[i])
            for i in range(course_wise_connection.right_top_course, self.right_swatch.height):
                self.seam_network.remove_node(self.right_swatch_boundaries_by_course_index[i])
