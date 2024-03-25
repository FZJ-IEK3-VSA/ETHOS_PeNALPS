import numbers
import math
import datetime
import warnings
from collections.abc import Iterator
from dataclasses import dataclass, field

import numpy
import pandas

from ethos_penalps.data_classes import (
    OrderCollection,
    ProcessChainIdentifier,
    ProductionOrder,
    Commodity,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.exceptions_and_warnings import MisconfigurationError
from ethos_penalps.stream import ContinuousStream, BatchStream
from ethos_penalps.utilities.general_functions import (
    check_if_date_1_is_before_date_2,
    check_if_date_1_is_before_or_at_date_2,
)


@dataclass
class SplittedOrderCollection:
    """Represents a set of orders that has been splitted
    among multiple ProcessChains
    """

    stream_name: str
    commodity: Commodity
    process_chain_identifier: ProcessChainIdentifier
    order_data_frame: pandas.DataFrame
    target_mass: numbers.Number
    current_order_number: int = 0

    def check_if_order_are_empty(self):
        """Raises an error if an order is empty.

        Raises:
            MisconfigurationError: Is raised if the order is empty.
        """
        if self.order_data_frame.empty:
            raise MisconfigurationError(
                "A splitted order of chain: "
                + self.process_chain_identifier.chain_name
                + " has no order. The corresponding sink has too few order too distribute to each chain."
            )

    def get_order_by_order_number(self, order_number: int) -> ProductionOrder:
        """Returns an order based on the order number.

        Args:
            order_number (int): Number that identifies the order.

        Returns:
            ProductionOrder: Order for a product oder intermediate product.
        """
        order_data_frame_row = self.order_data_frame.iloc[order_number]
        production_order = ProductionOrder(
            production_target=order_data_frame_row.loc["production_target"],
            production_deadline=order_data_frame_row.loc["production_deadline"],
            order_number=order_data_frame_row.loc["order_number"],
            commodity=order_data_frame_row.loc["commodity"],
            global_unique_identifier=order_data_frame_row.loc[
                "global_unique_identifier"
            ],
            produced_mass=order_data_frame_row.loc["produced_mass"],
        )
        return production_order

    def update_order(self, produced_mass: numbers.Number):
        """Updates the mass that is already produced.

        Args:
            produced_mass (numbers.Number): The additional mass that has been
                produced and should be added to the order.
        """
        self.order_data_frame.at[self.current_order_number, "produced_mass"] = (
            self.order_data_frame.at[self.current_order_number, "produced_mass"]
            + produced_mass
        )


class OrderDistributor:
    """Distributes the orders among multiple ProcessChains."""

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
        self.node_name: str = node_name
        self.dict_of_stream_names: dict[ProcessChainIdentifier, str] = {}
        self.stream_handler: StreamHandler = stream_handler
        self.splitted_order_iterator: Iterator[SplittedOrderCollection]
        self.order_collection: OrderCollection = production_order_collection
        self.dict_of_splitted_order: dict[
            ProcessChainIdentifier, SplittedOrderCollection
        ] = {}
        self.current_splitted_order: SplittedOrderCollection

    def update_order_collection(self, new_order_collection: OrderCollection):
        """Adds new orders to the current set of orders.

        Args:
            new_order_collection (OrderCollection): The set of orders
                that should be added to the current one.
        """
        self.order_collection.append_order_collection(new_order_collection)
        self.split_production_order_dict()

    def set_current_splitted_order_by_chain_identifier(
        self, process_chain_identifier: ProcessChainIdentifier
    ):
        """Activates the set of splitted orders for a new process chain.

        Args:
            process_chain_identifier (ProcessChainIdentifier): The process chain
                that should that is simulated next.
        """
        self.current_splitted_order = self.dict_of_splitted_order[
            process_chain_identifier
        ]

    def get_current_splitted_order(
        self,
    ) -> SplittedOrderCollection:
        """Returns the set of orders that is currently simulated.

        Returns:
            SplittedOrderCollection: Current set of orders.
        """
        return self.current_splitted_order

    def check_if_there_are_sufficient_order_for_distribution(self):
        """Checks if there are sufficient orders for each process chain.
        Each process chain requires at least one order.

        Raises:
            MisconfigurationError: Raises in error if there are too few order.
        """
        if len(self.order_collection.order_data_frame) < len(
            self.dict_of_splitted_order
        ):
            raise MisconfigurationError(
                "There are too few orders to distribute in the node " + self.node_name
            )

    def split_production_order_dict(self):
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
            if all(
                isinstance(current_stream, ContinuousStream)
                for current_stream in list_of_all_streams
            ):
                all_streams_are_continuous = True
                stream_name = next(iter(self.dict_of_stream_names.values()))
                current_stream = self.stream_handler.get_stream(stream_name=stream_name)
                total_operation_rate_of_streams = (
                    current_stream.static_data.maximum_operation_rate
                    * len(list_of_all_streams)
                )
                aggregated_data_frame = self.aggregate_order_continuos_streams(
                    order_data_frame=self.order_collection.order_data_frame,
                    total_operation_rate_of_streams=total_operation_rate_of_streams,
                )
            elif all(
                isinstance(current_stream, BatchStream)
                for current_stream in list_of_all_streams
            ):
                all_streams_are_batch = True
                stream_name = next(iter(self.dict_of_stream_names.values()))
                current_stream = self.stream_handler.get_stream(stream_name=stream_name)
                aggregation_target_mass = (
                    current_stream.static_data.maximum_batch_mass_value
                )
                aggregated_data_frame = self.aggregate_order_batch_streams(
                    input_order_data_frame=self.order_collection.order_data_frame,
                    order_target_mass=aggregation_target_mass,
                )
            else:
                raise Exception(
                    "Mixed Batch and Continuous stream is not implemented in storage:"
                    + self.node_name
                )
            current_stream_number = 0

            # Distribute orders to streams
            for (
                process_chain_identifier,
                stream_name,
            ) in self.dict_of_stream_names.items():
                current_stream = self.stream_handler.get_stream(stream_name=stream_name)
                if all_streams_are_continuous is True:
                    # aggregate all order into a single stream
                    splitted_data_frame = aggregated_data_frame.copy()
                    splitted_data_frame.loc[:, "production_target"] / number_of_streams

                    splitted_target_mass = splitted_data_frame.loc[
                        :, "production_target"
                    ].sum()
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
                    splitted_target_mass = splitted_data_frame.loc[
                        :, "production_target"
                    ].sum()
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
            warnings.warn(
                "Attempted to split an empty order dictionary in " + str(self.node_name)
            )

    def aggregate_order_continuos_streams(
        self,
        order_data_frame: pandas.DataFrame,
        total_operation_rate_of_streams: numbers.Number,
    ) -> pandas.DataFrame:
        """Aggregates a set of orders in case there are only
        continuous streams connected to the sink.

        Args:
            order_data_frame (pandas.DataFrame): DataFrame of orders that
                should be aggregated.
            total_operation_rate_of_streams (numbers.Number): The combined operation
                rate of all continuous streams that are connected to the sink.


        Returns:
            pandas.DataFrame: Aggregated data frame of orders.
        """
        intermediate_data_frame = order_data_frame.copy()
        intermediate_data_frame.sort_values(
            by="production_deadline", ascending=False, inplace=True
        )
        intermediate_data_frame.reset_index(inplace=True, drop=True)
        series_of_operation_rate_multiplier = (
            intermediate_data_frame.loc[:, "production_target"]
            / total_operation_rate_of_streams
        )
        duration_list = []
        for multiplier in series_of_operation_rate_multiplier:
            duration_list.append(multiplier * datetime.timedelta(hours=1))
        intermediate_data_frame.loc[:, "duration_list"] = duration_list
        intermediate_data_frame.loc[:, "start_time"] = (
            intermediate_data_frame.loc[:, "production_deadline"]
            - intermediate_data_frame.loc[:, "duration_list"]
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
        for index, current_row in intermediate_data_frame.iterrows():
            current_deadline = current_row["production_deadline"]
            current_start_time = current_row["start_time"]
            current_duration = current_row["duration_list"]
            # if deadline_accumulated_order is None:
            #     deadline_accumulated_order = current_deadline
            if (
                first_deadline_has_been_set is False
                and second_deadline_has_been_set is False
            ):
                deadline_accumulated_order = current_deadline
                first_deadline_has_been_set = True
            if (
                first_deadline_has_been_set is True
                and second_deadline_has_been_set is False
            ):
                deadline_accumulated_order = current_deadline
                second_deadline_has_been_set = True
            if start_time_agglomerated_order is None:
                start_time_agglomerated_order = current_start_time
            else:
                start_time_agglomerated_order = (
                    start_time_agglomerated_order - current_duration
                )

            aggregated_production_target = (
                aggregated_production_target + current_row["production_target"]
            )

            # To skip agglomeration on first entry
            if previous_deadline is not None and previous_start_time is not None:
                stream_finishes_before_next_deadline = (
                    check_if_date_1_is_before_or_at_date_2(
                        date_1=current_deadline,
                        date_2=start_time_agglomerated_order,
                    )
                )

                if stream_finishes_before_next_deadline is True:
                    production_order = ProductionOrder(
                        production_target=aggregated_production_target,
                        production_deadline=deadline_accumulated_order,
                        order_number=current_order_number,
                        commodity=current_row["commodity"],
                    )
                    output_order_list.append(production_order)
                    current_order_number = current_order_number + 1
                    aggregated_production_target = 0
                    deadline_accumulated_order = None
                    start_time_agglomerated_order = None
                    first_deadline_has_been_set = False
                    second_deadline_has_been_set = False

                # else:
                #     aggregated_production_target = (
                #         aggregated_production_target + current_row["production_target"]
                #     )
                #     combined_start_time_of_output_order = (
                #         combined_start_time_of_output_order
                #         - current_row["duration_list"]
                #     )

            previous_deadline = current_row["production_deadline"]
            previous_start_time = current_row["start_time"]
        if aggregated_production_target < 0 or isinstance(
            deadline_accumulated_order, datetime.datetime
        ):
            production_order = ProductionOrder(
                production_target=aggregated_production_target,
                production_deadline=deadline_accumulated_order,
                order_number=current_order_number,
                commodity=current_row["commodity"],
            )
            output_order_list.append(production_order)

        aggregated_data_frame = pandas.DataFrame(data=output_order_list)
        return aggregated_data_frame

    def aggregate_order_batch_streams(
        self,
        input_order_data_frame: pandas.DataFrame,
        order_target_mass: numbers.Number,
    ) -> pandas.DataFrame:
        """Aggregates a set of orders in case there are only
        batch streams connected to the sink.

        Args:
            input_order_data_frame (pandas.DataFrame): DataFrame of orders that
                should be aggregated.
            order_target_mass (numbers.Number): The combined operation
                rate of all continuous streams that are connected to the sink.


        Returns:
            pandas.DataFrame: Aggregated data frame of orders.
        """

        input_order_data_frame = input_order_data_frame.copy()
        input_order_data_frame.sort_values(
            by="production_deadline", ascending=False, inplace=True
        )
        input_order_data_frame.reset_index(inplace=True, drop=True)
        # It is expected that the data frame is ordered from the latest order at index[0]
        # to the newest at index [-1]

        total_sum = input_order_data_frame.loc[:, "production_target"].sum()
        number_of_output_order = math.ceil(total_sum / order_target_mass)
        input_order_data_frame.loc[:, "Cumulative Target Upper Bound"] = (
            input_order_data_frame.loc[:, "production_target"].cumsum()
        )

        # input_order_data_frame.loc[:, "Cumulative Target Lower Bound"] = (
        #     input_order_data_frame.loc[:, "Cumulative Target Upper Bound"]
        #     - input_order_data_frame.loc[:, "production_target"]
        # )

        list_of_aggregated_production_order = []
        for current_output_order_number in range(1, number_of_output_order + 1):
            # Determine the upper and lower bound for the cumulative mass cumulative mass for the
            lower_bound_required_cumulative_mass = numpy.float64(order_target_mass) * (
                numpy.float64(current_output_order_number) - numpy.float64(1)
            )
            upper_bound_required_cumulative_mass = numpy.float64(
                order_target_mass
            ) * numpy.float64(current_output_order_number)

            # Determine the index of the
            # selection_lower_index = input_order_data_frame.loc[
            #     input_order_data_frame.loc[:, "Cumulative Target Lower Bound"]
            #     >= lower_bound_required_cumulative_mass
            # ]
            # Determine indices of relevant input orders
            # Determine lower index

            # Decrease

            # if selection_lower_index.empty is True:
            #     lower_index = input_order_data_frame.index[-1]
            # else:
            #     lower_index = selection_lower_index.index[0]
            #     if (
            #         selection_lower_index.loc[
            #             lower_index, "Cumulative Target Lower Bound"
            #         ]
            #         != lower_bound_required_cumulative_mass
            #     ):
            #         lower_index = lower_index - 1

            # Determine Upper index
            selection_upper_index = input_order_data_frame.loc[
                input_order_data_frame.loc[:, "Cumulative Target Upper Bound"]
                <= upper_bound_required_cumulative_mass
            ]

            # Determine upper index
            if selection_upper_index.empty is True:
                upper_index = input_order_data_frame.index[-1]
            else:
                upper_index = selection_upper_index.index[-1]

            # Determine production target of output order
            cumulative_mass_at_upper_index = input_order_data_frame.at[
                upper_index, "Cumulative Target Upper Bound"
            ]

            if (
                cumulative_mass_at_upper_index < upper_bound_required_cumulative_mass
                and not math.isclose(
                    cumulative_mass_at_upper_index, upper_bound_required_cumulative_mass
                )
            ):
                if upper_index < input_order_data_frame.shape[0] - 1:
                    upper_index = upper_index + 1

            updated_cumulative_mass_at_upper_index = input_order_data_frame.at[
                upper_index, "Cumulative Target Upper Bound"
            ]

            available_mass_in_order_range = (
                updated_cumulative_mass_at_upper_index
                - lower_bound_required_cumulative_mass
            )

            if available_mass_in_order_range < order_target_mass and not math.isclose(
                available_mass_in_order_range, order_target_mass
            ):
                production_target = available_mass_in_order_range
            else:
                production_target = order_target_mass

            # Create
            deadline = input_order_data_frame.loc[upper_index, "production_deadline"]
            if production_target == 0 or not isinstance(deadline, datetime.datetime):
                raise Exception("asd")
            production_order = ProductionOrder(
                production_target=production_target,
                production_deadline=deadline,
                commodity=self.order_collection.commodity,
                order_number=current_output_order_number,
            )

            list_of_aggregated_production_order.append(production_order)

        output_data_frame = pandas.DataFrame(data=list_of_aggregated_production_order)

        # print("input_order_data_frame", input_order_data_frame)
        # print(input_order_data_frame.loc[:, "production_target"].sum())
        # print("output_data_frame", output_data_frame)
        # print(
        #     output_data_frame.loc[:, "production_target"].sum(),
        # )
        # print("")
        return output_data_frame

    def get_current_production_order(self) -> ProductionOrder:
        """Returns the current production order.

        Returns:
            ProductionOrder: Active production order.
        """
        return self.current_splitted_order.get_order_by_order_number(
            self.current_splitted_order.current_order_number
        )

    def update_production_order(self, produced_mass: numbers.Number):
        """Updates the production order mass that has been produced.

        Args:
            produced_mass (numbers.Number): New mass that has been produced
                to fulfill the current order.
        """
        self.current_splitted_order.update_order(produced_mass=produced_mass)

    def get_current_stream_name(self) -> str:
        """Returns the stream name of the active ProcessChain.

        Returns:
            str: Stream name of the active process chain.
        """
        return self.current_splitted_order.stream_name

    def add_stream_name(
        self, stream_name: str, process_chain_identifier: ProcessChainIdentifier
    ):
        """Adds a stream name that connects the sink to a process chain.

        Args:
            stream_name (str): Name of a stream that connects the sink to a process chain.
            process_chain_identifier (ProcessChainIdentifier): Identifies the respective
                ProcessChain.
        """
        self.dict_of_stream_names[process_chain_identifier] = stream_name

    def check_if_current_order_is_fulfilled(
        self,
    ) -> bool:
        """Determines if enough mass has been produced to fulfill the current order.


        Returns:
            bool: Is True if sufficient mass is provided.
        """
        current_order = self.get_current_production_order()
        remaining_mass = current_order.production_target - current_order.produced_mass

        if remaining_mass == 0:
            production_order_is_fulfilled = True
        elif remaining_mass > 0:
            production_order_is_fulfilled = False
        elif remaining_mass < 0:
            raise Exception(
                "Something went wrong while fulfilling this production order: "
                + str(ProductionOrder)
            )
        return production_order_is_fulfilled

    def update_current_order_number(self):
        """Increments order number of the active order."""
        self.current_splitted_order.current_order_number = (
            self.current_splitted_order.current_order_number + 1
        )

    def check_if_process_chain_orders_are_satisfied(self) -> bool:
        """Determines if all orders for a process chain are fulfilled.

        Returns:
            bool: Returns True if all orders for a ProcessChain are fulfilled.
        """
        process_chain_orders_are_satisfied = (
            self.current_splitted_order.current_order_number
            >= self.current_splitted_order.order_data_frame.shape[0]
        )
        return process_chain_orders_are_satisfied

    def get_stream_name_chain_identifier(
        self, process_chain_identifier: ProcessChainIdentifier
    ) -> str:
        """Returns the stream name of the stream that connects the sink to a specific
        process chain.

        Args:
            process_chain_identifier (ProcessChainIdentifier): The process chain
                for which the stream name should be returned.

        Returns:
            str: Stream name of the stream that connects the sink to a specific
        process chain.
        """
        stream_name = self.dict_of_stream_names[process_chain_identifier]
        return stream_name
