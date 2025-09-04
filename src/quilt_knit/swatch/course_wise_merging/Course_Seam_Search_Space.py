"""Module containing the Course_Seam_Search_Space class."""

from knitout_interpreter.knitout_operations.Knitout_Line import Knitout_Line
from networkx import DiGraph

from quilt_knit.swatch.course_boundary_instructions import Course_Boundary_Instruction
from quilt_knit.swatch.course_wise_merging.Course_Seam_Connection import (
    Course_Seam_Connection,
)
from quilt_knit.swatch.course_wise_merging.Course_Wise_Connection import (
    Course_Wise_Connection,
)
from quilt_knit.swatch.Swatch import Swatch


class Course_Seam_Search_Space:
    """
        Network of potential linking instructions between swatches to form a vertical seam along the courses.
    """

    def __init__(self, left_swatch: Swatch, right_swatch: Swatch):
        self.right_swatch: Swatch = right_swatch
        self.left_swatch: Swatch = left_swatch
        self.seam_network: DiGraph = DiGraph()
        for left_exit in self.right_swatch.left_exits:
            for right_entrance in self.left_swatch.right_entrances:
                if left_exit.has_potential_left_to_right_connection(right_entrance):
                    connection = Course_Seam_Connection(left_exit, right_entrance)
                    self.seam_network.add_edge(left_exit, right_entrance, connection=connection)
        for right_exit in self.left_swatch.right_exits:
            for left_entrance in self.right_swatch.left_entrances:
                if left_entrance.has_potential_left_to_right_connection(right_exit):
                    connection = Course_Seam_Connection(right_exit, left_entrance)
                    self.seam_network.add_edge(right_exit, left_entrance, connection=connection)
        self.instructions_to_boundary_instruction: dict[Knitout_Line, Course_Boundary_Instruction] = {}
        self.left_swatch_boundaries_by_course_index: dict[int, Course_Boundary_Instruction] = {}
        for boundary in self.left_swatch.right_boundary:
            self.left_swatch_boundaries_by_course_index[boundary.carriage_pass_index] = boundary
            self.instructions_to_boundary_instruction[boundary.instruction] = boundary
        self.right_swatch_boundaries_by_course_index: dict[int, Course_Boundary_Instruction] = {}
        for boundary in self.right_swatch.left_boundary:
            self.right_swatch_boundaries_by_course_index[boundary.carriage_pass_index] = boundary
            self.instructions_to_boundary_instruction[boundary.instruction] = boundary
        self.preserved_search_space: DiGraph = self.seam_network.copy()  # used to reset the search space after merging.

    def print_search_space(self) -> None:
        """
        Prints out the search space for debugging purposes.
        """
        print(f"Left Exits from Right Swatch {self.right_swatch}")
        for left_exit in self.right_swatch.left_exits:
            if self.seam_network.has_node(left_exit):
                print(f"\texit {left_exit}")
                for potential_right_entrance in self.seam_network.successors(left_exit):
                    print(f"\t\t{potential_right_entrance} enter:\n\t\t\t{self.seam_network.edges[left_exit, potential_right_entrance]['connection']}")
            else:
                print(f"\texit {left_exit} -> no compatible right entrances")
        print(f"Right Exits from Left Swatch {self.left_swatch}")
        for right_exit in self.left_swatch.right_exits:
            if self.seam_network.has_node(right_exit):
                print(f"\t{right_exit} exit")
                for potential_left_entrance in self.seam_network.successors(right_exit):
                    print(f"\t\tenter {potential_left_entrance}:\n\t\t\t{self.seam_network.edges[right_exit, potential_left_entrance]['connection']}")
            else:
                print(f"\t{right_exit} exit -> no compatible left entrances")

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

    def remove_boundary(self, instruction: Knitout_Line) -> None:
        """
        Removes any boundary instruction associated with the given instruction from the search space.
        If the instruction does not belong to a boundary, nothing happens.

        Args:
            instruction (Knitout_Line): The boundary instruction to remove from the search space.
        """
        if instruction in self.instructions_to_boundary_instruction:
            boundary = self.instructions_to_boundary_instruction[instruction]
            if self.seam_network.has_node(boundary):
                self.seam_network.remove_node(boundary)

    def get_connection(self, exit_instruction: Course_Boundary_Instruction, entrance_instruction: Course_Boundary_Instruction) -> Course_Seam_Connection:
        """

        Args:
            exit_instruction (Course_Boundary_Instruction): The exit instruction to find the connection of.
            entrance_instruction (Course_Boundary_Instruction): The entrance instruction to find the connection of.

        Returns:
            Course_Seam_Connection : The connection from the exit to the entrance instruction in the search space.

        Raises:
            ValueError: If there is not a connection between the exit instruction and the entrance instruction in the search space.
        """
        if self.seam_network.has_edge(exit_instruction, entrance_instruction):
            connection = self.seam_network.edges[exit_instruction, entrance_instruction]['connection']
            assert isinstance(connection, Course_Seam_Connection)
            return connection
        else:
            raise ValueError(f"No connection found from {exit_instruction} to {entrance_instruction}")
