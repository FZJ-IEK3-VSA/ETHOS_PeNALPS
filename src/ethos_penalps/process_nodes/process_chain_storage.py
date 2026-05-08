import cloudpickle

from ethos_penalps.data_classes import (
    Commodity,
    OrderProcessingType,
    ProcessChainIdentifier,
)
from ethos_penalps.node_operations import (
    DownstreamAdaptionOrder,
    DownstreamValidationOrder,
    NodeOperation,
    ProductionOrder,
    TerminateProduction,
    UpstreamAdaptionOrder,
    UpstreamNewProductionOrder,
)
from ethos_penalps.order_distributor.base_node_distributor import OrderSource
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream import BatchStream, ContinuousStream
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.type_aliases import numbers_alias


class ProcessChainStorage(ProcessNode):
    """This node is used to connect two NetworkLevel. During the simulation of
    the downstream NetworkLevel this nodes acts as an source and tracks all required output streams.
    At the start of the simulation of the upstream NetworkLevel all streams that were requested from
    the this node as a source a converted into orders. These orders are then aggregated and distributed
    among the ProcessChains of the upstream NetworkLevel.

    """

    def __init__(
        self,
        name: str,
        commodity: Commodity,
        stream_handler: StreamHandler,
        production_plan: ProductionPlan,
        time_data: TimeData,
        order_processing_type: OrderProcessingType = OrderProcessingType.AGGREGATE_AND_DISTRIBUTE,
    ) -> None:
        """

        Args:
            name (str): Name of the storage that is used in some figures
                and for identification. Must be unique.
            commodity (Commodity): The commodity that is stored in this node.
            stream_handler (StreamHandler): contains all streams that are connected
                to this node.
            production_plan (ProductionPlan): Is used to store the storage states
                of this node.
            time_data (TimeData): Contains the the start and end date that is used
                for the creation of the storage states.
        """
        self.source: Source = Source(
            name=name,
            commodity=commodity,
            stream_handler=stream_handler,
            production_plan=production_plan,
            time_data=time_data,
        )
        self.sink: Sink
        super().__init__(stream_handler=stream_handler, name=name)

        self.commodity: Commodity = commodity
        self.production_plan: ProductionPlan = production_plan
        self.time_data: TimeData = time_data
        self.acts_as_source: bool = True
        self.aggregate_orders: OrderProcessingType = order_processing_type
        self.storage_entries_have_been_created: bool = False

    def add_sink_from_next_network_level(
        self,
        name: str,
        commodity: Commodity,
        stream_handler: StreamHandler,
        production_plan: ProductionPlan,
        time_data: TimeData,
        order_processing_type: OrderProcessingType,
    ):
        """Creates a sink from the upstream NetworkLevel

        Args:
            name (str): Name of the storage that is used in some figures
                and for identification. Must be unique.
            commodity (Commodity): The commodity that is stored in this node.
            stream_handler (StreamHandler): contains all streams that are connected
                to this node.
            production_plan (ProductionPlan): Is used to store the storage states
                of this node.
            time_data (TimeData): Contains the the start and end date that is used
                for the creation of the storage states.
        """
        self.sink: Sink = Sink(
            name=name,
            commodity=commodity,
            stream_handler=stream_handler,
            production_plan=production_plan,
            time_data=time_data,
            order_processing_type=order_processing_type,
        )

    def add_split_factor(
        self,
        split_factor_float: float,
        process_chain_identifier: ProcessChainIdentifier,
    ):
        self.sink.add_split_factor(
            split_factor_float=split_factor_float,
            process_chain_identifier=process_chain_identifier,
        )

    def switch_from_source_to_sink(self):
        """Switches the behavior of the process_input_order method
        from source to sink. The distributor lazily pulls only the
        data it needs from the source.
        """
        # Pass methods as callables to allow lazy pulling of the data. This prevents unnecessary function calls.
        self.sink.order_distributor.receive_orders(
            OrderSource(
                get_order_collection=lambda: self.source.create_production_order_collection_from_input_states(),
                get_storage_entries=lambda: self.source.create_storage_entries(assume_output_streams_as_input=True),
            )
        )
        self.acts_as_source = False

    def create_storage_entries(self):
        """Creates the storage entries of this node."""
        if self.acts_as_source is True:
            return None

        if self.storage_entries_have_been_created is False:
            self.sink.stream_handler.stream_dict.update(self.source.stream_handler.stream_dict)

            if self.aggregate_orders is OrderProcessingType.ORDER_PARALLEL:
                list_of_storage_entries, _, _ = self.sink.storage.create_storage_entries_from_streams(
                    input_stream_state_list=self.sink.input_stream_state_list,
                    output_stream_state_list=self.source.list_of_output_stream_states,
                    storage_level_at_start="auto_offset",
                    start_time=self.time_data.start_time_valid,
                    end_time=self.time_data.end_time_valid,
                )
                self.sink.production_plan.add_list_of_storage_entries(
                    storage_name=self.sink.name,
                    commodity=self.commodity,
                    list_of_storage_entries=list_of_storage_entries,
                )
            else:
                self.sink.create_storage_entries(list_of_output_stream_states=self.source.list_of_output_stream_states)

            self.storage_entries_have_been_created = True

    def process_input_order(
        self,
        input_node_operation: DownstreamAdaptionOrder
        | DownstreamValidationOrder
        | UpstreamNewProductionOrder
        | TerminateProduction,
    ):
        """Either works as a Source or as a Sink depending on the progress of the simulation.
        It works as a Source as long as the downstream NetworkLevel has not terminated the
        simulation. Afterwards it works as a sink for the upstream NetworkLevel

        Args:
            input_node_operation (DownstreamAdaptionOrder  |  DownstreamValidationOrder  |  UpstreamNewProductionOrder  |  TerminateProduction): _description_

        Returns:
            _type_: Creates DownstreamValidationOrder as long as it works as a source. Afterwards UpstreamNewProductionOrder, DownstreamAdaptionOrder
            and TerminateProduction are created to indicate that a new input stream is required, the requested stream is adapted or the simulation
            of the Process Chain is terminated.
        """
        if self.acts_as_source is True:
            assert type(input_node_operation) is UpstreamNewProductionOrder
            output_node_operation = self.source.process_input_order(input_node_operation=input_node_operation)
        elif self.acts_as_source is False:
            assert (
                type(input_node_operation) is DownstreamAdaptionOrder
                or type(input_node_operation) is DownstreamValidationOrder
            )

            output_node_operation = self.sink.process_input_order(input_node_operation=input_node_operation)

        return output_node_operation

    def add_output_stream(
        self,
        output_stream: ContinuousStream | BatchStream,
        process_chain_identifier: ProcessChainIdentifier,
    ):
        """Adds an output stream to this node. This information is required
        for the simulation.

        Args:
            output_stream (ContinuousStream | BatchStream): Output stream of this node
                to another ProcessStep in the downstream NetworkLevel.
            process_chain_identifier (ProcessChainIdentifier): Identifies the
                process chain that the stream belongs to.
        """
        self.source.add_output_stream(
            output_stream=output_stream,
            process_chain_identifier=process_chain_identifier,
        )

    def add_input_stream(
        self,
        input_stream: ContinuousStream | BatchStream,
        process_chain_identifier: ProcessChainIdentifier,
    ):
        """_summary_

        Args:
            input_stream (ContinuousStream | BatchStream): Input stream from another
                ProcessStep in the Upstream NetworkLevel.
            process_chain_identifier (ProcessChainIdentifier): Identifies the
                process chain that the stream belongs to.
        """
        self.sink.add_input_stream(input_stream=input_stream, process_chain_identifier=process_chain_identifier)

    def initialize_sink(self):
        """Converts the streams from the source into orders,
        aggregates and distributes the orders among the upstream
        ProcessChain.
        """
        self.switch_from_source_to_sink()
        self.sink.initialize_sink()

    def get_input_stream_name(self) -> str:
        """Returns the current input stream name of the node.

        Returns:
            str: Active input stream name.
        """
        input_stream_name = self.sink.get_input_stream_name()
        return input_stream_name

    def get_output_stream_name(self) -> str:
        """Returns the active output stream name of the node.

        Returns:
            str: Active output stream name.
        """
        output_stream_name = self.source.get_output_stream_name()
        return output_stream_name

    def prepare_sink_for_next_chain(self, process_chain_identifier: ProcessChainIdentifier):
        """Prepares the sink for next chain. Is called to initiate the first
        or a following chain.

        Args:
            process_chain_identifier (ProcessChainIdentifier): Identifies
                the chain that should be simulated.
        """
        self.sink.prepare_sink_for_next_chain(process_chain_identifier=process_chain_identifier)

    def prepare_source_for_next_chain(self, process_chain_identifier: ProcessChainIdentifier):
        """Prepares the source for the next chain.

        Args:
            process_chain_identifier (ProcessChainIdentifier): Identifies the
                chain that should be activated for simulation.
        """
        self.source.prepare_source_for_next_chain(process_chain_identifier=process_chain_identifier)

    def check_if_sink_has_orders(self):
        """Checks if the sink has orders. No orders indicate
        an ill defined simulation.
        """
        self.sink.check_if_sink_has_orders()

    def plan_production(self) -> UpstreamNewProductionOrder:
        """Creates the next Upstream production order to fulfill the next order.

        Returns:
            UpstreamNewProductionOrder: Next UpstreamNewProductionOrder that
                is requests a new input stream state for the sink.
        """
        upstream_order = self.sink.plan_production()
        return upstream_order

    def get_upstream_node_name(self) -> str:
        """Returns the name of the node upstream of the Storage of the currently active
        process chain.

        Returns:
            str: Name of the node upstream of the Storage of the currently active
            process chain
        """
        return self.sink.get_upstream_node_name()

    def get_downstream_node_name(self) -> str:
        """Returns the name of the node of the currently active
        chain downstream of the Storage.

        Returns:
            str: Name of the node of the currently active
        chain downstream of the Storage.
        """
        return self.source.get_downstream_node_name()
