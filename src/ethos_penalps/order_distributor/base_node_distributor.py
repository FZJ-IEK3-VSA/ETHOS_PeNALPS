import datetime
import math
import numbers
import warnings
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

import numpy
import pandas

from ethos_penalps.data_classes import (
    Commodity,
    OrderCollection,
    OrderWithMassTransferDurationCollection,
    ProcessChainIdentifier,
    ProductionOrder,
    StorageProductionPlanEntry,
)
from ethos_penalps.order_distributor.splitted_order import SplittedOrderCollection
from ethos_penalps.stream import BatchStream, ContinuousStream
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.exceptions_and_warnings import MisconfigurationError
from ethos_penalps.utilities.general_functions import (
    check_if_date_1_is_before_date_2,
    check_if_date_1_is_before_or_at_date_2,
)
from ethos_penalps.utilities.type_aliases import numbers_alias


@dataclass
class OrderSource:
    """Wraps the lazy callables that a storage node provides to its distributor.

    Each distributor subclass evaluates only the callable it needs,
    avoiding unnecessary conversions.
    """

    get_order_collection: Callable[[], OrderCollection]
    get_storage_entries: Callable[[], list[StorageProductionPlanEntry]]


class OrderDistributorBase:
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
        self.dict_of_splitted_order: dict[ProcessChainIdentifier, SplittedOrderCollection] = {}
        self.current_splitted_order: SplittedOrderCollection

    def receive_orders(self, order_source: OrderSource) -> None:
        """Receives order data from an OrderSource.

        Each subclass evaluates only the callable it needs from the
        source, so the expensive conversion only happens for the
        data that is actually required.

        Args:
            order_source: Container holding lazy callables for both
                order-collection and storage-entry data.
        """
        raise NotImplementedError

    def _do_split(self):
        """Subclass-specific splitting logic. Override this instead
        of calling split_and_finalize directly."""
        raise NotImplementedError

    def split_and_finalize(self):
        """Splits orders among chains and ensures order_collection
        is populated afterwards."""
        result = self._do_split()
        self._sync_order_collection_from_splits()
        return result

    def _sync_order_collection_from_splits(self):
        """If order_collection is empty but splits exist, reconstruct it
        from the per-chain splitted orders."""
        if self.order_collection.order_data_frame.empty and self.dict_of_splitted_order:
            frames = [s.order_data_frame for s in self.dict_of_splitted_order.values()]
            combined = pandas.concat(frames, ignore_index=True)
            self.order_collection.order_data_frame = combined
            self.order_collection.target_mass = combined["production_target"].sum()

    def update_order_collection(
        self,
        new_order_collection: OrderCollection | OrderWithMassTransferDurationCollection,
    ):
        """Adds new orders to the current set of orders.

        Args:
            new_order_collection (OrderCollection): The set of orders
                that should be added to the current one.
        """
        self.order_collection.append_order_collection(new_order_collection)
        self.split_and_finalize()

    def set_current_splitted_order_by_chain_identifier(self, process_chain_identifier: ProcessChainIdentifier):
        """Activates the set of splitted orders for a new process chain.

        Args:
            process_chain_identifier (ProcessChainIdentifier): The process chain
                that should that is simulated next.
        """
        self.current_splitted_order = self.dict_of_splitted_order[process_chain_identifier]

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
        if len(self.order_collection.order_data_frame) < len(self.dict_of_splitted_order):
            raise MisconfigurationError("There are too few orders to distribute in the node " + self.node_name)

    def get_current_production_order(self) -> ProductionOrder:
        """Returns the current production order.

        Returns:
            ProductionOrder: Active production order.
        """
        return self.current_splitted_order.get_order_by_order_number(self.current_splitted_order.current_order_number)

    def update_production_order(self, produced_mass: numbers_alias):
        """Updates the production order mass that has been produced.

        Args:
            produced_mass (numbers_alias): New mass that has been produced
                to fulfill the current order.
        """
        self.current_splitted_order.update_order(produced_mass=produced_mass)

    def get_current_stream_name(self) -> str:
        """Returns the stream name of the active ProcessChain.

        Returns:
            str: Stream name of the active process chain.
        """
        return self.current_splitted_order.stream_name

    def add_stream_name(self, stream_name: str, process_chain_identifier: ProcessChainIdentifier):
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
            raise Exception("Something went wrong while fulfilling this production order: " + str(ProductionOrder))
        return production_order_is_fulfilled

    def update_current_order_number(self):
        """Increments order number of the active order."""
        self.current_splitted_order.current_order_number = self.current_splitted_order.current_order_number + 1

    def check_if_process_chain_orders_are_satisfied(self) -> bool:
        """Determines if all orders for a process chain are fulfilled.

        Returns:
            bool: Returns True if all orders for a ProcessChain are fulfilled.
        """
        process_chain_orders_are_satisfied = (
            self.current_splitted_order.current_order_number >= self.current_splitted_order.order_data_frame.shape[0]
        )
        return process_chain_orders_are_satisfied

    def get_stream_name_chain_identifier(self, process_chain_identifier: ProcessChainIdentifier) -> str:
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


class OrderDistributor(OrderDistributorBase):
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
        if all(isinstance(current_stream, ContinuousStream) for current_stream in list_of_all_streams):
            all_streams_are_continuous = True
        elif all(isinstance(current_stream, BatchStream) for current_stream in list_of_all_streams):
            all_streams_are_batch = True

        aggregated_data_frame = self.order_collection.order_data_frame.copy()
        aggregated_data_frame.sort_values(by="production_deadline", ascending=False, inplace=True)
        aggregated_data_frame.reset_index(inplace=True, drop=True)
        aggregated_data_frame["order_number"] = aggregated_data_frame.index
        # Distribute orders to streams
        current_stream_number = 0
        for (
            process_chain_identifier,
            stream_name,
        ) in self.dict_of_stream_names.items():
            current_stream = self.stream_handler.get_stream(stream_name=stream_name)
            if all_streams_are_continuous is True:
                # aggregate all order into a single stream
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
                # splitted_data_frame.loc[:, "production_target"] / number_of_streams

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
            if all_streams_are_batch is True:
                raise NotImplementedError(
                    "The distribution of batch streams has not been implemented for all batch streams"
                )
            if all_streams_are_batch is False and all_streams_are_continuous is False:
                raise NotImplementedError("The distribution of a mix of batch streams is not implemented yet")
