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

mass_tolerance = 0.000001


@dataclass
class OrderWithoutDeadline:
    """Order without deadline."""

    chain_identifier: ProcessChainIdentifier
    stream_name: str
    batch_size: float


@dataclass
class SplitGroup:
    """Creates a

    Returns:
        _type_: _description_
    """

    chain_identifier: ProcessChainIdentifier
    stream_name: str
    split_factor: float
    batch_size: float
    total_production_mass: float
    max_split_factor: float

    def __post_init__(self):
        self.splitted_total_mass_current_group: float = self.total_production_mass * self.split_factor
        self.splitted_total_mass_max_group: float = self.total_production_mass * self.max_split_factor
        self.number_of_previous_batches: int = 0
        self.splitted_mass_current: float = 0

    def get_number_of_batches(self) -> int:
        number_of_batches = math.ceil(self.total_production_mass / self.batch_size)
        return number_of_batches

    def get_number_additional_batches(self, target_percentage_of_production: float) -> list[OrderWithoutDeadline]:

        target_batch_mass_current_group = target_percentage_of_production * self.splitted_total_mass_current_group

        new_requested_batch_mass = target_batch_mass_current_group - self.splitted_mass_current
        pass
        if new_requested_batch_mass <= mass_tolerance:
            return []

        number_of_batches_current_group = int(math.ceil(new_requested_batch_mass / self.batch_size))
        new_batch_mass_full_batches = number_of_batches_current_group * self.batch_size
        new_splitted_mass = new_batch_mass_full_batches + self.splitted_mass_current
        if new_splitted_mass <= self.splitted_total_mass_current_group:
            output_batch_list = [
                OrderWithoutDeadline(
                    chain_identifier=self.chain_identifier,
                    stream_name=self.stream_name,
                    batch_size=self.batch_size,
                )
            ] * number_of_batches_current_group
            self.splitted_mass_current = new_splitted_mass
        else:
            output_batch_list = [
                OrderWithoutDeadline(
                    chain_identifier=self.chain_identifier,
                    stream_name=self.stream_name,
                    batch_size=self.batch_size,
                )
            ] * (number_of_batches_current_group - 1)
            added_batch_mass_without_last_batch = self.batch_size * (number_of_batches_current_group - 1)
            last_batch_size = (
                self.splitted_total_mass_current_group
                - added_batch_mass_without_last_batch
                - self.splitted_mass_current
            )
            if last_batch_size > mass_tolerance:
                output_batch_list.append(
                    OrderWithoutDeadline(
                        chain_identifier=self.chain_identifier,
                        stream_name=self.stream_name,
                        batch_size=last_batch_size,
                    )
                )
            self.splitted_mass_current = (
                self.splitted_mass_current + added_batch_mass_without_last_batch + last_batch_size
            )
        return output_batch_list


class SplitGroupHandler:
    def __init__(
        self,
    ):
        self.split_group_dict: dict[ProcessChainIdentifier, SplitGroup] = {}

    def add_split_group(self, split_group: SplitGroup):
        self.split_group_dict[split_group.chain_identifier] = split_group

    def get_group_with_biggest_batch_size(self) -> SplitGroup:
        group_with_biggest_batch_size = None
        for current_split_group in self.split_group_dict.values():
            if group_with_biggest_batch_size is None:
                group_with_biggest_batch_size = current_split_group
            if group_with_biggest_batch_size.batch_size < current_split_group.batch_size:
                group_with_biggest_batch_size = current_split_group
        return group_with_biggest_batch_size

    def get_max_batch_size_from_group(
        self,
    ):
        list_of_batch_sizes = []
        for split_group in self.split_group_dict.values():
            list_of_batch_sizes.append(split_group.batch_size)

        return max(list_of_batch_sizes)

    def get_biggest_mass_share_group(self):
        list_of_splitted_total_mass = []
        for split_group in self.split_group_dict.values():
            list_of_splitted_total_mass.append(split_group.splitted_total_mass_current_group)

        return max(list_of_splitted_total_mass)

    def _create_cumulative_list_of_total_production_shares(self, number_of_steps: int) -> list[float]:
        cumulative_list_of_total_production_shares = []
        current_cumulative_percentage = 0
        increment_per_step = 1 / number_of_steps
        for current_step_number in range(1, number_of_steps + 1):
            current_cumulative_percentage = current_cumulative_percentage + increment_per_step
            cumulative_list_of_total_production_shares.append(current_cumulative_percentage)

        if cumulative_list_of_total_production_shares[-1] > 1:
            cumulative_list_of_total_production_shares[-1] = 1
        if math.isclose(cumulative_list_of_total_production_shares[-1], 1):
            cumulative_list_of_total_production_shares[-1] = 1

        return cumulative_list_of_total_production_shares

    def create_order_without_deadline_list(self) -> list[OrderWithoutDeadline]:
        """Creates a list of order withouts deadlines from the incoming

        Returns:
            list[OrderWithoutDeadline]: _description_
        """
        group_with_biggest_batch_size = self.get_group_with_biggest_batch_size()

        number_of_group_steps = math.ceil(
            group_with_biggest_batch_size.splitted_total_mass_current_group / group_with_biggest_batch_size.batch_size
        )

        cumulative_list_of_total_production_shares = self._create_cumulative_list_of_total_production_shares(
            number_of_steps=number_of_group_steps
        )

        order_without_deadline_list = []
        for target_percentage_of_production in cumulative_list_of_total_production_shares:
            for split_group in self.split_group_dict.values():
                new_order_without_deadline_list = split_group.get_number_additional_batches(
                    target_percentage_of_production=target_percentage_of_production
                )
                order_without_deadline_list.extend(new_order_without_deadline_list)

        self.get_masses_of_order_without_deadline_list(order_without_deadline_list=order_without_deadline_list)
        pass

        return order_without_deadline_list

    def get_masses_of_order_without_deadline_list(self, order_without_deadline_list: list[OrderWithoutDeadline]):
        output_dict = {}
        for current_order in order_without_deadline_list:
            if current_order.chain_identifier.chain_name in output_dict:
                output_dict[current_order.chain_identifier.chain_name] = (
                    current_order.batch_size + output_dict[current_order.chain_identifier.chain_name]
                )

            else:
                output_dict[current_order.chain_identifier.chain_name] = current_order.batch_size

        print(output_dict)
        return output_dict


