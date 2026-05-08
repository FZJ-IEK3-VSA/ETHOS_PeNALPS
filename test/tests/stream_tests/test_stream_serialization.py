"""Round-trip serialization tests for stream states and StreamHandler.

Tests that to_json()/from_json() and json_dumps_streams()/json_loads_streams()
correctly preserve all field values after a full serialization round-trip.

The DateTimeRange codec bug (end always equalled start before the fix) would
cause many of these assertions to fail; they serve as regression guards.
"""

import datetime
import json
import tempfile
from pathlib import Path

import pytest

from ethos_penalps.stream import BatchStreamState, ContinuousStreamState
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.testing.stream.stream_test_case import make_batch_stream, make_continuous_stream

T0 = datetime.datetime(2024, 1, 15, 8, 0, 0)
HOUR = datetime.timedelta(hours=1)
HALF_DAY = datetime.timedelta(hours=12)


# ---------------------------------------------------------------------------
# BatchStreamState round-trip
# ---------------------------------------------------------------------------


class TestBatchStreamStateJsonRoundtrip:
    """BatchStreamState.to_json() → BatchStreamState.from_json() preserves all fields."""

    @pytest.fixture
    def state(self) -> BatchStreamState:
        setup = make_batch_stream(delay=HALF_DAY, maximum_batch_mass_value=200)
        return setup.stream.create_batch_state(end_time=T0, batch_mass_value=150)

    def test_name_preserved(self, state):
        recovered = BatchStreamState.from_json(state.to_json())
        assert recovered.name == state.name

    def test_start_time_preserved(self, state):
        recovered = BatchStreamState.from_json(state.to_json())
        assert recovered.start_time == state.start_time

    def test_end_time_preserved(self, state):
        recovered = BatchStreamState.from_json(state.to_json())
        assert recovered.end_time == state.end_time

    def test_start_and_end_differ(self, state):
        """Regression: DateTimeRange bug caused end_time to equal start_time after round-trip."""
        recovered = BatchStreamState.from_json(state.to_json())
        assert recovered.start_time != recovered.end_time

    def test_datetime_range_start_preserved(self, state):
        recovered = BatchStreamState.from_json(state.to_json())
        assert recovered.date_time_range.start_datetime == state.start_time

    def test_datetime_range_end_preserved(self, state):
        """Regression: DateTimeRange bug caused end_datetime to always equal start_datetime."""
        recovered = BatchStreamState.from_json(state.to_json())
        assert recovered.date_time_range.end_datetime == state.end_time

    def test_batch_mass_preserved(self, state):
        recovered = BatchStreamState.from_json(state.to_json())
        assert recovered.batch_mass_value == state.batch_mass_value

    def test_computed_start_time_seconds(self, state):
        recovered = BatchStreamState.from_json(state.to_json())
        assert recovered.start_time_seconds == pytest.approx(state.start_time_seconds)

    def test_computed_end_time_seconds(self, state):
        recovered = BatchStreamState.from_json(state.to_json())
        assert recovered.end_time_seconds == pytest.approx(state.end_time_seconds)

    def test_duration_preserved(self, state):
        recovered = BatchStreamState.from_json(state.to_json())
        assert (recovered.end_time - recovered.start_time) == HALF_DAY

    def test_json_is_valid_json_string(self, state):
        json_str = state.to_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# ContinuousStreamState round-trip
# ---------------------------------------------------------------------------


