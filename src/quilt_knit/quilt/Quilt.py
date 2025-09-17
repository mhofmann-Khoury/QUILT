"""The module containing the Quilt class."""
from typing import cast

from knitout_interpreter.knitout_operations.Knitout_Line import Knitout_Comment_Line
from networkx import DiGraph, topological_generations, topological_sort

from quilt_knit.quilt.Swatch_Neighborhood import Swatch_Neighborhood
from quilt_knit.swatch.course_wise_merging.Course_Merge_Process import (
    Course_Merge_Process,
)
from quilt_knit.swatch.course_wise_merging.Course_Wise_Connection import (
    Course_Wise_Connection,
)
from quilt_knit.swatch.Swatch import Swatch
from quilt_knit.swatch.Swatch_Connection import Swatch_Connection
from quilt_knit.swatch.wale_wise_merging.Wale_Merge_Process import Wale_Merge_Process
from quilt_knit.swatch.wale_wise_merging.Wale_Wise_Connection import (
    Wale_Wise_Connection,
)


class Blocked_Swatch_Connection_Exception(Exception):
    """
    An Exception raised when attempting to add a blocked connection to a quilt.

    Attributes:
        connection (Swatch_Connection): The blocked connection.
        blocking_connections (set[Swatch_Connection]): The connections in the quilt that blocked the new connection.
    """

    def __init__(self, connection: Swatch_Connection, blocking_connections: set[Swatch_Connection]):
        """
        Args:
            connection (Swatch_Connection): The blocked connection.
            blocking_connections (set[Swatch_Connection]): The connections in the quilt that blocked the new connection.
        """
        self.connection: Swatch_Connection = connection
        self.blocking_connections: set[Swatch_Connection] = blocking_connections
        super().__init__(f"Connection {connection} is blocked by connections {blocking_connections}")


class Unconnected_Swatches_Exception(Exception):
    """
    An Exception raised when attempting to merge two unconnected swatches in a quilt.

    Attributes:
        a_swatch (Swatch): The first swatch.
        b_swatch (Swatch): The second swatch.
    """

    def __init__(self, a_swatch: Swatch, b_swatch: Swatch) -> None:
        """
        Args:
            a_swatch (Swatch): The first swatch.
            b_swatch (Swatch): The second swatch.
        """
        self.a_swatch: Swatch = a_swatch
        self.b_swatch: Swatch = b_swatch
        super().__init__(f"Cannot merge unconnected swatches {a_swatch} and {b_swatch}")


