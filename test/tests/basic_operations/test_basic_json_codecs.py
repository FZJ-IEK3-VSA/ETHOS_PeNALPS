"""Round-trip tests for the JSON codec functions in json_coding_functions.py.

Each codec function is tested independently: serialization followed by
deserialization must reproduce the original value exactly.

These tests caught two bugs that existed before this file was added:
  - json_datetime_range_deserialization_function used "start_datetime" key
    for both start and end, so end_datetime was always equal to start_datetime.
  - json_pint_unit_deserialization_function called json.load (file object)
    instead of json.loads (string), raising TypeError on every call.
"""

import datetime

import datetimerange
import pytest

from ethos_penalps.utilities.json_coding_functions import (
    json_datetime_deserialization_function,
    json_datetime_range_deserialization_function,
    json_datetime_range_serialization_function,
    json_datetime_serialization_function,
    json_pint_unit_deserialization_function,
    json_pint_unit_serialization_function,
    json_timedelta_deserialization_function,
    json_timedelta_serialization_function,
)
from ethos_penalps.utilities.units import Units

T0 = datetime.datetime(2024, 3, 15, 10, 30, 0)
T1 = datetime.datetime(2024, 3, 15, 14, 45, 59, 123456)


class TestDatetimeCodec:
    def test_roundtrip_basic(self):
        serialized = json_datetime_serialization_function(T0)
        assert json_datetime_deserialization_function(serialized) == T0

    def test_roundtrip_with_microseconds(self):
        serialized = json_datetime_serialization_function(T1)
        assert json_datetime_deserialization_function(serialized) == T1

    def test_serialized_form_is_isoformat(self):
        serialized = json_datetime_serialization_function(T0)
        assert serialized == T0.isoformat()

    def test_roundtrip_midnight(self):
        dt = datetime.datetime(2000, 1, 1, 0, 0, 0)
        assert json_datetime_deserialization_function(json_datetime_serialization_function(dt)) == dt


class TestTimedeltaCodec:
    @pytest.mark.parametrize(
        "delta",
        [
            datetime.timedelta(hours=1),
            datetime.timedelta(days=2, hours=3, minutes=15, seconds=30),
            datetime.timedelta(seconds=0),
            datetime.timedelta(milliseconds=500),
            datetime.timedelta(days=365),
        ],
    )
    def test_roundtrip(self, delta):
        serialized = json_timedelta_serialization_function(delta)
        recovered = json_timedelta_deserialization_function(serialized)
        assert recovered == delta

    def test_serialized_form_is_total_seconds(self):
        delta = datetime.timedelta(hours=2, minutes=30)
        serialized = json_timedelta_serialization_function(delta)
        assert serialized == pytest.approx(delta.total_seconds())


class TestDatetimeRangeCodec:
    """Tests for the DateTimeRange codec — previously broken by a copy-paste bug
    that set end_datetime = start_datetime on every deserialization."""

    def test_roundtrip_preserves_start(self):
        dtr = datetimerange.DateTimeRange(start_datetime=T0, end_datetime=T1)
        serialized = json_datetime_range_serialization_function(dtr)
        recovered = json_datetime_range_deserialization_function(serialized)
        assert recovered.start_datetime == T0

    def test_roundtrip_preserves_end(self):
        """This is the field that was previously always set to start_datetime."""
        dtr = datetimerange.DateTimeRange(start_datetime=T0, end_datetime=T1)
        serialized = json_datetime_range_serialization_function(dtr)
        recovered = json_datetime_range_deserialization_function(serialized)
        assert recovered.end_datetime == T1

    def test_start_and_end_differ(self):
        dtr = datetimerange.DateTimeRange(start_datetime=T0, end_datetime=T1)
        serialized = json_datetime_range_serialization_function(dtr)
        recovered = json_datetime_range_deserialization_function(serialized)
        assert recovered.start_datetime != recovered.end_datetime

    def test_roundtrip_same_day(self):
        start = datetime.datetime(2022, 6, 1, 8, 0)
        end = datetime.datetime(2022, 6, 1, 20, 0)
        dtr = datetimerange.DateTimeRange(start_datetime=start, end_datetime=end)
        serialized = json_datetime_range_serialization_function(dtr)
        recovered = json_datetime_range_deserialization_function(serialized)
        assert recovered.start_datetime == start
        assert recovered.end_datetime == end

    def test_serialized_form_is_json_string(self):
        import json

        dtr = datetimerange.DateTimeRange(start_datetime=T0, end_datetime=T1)
        serialized = json_datetime_range_serialization_function(dtr)
        parsed = json.loads(serialized)
        assert "start_datetime" in parsed
        assert "end_datetime" in parsed


class TestPintUnitCodec:
    """Tests for the pint.Unit codec — previously broken by json.load vs json.loads."""

    @pytest.mark.parametrize(
        "unit",
        [
            Units.mass_unit,
            Units.energy_unit,
            Units.power_unit,
            Units.time_unit,
            Units.mass_throughput_rate,
        ],
    )
    def test_roundtrip(self, unit):
        serialized = json_pint_unit_serialization_function(unit)
        recovered = json_pint_unit_deserialization_function(serialized)
        assert recovered == unit

    def test_serialized_form_is_json_string(self):
        import json

        serialized = json_pint_unit_serialization_function(Units.mass_unit)
        parsed = json.loads(serialized)
        assert "unit" in parsed
