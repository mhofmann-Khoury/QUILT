"""The Module containing the Swatch_Neighborhood class."""
from quilt_knit.quilt.Connection_Interval_Tree import Connection_Interval_Tree
from quilt_knit.swatch.course_wise_merging.Course_Wise_Connection import (
    Course_Wise_Connection,
)
from quilt_knit.swatch.Swatch import Swatch
from quilt_knit.swatch.Swatch_Connection import Swatch_Connection
from quilt_knit.swatch.wale_wise_merging.Wale_Wise_Connection import (
    Wale_Wise_Connection,
)


class Swatch_Neighborhood:
    """A data structure organizing the interval trees of course and wale wise connections to a specific swatch.

    Attributes:
        swatch (Swatch): The swatch at the center of this neighborhood.
        intervals_to_left (Connection_Interval_Tree): The intervals of connections on the left of the swatch.
        intervals_to_right (Connection_Interval_Tree): The intervals of connections on the right of the swatch.
        intervals_below (Connection_Interval_Tree): The intervals of connections below the swatch.
        intervals_above (Connection_Interval_Tree): The intervals of connections above the swatch.
    """

    def __init__(self, swatch: Swatch):
        self.swatch: Swatch = swatch
        self.intervals_to_left: Connection_Interval_Tree = Connection_Interval_Tree(self.swatch)
        self.intervals_to_right: Connection_Interval_Tree = Connection_Interval_Tree(self.swatch)
        self.intervals_below: Connection_Interval_Tree = Connection_Interval_Tree(self.swatch)
        self.intervals_above: Connection_Interval_Tree = Connection_Interval_Tree(self.swatch)

    def get_all_connections(self) -> set[Swatch_Connection]:
        """
        Returns:
            set[Swatch_Connection]: The set of all connections in this swatch neighborhood.
        """
        connections = self.intervals_to_left.connections()
        connections.update(self.intervals_to_right.connections())
        connections.update(self.intervals_above.connections())
        connections.update(self.intervals_below.connections())
        return connections

    def get_connections_to_courses(self, lower_course: int = 0, upper_course: int | None = None,
                                   exclude_right_connections: bool = False,
                                   exclude_left_connection: bool = False,
                                   exclude_bottom_connections: bool = False,
                                   exclude_top_connections: bool = False) -> set[Swatch_Connection]:
        """
        Args:
            lower_course (int, optional): The lowest course to find connections to. If this is 0, the connections will include bottom wale-wise connections. Defaults to 0.
            upper_course (int, optional):
                The highest course to find connections to. If this is the height of the swatch, the connections will include top wale-wise connections. Defaults to the height of the swatch.
            exclude_right_connections (bool, optional): Whether to exclude course-wise connections to the right of the swatch. Defaults to False.
            exclude_left_connection (bool, optional): Whether to exclude course-wise connections to the left of the swatch. Defaults to False.
            exclude_bottom_connections (bool, optional): Whether to exclude connections to the bottom of the swatch. Defaults to False.:
            exclude_top_connections (bool, optional): Whether to exclude connections to the top of the swatch. Defaults to False.

        Returns:
            set[Swatch_Connection]: The set of all connections in this swatch neighborhood that match the given specification.
        """
        if upper_course is None:
            upper_course = self.swatch.height
        lower_course = max(lower_course, 0)
        upper_course = min(upper_course, self.swatch.height)
        connections: set[Swatch_Connection] = set()
        if not exclude_top_connections and upper_course >= (self.swatch.height - 1):  # Do this before skipping out on mismatch lower and upper courses
            connections.update(i.data for i in self.intervals_above.interval_tree)
        if lower_course > upper_course:
            return connections
        if not exclude_left_connection:
            left_intervals = self.intervals_to_left.interval_tree[lower_course:upper_course]
            connections.update(i.data for i in left_intervals)
        if not exclude_right_connections:
            right_intervals = self.intervals_to_right.interval_tree[lower_course:upper_course]
            connections.update(i.data for i in right_intervals)
        if not exclude_bottom_connections and lower_course == 0:
            connections.update(i.data for i in self.intervals_below.interval_tree)
        return connections

    def get_interval_tree(self, connection: Swatch_Connection) -> Connection_Interval_Tree:
        """
        Args:
            connection (Swatch_Connection): The connection to find the interval tree for.

        Returns:
            Connection_Interval_Tree: The interval_tree associated with the given connection.

        Raises:
            ValueError: If the given connection is not in this swatch neighborhood.
        """
        if self.swatch not in connection:
            raise ValueError(f"{connection} is not in the swatch neighborhood of Swatch {self.swatch}")
        if isinstance(connection, Course_Wise_Connection):
            if connection.left_swatch == self.swatch:
                return self.intervals_to_right
            elif connection.right_swatch == self.swatch:
                return self.intervals_to_left
            else:
                raise ValueError(f"{connection} is not in the swatch neighborhood of Swatch {self.swatch}")
        else:
            assert isinstance(connection, Wale_Wise_Connection)
            if connection.bottom_swatch == self.swatch:
                return self.intervals_above
            elif connection.top_swatch == self.swatch:
                return self.intervals_below
            else:
                raise ValueError(f"{connection} is not in the swatch neighborhood of Swatch {self.swatch}")

    def enveloped_connections(self, connection: Swatch_Connection) -> set[Swatch_Connection]:
        """
        Args:
            connection [Swatch_Connection]: The swatch connection in the neighborhood to get the enveloped by the given connection.

        Returns:
            set[Swatch_Connection]: The set of connections that are enveloped by the given connection.
        """
        return self.get_interval_tree(connection).enveloped_connections(connection)

    def blocking_connections(self, connection: Swatch_Connection) -> set[Swatch_Connection]:
        """
        A connection blocks connections in the neighborhood if they do not connect the same swatches and the intervals of the connections overlap but do not envelop the given connection.

        Args:
            connection [Swatch_Connection]: The swatch connection in the neighborhood to get the enveloped by the given connection.

        Returns:
            set[Swatch_Connection]: The set of connections in this neighborhood that are blocked by the given connection.
        """
        return self.get_interval_tree(connection).blocking_connections(connection)

    def remove_connection(self, prior_connection: Swatch_Connection) -> None:
        """
        Remove a given connection from the swatch's neighborhood if the connection exists in the neighborhood.

        Args:
            prior_connection (Swatch_Connection): The connection to remove, if present.
        """
        try:
            self.get_interval_tree(prior_connection).remove_connection(prior_connection)
        except ValueError:
            pass

    def make_connection(self, connection: Swatch_Connection) -> None:
        """
        Add the given connection to this neighborhood.

        Args:
            connection (Swatch_Connection): The connection to add to the swatch neighborhood tree.

        Notes:
            This method does not verify that the connection should be added to the neighborhood and does not override or overlap an existing connection.
        """
        interval_tree = self.get_interval_tree(connection)
        if interval_tree is not None:
            self.get_interval_tree(connection).make_connection(connection)
