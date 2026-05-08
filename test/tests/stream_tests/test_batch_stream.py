"""Tests for BatchStream state creation and consistency.

Covers:
    - State creation computes correct start_time, datetime range, and timestamps
    - Different delays produce matching durations
    - Multiple states from the same stream are independent and consistent
"""

import datetime

import pytest

from ethos_penalps.stream import BatchStream, BatchStreamState
from ethos_penalps.testing.stream.stream_test_case import (
    BatchStreamTestComponents,
    make_batch_stream,
)
from ethos_penalps.utilities.general_functions import datetime_to_seconds

T0 = datetime.datetime(year=2024, month=1, day=1, hour=12)
HOUR = datetime.timedelta(hours=1)


class TestBatchStreamStateCreation:
    """Verify create_batch_state computes correct states."""

    def test_start_time_equals_end_minus_delay(self):
        """start_time = end_time - delay."""
        delay = datetime.timedelta(hours=2)
        setup = make_batch_stream(delay=delay)
        state = setup.stream.create_batch_state(
            end_time=T0,
            batch_mass_value=50,
        )
        assert state.start_time == T0 - delay
        assert state.end_time == T0

    def test_datetime_range_set(self):
        setup = make_batch_stream(delay=HOUR)
        state = setup.stream.create_batch_state(
            end_time=T0,
            batch_mass_value=10,
        )
        assert state.date_time_range.start_datetime == state.start_time
        assert state.date_time_range.end_datetime == state.end_time

    def test_timestamp_seconds_computed(self):
        setup = make_batch_stream(delay=HOUR)
        state = setup.stream.create_batch_state(
            end_time=T0,
            batch_mass_value=10,
        )
        assert state.start_time_seconds == pytest.approx(datetime_to_seconds(state.start_time))
        assert state.end_time_seconds == pytest.approx(datetime_to_seconds(state.end_time))


class TestBatchStreamDifferentDelays:
    """Different delay values produce the expected durations."""

    def test_delay_determines_duration(self):
        for delay_hours in [0.5, 1, 2, 6, 24]:
            delay = datetime.timedelta(hours=delay_hours)
            setup = make_batch_stream(delay=delay)
            state = setup.stream.create_batch_state(
                end_time=T0,
                batch_mass_value=50,
            )
            duration = state.end_time - state.start_time
            assert duration == delay


class TestBatchStreamMultipleStates:
    """Multiple states from the same stream are independent and consistent."""

    def test_states_have_same_stream_name(self):
        setup = make_batch_stream()
        s1 = setup.stream.create_batch_state(end_time=T0, batch_mass_value=50)
        s2 = setup.stream.create_batch_state(end_time=T0 + 3 * HOUR, batch_mass_value=30)
        assert s1.name == s2.name

    def test_states_are_independent(self):
        setup = make_batch_stream()
        s1 = setup.stream.create_batch_state(end_time=T0, batch_mass_value=50)
        s2 = setup.stream.create_batch_state(end_time=T0 + 3 * HOUR, batch_mass_value=30)
        assert s1.batch_mass_value == 50
        assert s2.batch_mass_value == 30
        assert s1.end_time != s2.end_time

    def test_different_masses_same_duration(self):
        """Different batch masses don't affect duration (only delay does)."""
        setup = make_batch_stream(delay=HOUR)
        s_small = setup.stream.create_batch_state(end_time=T0, batch_mass_value=10)
        s_large = setup.stream.create_batch_state(end_time=T0, batch_mass_value=100)
        assert (s_small.end_time - s_small.start_time) == (s_large.end_time - s_large.start_time)