class TestContinuousStreamStateJsonRoundtrip:
    """ContinuousStreamState.to_json() → ContinuousStreamState.from_json() preserves all fields."""

    @pytest.fixture
    def state(self) -> ContinuousStreamState:
        setup = make_continuous_stream(maximum_operation_rate=20)
        return setup.stream.create_stream_state_for_commodity_amount(
            end_time=T0,
            commodity_amount=100,
            operation_rate=10,
        )

    def test_name_preserved(self, state):
        recovered = ContinuousStreamState.from_json(state.to_json())
        assert recovered.name == state.name

    def test_start_time_preserved(self, state):
        recovered = ContinuousStreamState.from_json(state.to_json())
        assert recovered.start_time == state.start_time

    def test_end_time_preserved(self, state):
        recovered = ContinuousStreamState.from_json(state.to_json())
        assert recovered.end_time == state.end_time

    def test_start_and_end_differ(self, state):
        """Regression: DateTimeRange bug caused end_time to equal start_time after round-trip."""
        recovered = ContinuousStreamState.from_json(state.to_json())
        assert recovered.start_time != recovered.end_time

    def test_datetime_range_start_preserved(self, state):
        recovered = ContinuousStreamState.from_json(state.to_json())
        assert recovered.date_time_range.start_datetime == state.start_time

    def test_datetime_range_end_preserved(self, state):
        """Regression: DateTimeRange bug caused end_datetime to always equal start_datetime."""
        recovered = ContinuousStreamState.from_json(state.to_json())
        assert recovered.date_time_range.end_datetime == state.end_time

    def test_total_mass_preserved(self, state):
        recovered = ContinuousStreamState.from_json(state.to_json())
        assert recovered.total_mass == pytest.approx(state.total_mass)

    def test_operation_rate_preserved(self, state):
        recovered = ContinuousStreamState.from_json(state.to_json())
        assert recovered.current_operation_rate == pytest.approx(state.current_operation_rate)

    def test_computed_start_time_seconds(self, state):
        recovered = ContinuousStreamState.from_json(state.to_json())
        assert recovered.start_time_seconds == pytest.approx(state.start_time_seconds)

    def test_computed_end_time_seconds(self, state):
        recovered = ContinuousStreamState.from_json(state.to_json())
        assert recovered.end_time_seconds == pytest.approx(state.end_time_seconds)


# ---------------------------------------------------------------------------
# BatchStream.json_dumps_state / json_load_state (file round-trip)
# ---------------------------------------------------------------------------


class TestBatchStreamStatFileRoundtrip:
    """BatchStream.json_dumps_state() → file → json_load_state() preserves all fields."""

    def test_file_roundtrip(self, tmp_path):
        setup = make_batch_stream(delay=HOUR, maximum_batch_mass_value=300)
        state = setup.stream.create_batch_state(end_time=T0, batch_mass_value=200)

        setup.stream.json_dumps_state(stream_state=state, path_to_save_folder=str(tmp_path))

        state_file = tmp_path / f"{state.name}.json"
        assert state_file.exists()

        recovered = setup.stream.json_load_state(path_to_file=str(state_file))

        assert recovered.name == state.name
        assert recovered.start_time == state.start_time
        assert recovered.end_time == state.end_time
        assert recovered.batch_mass_value == state.batch_mass_value
        assert recovered.date_time_range.start_datetime == state.start_time
        assert recovered.date_time_range.end_datetime == state.end_time


# ---------------------------------------------------------------------------
# StreamHandler JSON round-trip (in-memory)
# ---------------------------------------------------------------------------


