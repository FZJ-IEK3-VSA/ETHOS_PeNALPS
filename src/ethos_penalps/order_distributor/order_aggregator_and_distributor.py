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
)
from ethos_penalps.order_distributor.base_node_distributor import OrderDistributorBase, OrderSource
from ethos_penalps.order_distributor.splitted_order import SplittedOrderCollection
from ethos_penalps.stream import BatchStream, ContinuousStream
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.exceptions_and_warnings import MisconfigurationError
from ethos_penalps.utilities.general_functions import (
    check_if_date_1_is_before_date_2,
    check_if_date_1_is_before_or_at_date_2,
    dataframe_from_dataclasses,
)
from ethos_penalps.utilities.type_aliases import numbers_alias


class OrderAggregatorAndDistributor(OrderDistributorBase):
    def receive_orders(self, order_source: OrderSource) -> None:
        order_collection = order_source.get_order_collection()
        self.order_collection.append_order_collection(order_collection)

    def _do_split(self):
        """Splits the current set of order among the process chains
        of this NetworkLevel. Currently it is no supported to connect
        a mix of batch and continuous streams to the sink.
        """
        number_of_streams = len(self.dict_of_stream_names)
        list_of_all_streams = []

        for stream_name in self.dict_of_stream_names.values():
            stream = self.stream_handler.get_stream(stream_name=stream_name)
            list_of_all_streams.append(stream)

        all_streams_are_continuous = False
        all_streams_are_batch = False

        # Aggregate orders
        if not self.order_collection.order_data_frame.empty:
            if all(isinstance(current_stream, ContinuousStream) for current_stream in list_of_all_streams):
                all_streams_are_continuous = True
                stream_name = next(iter(self.dict_of_stream_names.values()))
                current_stream = self.stream_handler.get_stream(stream_name=stream_name)
                total_operation_rate_of_streams = current_stream.static_data.maximum_operation_rate * len(
                    list_of_all_streams
                )

                aggregated_data_frame = self.aggregate_order_continuos_streams(
                    order_data_frame=self.order_collection.order_data_frame,
                    total_operation_rate_of_streams=total_operation_rate_of_streams,
                )
            elif all(isinstance(current_stream, BatchStream) for current_stream in list_of_all_streams):
                all_streams_are_batch = True
                stream_name = next(iter(self.dict_of_stream_names.values()))
                current_stream = self.stream_handler.get_stream(stream_name=stream_name)
                aggregation_target_mass = current_stream.static_data.maximum_batch_mass_value
                aggregated_data_frame = self.aggregate_order_batch_streams(
                    input_order_data_frame=self.order_collection.order_data_frame,
                    order_target_mass=aggregation_target_mass,
                )
            else:
                raise Exception("Mixed Batch and Continuous stream is not implemented in storage:" + self.node_name)
            current_stream_number = 0

            # Distribute orders to streams
            for (
                process_chain_identifier,
                stream_name,
            ) in self.dict_of_stream_names.items():
                current_stream = self.stream_handler.get_stream(stream_name=stream_name)
                if all_streams_are_continuous is True:
                    # aggregate all order into a single stream
                    number_of_total_aggregated_orders = aggregated_data_frame.shape[0]
                    # list_index = list(
                    #     range(
                    #         current_stream_number,
                    #         number_of_total_aggregated_orders,
                    #         number_of_streams,
                    #     )
                    # )
                    splitted_data_frame = aggregated_data_frame.copy()
                    splitted_data_frame.reset_index(inplace=True)
                    splitted_data_frame.loc[:, "production_target"] = (
                        splitted_data_frame.loc[:, "production_target"] / number_of_streams
                    )

                    splitted_target_mass = splitted_data_frame.loc[:, "production_target"].sum()
                    splitted_order = SplittedOrderCollection(
                        stream_name=stream_name,
                        process_chain_identifier=process_chain_identifier,
                        order_data_frame=splitted_data_frame,
                        commodity=self.order_collection.commodity,
                        target_mass=splitted_target_mass,
                    )
                elif all_streams_are_batch is True:
                    number_of_total_aggregated_orders = aggregated_data_frame.shape[0]
                    list_index = list(
                        range(
                            current_stream_number,
                            number_of_total_aggregated_orders,
                            number_of_streams,
                        )
                    )
                    splitted_data_frame = aggregated_data_frame.iloc[list_index].copy()
                    splitted_data_frame.reset_index(inplace=True)
                    splitted_target_mass = splitted_data_frame.loc[:, "production_target"].sum()
                    splitted_order = SplittedOrderCollection(
                        stream_name=stream_name,
                        process_chain_identifier=process_chain_identifier,
                        order_data_frame=splitted_data_frame,
                        commodity=self.order_collection.commodity,
                        target_mass=splitted_target_mass,
                    )

                splitted_order.check_if_order_are_empty()
                self.dict_of_splitted_order[process_chain_identifier] = splitted_order
                current_stream_number = current_stream_number + 1
        else:
            warnings.warn("Attempted to split an empty order dictionary in " + str(self.node_name))

    def aggregate_order_continuos_streams(
        self,
        order_data_frame: pandas.DataFrame,
        total_operation_rate_of_streams: numbers_alias,
    ) -> pandas.DataFrame:
        """Aggregates a set of orders in case there are only
        continuous streams connected to the sink.

        Args:
            order_data_frame (pandas.DataFrame): DataFrame of orders that
                should be aggregated.
            total_operation_rate_of_streams (numbers_alias): The combined operation
                rate of all continuous streams that are connected to the sink.


        Returns:
            pandas.DataFrame: Aggregated data frame of orders.
        """
        intermediate_data_frame = order_data_frame.copy()
        intermediate_data_frame.sort_values(by="production_deadline", ascending=False, inplace=True)
        intermediate_data_frame.reset_index(inplace=True, drop=True)
        series_of_operation_rate_multiplier = (
            intermediate_data_frame.loc[:, "production_target"] / total_operation_rate_of_streams
        )
        duration_list = []
        for multiplier in series_of_operation_rate_multiplier:
            duration_list.append(multiplier * datetime.timedelta(hours=1))
        intermediate_data_frame.loc[:, "duration_list"] = duration_list
        intermediate_data_frame.loc[:, "start_time"] = (
            intermediate_data_frame.loc[:, "production_deadline"] - intermediate_data_frame.loc[:, "duration_list"]
        )
        storage_level = 0
        previous_deadline = None
        previous_start_time = None
        current_deadline = None
        current_start_time = None
        aggregated_production_target = 0
        output_order_list = []
        current_order_number = 1
        stream_finishes_before_next_deadline = True
        first_deadline_has_been_set = False
        second_deadline_has_been_set = False
        deadline_accumulated_order = None
        start_time_agglomerated_order = None
        for row in intermediate_data_frame.itertuples(index=False):
            current_deadline = row.production_deadline
            current_start_time = row.start_time
            current_duration = row.duration_list
            row_production_target = row.production_target
            row_commodity = row.commodity
            row_mass_unit = row.mass_unit
            # if deadline_accumulated_order is None:
            #     deadline_accumulated_order = current_deadline
            if first_deadline_has_been_set is False and second_deadline_has_been_set is False:
                deadline_accumulated_order = current_deadline
                first_deadline_has_been_set = True
            if first_deadline_has_been_set is True and second_deadline_has_been_set is False:
                deadline_accumulated_order = current_deadline
                second_deadline_has_been_set = True
            if start_time_agglomerated_order is None:
                start_time_agglomerated_order = current_start_time
            else:
                start_time_agglomerated_order = start_time_agglomerated_order - current_duration

            aggregated_production_target = aggregated_production_target + row_production_target

            # To skip agglomeration on first entry
            if previous_deadline is not None and previous_start_time is not None:
                stream_finishes_before_next_deadline = check_if_date_1_is_before_or_at_date_2(
                    date_1=current_deadline,
                    date_2=start_time_agglomerated_order,
                )

                if stream_finishes_before_next_deadline is True:
                    production_order = ProductionOrder(
                        production_target=aggregated_production_target,
                        production_deadline=deadline_accumulated_order,
                        order_number=current_order_number,
                        commodity=row_commodity,
                        mass_unit=row_mass_unit,
                    )
                    output_order_list.append(production_order)
                    current_order_number = current_order_number + 1
                    aggregated_production_target = 0
                    deadline_accumulated_order = None
                    start_time_agglomerated_order = None
                    first_deadline_has_been_set = False
                    second_deadline_has_been_set = False

            previous_deadline = current_deadline
            previous_start_time = current_start_time
        if aggregated_production_target < 0 or isinstance(deadline_accumulated_order, datetime.datetime):
            production_order = ProductionOrder(
                production_target=aggregated_production_target,
                production_deadline=deadline_accumulated_order,
                order_number=current_order_number,
                commodity=row_commodity,
                mass_unit=row_mass_unit,
            )
            output_order_list.append(production_order)

        aggregated_data_frame = dataframe_from_dataclasses(output_order_list)
        return aggregated_data_frame

    def aggregate_order_batch_streams(
        self,
        input_order_data_frame: pandas.DataFrame,
        order_target_mass: numbers_alias,
    ) -> pandas.DataFrame:
        """Aggregates a set of orders in case there are only
        batch streams connected to the sink.

        Args:
            input_order_data_frame (pandas.DataFrame): DataFrame of orders that
                should be aggregated.
            order_target_mass (numbers_alias): The combined operation
                rate of all continuous streams that are connected to the sink.


        Returns:
            pandas.DataFrame: Aggregated data frame of orders.
        """

        input_order_data_frame = input_order_data_frame.copy()
        input_order_data_frame.sort_values(by="production_deadline", ascending=False, inplace=True)
        input_order_data_frame.reset_index(inplace=True, drop=True)
        unit_array = input_order_data_frame.loc[:, "mass_unit"].unique()
        mass_unit = list(unit_array)[0]
        # It is expected that the data frame is ordered from the latest order at index[0]
        # to the newest at index [-1]

        total_sum = input_order_data_frame.loc[:, "production_target"].sum()
        number_of_output_order = math.ceil(total_sum / order_target_mass)
        input_order_data_frame.loc[:, "Cumulative Target Upper Bound"] = input_order_data_frame.loc[
            :, "production_target"
        ].cumsum()

        # input_order_data_frame.loc[:, "Cumulative Target Lower Bound"] = (
        #     input_order_data_frame.loc[:, "Cumulative Target Upper Bound"]
        #     - input_order_data_frame.loc[:, "production_target"]
        # )

        # Pre-extract numpy arrays for fast lookup (avoids repeated boolean indexing)
        cumulative_upper_bound_arr = input_order_data_frame["Cumulative Target Upper Bound"].values
        deadline_arr = input_order_data_frame["production_deadline"].values
        last_index = len(cumulative_upper_bound_arr) - 1

        list_of_aggregated_production_order = []
        for current_output_order_number in range(1, number_of_output_order + 1):
            lower_bound_required_cumulative_mass = numpy.float64(order_target_mass) * (
                numpy.float64(current_output_order_number) - numpy.float64(1)
            )
            upper_bound_required_cumulative_mass = numpy.float64(order_target_mass) * numpy.float64(
                current_output_order_number
            )

            # Use searchsorted instead of boolean indexing: find last index where cumsum <= upper_bound
            # searchsorted('right') gives first index where value > upper_bound, so subtract 1
            search_idx = (
                numpy.searchsorted(cumulative_upper_bound_arr, upper_bound_required_cumulative_mass, side="right") - 1
            )
            if search_idx < 0:
                upper_index = last_index
            else:
                upper_index = int(search_idx)

            cumulative_mass_at_upper_index = cumulative_upper_bound_arr[upper_index]

            if cumulative_mass_at_upper_index < upper_bound_required_cumulative_mass and not math.isclose(
                cumulative_mass_at_upper_index, upper_bound_required_cumulative_mass
            ):
                if upper_index < last_index:
                    upper_index = upper_index + 1

            updated_cumulative_mass_at_upper_index = cumulative_upper_bound_arr[upper_index]

            available_mass_in_order_range = (
                updated_cumulative_mass_at_upper_index - lower_bound_required_cumulative_mass
            )

            if available_mass_in_order_range < order_target_mass and not math.isclose(
                available_mass_in_order_range, order_target_mass
            ):
                production_target = available_mass_in_order_range
            else:
                production_target = order_target_mass

            deadline = pandas.Timestamp(deadline_arr[upper_index]).to_pydatetime()
            if production_target == 0 or not isinstance(deadline, datetime.datetime):
                raise Exception("asd")
            production_order = ProductionOrder(
                production_target=production_target,
                production_deadline=deadline,
                commodity=self.order_collection.commodity,
                order_number=current_output_order_number,
                mass_unit=mass_unit,
            )

            list_of_aggregated_production_order.append(production_order)

        output_data_frame = dataframe_from_dataclasses(list_of_aggregated_production_order)

        output_data_frame.sort_values(by="production_deadline", ascending=False, inplace=True)
        output_data_frame.reset_index(inplace=True, drop=True)
        # print("input_order_data_frame", input_order_data_frame)
        # print(input_order_data_frame.loc[:, "production_target"].sum())
        # print("output_data_frame", output_data_frame)
        # print(
        #     output_data_frame.loc[:, "production_target"].sum(),
        # )
        # print("")
        return output_data_frame
