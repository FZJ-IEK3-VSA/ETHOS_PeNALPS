import json
import datetime
from ethos_penalps.utilities.own_object_json_encoding_decoding import (
    MyEncoder,
    MyDecoder,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamStaticData,
    ContinuousStreamStaticData,
    ContinuousStream,
)
from ethos_penalps.data_classes import Commodity, LoadType, StreamLoadEnergyData
from ethos_penalps.utilities.units import Units
from dataclasses import dataclass, field
from dataclasses_json import DataClassJsonMixin, dataclass_json


def test_encode_and_decode_batch_energy_load():
    test_load = LoadType("Test_load")

    load_json_string = test_load.to_json()

    reread_load = LoadType.from_json(load_json_string)

    assert test_load == reread_load


def test_encode_and_decode_batch_energy_dictionary():
    test_load = LoadType("Test_load")
    stream_energy_data = StreamLoadEnergyData(
        stream_name="Stream 1", specific_energy_demand=1, load_type=test_load
    )

    load_json_string = stream_energy_data.to_json()

    reread_stream_energy_data = StreamLoadEnergyData.from_json(load_json_string)

    assert stream_energy_data == reread_stream_energy_data


def test_encode_and_decode_batch_stream_static_data():
    stream_handler = StreamHandler()
    test_commodity = Commodity("Test commodity")
    batch_stream_static_data = batch_stream_static_data = BatchStreamStaticData(
        start_process_step_name="Start",
        end_process_step_name="End",
        delay=datetime.timedelta(minutes=10),
        commodity=test_commodity,
    )

    batch_stream_json_string = batch_stream_static_data.to_json()

    reread_batch_stream_static_data = BatchStreamStaticData.from_json(
        batch_stream_json_string
    )

    assert reread_batch_stream_static_data == batch_stream_static_data


def test_encode_and_decode_batch_stream():
    stream_handler = StreamHandler()
    test_commodity = Commodity("Test commodity")
    batch_stream = stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name="Start",
            end_process_step_name="End",
            delay=datetime.timedelta(minutes=10),
            commodity=test_commodity,
        )
    )
    batch_stream_json_string = batch_stream.to_json()

    reread_batch_stream = BatchStream.from_json(batch_stream_json_string)

    assert isinstance(reread_batch_stream, BatchStream), " Is not"
    assert (
        reread_batch_stream.static_data.start_process_step_name
        == batch_stream.static_data.start_process_step_name
    )
    assert (
        reread_batch_stream.static_data.end_process_step_name
        == batch_stream.static_data.end_process_step_name
    )
    assert reread_batch_stream == batch_stream


def test_encode_and_decode_batch_stream_with_energy_data():
    stream_handler = StreamHandler()
    test_commodity = Commodity("Test commodity")
    batch_stream = stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name="Start",
            end_process_step_name="End",
            delay=datetime.timedelta(minutes=10),
            commodity=test_commodity,
        )
    )
    load_type = LoadType(name="Test Load")
    batch_stream.create_stream_energy_data(
        specific_energy_demand=3,
        load_type=load_type,
    )
    batch_stream_json_string = batch_stream.to_json()

    reread_batch_stream = BatchStream.from_json(batch_stream_json_string)

    assert isinstance(reread_batch_stream, BatchStream), " Is not"
    assert (
        reread_batch_stream.static_data.start_process_step_name
        == batch_stream.static_data.start_process_step_name
    )
    assert (
        reread_batch_stream.static_data.end_process_step_name
        == batch_stream.static_data.end_process_step_name
    )
    assert reread_batch_stream == batch_stream


def test_encode_and_decode_continuous_stream():
    stream_handler = StreamHandler()
    test_commodity = Commodity("Test commodity")
    continuous_stream = stream_handler.create_continuous_stream(
        continuous_stream_static_data=ContinuousStreamStaticData(
            start_process_step_name="Start",
            end_process_step_name="End",
            commodity=test_commodity,
            time_unit=datetime.timedelta(minutes=35),
            maximum_operation_rate=200,
        )
    )
    continuous_stream_string = continuous_stream.to_json()

    reread_continuous_stream = ContinuousStream.from_json(continuous_stream_string)
    assert (
        reread_continuous_stream.static_data.mass_unit
        == continuous_stream.static_data.mass_unit
    )
    assert reread_continuous_stream.static_data == continuous_stream.static_data
    assert reread_continuous_stream == continuous_stream


def test_encode_and_decode_stream_handler():
    stream_handler = StreamHandler()
    test_commodity = Commodity("Test commodity")
    continuous_stream = stream_handler.create_continuous_stream(
        continuous_stream_static_data=ContinuousStreamStaticData(
            start_process_step_name="Start Continuous",
            end_process_step_name="End Continuous",
            commodity=test_commodity,
            time_unit=datetime.timedelta(minutes=35),
            maximum_operation_rate=200,
        )
    )
    batch_stream = stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name="Start  Batch",
            end_process_step_name="End Batch",
            delay=datetime.timedelta(minutes=10),
            commodity=test_commodity,
        )
    )
    reread_stream_handler = StreamHandler()
    stream_handler_string = stream_handler.json_dumps_streams()
    reread_stream_handler.json_loads_streams(json_string=stream_handler_string)

    assert reread_stream_handler.get_stream(
        continuous_stream.name
    ) == stream_handler.get_stream(continuous_stream.name)
    assert reread_stream_handler.get_stream(
        batch_stream.name
    ) == stream_handler.get_stream(batch_stream.name)
    assert reread_stream_handler.stream_dict == stream_handler.stream_dict