class TestStreamHandlerJsonRoundtrip:
    """StreamHandler.json_dumps_streams() → json_loads_streams() reconstructs all streams."""

    def test_continuous_stream_registered(self):
        setup = make_continuous_stream(
            start_process_step_name="A",
            end_process_step_name="B",
            commodity_name="Steel",
        )
        json_str = setup.stream_handler.json_dumps_streams()

        new_handler = StreamHandler()
        new_handler.json_loads_streams(json_str)

        assert setup.stream.name in new_handler.stream_dict

    def test_batch_stream_registered(self):
        setup = make_batch_stream(
            start_process_step_name="X",
            end_process_step_name="Y",
            commodity_name="Coal",
        )
        json_str = setup.stream_handler.json_dumps_streams()

        new_handler = StreamHandler()
        new_handler.json_loads_streams(json_str)

        assert setup.stream.name in new_handler.stream_dict

    def test_continuous_stream_static_data_preserved(self):
        setup = make_continuous_stream(maximum_operation_rate=50, minimum_operation_rate=5)
        json_str = setup.stream_handler.json_dumps_streams()

        new_handler = StreamHandler()
        new_handler.json_loads_streams(json_str)

        recovered = new_handler.stream_dict[setup.stream.name]
        assert recovered.static_data.maximum_operation_rate == pytest.approx(50)
        assert recovered.static_data.minimum_operation_rate == pytest.approx(5)

    def test_batch_stream_static_data_preserved(self):
        delay = datetime.timedelta(hours=6)
        setup = make_batch_stream(
            maximum_batch_mass_value=400,
            minimum_batch_mass_value=10,
            delay=delay,
        )
        json_str = setup.stream_handler.json_dumps_streams()

        new_handler = StreamHandler()
        new_handler.json_loads_streams(json_str)

        recovered = new_handler.stream_dict[setup.stream.name]
        assert recovered.static_data.maximum_batch_mass_value == pytest.approx(400)
        assert recovered.static_data.minimum_batch_mass_value == pytest.approx(10)
        assert recovered.static_data.delay == delay

    def test_mixed_streams_both_registered(self):
        cont_setup = make_continuous_stream(
            start_process_step_name="Source",
            end_process_step_name="Storage",
            commodity_name="Material",
        )
        batch_setup = make_batch_stream(
            start_process_step_name="Storage",
            end_process_step_name="Sink",
            commodity_name="Material",
            stream_handler=cont_setup.stream_handler,
        )
        json_str = cont_setup.stream_handler.json_dumps_streams()

        new_handler = StreamHandler()
        new_handler.json_loads_streams(json_str)

        assert cont_setup.stream.name in new_handler.stream_dict
        assert batch_setup.stream.name in new_handler.stream_dict
        assert len(new_handler.stream_dict) == 2

    def test_commodity_name_preserved(self):
        setup = make_continuous_stream(commodity_name="Copper Scrap")
        json_str = setup.stream_handler.json_dumps_streams()

        new_handler = StreamHandler()
        new_handler.json_loads_streams(json_str)

        recovered = new_handler.stream_dict[setup.stream.name]
        assert recovered.static_data.commodity.name == "Copper Scrap"

    def test_process_step_names_preserved(self):
        setup = make_continuous_stream(
            start_process_step_name="Furnace",
            end_process_step_name="Cooling",
        )
        json_str = setup.stream_handler.json_dumps_streams()

        new_handler = StreamHandler()
        new_handler.json_loads_streams(json_str)

        recovered = new_handler.stream_dict[setup.stream.name]
        assert recovered.static_data.start_process_step_name == "Furnace"
        assert recovered.static_data.end_process_step_name == "Cooling"

    def test_dumps_produces_valid_json(self):
        setup = make_continuous_stream()
        json_str = setup.stream_handler.json_dumps_streams()
        parsed = json.loads(json_str)
        assert "continuous" in parsed
        assert "batch" in parsed


# ---------------------------------------------------------------------------
# StreamHandler file round-trip
# ---------------------------------------------------------------------------


class TestStreamHandlerFileRoundtrip:
    """json_dump_streams() → file → json_load_streams() reconstructs all streams."""

    def test_file_roundtrip_continuous(self, tmp_path):
        setup = make_continuous_stream(
            maximum_operation_rate=30,
            commodity_name="Iron Ore",
        )
        path = str(tmp_path / "streams.json")
        setup.stream_handler.json_dump_streams(path=path)

        new_handler = StreamHandler()
        new_handler.json_load_streams(path=path)

        assert setup.stream.name in new_handler.stream_dict
        recovered = new_handler.stream_dict[setup.stream.name]
        assert recovered.static_data.maximum_operation_rate == pytest.approx(30)
        assert recovered.static_data.commodity.name == "Iron Ore"

    def test_file_roundtrip_batch(self, tmp_path):
        delay = datetime.timedelta(hours=8)
        setup = make_batch_stream(maximum_batch_mass_value=500, delay=delay)
        path = str(tmp_path / "streams.json")
        setup.stream_handler.json_dump_streams(path=path)

        new_handler = StreamHandler()
        new_handler.json_load_streams(path=path)

        assert setup.stream.name in new_handler.stream_dict
        recovered = new_handler.stream_dict[setup.stream.name]
        assert recovered.static_data.maximum_batch_mass_value == pytest.approx(500)
        assert recovered.static_data.delay == delay

    def test_file_is_valid_json(self, tmp_path):
        setup = make_continuous_stream()
        path = str(tmp_path / "streams.json")
        setup.stream_handler.json_dump_streams(path=path)

        with open(path) as f:
            parsed = json.load(f)
        assert "continuous" in parsed
        assert "batch" in parsed
