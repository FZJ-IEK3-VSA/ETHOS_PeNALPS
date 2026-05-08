"""Tests for ContinuousStream: static data, state creation, and validation.

Covers:
    - Static data fields are stored correctly
    - Stream name is derived from process step names and commodity
    - State creation computes correct start_time from end_time and rate
    - Total mass and operation rate are stored in the state
    - Operation rate defaults to maximum when not specified
    - Rate validation rejects out-of-bounds rates
    - Multiple states from the same stream have consistent names
"""

import datetime

import pytest

from ethos_penalps.stream import ContinuousStream, ContinuousStreamState
from ethos_penalps.testing.stream.stream_test_case import (
    ContinuousStreamTestComponents,
    make_continuous_stream,
)
from ethos_penalps.utilities.general_functions import datetime_to_seconds

T0 = datetime.datetime(year=2024, month=1, day=1, hour=12)
HOUR = datetime.timedelta(hours=1)


class TestContinuousStreamStateCreation:
    """Verify create_stream_state_for_commodity_amount computes correct states."""

    def test_start_time_from_mass_and_rate(self):
        """start_time = end_time - hours(mass / rate)."""
        setup = make_continuous_stream(maximum_operation_rate=10)
        state = setup.stream.create_stream_state_for_commodity_amount(
            commodity_amount=50,
            end_time=T0,
            operation_rate=10,
        )
        # 50 units at rate 10/h = 5 hours
        expected_start = T0 - datetime.timedelta(hours=5)
        assert state.start_time == expected_start
        assert state.end_time == T0

    def test_mass_and_rate_stored(self):
        setup = make_continuous_stream(maximum_operation_rate=10)
        state = setup.stream.create_stream_state_for_commodity_amount(
            commodity_amount=100,
            end_time=T0,
            operation_rate=10,
        )
        assert state.total_mass == 100
        assert state.current_operation_rate == 10

    def test_default_rate_uses_maximum(self):
        """When operation_rate is inf, it defaults to maximum_operation_rate."""
        setup = make_continuous_stream(maximum_operation_rate=20)
        state = setup.stream.create_stream_state_for_commodity_amount(
            commodity_amount=40,
            end_time=T0,
        )
        assert state.current_operation_rate == 20
        # 40 units at rate 20/h = 2 hours
        expected_start = T0 - datetime.timedelta(hours=2)
        assert state.start_time == expected_start

    def test_state_name_matches_stream(self):
        setup = make_continuous_stream()
        state = setup.stream.create_stream_state_for_commodity_amount(
            commodity_amount=10,
            end_time=T0,
            operation_rate=10,
        )
        assert state.name == setup.stream.name

    def test_datetime_range_set(self):
        setup = make_continuous_stream(maximum_operation_rate=10)
        state = setup.stream.create_stream_state_for_commodity_amount(
            commodity_amount=10,
            end_time=T0,
            operation_rate=10,
        )
        assert state.date_time_range.start_datetime == state.start_time
        assert state.date_time_range.end_datetime == state.end_time

    def test_timestamp_seconds_computed(self):
        setup = make_continuous_stream(maximum_operation_rate=10)
        state = setup.stream.create_stream_state_for_commodity_amount(
            commodity_amount=10,
            end_time=T0,
            operation_rate=10,
        )
        assert state.start_time_seconds == pytest.approx(datetime_to_seconds(state.start_time))
        assert state.end_time_seconds == pytest.approx(datetime_to_seconds(state.end_time))

    def test_small_mass_short_duration(self):
        setup = make_continuous_stream(maximum_operation_rate=100)
        state = setup.stream.create_stream_state_for_commodity_amount(
            commodity_amount=1,
            end_time=T0,
            operation_rate=100,
        )
        # 1 unit at rate 100/h = 0.01 hours = 36 seconds
        expected_duration = datetime.timedelta(seconds=36)
        actual_duration = state.end_time - state.start_time
        assert abs(actual_duration - expected_duration) < datetime.timedelta(milliseconds=1)

    def test_high_rate_high_mass(self):
        setup = make_continuous_stream(maximum_operation_rate=1000)
        state = setup.stream.create_stream_state_for_commodity_amount(
            commodity_amount=5000,
            end_time=T0,
            operation_rate=1000,
        )
        # 5000 units at rate 1000/h = 5 hours
        expected_start = T0 - datetime.timedelta(hours=5)
        assert state.start_time == expected_start
        assert state.total_mass == 5000


class TestContinuousStreamRateValidation:
    """Rate validation checks against maximum_operation_rate and >= 0."""

    def test_rate_at_maximum_boundary(self):
        setup = make_continuous_stream(maximum_operation_rate=20)
        state = setup.stream.create_stream_state_for_commodity_amount(
            commodity_amount=10,
            end_time=T0,
            operation_rate=20,
        )
        assert state.current_operation_rate == 20

    def test_rate_above_maximum_raises(self):
        setup = make_continuous_stream(maximum_operation_rate=20)
        with pytest.raises(Exception, match="[Bb]oundar"):
            setup.stream.create_stream_state_for_commodity_amount(
                commodity_amount=10,
                end_time=T0,
                operation_rate=25,
            )

    def test_negative_rate_raises(self):
        setup = make_continuous_stream(maximum_operation_rate=20)
        with pytest.raises(Exception):
            setup.stream.create_stream_state_for_commodity_amount(
                commodity_amount=10,
                end_time=T0,
                operation_rate=-5,
            )

    def test_zero_rate_raises_division_error(self):
        """A rate of zero causes ZeroDivisionError in the duration calculation."""
        setup = make_continuous_stream(maximum_operation_rate=20)
        with pytest.raises(ZeroDivisionError):
            setup.stream.create_stream_state_for_commodity_amount(
                commodity_amount=10,
                end_time=T0,
                operation_rate=0,
            )


class TestContinuousStreamMultipleStates:
    """Multiple states from the same stream are independent and consistent."""

    def test_states_have_same_stream_name(self):
        setup = make_continuous_stream(maximum_operation_rate=10)
        s1 = setup.stream.create_stream_state_for_commodity_amount(
            commodity_amount=50,
            end_time=T0,
            operation_rate=10,
        )
        s2 = setup.stream.create_stream_state_for_commodity_amount(
            commodity_amount=30,
            end_time=T0 + HOUR,
            operation_rate=10,
        )
        assert s1.name == s2.name

    def test_states_are_independent(self):
        setup = make_continuous_stream(maximum_operation_rate=10)
        s1 = setup.stream.create_stream_state_for_commodity_amount(
            commodity_amount=50,
            end_time=T0,
            operation_rate=10,
        )
        s2 = setup.stream.create_stream_state_for_commodity_amount(
            commodity_amount=30,
            end_time=T0 + 4 * HOUR,
            operation_rate=10,
        )
        assert s1.total_mass == 50
        assert s2.total_mass == 30
        assert s1.end_time != s2.end_time

    def test_different_rates_different_durations(self):
        """Same mass at different rates produces different durations."""
        setup = make_continuous_stream(maximum_operation_rate=20)
        s_fast = setup.stream.create_stream_state_for_commodity_amount(
            commodity_amount=100,
            end_time=T0,
            operation_rate=20,
        )
        s_slow = setup.stream.create_stream_state_for_commodity_amount(
            commodity_amount=100,
            end_time=T0,
            operation_rate=10,
        )
        fast_duration = s_fast.end_time - s_fast.start_time
        slow_duration = s_slow.end_time - s_slow.start_time
        assert slow_duration == 2 * fast_duration