class Quilt:
    """A data structure of a dynamic grid of connected swatches which can be merged to form a unified swatch.

    Attributes:
        course_wise_connections (DiGraph): A directed graph of the course wise connections between swatches in the quilt.
        wale_wise_connections (DiGraph): A directed graph of the wale wise connections between swatches in the quilt.
        swatch_neighborhoods (dict[Swatch, Swatch_Neighborhood]): A dictionary of swatches keyed to their neighborhoods.
        swatches_to_rightward_shifts (dict[Swatch, int]): A dictionary of swatches keyed to the number of needles to shift them by rightward when merging the quilt.
    """
    _CONNECTION: str = "connection"

    def __init__(self) -> None:
        self.course_wise_connections: DiGraph = DiGraph()
        self.wale_wise_connections: DiGraph = DiGraph()
        self.swatch_neighborhoods: dict[Swatch, Swatch_Neighborhood] = {}
        self.swatches_to_rightward_shifts: dict[Swatch, int] = {}

    def connect_swatches_wale_wise(self, bottom_swatch: Swatch, top_swatch: Swatch,
                                   bottom_leftmost_needle_position: int = 0, bottom_rightmost_needle_position: int | None = None,
                                   top_leftmost_needle_position: int = 0, top_rightmost_needle_position: int | None = None,
                                   remove_cast_ons: bool = True) -> Wale_Wise_Connection:
        """
        Forms a wale-wise connection with the given specification and adds it to the Quilt.

        Args:
            bottom_swatch (Swatch): The bottom swatch in the connection.
            top_swatch (Swatch): The top swatch in the connection.
            bottom_leftmost_needle_position (int, optional): The leftmost needle position to merge from the bottom swatch. Defaults to 0.
            bottom_rightmost_needle_position (int, optional): The rightmost needle position to merge from the bottom swatch. Defaults to the width of the bottom swatch.
            top_leftmost_needle_position (int, optional): The leftmost needle position to merge into the top swatch. Defaults to 0.
            top_rightmost_needle_position (int, optional): The rightmost needle position to merge into the top swatch. Defaults to the width of the top swatch.
            remove_cast_ons (bool, optional): Whether to remove cast-on operations from the top swatch before merging. Defaults to True.

        Returns:
            Wale_Wise_Connection: The connection formed and added to the quilt.

        Raises:
            Blocked_Swatch_Connection_Exception: If the new connection is blocked by existing connections in the quilt.
        """
        return cast(Wale_Wise_Connection, self._connect_swatches(Wale_Wise_Connection(bottom_swatch, top_swatch,
                                                                                      bottom_leftmost_needle_position, bottom_rightmost_needle_position,
                                                                                      top_leftmost_needle_position, top_rightmost_needle_position, remove_cast_ons)))

    def connect_swatches_course_wise(self, left_swatch: Swatch, right_swatch: Swatch,
                                     first_carriage_pass_on_left: int = 0, last_carriage_pass_on_left: int | None = None,
                                     first_carriage_pass_on_right: int = 0, last_carriage_pass_on_right: int | None = None) -> Course_Wise_Connection | None:
        """
        Forms a course-wise connection with the given specification and adds it to the Quilt.
        Args:
            left_swatch (Swatch): The left swatch in the connection.
            right_swatch (Swatch): The right swatch in the connection.
            first_carriage_pass_on_left (int, optional): The first carriage pass to merge from on the left side. Defaults to 0.
            last_carriage_pass_on_left (int, optional): The last carriage pass to merge from on the left side. Defaults to the height of the left swatch.
            first_carriage_pass_on_right (int, optional): The first carriage pass to merge from on the right side. Defaults to 0.
            last_carriage_pass_on_right (int, optional): The last carriage pass to merge from on the right side. Defaults to the height of the right swatch.

        Returns:
            Course_Wise_Connection: The connection formed and added to the quilt.

        Raises:
            Blocked_Swatch_Connection_Exception: If the new connection is blocked by existing connections in the quilt.
        """
        return cast(Course_Wise_Connection, self._connect_swatches(Course_Wise_Connection(left_swatch, right_swatch,
                                                                                          first_carriage_pass_on_left, last_carriage_pass_on_left,
                                                                                          first_carriage_pass_on_right, last_carriage_pass_on_right)))

    def _connect_swatches(self, new_connection: Swatch_Connection) -> Swatch_Connection:
        """
        Adds the given new connection to the quilt. If a previous connection envelops the given connection, nothing happens and the enveloping connection is returned.
        Any connections enveloped by this new connection are removed from the quilt.

        Args:
            new_connection (Swatch_Connection): The new connection to add to the quilt.

        Returns:
            Swatch_Connection: The connection formed and added to the quilt.

        Raises:
            Blocked_Swatch_Connection_Exception: If the new connection is blocked by existing connections in the quilt.
        """
        prior_connection = self.get_connection(new_connection.from_swatch, new_connection.to_swatch)
        new_connection = new_connection.update_connection(prior_connection)
        if new_connection is None:  # The prior connection subsumes the new connection. No Update needed.
            assert isinstance(prior_connection, Swatch_Connection)
            return prior_connection
        if new_connection.from_swatch in self:
            blocked_connections = self.swatch_neighborhoods[new_connection.from_swatch].blocking_connections(new_connection)
            if len(blocked_connections) > 0:
                raise Blocked_Swatch_Connection_Exception(new_connection, blocked_connections)
        if new_connection.to_swatch in self:
            blocked_connections = self.swatch_neighborhoods[new_connection.to_swatch].blocking_connections(new_connection)
            if len(blocked_connections) > 0:
                raise Blocked_Swatch_Connection_Exception(new_connection, blocked_connections)
        if prior_connection is not None:
            self._remove_connection(prior_connection)
        enveloped_connections = set()
        if new_connection.from_swatch in self:
            enveloped_connections = self.swatch_neighborhoods[new_connection.from_swatch].enveloped_connections(new_connection)
        if new_connection.to_swatch in self:
            enveloped_connections.update(self.swatch_neighborhoods[new_connection.to_swatch].enveloped_connections(new_connection))
        for enveloped_connection in enveloped_connections:
            self._remove_connection(enveloped_connection)
        self._add_connection(new_connection)
        return new_connection

    def __contains__(self, item: None | Swatch | tuple[Swatch, Swatch] | Swatch_Neighborhood | Swatch_Connection) -> bool:
        """

        Args:
            item (None | Swatch | tuple[Swatch, Swatch] | Swatch_Neighborhood | Swatch_Connection):
                The item to search for in the swatch.

        Returns:
            bool:
                True if the item is in the quilt. False otherwise.
                * A None item returns False.
                * If given a swatch, returns True if the swatch is in the quilt.
                * If given a tuple of two swatches, returns True if there is a wale-wise or course-wise connection between these swatches in the quilt.
                * If given a swatch neighborhood, returns True if the swatch of that neighborhood is in the quilt.
                * If given a swatch connections, returns True if the connections is in the quilt.
        """
        if item is None:
            return False
        if isinstance(item, Swatch):
            return item in self.swatch_neighborhoods
        elif isinstance(item, tuple):
            a_swatch, b_swatch = item
            return bool(self.course_wise_connections.has_edge(a_swatch, b_swatch) or self.wale_wise_connections.has_edge(a_swatch, b_swatch)
                        or self.course_wise_connections.has_edge(b_swatch, a_swatch) or self.wale_wise_connections.has_edge(b_swatch, a_swatch))
        elif isinstance(item, Swatch_Neighborhood):
            return item.swatch in self
        elif isinstance(item, Swatch_Connection):
            prior_connection = self.get_connection(item.from_swatch, item.to_swatch, force_direction=False)
            return prior_connection is item

    def get_connection(self, a_swatch: Swatch, b_swatch: Swatch, force_direction: bool = True) -> Swatch_Connection | None:
        """
        Args:
            a_swatch (Swatch): The first swatch in the connection.
            b_swatch (Swatch): The second swatch in the connection.
            force_direction (bool, optional): If True, only returns connections from a_swatch to b_swatch. Defaults to True.

        Returns:
            Swatch_Connection | None: The connection in the quilt between the given swatches or None if no connection exists.
        """
        prior_connection = self.get_course_wise_connection(a_swatch, b_swatch, force_direction)
        if prior_connection is None:
            return self.get_wale_wise_connection(a_swatch, b_swatch, force_direction)
        else:
            return prior_connection

    def get_course_wise_connection(self, a_swatch: Swatch, b_swatch: Swatch, force_direction: bool = True) -> Course_Wise_Connection | None:
        """
        Args:
            a_swatch (Swatch): The first swatch in the connection.
            b_swatch (Swatch): The second swatch in the connection.
            force_direction (bool, optional): If True, only returns connections from a_swatch to b_swatch. Defaults to True.

        Returns:
            Course_Wise_Connection | None: The course wise connection in the quilt between the given swatches or None if no connection exists.
        """
        if self.course_wise_connections.has_edge(a_swatch, b_swatch):
            return cast(Course_Wise_Connection, self.course_wise_connections[a_swatch][b_swatch][Quilt._CONNECTION])
        elif not force_direction and self.course_wise_connections.has_edge(b_swatch, a_swatch):
            return cast(Course_Wise_Connection, self.course_wise_connections[b_swatch][a_swatch][Quilt._CONNECTION])
        else:
            return None

    def get_wale_wise_connection(self, a_swatch: Swatch, b_swatch: Swatch, force_direction: bool = True) -> Wale_Wise_Connection | None:
        """
        Args:
            a_swatch (Swatch): The first swatch in the connection.
            b_swatch (Swatch): The second swatch in the connection.
            force_direction (bool, optional): If True, only returns connections from a_swatch to b_swatch. Defaults to True.

        Returns:
            Wale_Wise_Connection | None: The wale-wise connection in the quilt between the given swatches or None if no connection exists.
        """
        if self.wale_wise_connections.has_edge(a_swatch, b_swatch):
            return cast(Wale_Wise_Connection, self.wale_wise_connections[a_swatch][b_swatch][Quilt._CONNECTION])
        elif not force_direction and self.wale_wise_connections.has_edge(b_swatch, a_swatch):
            return cast(Wale_Wise_Connection, self.wale_wise_connections[b_swatch][a_swatch][Quilt._CONNECTION])
        else:
            return None

    def add_swatch(self, swatch: Swatch) -> None:
        """
        Adds the given swatch to the quilt with no connections to other swatches.

        Args:
            swatch (Swatch): The swatch to add to the quilt.
        """
        self.course_wise_connections.add_node(swatch)
        self.wale_wise_connections.add_node(swatch)
        self.swatch_neighborhoods[swatch] = Swatch_Neighborhood(swatch)
        self.swatches_to_rightward_shifts[swatch] = 0

    def _remove_swatch(self, swatch: Swatch) -> Swatch_Neighborhood | None:
        """
        Removes the given swatch from the quilt.
        Args:
            swatch (Swatch): The swatch to remove.

        Returns:
            Swatch_Neighborhood | None: The neighborhood of the removed swatch or None if the swatch was not in the Quilt.
        """
        if swatch in self:
            neighborhood = self.swatch_neighborhoods[swatch]
            for connection in neighborhood.get_all_connections():
                self._remove_connection(connection)
            self.course_wise_connections.remove_node(swatch)
            self.wale_wise_connections.remove_node(swatch)
            del self.swatch_neighborhoods[swatch]
            del self.swatches_to_rightward_shifts[swatch]
            return neighborhood
        else:
            return None

    def _remove_connection(self, connection: Swatch_Connection) -> None:
        """
        Removes the given connection from the quilt.

        Args:
            connection (Swatch_Connection): The connection to remove.
        """
        if connection in self:
            self.swatch_neighborhoods[connection.from_swatch].remove_connection(connection)
            self.swatch_neighborhoods[connection.to_swatch].remove_connection(connection)
            if isinstance(connection, Course_Wise_Connection):
                self.course_wise_connections.remove_edge(connection.from_swatch, connection.to_swatch)
            else:
                self.wale_wise_connections.remove_edge(connection.from_swatch, connection.to_swatch)

    def _add_connection(self, connection: Swatch_Connection) -> None:
        """
        Adds the given connection to the quilt. If the swatches in the connection are not in the quilt, they are added to the quilt.
        Args:
            connection (Swatch_Connection): The connection to add to the quilt.
        """
        if connection.from_swatch not in self:
            self.add_swatch(connection.from_swatch)
        if connection.to_swatch not in self:
            self.add_swatch(connection.to_swatch)
        self.swatch_neighborhoods[connection.from_swatch].make_connection(connection)
        self.swatch_neighborhoods[connection.to_swatch].make_connection(connection)
        if isinstance(connection, Course_Wise_Connection):
            self.course_wise_connections.add_edge(connection.from_swatch, connection.to_swatch, connection=connection)
        else:
            assert isinstance(connection, Wale_Wise_Connection)
            self.wale_wise_connections.add_edge(connection.from_swatch, connection.to_swatch, connection=connection)

    def _reconnect_swatch(self, swatch: Swatch | None, prior_connections: set[Swatch_Connection],
                          match_prior_swatch: None | Swatch,
                          shift_match_course_interval: int | dict[int, int] = 0, shift_match_wale_interval: int = 0) -> None:
        """
        Connect the given swatch to the quilt using the given prior connections.
        The prior connections may not include the original swatch but can be modified to swap the given swatch in for a matching swatch.

        Args:
            swatch (Swatch | None): The swatch to reconnect to the quilt. If the swatch is None, nothing happens.
            prior_connections (set[Swatch_Connection]): The prior connections to reconnect the swatch.
            match_prior_swatch (Swatch | None): If given a swatch to match, connections containing this matching swatch will be replaced with the given swatch.
            shift_match_course_interval (int, dict[int, int], optional): The amount to shift the course interval on the swatch side by for course wise connections. Defaults to 0.
            shift_match_wale_interval (int): The amount to shift the wale interval on the swatch side by for wale wise connections.
        """
        if swatch is None:
            return
        if len(prior_connections) == 0:
            self.add_swatch(swatch)
            return
        prior_connections = set(c for c in prior_connections if swatch in c or match_prior_swatch in c)
        prior_course_wise_connections = set(c for c in prior_connections if isinstance(c, Course_Wise_Connection))
        prior_wale_wise_connections = set(c for c in prior_connections if isinstance(c, Wale_Wise_Connection))
        if match_prior_swatch is not None:
            if isinstance(shift_match_course_interval, dict):
                prior_course_wise_connections = set(c.swap_matching_swatch_by_carriage_pass_alignment(swatch, match_prior_swatch, interval_shift=shift_match_course_interval)
                                                    if match_prior_swatch in c else c for c in prior_course_wise_connections)
            else:
                prior_course_wise_connections = set(c.swap_matching_swatch(swatch, match_prior_swatch, interval_shift=shift_match_course_interval)
                                                    if match_prior_swatch in c else c for c in prior_course_wise_connections)
            prior_wale_wise_connections = set(c.swap_matching_swatch(swatch, match_prior_swatch, interval_shift=shift_match_wale_interval)
                                              if match_prior_swatch in c else c for c in prior_wale_wise_connections)
        for connection in prior_course_wise_connections:
            self.connect_swatches_course_wise(connection.left_swatch, connection.right_swatch,
                                              connection.left_bottom_course, connection.left_top_course,
                                              connection.right_bottom_course, connection.right_top_course)
        for connection in prior_wale_wise_connections:
            self.connect_swatches_wale_wise(connection.bottom_swatch, connection.top_swatch,
                                            connection.bottom_left_needle_position, connection.bottom_right_needle_position,
                                            connection.top_left_needle_position, connection.top_right_needle_position, remove_cast_ons=False)

    def merge_swatches_course_wise(self, left_swatch: Swatch, right_swatch: Swatch,
                                   discard_unconnected_lower_courses: bool = False,
                                   discard_unconnected_upper_courses: bool = False) -> tuple[Swatch, set[Swatch], set[Swatch]]:
        """
        Merges the given swatches based on their connection in the quilt. The merged swatch is re-attached to the quilt in their place.

        Args:
            left_swatch (Swatch): The left swatch to merge.
            right_swatch (Swatch): The right swatch to merge.
            discard_unconnected_lower_courses (bool, optional): If True, The lower courses of the swatch that have no connections in the quilt will be discarded. Defaults to False.
            discard_unconnected_upper_courses (bool, optional): If True, The upper courses of the swatch that have no connections in the quilt will be discarded. Defaults to False.

        Returns:
            tuple[Swatch, set[Swatch], set[Swatch]:
                A tuple containing:
                * The swatch resulting from the merge.
                * The set of swatches created by slicing off the lower portions of the merging swatches. These remain in the quilt.
                * The set of swatches created by slicing off the upper portions of the merging swatches. These remain in the quilt.

        Raises:
            Unconnected_Swatches_Exception: If the given swatches are not connected in the quilt.
        """
        original_connection = self.get_course_wise_connection(left_swatch, right_swatch)
        if original_connection is None:
            raise Unconnected_Swatches_Exception(left_swatch, right_swatch)
        left_original_neighborhood = self.swatch_neighborhoods[left_swatch]
        right_original_neighborhood = self.swatch_neighborhoods[right_swatch]
        left_swatch_effected_connections = left_original_neighborhood.get_connections_to_courses(original_connection.left_bottom_course,
                                                                                                 original_connection.left_top_course, exclude_right_connections=True)
        right_swatch_effected_connections = right_original_neighborhood.get_connections_to_courses(original_connection.right_bottom_course,
                                                                                                   original_connection.right_top_course, exclude_left_connection=True)

        # split off the portions of the swatches.
        connections_to_lower_left = left_original_neighborhood.get_connections_to_courses(0, original_connection.left_bottom_course)
        lower_left_swatch, remaining_left_swatch, left_lost_xfer_pass = left_swatch.split_swatch_at_carriage_pass(original_connection.left_bottom_course,
                                                                                                                  f"{left_swatch.name}c_0_{original_connection.left_bottom_course}",
                                                                                                                  left_swatch.name)
        height_removed_from_left = 0
        if lower_left_swatch is not None:
            height_removed_from_left = lower_left_swatch.height
        if discard_unconnected_lower_courses and len(connections_to_lower_left) == 0:  # discard the lower portion of the swatch since it is not connected to anything.
            lower_left_swatch = None
            connections_to_lower_left = set()

        # split off the lower portion of the right swatch.
        connections_to_lower_right = right_original_neighborhood.get_connections_to_courses(0, original_connection.right_bottom_course)
        lower_right_swatch, remaining_right_swatch, right_lost_xfer_pass = right_swatch.split_swatch_at_carriage_pass(original_connection.right_bottom_course,
                                                                                                                      f"{right_swatch.name}c_0_{original_connection.right_bottom_course}",
                                                                                                                      right_swatch.name)
        height_removed_from_right = 0
        if lower_right_swatch is not None:
            height_removed_from_right = lower_right_swatch.height
        if discard_unconnected_lower_courses and len(connections_to_lower_right) == 0:  # discard the lower portion of the swatch since it is not connected to anything.
            lower_right_swatch = None
            connections_to_lower_right = set()

        # Split off the upper portion of the left swatch.
        connections_to_upper_left = left_original_neighborhood.get_connections_to_courses(original_connection.left_top_course + 1, left_swatch.height)
        assert isinstance(remaining_left_swatch, Swatch)
        remaining_left_swatch, upper_left_swatch, upper_left_lost_xfer_pass = remaining_left_swatch.split_swatch_at_carriage_pass(original_connection.left_top_course - height_removed_from_left,
                                                                                                                                  left_swatch.name,
                                                                                                                                  f"{left_swatch.name}c_{original_connection.left_top_course + 1}_up")
        if discard_unconnected_upper_courses and len(connections_to_upper_left) == 0:
            upper_left_swatch = None
            upper_left_lost_xfer_pass = False
            connections_to_upper_left = set()

        # Split off the upper portion of the right swatch.
        connections_to_upper_right = right_original_neighborhood.get_connections_to_courses(original_connection.right_top_course + 1, right_swatch.height)
        assert isinstance(remaining_right_swatch, Swatch)
        (remaining_right_swatch, upper_right_swatch,
         upper_right_lost_xfer_pass) = remaining_right_swatch.split_swatch_at_carriage_pass(original_connection.right_top_course - height_removed_from_right,
                                                                                            right_swatch.name,
                                                                                            f"{right_swatch.name}c_{original_connection.right_top_course + 1}_up")
        if discard_unconnected_upper_courses and len(connections_to_upper_right) == 0:
            upper_right_swatch = None
            upper_right_lost_xfer_pass = False
            connections_to_upper_right = set()

        # Merge the remaining band of the left and right swatch
        assert isinstance(remaining_left_swatch, Swatch)
        assert isinstance(remaining_right_swatch, Swatch)
        merge_connection = Course_Wise_Connection(remaining_left_swatch, remaining_right_swatch)
        merger = Course_Merge_Process(merge_connection)
        merged_instructions = merger.merge_swatches()
        merged_instructions = [i for i in merged_instructions if not isinstance(i, Knitout_Comment_Line)]
        for instruction in merged_instructions:
            instruction.comment = None
        merged_swatch = Swatch(f"{left_swatch.name}_cm_{right_swatch.name}", merged_instructions)

        # Determine which cp-index corresponded to the left and right connection points from the original swatches to the merged swatch.
        left_swatch_cp_conversion: dict[int, int] = {left_swatch.height: merged_swatch.height}
        right_swatch_cp_conversion: dict[int, int] = {right_swatch.height: merged_swatch.height}
        for cp_index, cp in enumerate(merged_swatch.carriage_passes):
            left_cp_index, right_cp_index = merger.get_original_cp_index(cp)
            if left_cp_index is not None:
                left_swatch_cp_conversion[left_cp_index + height_removed_from_left] = cp_index
            if right_cp_index is not None:
                right_swatch_cp_conversion[right_cp_index + height_removed_from_right] = cp_index

        # Create connections from the merged swatch back to its slices.
        if lower_left_swatch is not None:
            left_swatch_effected_connections.add(Wale_Wise_Connection(lower_left_swatch, merged_swatch, top_rightmost_needle_position=lower_left_swatch.width - 1, remove_cast_ons=True))
        if upper_left_swatch is not None:
            left_swatch_effected_connections.add(Wale_Wise_Connection(merged_swatch, upper_left_swatch, bottom_rightmost_needle_position=upper_left_swatch.width - 1, remove_cast_ons=True))
        if lower_right_swatch is not None:
            right_swatch_effected_connections.add(Wale_Wise_Connection(lower_right_swatch, merged_swatch, top_leftmost_needle_position=left_swatch.max_needle + 1, remove_cast_ons=True))
        if upper_right_swatch is not None:
            self.swatches_to_rightward_shifts[upper_right_swatch] = left_swatch.width
            right_swatch_effected_connections.add(Wale_Wise_Connection(merged_swatch, upper_right_swatch, bottom_leftmost_needle_position=left_swatch.max_needle + 1, remove_cast_ons=True))

        # Remove the original swatch connections
        self._remove_swatch(left_swatch)
        self._remove_swatch(right_swatch)

        # Connect the lower slices to the original quilt
        self._reconnect_swatch(lower_left_swatch, connections_to_lower_left, left_swatch)
        self._reconnect_swatch(lower_right_swatch, connections_to_lower_right, right_swatch)

        # Shift the course-wise connection down by the height of the removed bottom course and 1 if a transfer pass was removed
        upper_left_down_shift = -1 - original_connection.left_top_course - int(upper_left_lost_xfer_pass)
        self._reconnect_swatch(upper_left_swatch, connections_to_upper_left, left_swatch,
                               shift_match_course_interval=upper_left_down_shift)

        # Shift the course-wise connection down by the height of the removed bottom course and 1 if a transfer pass was removed
        upper_right_down_shift = -1 - original_connection.right_top_course - int(upper_right_lost_xfer_pass)
        self._reconnect_swatch(upper_right_swatch, connections_to_upper_right, right_swatch,
                               shift_match_course_interval=upper_right_down_shift)

        # Reconnect the merged swatch
        self._reconnect_swatch(merged_swatch, left_swatch_effected_connections, left_swatch,
                               shift_match_course_interval=left_swatch_cp_conversion)
        self._reconnect_swatch(merged_swatch, right_swatch_effected_connections, right_swatch,
                               shift_match_course_interval=right_swatch_cp_conversion,
                               shift_match_wale_interval=left_swatch.width)

        upper_slices = {upper_left_swatch, upper_right_swatch}
        if None in upper_slices:
            upper_slices.remove(None)
        lower_slices = {lower_left_swatch, lower_right_swatch}
        if None in lower_slices:
            lower_slices.remove(None)

        if discard_unconnected_lower_courses:
            removed_lower_left = self._skip_swatch_wale_wise(lower_left_swatch)
            if removed_lower_left:
                lower_slices.remove(lower_left_swatch)
            removed_lower_right = self._skip_swatch_wale_wise(lower_right_swatch)
            if removed_lower_right:
                lower_slices.remove(lower_right_swatch)
        return merged_swatch, cast(set[Swatch], upper_slices), cast(set[Swatch], lower_slices)

    def _skip_swatch_wale_wise(self, skipped_swatch: Swatch | None) -> bool:
        """
        Skipping a swatch wale-wise means connecting its bottom-wale-connected swatches to its top-wale-connected swatches. For example, to remove cast-on lines from a swatch in the middle of a quilt.

        Args:
            skipped_swatch (Swatch | None): The swatch to skip over wale-wise. If this is None, returns False.

        Returns:
            bool: True if the given swatch can be skipped over because it has no course-wise connections. False, otherwise.

        """
        if skipped_swatch is None:
            return False
        course_connections = self.swatch_neighborhoods[skipped_swatch].get_connections_to_courses(exclude_bottom_connections=True, exclude_top_connections=True)
        if len(course_connections) == 0:  # skipped is not connected to a band of the quilt. Can be replaced with connections to its upper swatch.
            top_connections = self.swatch_neighborhoods[skipped_swatch].get_connections_to_courses(exclude_left_connection=True, exclude_right_connections=True,
                                                                                                   exclude_bottom_connections=True)
            assert len(top_connections) == 1
            top_connection = [*top_connections][0]
            assert isinstance(top_connection, Wale_Wise_Connection)
            top_shift = top_connection.to_begin
            bottom_connections = self.swatch_neighborhoods[skipped_swatch].get_connections_to_courses(exclude_left_connection=True, exclude_right_connections=True,
                                                                                                      exclude_top_connections=True)
            self._remove_swatch(skipped_swatch)
            self._reconnect_swatch(top_connection.top_swatch, bottom_connections, skipped_swatch, shift_match_wale_interval=top_shift)
            return True
        else:
            return False

    def _merge_course_wise_quilt_layer(self, layer_swatches: set[Swatch], discard_unconnected_lower_courses: bool) -> tuple[set[Swatch], set[Swatch], set[Swatch]]:
        """
        Merges a set of swatches in a topological generation of wale-wise connections.
        Swatches will be sliced down to the minimum overlapping courses in the layer.
        The remaining sliced swatches will be retained in the quilt.

        Args:
            layer_swatches (set[Swatch]): The wale-wise topological generation of swatches to merge.

        Returns:
            tuple[set[Swatch], set[Swatch], set[Swatch]]:
                A tuple containing:
                * The set of swatches that are merged together from the layer.
                * The set of swatches produced by slicing off the lower portion of the swatches in the merged layer.
                * The set of swatches produced by slicing off the upper portion of the swatches in the merged layer.
        """
        if len(layer_swatches) == 0:  # Nothing to merge
            return set(), set(), set()
        lower_slices: set[Swatch] = set()
        upper_slices: set[Swatch] = set()
        layer_graph = DiGraph()
        for swatch in layer_swatches:
            layer_graph.add_node(swatch)
            for successor in self.course_wise_connections.successors(swatch):
                if successor in layer_swatches:
                    layer_graph.add_edge(swatch, successor, connection=self.get_connection(swatch, successor))

        def _merge_to_successors(swatch_to_merge: Swatch) -> Swatch:
            """
            Args:
                swatch_to_merge (Swatch): The swatch to merge to its successors in the layer graph.

            Returns:
                Swatch: The swatch merged into its successors.
            """
            successors = [*layer_graph.successors(swatch_to_merge)]
            layer_graph.remove_node(swatch_to_merge)
            assert len(successors) <= 1
            for swatch_to_merge_to in successors:
                merged_swatch, new_upper_slices, new_lower_slices = self.merge_swatches_course_wise(swatch_to_merge, swatch_to_merge_to,
                                                                                                    discard_unconnected_lower_courses=discard_unconnected_lower_courses)
                layer_graph.add_node(merged_swatch)
                lower_slices.update(new_lower_slices)
                upper_slices.update(new_upper_slices)
                for right_successor in [*layer_graph.successors(swatch_to_merge_to)]:
                    layer_graph.add_edge(merged_swatch, right_successor)
                layer_graph.remove_node(swatch_to_merge_to)
                return _merge_to_successors(merged_swatch)
            return swatch_to_merge

        merged_swatches = set()
        while len(layer_graph.edges) > 0:
            for swatch in [*topological_sort(layer_graph)]:
                if swatch in layer_graph:  # Note, the layer will be destroyed by the merge process, removing nodes from the prior topological sort.
                    merged_swatches.add(_merge_to_successors(swatch))
        merged_swatches.update(layer_graph.nodes)
        return merged_swatches, lower_slices, upper_slices

    def convert_quilt_to_course_bands(self) -> list[set[Swatch]]:
        """
        Merge all the swatches in course-wise bands of the quilt until there are no more course wise connections to merge.

        Returns:
            list[set[Swatch]]: The list, sorted from the bottom to the top of the quilt, of course-wise bands resulting from merging the swatches.
        """
        converted_layers: list[set[Swatch]] = []
        wale_wise_generations = [*topological_generations(self.wale_wise_connections)]
        while len(wale_wise_generations) > len(converted_layers):
            unmerged_layer = wale_wise_generations[len(converted_layers)]
            if len(unmerged_layer) == 1:  # Only one swatch in the layer, nothing to merge
                converted_layers.append(unmerged_layer)
            elif len(unmerged_layer) > 0:  # Multiple swatches in the layer to merge.
                if len(converted_layers) == 0:
                    discard_lower = False
                else:
                    discard_lower = True
                merged_layer, lower_slices, upper_slices = self._merge_course_wise_quilt_layer(unmerged_layer, discard_unconnected_lower_courses=discard_lower)
                if len(lower_slices) > 0:
                    converted_layers.append(lower_slices)
                if len(merged_layer) > 0:
                    converted_layers.append(merged_layer)
                wale_wise_generations = [*topological_generations(self.wale_wise_connections)]
        return converted_layers

    def _shift_sliced_swatches(self) -> None:
        """
        Shifts all swatches to the right based on their shifted position specified by the merge process.
        """
        for swatch, shift in self.swatches_to_rightward_shifts.items():
            if shift > 0:
                self._reconnect_swatch(swatch, self.swatch_neighborhoods[swatch].get_all_connections(), swatch, shift_match_wale_interval=shift)

    def merge_quilt(self, compile_merges: bool = False, compile_bands: bool = False) -> set[Swatch]:
        """
        Merges all connected swatches in the quilt.

        Args:
            compile_merges (bool, optional): If set to True, interstitial swatch merges are compiled to DAT files. Defaults to False.
            compile_bands (bool, optional): If set to True, all bands of merged swatches are compiled to DAT files. Defaults to False.

        Returns:
            set[Swatch]: The set of swatches remaining in the quilt after the merge is complete.
        """
        bands = self.convert_quilt_to_course_bands()
        if compile_bands:
            for band in bands:
                for swatch in band:
                    swatch.compile_to_knitout()
                    swatch.compile_to_dat()
        self._shift_sliced_swatches()
        resets: dict[Swatch, Swatch] = {}
        for band in bands:
            resets.update({s: s for s in band})
        swatch_includes: dict[Swatch: set[Swatch]] = {s: {s} for s in resets}
        for band in bands:
            for swatch in band:
                update_swatch = resets[swatch]
                last_position = update_swatch.carriage_passes[update_swatch.height - 1].last_instruction.needle.position
                included_in_update = swatch_includes[update_swatch]
                # Sort connections by proximity to the last needle position in the swatch being updated.
                top_connections = sorted(self.swatch_neighborhoods[swatch].get_connections_to_courses(exclude_left_connection=True, exclude_right_connections=True, exclude_bottom_connections=True),
                                         key=lambda c: min(abs(c.bottom_left_needle_position - last_position), abs(c.bottom_right_needle_position - last_position)))
                if len(top_connections) > 0:
                    del swatch_includes[update_swatch]
                for top_connection in top_connections:
                    assert isinstance(top_connection, Wale_Wise_Connection)
                    merge_connection = Wale_Wise_Connection(update_swatch, top_connection.top_swatch,
                                                            top_connection.bottom_left_needle_position, top_connection.bottom_right_needle_position,
                                                            top_connection.top_left_needle_position, top_connection.top_right_needle_position,
                                                            remove_cast_ons=True)
                    merger = Wale_Merge_Process(merge_connection)
                    merger.merge_swatches()
                    if compile_merges:
                        merger.compile_to_dat()
                    merged_swatch = Swatch(f"merged_quilt", merger.get_merged_instructions())
                    resets[swatch] = merged_swatch
                    resets[top_connection.top_swatch] = merged_swatch
                    included_in_update.add(merged_swatch)
                    included_in_update.update(swatch_includes[top_connection.top_swatch])
                    del swatch_includes[top_connection.top_swatch]
                    swatch_includes[merged_swatch] = included_in_update
                    update_swatch = merged_swatch
        return set(s for s in swatch_includes)
