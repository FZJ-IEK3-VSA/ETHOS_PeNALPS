import datetime
import math
import pathlib
from dataclasses import dataclass

import pandas

from ethos_penalps.data_classes import (
    Commodity,
    OrderCollection,
    ProcessChainIdentifier,
    ProductionOrderMetadata,
    StorageProductionPlanEntry,
)
from ethos_penalps.order_distributor.order_to_chain_splitter import (
    OrderToChainSplitter,
)
from ethos_penalps.order_distributor.parallel_order_aggregator import (
    ParallelOrderAggregator,
)
from ethos_penalps.post_processing.time_series_visualizations.gantt_chart import (
    create_gantt_chart,
)
from ethos_penalps.post_processing.time_series_visualizations.order_plot import (
    create_order_gantt_plot,
    post_process_order_collection,
)
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.storage import BaseStorage
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamStaticData,
    ContinuousStream,
    ContinuousStreamStaticData,
)
from ethos_penalps.stream_handler import StreamHandler


@dataclass
class ContinuousTestTwoStreams:
    sink_name: str
    sink_input_stream_1: ContinuousStream
    sink_input_stream_2: ContinuousStream
    chain_identifier_1: ProcessChainIdentifier
    chain_identifier_2: ProcessChainIdentifier
    stream_handler: StreamHandler
    list_of_storage_entries: StorageProductionPlanEntry
    commodity: Commodity


@dataclass
class ContinuousTestOneStream:
    sink_name: str
    sink_input_stream_1: ContinuousStream
    chain_identifier_1: ProcessChainIdentifier
    stream_handler: StreamHandler
    list_of_storage_entries: StorageProductionPlanEntry
    commodity: Commodity


def create_storage_entry(
    process_step_name: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    storage_level_at_end: float,
    storage_level_at_start: float,
    commodity: Commodity,
) -> StorageProductionPlanEntry:
    duration = str(end_time - start_time)
    return StorageProductionPlanEntry(
        process_step_name=process_step_name,
        start_time=start_time,
        end_time=end_time,
        duration=duration,
        storage_level_at_end=storage_level_at_end,
        storage_level_at_start=storage_level_at_start,
        commodity=commodity,
    )


def create_conti_single_stream_test_data() -> ContinuousTestOneStream:
    test_commodity = Commodity(name="Test Commodity")
    # storage_entry_1=StorageProductionPlanEntry(process_step_name=)
    sink_name = "Test Sink"

    start_process_step_name_1 = "Process Step 1"
    storage_entry_1 = create_storage_entry(
        process_step_name=sink_name,
        start_time=datetime.datetime(year=2022, month=1, day=1, hour=1),
        end_time=datetime.datetime(year=2022, month=1, day=1, hour=2),
        storage_level_at_start=0,
        storage_level_at_end=100,
        commodity=test_commodity,
    )
    storage_entry_2 = create_storage_entry(
        process_step_name=sink_name,
        start_time=datetime.datetime(year=2022, month=1, day=1, hour=2),
        end_time=datetime.datetime(year=2022, month=1, day=1, hour=3),
        storage_level_at_start=100,
        storage_level_at_end=100,
        commodity=test_commodity,
    )
    storage_entry_3 = create_storage_entry(
        process_step_name=sink_name,
        start_time=datetime.datetime(year=2022, month=1, day=1, hour=3),
        end_time=datetime.datetime(year=2022, month=1, day=1, hour=4),
        storage_level_at_start=100,
        storage_level_at_end=150,
        commodity=test_commodity,
    )
    list_of_storage_entries = [storage_entry_1, storage_entry_2, storage_entry_3]

    stream_handler = StreamHandler()
    stream_1 = stream_handler.create_continuous_stream(
        continuous_stream_static_data=ContinuousStreamStaticData(
            start_process_step_name=start_process_step_name_1,
            end_process_step_name=sink_name,
            commodity=test_commodity,
            maximum_operation_rate=100,
        )
    )

    process_chain_identifier_1 = ProcessChainIdentifier(chain_number=1, chain_name="Chain 1")

    batch_test = ContinuousTestOneStream(
        sink_name=sink_name,
        sink_input_stream_1=stream_1,
        chain_identifier_1=process_chain_identifier_1,
        list_of_storage_entries=list_of_storage_entries,
        commodity=test_commodity,
        stream_handler=stream_handler,
    )
    return batch_test


def create_two_stream_continuous_data() -> ContinuousTestTwoStreams:
    test_commodity = Commodity(name="Test Commodity")
    # storage_entry_1=StorageProductionPlanEntry(process_step_name=)
    sink_name = "Test Sink"

    start_process_step_name_1 = "Process Step 1"
    start_process_step_name_2 = "Process Step 2"
    storage_entry_1 = create_storage_entry(
        process_step_name=sink_name,
        start_time=datetime.datetime(year=2022, month=1, day=1, hour=1),
        end_time=datetime.datetime(year=2022, month=1, day=1, hour=2),
        storage_level_at_start=0,
        storage_level_at_end=100,
        commodity=test_commodity,
    )
    storage_entry_2 = create_storage_entry(
        process_step_name=sink_name,
        start_time=datetime.datetime(year=2022, month=1, day=1, hour=2),
        end_time=datetime.datetime(year=2022, month=1, day=1, hour=3),
        storage_level_at_start=100,
        storage_level_at_end=100,
        commodity=test_commodity,
    )
    storage_entry_3 = create_storage_entry(
        process_step_name=sink_name,
        start_time=datetime.datetime(year=2022, month=1, day=1, hour=3),
        end_time=datetime.datetime(year=2022, month=1, day=1, hour=4),
        storage_level_at_start=100,
        storage_level_at_end=150,
        commodity=test_commodity,
    )
    list_of_storage_entries = [storage_entry_1, storage_entry_2, storage_entry_3]

    stream_handler = StreamHandler()
    stream_1 = stream_handler.create_continuous_stream(
        continuous_stream_static_data=ContinuousStreamStaticData(
            start_process_step_name=start_process_step_name_1,
            end_process_step_name=sink_name,
            commodity=test_commodity,
            maximum_operation_rate=100,
        )
    )

    stream_2 = stream_handler.create_continuous_stream(
        continuous_stream_static_data=ContinuousStreamStaticData(
            start_process_step_name=start_process_step_name_2,
            end_process_step_name=sink_name,
            commodity=test_commodity,
            maximum_operation_rate=100,
        )
    )

    process_chain_identifier_1 = ProcessChainIdentifier(chain_number=1, chain_name="Chain 1")
    process_chain_identifier_2 = ProcessChainIdentifier(chain_number=2, chain_name="Chain 2")
    batch_test = ContinuousTestTwoStreams(
        sink_name=sink_name,
        sink_input_stream_1=stream_1,
        sink_input_stream_2=stream_2,
        chain_identifier_1=process_chain_identifier_1,
        chain_identifier_2=process_chain_identifier_2,
        list_of_storage_entries=list_of_storage_entries,
        commodity=test_commodity,
        stream_handler=stream_handler,
    )
    return batch_test
