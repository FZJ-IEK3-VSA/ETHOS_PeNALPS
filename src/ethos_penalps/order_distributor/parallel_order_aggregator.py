import datetime
import math
import numbers
import warnings
from collections.abc import Iterator
from dataclasses import dataclass, field

import numpy
import pandas

from ethos_penalps.data_classes import (
    Commodity,
    OrderCollection,
    ProcessChainIdentifier,
    ProductionOrder,
    StorageProductionPlanEntry,
)
from ethos_penalps.order_distributor.base_node_distributor import OrderDistributorBase, OrderSource
from ethos_penalps.order_distributor.splitted_order import SplittedOrderCollection
from ethos_penalps.stream import BatchStream, ContinuousStream
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.time_overlap_analyzer import (
    TimeOverLapAnalyzer,
    TimeRange,
    TimeRangeDatetime,
    TimeRangesHandler,
)
from ethos_penalps.utilities.exceptions_and_warnings import MisconfigurationError
from ethos_penalps.utilities.general_functions import (
    check_if_date_1_is_before_date_2,
    check_if_date_1_is_before_or_at_date_2,
    dataframe_from_dataclasses,
)
from ethos_penalps.utilities.type_aliases import numbers_alias

mass_tolerance = 0.000001


class ParallelOrderAggregator(OrderDistributorBase):
    def __init__(
        self,
        stream_handler: StreamHandler,
        production_order_collection: OrderCollection,
        node_name: str,
    ) -> None:
        """

        Args:
            stream_handler (StreamHandler): Container for all streams
                connected the sink to the process chains.
            production_order_collection (OrderCollection): Set of orders
                that should be delivered to the sink.
            node_name (str): Name of the sink that should receive the orders.
        """
        super(ParallelOrderAggregator, self).__init__(
            stream_handler=stream_handler,
            production_order_collection=production_order_collection,
            node_name=node_name,
        )
        self.list_of_storage_entries: list[StorageProductionPlanEntry] = []
        self.split_value_dictionary: dict[ProcessChainIdentifier, float] = {}

    def receive_orders(self, order_source: OrderSource) -> None:
        storage_entries = order_source.get_storage_entries()
        self.list_of_storage_entries.extend(storage_entries)

    def _do_split(self) -> float:
        """Splits the current set of order among the process chains
        of this NetworkLevel. Currently it is no supported to connect
        a mix of batch and continuous streams to the sink.
        """
        list_of_all_streams = []

        for stream_name in self.dict_of_stream_names.values():
            stream = self.stream_handler.get_stream(stream_name=stream_name)
            list_of_all_streams.append(stream)

        # Aggregate orders

        if all(isinstance(current_stream, ContinuousStream) for current_stream in list_of_all_streams):
            mass_split_dict = self.determine_split_dict(list_of_continuos_streams=list_of_all_streams)
        elif all(isinstance(current_stream, BatchStream) for current_stream in list_of_all_streams):
            raise Exception("Is not implemented yet")

        else:
            raise Exception("Mixed Batch and Continuous stream is not implemented in storage:" + self.node_name)

        # self.create_splitted_order_with_time_shift(mass_split_dict=mass_split_dict)
        start_storage_level = self.create_splitted_order_with_storage_level(mass_split_dict=mass_split_dict)
        return start_storage_level

    # def create_splitted_order_with_time_shift(self, mass_split_dict: dict[str, float]) -> float:
    #     total_mass = self._determine_maximum_total_mass(list_of_storage_entries=self.list_of_storage_entries)
    #     first_start_time = self.determine_first_start_time(list_of_storage_entries=self.list_of_storage_entries)
    #     last_end_time = self.determine_last_end_time(list_of_storage_entries=self.list_of_storage_entries)
    #     average_production_rate = self.determine_average_production_rate(
    #         total_mass=total_mass,
    #         first_start_time=first_start_time,
    #         last_end_time=last_end_time,
    #     )
    #     list_of_storage_level, list_of_datetimes = self.create_storage_level_and_datetime_list(
    #         list_of_storage_entries=self.list_of_storage_entries
    #     )
    #     output_start_time, output_end_time = self.determine_required_start_and_end_time(
    #         average_rate=average_production_rate,
    #         list_of_storage_level=list_of_storage_level,
    #         list_of_datetimes=list_of_datetimes,
    #     )
    #     self.create_continuous_splitted_order(
    #         total_mass=total_mass,
    #         last_end_time=output_end_time,
    #         mass_split_dict=mass_split_dict,
    #     )
    #     start_storage_level = 0
    #     return start_storage_level

    def create_splitted_order_with_storage_level(self, mass_split_dict: dict[str, float]):
        total_mass = self._determine_maximum_total_mass(list_of_storage_entries=self.list_of_storage_entries)
        first_start_time = self.determine_first_start_time(list_of_storage_entries=self.list_of_storage_entries)
        last_end_time = self.determine_last_end_time(list_of_storage_entries=self.list_of_storage_entries)
        average_production_rate = self.determine_average_production_rate(
            total_mass=total_mass,
            first_start_time=first_start_time,
            last_end_time=last_end_time,
        )
        list_of_storage_level, list_of_datetimes = self.create_storage_level_and_datetime_list(
            list_of_storage_entries=self.list_of_storage_entries
        )
        required_start_storage_level = self.determine_required_start_storage_level(
            average_rate=average_production_rate,
            list_of_storage_level=list_of_storage_level,
            list_of_datetimes=list_of_datetimes,
        )
        self.create_continuous_splitted_order(
            total_mass=total_mass,
            last_end_time=last_end_time,
            mass_split_dict=mass_split_dict,
        )
        return required_start_storage_level

    def determine_split_dict(self, list_of_continuos_streams: list[ContinuousStream]) -> dict[str, float]:
        total_rate = 0
        mass_split_dict = {}
        for current_stream in list_of_continuos_streams:
            total_rate = total_rate + current_stream.static_data.maximum_operation_rate
        for current_stream in list_of_continuos_streams:
            split_factor = current_stream.static_data.maximum_operation_rate / total_rate
            mass_split_dict[current_stream.name] = split_factor
        return mass_split_dict

    def _determine_maximum_total_mass(self, list_of_storage_entries: list[StorageProductionPlanEntry]) -> float:
        total_mass = (
            list_of_storage_entries[-1].storage_level_at_end - list_of_storage_entries[0].storage_level_at_start
        )
        return total_mass

    def determine_first_start_time(self, list_of_storage_entries: list[StorageProductionPlanEntry]) -> float:
        first_start_time = list_of_storage_entries[0].start_time
        return first_start_time

    def determine_last_end_time(self, list_of_storage_entries: list[StorageProductionPlanEntry]) -> float:
        last_end_time = list_of_storage_entries[-1].end_time
        return last_end_time

    def _get_mass_unit(
        self,
    ) -> str:
        mass_unit = "metric_ton"
        return mass_unit

    def determine_average_production_rate(
        self,
        total_mass: float,
        first_start_time: datetime.datetime,
        last_end_time: datetime.datetime,
    ) -> float:
        average_production_rate = total_mass / ((last_end_time - first_start_time) / datetime.timedelta(hours=1))
        return average_production_rate

    def create_storage_level_and_datetime_list(self, list_of_storage_entries: list[StorageProductionPlanEntry]):
        list_of_storage_level: list[float] = []
        list_of_datetimes: list[datetime.datetime] = []
        for current_storage_entries in list_of_storage_entries:
            list_of_storage_level.append(current_storage_entries.storage_level_at_start)
            list_of_storage_level.append(current_storage_entries.storage_level_at_end)
            list_of_datetimes.append(current_storage_entries.start_time)
            list_of_datetimes.append(current_storage_entries.end_time)
        return list_of_storage_level, list_of_datetimes

    def determine_required_start_and_end_time(
        self,
        average_rate: float,
        list_of_storage_level: list[float],
        list_of_datetimes: list[datetime.datetime],
    ):
        initial_start_time = list_of_datetimes[0]
        initial_end_time = list_of_datetimes[-1]
        previous_storage_level = list_of_storage_level[0]
        previous_datetime = list_of_datetimes[0]
        datetime_divisor = datetime.timedelta(hours=1)
        required_time_shift = datetime.timedelta(hours=0)
        for current_input_storage_level, current_input_datetime in zip(
            list_of_storage_level[1:], list_of_datetimes[1:]
        ):
            current_duration = (current_input_datetime - previous_datetime) / datetime_divisor
            new_storage_level = previous_storage_level + current_duration * average_rate
            if new_storage_level < current_input_storage_level:
                mass_difference = current_input_storage_level - new_storage_level
                required_time_shift = required_time_shift + (mass_difference / average_rate) * datetime_divisor
                current_input_storage_level = current_input_storage_level + mass_difference
        output_start_time = initial_start_time - required_time_shift
        output_end_time = initial_end_time - required_time_shift
        return output_start_time, output_end_time

    def determine_required_start_storage_level(
        self,
        average_rate: float,
        list_of_storage_level: list[float],
        list_of_datetimes: list[datetime.datetime],
    ):
        # initial_start_time = list_of_datetimes[0]
        # initial_end_time = list_of_datetimes[-1]
        required_start_storage_level = 0
        previous_storage_level = list_of_storage_level[0]
        previous_datetime = list_of_datetimes[0]
        datetime_divisor = datetime.timedelta(hours=1)
        # required_time_shift = datetime.timedelta(hours=0)
        for current_input_storage_level, current_input_datetime in zip(
            list_of_storage_level[1:], list_of_datetimes[1:]
        ):
            current_duration = (current_input_datetime - previous_datetime) / datetime_divisor
            new_storage_level = previous_storage_level + current_duration * average_rate
            if new_storage_level < current_input_storage_level:
                mass_difference = current_input_storage_level - new_storage_level
                required_start_storage_level = max(required_start_storage_level, mass_difference)

        return required_start_storage_level

    def create_continuous_splitted_order(
        self,
        total_mass: float,
        last_end_time: datetime.datetime,
        mass_split_dict: dict[str, float],
    ):

        for (
            process_chain_identifier,
            stream_name,
        ) in self.dict_of_stream_names.items():
            splitted_mass = total_mass * mass_split_dict[stream_name]
            current_stream = self.stream_handler.get_stream(stream_name=stream_name)
            current_order = ProductionOrder(
                production_target=splitted_mass,
                production_deadline=last_end_time,
                order_number=0,
                commodity=current_stream.static_data.commodity,
                mass_unit=self._get_mass_unit(),
            )
            order_data_frame = dataframe_from_dataclasses([current_order])

            splitted_order = SplittedOrderCollection(
                stream_name=stream_name,
                commodity=current_stream.static_data.commodity,
                process_chain_identifier=process_chain_identifier,
                target_mass=splitted_mass,
                order_data_frame=order_data_frame,
            )
            splitted_order.check_if_order_are_empty()
            self.dict_of_splitted_order[process_chain_identifier] = splitted_order

