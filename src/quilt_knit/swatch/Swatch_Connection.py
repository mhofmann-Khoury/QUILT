"""The module containing the Swatch_Connection class."""
from __future__ import annotations

from intervaltree import Interval

from quilt_knit.swatch.Swatch import Swatch


class Swatch_Connection:
    """A class used as a super class to wale-wise and course-wise swatch connections for merging."""

    def __init__(self, from_swatch: Swatch, to_swatch: Swatch,
                 from_begin: int, from_end: int,
                 to_begin: int, to_end: int,
                 connection_symbol: str = "->") -> None:
        assert from_begin < from_end, f"from_begin ({from_begin}) must be less than from_end ({from_end} for {from_swatch.name} -> {to_swatch.name})"
        assert to_begin < to_end, f"to_begin ({to_begin}) must be less than to_end ({to_end} for {from_swatch.name} -> {to_swatch.name})"
        self.to_end: int = to_end
        self.to_begin: int = to_begin
        self.from_end: int = from_end
        self.from_begin: int = from_begin
        self.from_swatch: Swatch = from_swatch
        self.to_swatch: Swatch = to_swatch
        self._connection_symbol: str = connection_symbol

    def __hash__(self) -> int:
        """
        Returns:
            int: Hash of the tuple of the from_swatch, to_swatch, from_interval, and to_interval.
        """
        return hash((self.from_swatch, self.to_swatch, self.from_interval, self.to_interval))

    def connects_same_swatches(self, other_connection: Swatch_Connection) -> bool:
        """
        Args:
            other_connection (Swatch_Connection): The other swatch connection to compare to.

        Returns:
            bool: True if this and the other connection connect the same swatches. False, otherwise.
        """
        return self.from_swatch == other_connection.from_swatch and self.to_swatch == other_connection.to_swatch

    def __contains__(self, swatch: Swatch) -> bool:
        """
        Args:
            swatch (Swatch): The swatch to check for in this connection.

        Returns:
            bool: True if the swatch is involved in this connection. False, otherwise.
        """
        return self.from_swatch == swatch or self.to_swatch == swatch

    def __eq__(self, other_connection: Swatch_Connection) -> bool:
        """
        Args:
            other_connection (Swatch_Connection): The other swatch connection to compare to.

        Returns:
            bool: True if other_connection is of the same type and connects the same swatches and has the same intervals. False, otherwise.
        """
        return (self.__class__ == other_connection.__class__
                and self.connects_same_swatches(other_connection)
                and self.from_interval.range_matches(other_connection.from_interval)
                and self.to_interval.range_matches(other_connection.to_interval))

    def __repr__(self) -> str:
        """
        Returns:
            str: The string representation of this connection.
        """
        return str(self)

    def __str__(self) -> str:
        """
        Returns:
            str: The string representation of this connection.
        """
        return f"{self.from_swatch}[{self.from_begin}:{self.from_end}] {self._connection_symbol} {self.to_swatch}[{self.to_begin}:{self.to_end}]"

    @property
    def from_interval(self) -> Interval:
        """
        Returns:
            Interval: The interval of connection on the from-swatch.
        """
        return Interval(self.from_begin, self.from_end, data=self)

    @property
    def to_interval(self) -> Interval:
        """
        Returns:
            Interval: The interval of connection on the to-swatch.
        """
        return Interval(self.to_begin, self.to_end, data=self)

    def _from_range_matches(self, other_connection: Swatch_Connection) -> bool:
        """
        Args:
            other_connection (Swatch_Connection): The other swatch connection to compare to.

        Returns:
            bool: True if the range of needle connections of the from-swatches are identical. False otherwise.

        Notes:
            * This method does not test for equality of the swatches in this and the other connection.
        """
        return bool(self.from_interval.range_matches(other_connection.from_interval))

    def _to_range_matches(self, other_connection: Swatch_Connection) -> bool:
        """
        Args:
            other_connection (Swatch_Connection): The other swatch connection to compare to.

        Returns:
            bool: True if the range of needle connections of the to-swatches are identical. False otherwise.

        Notes:
            * This method does not test for equality of the swatches in this and the other connection.
        """
        return bool(self.to_interval.range_matches(other_connection.to_interval))

    def range_matches(self, other_connection: Swatch_Connection) -> bool:
        """
        Args:
            other_connection (Swatch_Connection): The other swatch connection to compare to.

        Returns:
            bool: True if the range of needle connections to and from intervals are identical. False otherwise.

        Notes:
            * This method does not test for equality of the swatches in this and the other connection.
        """
        return self._from_range_matches(other_connection) and self._to_range_matches(other_connection)

    def _envelops_from(self, other_connection: Swatch_Connection) -> bool:
        """
        Args:
            other_connection (Swatch_Connection): The other swatch connection to compare to.

        Returns:
            bool: True if the range of needle connections of the from-swatch envelops the interval in the other connection. False otherwise.

        Notes:
            * This method does not test for equality of the swatches in this and the other connection.
        """
        return bool(self.from_interval.contains_interval(other_connection.from_interval))

    def _envelops_to(self, other_connection: Swatch_Connection) -> bool:
        """
        Args:
            other_connection (Swatch_Connection): The other swatch connection to compare to.

        Returns:
            bool: True if the range of needle connections of the to-swatch envelops the interval in the other connection. False otherwise.

        Notes:
            * This method does not test for equality of the swatches in this and the other connection.
        """
        return bool(self.to_interval.contains_interval(other_connection.to_interval))

    def envelops(self, other_connection: Swatch_Connection) -> bool:
        """
        Args:
            other_connection (Swatch_Connection): The other swatch connection to compare to.

        Returns:
            bool: True if the range of needle connections of this swatch's intervals envelops the intervals in the other connection. False otherwise.

        Notes:
            * This method does not test for equality of the swatches in this and the other connection.
        """
        return self._envelops_from(other_connection) and self._envelops_to(other_connection)

    def _overlaps_from(self, other_connection: Swatch_Connection) -> bool:
        """
        Args:
            other_connection (Swatch_Connection): The other swatch connection to compare to.

        Returns:
            bool: True if the range of needle connections of the from-swatch overlaps the interval in the other connection. False otherwise.

        Notes:
            * This method does not test for equality of the swatches in this and the other connection.
        """
        if self.from_interval.overlaps(other_connection.from_interval):
            return True
        elif self.from_end == other_connection.from_begin:
            return True
        elif self.from_begin == other_connection.from_end:
            return True
        else:
            return False

    def _overlaps_to(self, other_connection: Swatch_Connection) -> bool:
        """
        Args:
            other_connection (Swatch_Connection): The other swatch connection to compare to.

        Returns:
            bool: True if the range of needle connections of the to-swatch overlaps the interval in the other connection. False otherwise.

        Notes:
            * This method does not test for equality of the swatches in this and the other connection.
        """
        if self.to_interval.overlaps(other_connection.to_interval):
            return True
        elif self.to_end == other_connection.to_begin:
            return True
        elif self.to_begin == other_connection.to_end:
            return True
        else:
            return False

    def overlaps(self, other_connection: Swatch_Connection) -> bool:
        """
        Args:
            other_connection (Swatch_Connection): The other swatch connection to compare to.

        Returns:
            bool: True if the range of needle connections overlaps the intervals in the other connection. False otherwise.

        Notes:
            * This method does not test for equality of the swatches in this and the other connection.
        """
        return self._overlaps_from(other_connection) and self._overlaps_to(other_connection)

    def _touches_from(self, other_connection: Swatch_Connection) -> bool:
        """
        Args:
            other_connection (Swatch_Connection): The other swatch connection to compare to.

        Returns:
            bool: True if the range of needle connections of the from-swatch touches the interval in the other connection. False otherwise.

        Notes:
            * This method does not test for equality of the swatches in this and the other connection.
        """
        return bool(hash(self.from_interval.distance_to(other_connection.from_interval)) <= 1)  # Hash used because interval distance_to returns Number with no explicit cast to int.

    def _touches_to(self, other_connection: Swatch_Connection) -> bool:
        """
        Args:
            other_connection (Swatch_Connection): The other swatch connection to compare to.

        Returns:
            bool: True if the range of needle connections of the to-swatch touches the interval in the other connection. False otherwise.

        Notes:
            * This method does not test for equality of the swatches in this and the other connection.
        """
        return bool(hash(self.to_interval.distance_to(other_connection.to_interval)) <= 1)

    def touches(self, other_connection: Swatch_Connection) -> bool:
        """
        Args:
            other_connection (Swatch_Connection): The other swatch connection to compare to.

        Returns:
            bool: True if the range of needle connections of this connection touches the intervals in the other connection. False otherwise.

        Notes:
            * This method does not test for equality of the swatches in this and the other connection.
        """
        return self._touches_from(other_connection) and self._touches_to(other_connection)

    def _merged_from_interval(self, other_connection: Swatch_Connection) -> Interval:
        """
        Args:
            other_connection (Swatch_Connection): The other connection to merge with.

        Returns:
            Interval: The interval that merges the from-interval of this and the other connection. The data attribute of the new interval includes this swatch connection.

        Notes:
            * This method does not test for equality of the swatches merged into the interval.
            * This method does not test for overlap or gaps between the intervals.
        """
        return Interval(min(self.from_begin, other_connection.from_begin),
                        max(self.from_end, other_connection.from_end),
                        data=self)

    def _merged_to_interval(self, other_connection: Swatch_Connection) -> Interval:
        """
        Args:
            other_connection (Swatch_Connection): The other connection to merge with.

        Returns:
            Interval: The interval that merges the to-interval of this and the other connection. The data attribute of the new interval includes this swatch connection.

        Notes:
            * This method does not test for equality of the swatches merged into the interval.
            * This method does not test for overlap or gaps between the intervals.
        """
        return Interval(min(self.to_begin, other_connection.to_begin),
                        max(self.to_end, other_connection.to_end),
                        data=self)

    def merged_connection(self, other_connection: Swatch_Connection) -> Swatch_Connection:
        """
        Args:
            other_connection (Swatch_Connection): The other connection to merge with.

        Returns:
            Swatch_Connection: The merged swatch connection.

        Raises:
            NotImplementedError: Implemented in subclass.

        Notes:
            * This method does not test for equality of the swatches merged into the interval.
            * This method does not test for overlap or gaps between the intervals.
        """
        raise NotImplemented("Implemented in subclasses")

    def swap_from_swatch(self, new_swatch: Swatch, interval_shift: int = 0) -> Swatch_Connection:
        """
        Args:
            new_swatch (Swatch): The new from swatch in the resulting swatch connection.
            interval_shift (int, optional): The amount to shift the interval by when swapping the from_swatch. Negative will shift the interval down. Defaults to 0.

        Returns:
            Swatch_Connection: A new connection with the same intervals and the from-swatch swapped for the new given swatch.

        Raises:
            NotImplementedError: Implemented in subclass.
        """
        raise NotImplemented("Implemented in subclasses")

    def swap_to_swatch(self, new_swatch: Swatch, interval_shift: int = 0) -> Swatch_Connection:
        """
        Args:
            new_swatch (Swatch): The new to-swatch in the resulting swatch connection.
            interval_shift (int, optional): The amount to shift the interval by when swapping the to_swatch. Negative will shift the interval down. Defaults to 0.

        Returns:
            Swatch_Connection: A new connection with the same intervals and the from-swatch swapped for the new given swatch.

        Raises:
            NotImplementedError: Implemented in subclass.
        """
        raise NotImplemented("Implemented in subclasses")

    def get_shifted_connection(self, from_shift: int = 0, to_shift: int = 0) -> Swatch_Connection:
        """
        Args:
            from_shift (int, optional): The amount to shift the interval by when swapping the from_swatch. Negative will shift the interval down. Defaults to 0.
            to_shift (int, optional): The amount to shift the interval by when swapping the to_swatch. Negative will shift the interval down. Defaults to 0.

        Returns:
            Swatch_Connection: A new connection involving the same swatches with the connection shifted by the given shift values on either side.

        Raises:
            NotImplementedError: Implemented in subclass.
        """
        raise NotImplemented("Implemented in subclasses")

    def swap_matching_swatch(self, new_swatch: Swatch, matching_swatch: Swatch, interval_shift: int = 0) -> Swatch_Connection:
        """

        Args:
            new_swatch (Swatch): The new swatch to swap into the place of the matching swatch.
            matching_swatch (Swatch): The matching swatch to swap out of the connection.
            interval_shift (int, optional): The amount to shift the interval on the matching swatch side. Negative will shift the interval down. Defaults to 0.

        Returns:
            Swatch_Connection:
                The swatch connection formed by swapping the new swatch into place of the matched swatch and shifting it by the given interval.
                If this connection does not contain the matching swatch, this connection is returned unchanged.
        """
        if self.from_swatch is matching_swatch:
            return self.swap_from_swatch(new_swatch, interval_shift)
        elif self.to_swatch is matching_swatch:
            return self.swap_to_swatch(new_swatch, interval_shift)
        else:
            return self

    def update_connection(self, prior_connection: Swatch_Connection | None) -> Swatch_Connection | None:
        """
        Args:
            prior_connection (Swatch_Connection | None): The prior connection to consider replacing this connection with.

        Returns:
            Swatch_Connection | None:
                The connection to replace the prior connection given this connection.
                * If the prior connection is None or does not involve these swatches, this connection is returned unchanged.
                * If the prior connection subsumes this connection, None is returned and no updated connection is needed.
                * If the prior connection overlaps this connection, a connection that merges both connection sis returned.
                * Otherwise, the two connections do not touch and this connection is returned unchanged to replace the prior connection.
        """
        """
        :param prior_connection: The prior connection to consider replacing this connection with. It may be None.
        :return: The connection to replace the prior connection given this connection.
        If there is no prior connection, or it does not involve the same swatches, this connection is given.
        If the prior connection subsumes this connection, None is returned as no updated connection is needed.
        If the prior connection overlaps this connection, a merged interval connection is given to replace both.
        Otherwise, if the two connections to do not touch, this connection is given to replace the prior connection.
        """
        if prior_connection is None:
            return self
        if not self.connects_same_swatches(prior_connection):
            return self  # This does not involve the same swatches, so the prior connection can be ignored.
        if prior_connection.range_matches(self) or prior_connection.envelops(self):
            return None  # No updated connection needed because the prior connection already matches or envelops the new connection range.
        elif self.envelops(prior_connection):
            return self  # Update to the new connection because the prior connection is subsumed by it.
        elif self.touches(prior_connection) or self.overlaps(prior_connection):
            return self.merged_connection(prior_connection)  # Merge the overlapping connections into one unified interval.
        else:
            return self  # The prior connection does not touch this connection, it will need to be replaced.
