"""Tests for datetime_to_seconds and seconds_to_datetime.

Covers:
    - Round-trip consistency (datetime -> seconds -> datetime)
    - DST-independent behavior: same wall-clock time yields same seconds
      regardless of whether it falls in summer or winter time
    - Microsecond precision is preserved
    - Known UTC epoch values
"""

import datetime

import pytest

from ethos_penalps.utilities.general_functions import (
    datetime_to_seconds,
    seconds_to_datetime,
)

# Dates chosen to fall on opposite sides of a CET DST boundary
# (last Sunday of March / last Sunday of October)
WINTER = datetime.datetime(2024, 1, 15, 12, 0, 0)  # CET (UTC+1)
SUMMER = datetime.datetime(2024, 7, 15, 12, 0, 0)  # CEST (UTC+2)


class TestDatetimeToSecondsRoundTrip:
    """datetime_to_seconds and seconds_to_datetime are exact inverses."""

    @pytest.mark.parametrize(
        "dt",
        [
            datetime.datetime(2024, 1, 1, 0, 0, 0),
            datetime.datetime(2024, 6, 15, 14, 30, 0),
            datetime.datetime(2024, 3, 31, 2, 30, 0),  # during CET->CEST switch
            datetime.datetime(2024, 10, 27, 2, 30, 0),  # during CEST->CET switch
            datetime.datetime(1970, 1, 1, 0, 0, 0),  # epoch
        ],
    )
    def test_round_trip(self, dt: datetime.datetime):
        seconds = datetime_to_seconds(dt)
        recovered = seconds_to_datetime(seconds)
        assert recovered == dt


class TestDSTIndependence:
    """Conversion must not depend on the local timezone's DST state."""

    def test_same_hour_same_offset(self):
        """Two dates at the same wall-clock hour that straddle a DST boundary
        must differ by exactly the number of days between them, not +-1 hour."""
        diff_seconds = datetime_to_seconds(SUMMER) - datetime_to_seconds(WINTER)
        diff_days = (SUMMER - WINTER).total_seconds() / 86400
        assert diff_seconds == diff_days * 86400

    def test_one_hour_step_across_spring_dst(self):
        """Stepping one hour across the CET spring-forward boundary (2024-03-31 02:00)
        must always produce exactly 3600 seconds."""
        before = datetime.datetime(2024, 3, 31, 1, 30, 0)
        after = datetime.datetime(2024, 3, 31, 2, 30, 0)
        assert datetime_to_seconds(after) - datetime_to_seconds(before) == 3600

    def test_one_hour_step_across_autumn_dst(self):
        """Stepping one hour across the CET fall-back boundary (2024-10-27 03:00)
        must always produce exactly 3600 seconds."""
        before = datetime.datetime(2024, 10, 27, 2, 0, 0)
        after = datetime.datetime(2024, 10, 27, 3, 0, 0)
        assert datetime_to_seconds(after) - datetime_to_seconds(before) == 3600


class TestKnownEpochValues:
    """Verify against hand-computed UTC timestamps."""

    def test_unix_epoch(self):
        assert datetime_to_seconds(datetime.datetime(1970, 1, 1, 0, 0, 0)) == 0.0

    def test_known_utc_timestamp(self):
        # 2024-01-01 00:00:00 UTC = 1704067200
        assert datetime_to_seconds(datetime.datetime(2024, 1, 1, 0, 0, 0)) == 1704067200.0


class TestMicrosecondPrecision:
    """Microseconds must survive the round trip."""

    def test_microseconds_preserved(self):
        dt = datetime.datetime(2024, 6, 15, 10, 30, 45, 123456)
        seconds = datetime_to_seconds(dt)
        recovered = seconds_to_datetime(seconds)
        assert recovered == dt

    def test_fractional_seconds(self):
        dt = datetime.datetime(2024, 1, 1, 0, 0, 0, 500000)  # half a second
        seconds = datetime_to_seconds(dt)
        assert seconds == pytest.approx(1704067200.5)