class OrderToChainSplitter(OrderDistributorBase):
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
        super(OrderToChainSplitter, self).__init__(
            stream_handler=stream_handler,
            production_order_collection=production_order_collection,
            node_name=node_name,
        )
        self.split_group_handler = SplitGroupHandler()
        self.split_value_dictionary: dict[ProcessChainIdentifier, float] = {}

    def receive_orders(self, order_source: OrderSource) -> None:
        order_collection = order_source.get_order_collection()
        self.order_collection.append_order_collection(order_collection)

    def _do_split(self):
        """Splits the current set of order among the process chains
        of this NetworkLevel. Currently it is no supported to connect
        a mix of batch and continuous streams to the sink.
        """
        list_of_all_streams = []

        for stream_name in self.dict_of_stream_names.values():
            stream = self.stream_handler.get_stream(stream_name=stream_name)
            list_of_all_streams.append(stream)

        # Aggregate orders
        if not self.order_collection.order_data_frame.empty:
            if all(isinstance(current_stream, ContinuousStream) for current_stream in list_of_all_streams):
                raise Exception("Is not implemented yet")
            elif all(isinstance(current_stream, BatchStream) for current_stream in list_of_all_streams):
                stream_name = next(iter(self.dict_of_stream_names.values()))
                self._create_split_groups()
                order_without_deadline_list = self.split_group_handler.create_order_without_deadline_list()

                self.aggregate_order_batch_streams(
                    input_order_data_frame=self.order_collection.order_data_frame,
                    order_without_deadline_list=order_without_deadline_list,
                )

            else:
                raise Exception("Mixed Batch and Continuous stream is not implemented in storage:" + self.node_name)

    def _create_split_groups(self):
        self._check_if_split_factors_add_up()
        total_mass_splitted_mass = 0
        max_split_value = self._get_max_split_value()
        for (
            process_chain_identifier,
            split_factor,
        ) in self.split_value_dictionary.items():
            stream_name = self.get_stream_name_chain_identifier(process_chain_identifier=process_chain_identifier)
            stream = self.stream_handler.get_stream(stream_name=stream_name)
            if not isinstance(stream, BatchStream):
                raise Exception("Not implemented yet")
            batch_size = stream.static_data.maximum_batch_mass_value
            split_group = SplitGroup(
                chain_identifier=process_chain_identifier,
                stream_name=stream_name,
                split_factor=split_factor,
                batch_size=batch_size,
                total_production_mass=self.order_collection.target_mass,
                max_split_factor=max_split_value,
            )
            self.split_group_handler.add_split_group(split_group)
            total_mass_splitted_mass = total_mass_splitted_mass + split_group.splitted_total_mass_current_group
            # split_group_dict[process_chain_identifier] = split_group

        assert math.isclose(total_mass_splitted_mass, self.order_collection.target_mass)

    def _check_if_split_factors_add_up(self):
        split_sum = 0
        for split_factor in self.split_value_dictionary.values():
            split_sum = split_sum + split_factor
        if not math.isclose(split_sum, 1):
            raise MisconfigurationError(
                "The split factor of the chains of the node : "
                + self.node_name
                + " do not add up to 1. The split sum is: "
                + str(split_sum)
                + " The split sum has to add up to 1 so that all mass requested is actually produced."
            )

    def _get_max_split_value(self) -> float:
        return max(self.split_value_dictionary.values())

    def add_order_split_to_process_chain(self, process_chain_identifier: ProcessChainIdentifier, splitter: float):
        self.split_value_dictionary[process_chain_identifier] = splitter

    def _get_batch_sizes_of_input_streams(self):
        dict_of_batch_masses = {}
        for stream_name in self.dict_of_stream_names.values():
            stream = self.stream_handler.get_stream(stream_name=stream_name)
            if not isinstance(stream, BatchStream):
                raise Exception(
                    "Stream of node: "
                    + str(self.node_name)
                    + " is not a batch stream. This case is not implemented yet. The stream is of type:"
                    + str(type(stream))
                )

            dict_of_batch_masses[stream_name] = stream.static_data.maximum_batch_mass_value
        return dict_of_batch_masses

    def aggregate_order_batch_streams(
        self,
        input_order_data_frame: pandas.DataFrame,
        order_without_deadline_list: list[OrderWithoutDeadline],
    ):
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

        input_order_data_frame.loc[:, "Cumulative Target Upper Bound"] = input_order_data_frame.loc[
            :, "production_target"
        ].cumsum()
        dict_of_output_order_list: dict[str, list[ProductionOrder]] = {}
        for process_chain_identifier in self.dict_of_stream_names:
            dict_of_output_order_list[process_chain_identifier] = []
        self._get_batch_sizes_of_input_streams()

        lower_bound_required_cumulative_mass = numpy.float64(0)
        for current_order_without_deadline in order_without_deadline_list:
            # Determine the upper and lower bound for the cumulative mass cumulative mass for the

            upper_bound_required_cumulative_mass = lower_bound_required_cumulative_mass + numpy.float64(
                current_order_without_deadline.batch_size
            )

            # Determine Upper index
            selection_upper_index = input_order_data_frame.loc[
                input_order_data_frame.loc[:, "Cumulative Target Upper Bound"] <= upper_bound_required_cumulative_mass
            ]

            # Determine upper index
            if selection_upper_index.empty is True:
                upper_index = input_order_data_frame.index[-1]
            else:
                upper_index = selection_upper_index.index[-1]

            # Determine production target of output order
            cumulative_mass_at_upper_index = input_order_data_frame.at[upper_index, "Cumulative Target Upper Bound"]

            if cumulative_mass_at_upper_index < upper_bound_required_cumulative_mass and not math.isclose(
                cumulative_mass_at_upper_index, upper_bound_required_cumulative_mass
            ):
                if upper_index < input_order_data_frame.shape[0] - 1:
                    upper_index = upper_index + 1

            updated_cumulative_mass_at_upper_index = input_order_data_frame.at[
                upper_index, "Cumulative Target Upper Bound"
            ]

            available_mass_in_order_range = (
                updated_cumulative_mass_at_upper_index - lower_bound_required_cumulative_mass
            )

            if available_mass_in_order_range < current_order_without_deadline.batch_size and not math.isclose(
                available_mass_in_order_range,
                current_order_without_deadline.batch_size,
            ):
                production_target = available_mass_in_order_range
            else:
                production_target = current_order_without_deadline.batch_size

            # Create
            deadline = input_order_data_frame.loc[upper_index, "production_deadline"]
            if production_target == 0 or not isinstance(deadline, datetime.datetime):
                raise Exception("asd")
            production_order = ProductionOrder(
                production_target=production_target,
                production_deadline=deadline,
                commodity=self.order_collection.commodity,
                order_number=current_order_without_deadline,
                mass_unit=mass_unit,
            )

            dict_of_output_order_list[current_order_without_deadline.chain_identifier].append(production_order)

            lower_bound_required_cumulative_mass = upper_bound_required_cumulative_mass

        for (
            current_process_chain_identifier,
            list_of_output_order,
        ) in dict_of_output_order_list.items():
            stream_name = self.dict_of_stream_names[current_process_chain_identifier]
            order_df = dataframe_from_dataclasses(list_of_output_order)
            splitted_order = SplittedOrderCollection(
                stream_name=stream_name,
                process_chain_identifier=current_process_chain_identifier,
                order_data_frame=order_df,
                commodity=self.order_collection.commodity,
                target_mass=order_df.loc[:, "production_target"].sum(),
            )
            splitted_order.check_if_order_are_empty()
            self.dict_of_splitted_order[current_process_chain_identifier] = splitted_order
        pass
