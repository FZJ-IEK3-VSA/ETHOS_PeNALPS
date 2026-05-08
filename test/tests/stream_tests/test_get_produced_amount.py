"""Tests that get_produced_amount returns correct values after removing isinstance checks.

Verifies that BatchStream.get_produced_amount and ContinuousStream.get_produced_amount
return identical results to the original implementation which included isinstance guards.
"""

import datetime

import datetimerange
import pytest

from ethos_penalps.data_classes import Commodity
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamState,
    BatchStreamStaticData,
    ContinuousStream,
    ContinuousStreamState,
    ContinuousStreamStaticData,
)
from ethos_penalps.utilities.units import Units

START = datetime.datetime(2023, 1, 1)
END = datetime.datetime(2023, 1, 2)
DATE_RANGE = datetimerange.DateTimeRange(START, END)
STREAM_NAME = "Source_Sink_Steel"


@pytest.fixture
def batch_stream():
    commodity = Commodity(name="Steel")
    static_data = BatchStreamStaticData(
        start_process_step_name="Source",
        end_process_step_name="Sink",
        commodity=commodity,
        name_to_display="Test Batch Stream",
        mass_unit=str(Units.mass_unit),
        delay=datetime.timedelta(hours=1),
        minimum_batch_mass_value=0,
        maximum_batch_mass_value=1000,
    )
    return BatchStream(static_data=static_data)


@pytest.fixture
def continuous_stream():
    commodity = Commodity(name="Steel")
    static_data = ContinuousStreamStaticData(
        start_process_step_name="Source",
        end_process_step_name="Sink",
        commodity=commodity,
        name_to_display="Test Continuous Stream",
        mass_unit=str(Units.mass_unit),
        minimum_operation_rate=0,
        maximum_operation_rate=100,
        operation_rate_unit=str(Units.mass_throughput_rate),
    )
    return ContinuousStream(static_data=static_data)


def _batch_state(mass):
    return BatchStreamState(
        name=STREAM_NAME,
        start_time=START,
        end_time=END,
        date_time_range=DATE_RANGE,
        batch_mass_value=mass,
    )


def _continuous_state(mass, rate=10.0):
    return ContinuousStreamState(
        name=STREAM_NAME,
        start_time=START,
        end_time=END,
        date_time_range=DATE_RANGE,
        total_mass=mass,
        current_operation_rate=rate,
    )


class TestBatchStreamGetProducedAmount:
    """Tests for BatchStream.get_produced_amount without isinstance check."""

    def test_returns_batch_mass_value(self, batch_stream):
        assert batch_stream.get_produced_amount(state=_batch_state(500.0)) == 500.0

    def test_zero_mass(self, batch_stream):
        assert batch_stream.get_produced_amount(state=_batch_state(0.0)) == 0.0

    def test_negative_mass(self, batch_stream):
        assert batch_stream.get_produced_amount(state=_batch_state(-100.0)) == -100.0

    def test_large_mass(self, batch_stream):
        assert batch_stream.get_produced_amount(state=_batch_state(1e12)) == 1e12

    def test_multiple_states_return_correct_values(self, batch_stream):
        """Verify that different states return their own batch_mass_value."""
        for mass in [100.0, 200.5, 0.0, 999.99, 1.0]:
            assert batch_stream.get_produced_amount(state=_batch_state(mass)) == mass

    def test_wrong_type_raises_attribute_error(self, batch_stream):
        """After removing isinstance, passing wrong type raises AttributeError
        since batch_mass_value won't exist on a string."""
        with pytest.raises(AttributeError):
            batch_stream.get_produced_amount(state="not_a_state")


class TestContinuousStreamGetProducedAmount:
    """Tests for ContinuousStream.get_produced_amount without isinstance check."""

    def test_returns_total_mass(self, continuous_stream):
        assert continuous_stream.get_produced_amount(state=_continuous_state(750.0)) == 750.0

    def test_zero_mass(self, continuous_stream):
        assert continuous_stream.get_produced_amount(state=_continuous_state(0.0, rate=0.0)) == 0.0

    def test_multiple_states_return_correct_values(self, continuous_stream):
        """Verify that different states return their own total_mass."""
        for mass in [100.0, 200.5, 0.0, 999.99, 1.0]:
            assert continuous_stream.get_produced_amount(state=_continuous_state(mass)) == mass

    def test_wrong_type_raises_attribute_error(self, continuous_stream):
        """After removing isinstance, passing wrong type raises AttributeError
        since total_mass won't exist on a string."""
        with pytest.raises(AttributeError):
            continuous_stream.get_produced_amount(state="not_a_state")
