"""Module containing the Connection Interval Tree class."""
from typing import cast

from intervaltree import Interval, IntervalTree

from quilt_knit.swatch.Swatch import Swatch
from quilt_knit.swatch.Swatch_Connection import Swatch_Connection


class Connection_Interval_Tree:
    """ A data structure representing an interval of connections between a swatch and its neighbors on a specific side (top, bottom, left, right).

    Attributes:
        source_swatch (Swatch): The swatch that owns these connections.
        interval_tree (IntervalTree): The interval tree representing the spacing of swatch connections.
    """

    def __init__(self, source_swatch: Swatch):
        self.source_swatch: Swatch = source_swatch
        self.interval_tree: IntervalTree = IntervalTree()

    def blocking_connections(self, connection: Swatch_Connection) -> set[Swatch_Connection]:
        """
        A connection blocks connections in this tree if they do not connect the same swatches and the intervals of the connections overlap but do not envelop the given connection.

        Args:
            connection (Swatch_Connection): The other connection that may block connections in tree.

        Returns:
            set[Swatch_Connection]: The set of connections in this tree that are blocked by the given connection.
        """
        overlaps = self.overlapped_intervals(connection)
        enveloped_intervals = self.enveloped_intervals(connection)
        overlaps.difference_update(enveloped_intervals)
        return set(i.data for i in overlaps if not i.data.connects_same_swatches(connection))

    def connection_is_blocked(self, connection: Swatch_Connection) -> bool:
        """
        A connection is blocked by this tree if the following criteria are met:
        * It involves the source swatch of this tree.
        * The connection overlaps, but does not envelop, an existing connection in the tree.

        Args:
            connection (Swatch_Connection): The connection that may be blocked by connections in this tree.

        Returns:
            bool: True if the given connection is blocked, False otherwise.
        """
        if self.source_swatch not in connection:
            return False
        elif self.overlaps_existing_connection(connection):
            enveloped_intervals = self.enveloped_intervals(connection)
            overlaps = self.overlapped_intervals(connection)
            overlaps.difference_update(enveloped_intervals)
            if len(overlaps) > 1:
                return True
            overlapped_connection = [*overlaps][0].data
            return not connection.connects_same_swatches(overlapped_connection)
        else:
            return False

    def interval_sorted_connections(self) -> list[Swatch_Connection]:
        """
        Returns:
             list[Swatch_Connection]: A list of connections sorted by their interval connections to the source swatch.
        """
        return [i.data for i in sorted(self.interval_tree)]

    def _get_source_interval(self, connection: Swatch_Connection) -> Interval:
        """
        Args:
            connection (Swatch_Connection): A connection in the interval tree.

        Returns:
            Interval: The interval on the source-swatch side of the given connection.

        Raises:
            ValueError: If the given connection is not in the interval tree.
        """
        if connection.from_swatch == self.source_swatch:
            return connection.from_interval
        elif connection.to_swatch == self.source_swatch:
            return connection.to_interval
        else:
            raise ValueError(f"{connection} does not involve swatch {self.source_swatch}")

    def make_connection(self, connection: Swatch_Connection) -> None:
        """
        Add the given connection to this connection interval tree.

        Args:
            connection (Swatch_Connection): The connection to add to the interval tree.

        Notes:
            This method does not verify that the connection should be added to the interval tree and does not override or overlap an existing connection.
        """
        interval = self._get_source_interval(connection)
        self.interval_tree[interval.begin: interval.end] = connection

    def remove_connection(self, prior_connection: Swatch_Connection) -> None:
        """
        Remove a given connection from the interval tree.
        Args:
            prior_connection (Swatch_Connection): The connection to remove from the interval tree.
        """
        prior_interval = self._get_source_interval(prior_connection)
        self.interval_tree.discardi(prior_interval.begin, prior_interval.end, data=prior_connection)

    def overlaps_existing_connection(self, connection: Swatch_Connection) -> bool:
        """
        Args:
            connection (Swatch_Connection): The connection to check for overlap with an interval in the tree.

        Returns:
            bool: True if the given connection overlaps with an interval in the tree, False otherwise.
        """
        return bool(self.interval_tree.overlaps(self._get_source_interval(connection)))

    def overlapped_intervals(self, connection: Swatch_Connection) -> set[Interval]:
        """
        Args:
            connection (Swatch_Connection): The connection to check for overlap with an interval in the tree.

        Returns:
            set[Interval]: The set of intervals that overlap the given connection.

        Notes:
            Interval overlaps are inclusive of the lower limit but exclusive of the upper limit.
            I.e., an existing interval will be included in the set if it has a point i such that begin <= i < end.
            The connection of each interval is stored as the interval's data value (i.e., interval.data).
        """
        return cast(set[Interval], self.interval_tree.overlap(self._get_source_interval(connection)))

    def enveloped_intervals(self, connection: Swatch_Connection) -> set[Interval]:
        """
        Args:
            connection (Swatch_Connection): The connection to check for enveloped intervals in the tree.

        Returns:
            set[Interval]: The set of intervals that envelop the given connection.
        """
        return cast(set[Interval], self.interval_tree.envelop(self._get_source_interval(connection)))

    def enveloped_connections(self, connection: Swatch_Connection) -> set[Swatch_Connection]:
        """
        Args:
            connection (Swatch_Connection): The connection that may be enveloped by connections in this tree.

        Returns:
            set[Swatch_Connection]: The set of swatch connections that envelop the given connection.
        """
        return set(i.data for i in self.enveloped_intervals(connection))

    def __hash__(self) -> int:
        """
        Returns:
            int: The hash value of the source swatch.
        """
        return hash(self.source_swatch)

    def __repr__(self) -> str:
        """
        Returns:
            str: A string representation of this connection.
        """
        return str(self.interval_sorted_connections())

    def connections(self) -> set[Swatch_Connection]:
        """
        Returns:
            set[Swatch_Connection]: The set of connections in this interval tree.
        """
        return set(i.data for i in self.interval_tree)
