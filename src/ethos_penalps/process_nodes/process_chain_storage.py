import cloudpickle

from ethos_penalps.data_classes import Commodity, ProcessChainIdentifier
from ethos_penalps.node_operations import (
    DownstreamAdaptionOrder,
    DownstreamValidationOrder,
    NodeOperation,
    ProductionOrder,
    TerminateProduction,
    UpstreamAdaptionOrder,
    UpstreamNewProductionOrder,
)
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream import BatchStream, ContinuousStream
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.general_functions import ResultPathGenerator


class ProcessChainStorage(ProcessNode):
    def __init__(
        self,
        name: str,
        commodity: Commodity,
        stream_handler: StreamHandler,
        production_plan: ProductionPlan,
        time_data: TimeData,
    ) -> None:
        self.source: Source = Source(
            name=name,
            commodity=commodity,
            stream_handler=stream_handler,
            production_plan=production_plan,
            time_data=time_data,
        )
        self.sink: Sink

        self.name: str = name
        self.commodity: Commodity = commodity
        self.production_plan: ProductionPlan = production_plan
        self.time_data: TimeData = time_data
        self.acts_as_source: bool = True

    def add_sink_from_next_network_level(
        self,
        name: str,
        commodity: Commodity,
        stream_handler: StreamHandler,
        production_plan: ProductionPlan,
        time_data: TimeData,
    ):
        self.sink: Sink = Sink(
            name=name,
            commodity=commodity,
            stream_handler=stream_handler,
            production_plan=production_plan,
            time_data=time_data,
        )

    def switch_from_source_to_sink(self):
        order_collection_from_source = (
            self.source.create_production_order_collection_from_input_states()
        )
        self.sink.get_order_from_parent_source(
            order_collection_from_source=order_collection_from_source
        )
        self.acts_as_source = False

    def create_storage_entries(self):
        if self.acts_as_source is True:
            pass
        else:
            self.sink.stream_handler.stream_dict.update(
                self.source.stream_handler.stream_dict
            )
            self.sink.create_storage_entries(
                list_of_output_stream_states=self.source.list_of_output_stream_states
            )

    def process_input_order(
        self,
        input_node_operation: DownstreamAdaptionOrder
        | DownstreamValidationOrder
        | UpstreamNewProductionOrder
        | TerminateProduction,
    ):
        if self.acts_as_source is True:
            output_node_operation = self.source.process_input_order(
                input_node_operation=input_node_operation
            )
        elif self.acts_as_source is False:
            output_node_operation = self.sink.process_input_order(
                input_node_operation=input_node_operation
            )

        return output_node_operation

    def add_output_stream(
        self,
        output_stream: ContinuousStream | BatchStream,
        process_chain_identifier: ProcessChainIdentifier,
    ):
        self.source.add_output_stream(
            output_stream=output_stream,
            process_chain_identifier=process_chain_identifier,
        )

    def add_input_stream(
        self,
        input_stream: ContinuousStream | BatchStream,
        process_chain_identifier: ProcessChainIdentifier,
    ):
        self.sink.add_input_stream(
            input_stream=input_stream, process_chain_identifier=process_chain_identifier
        )

    def initialize_sink(self):
        self.switch_from_source_to_sink()
        self.sink.initialize_sink()

    def get_input_stream_name(self) -> str:
        input_stream_name = self.sink.get_input_stream_name()
        return input_stream_name

    def get_output_stream_name(self) -> str:
        output_stream_name = self.source.get_output_stream_name()
        return output_stream_name

    def prepare_sink_for_next_chain(
        self, process_chain_identifier: ProcessChainIdentifier
    ):
        self.sink.prepare_sink_for_next_chain(
            process_chain_identifier=process_chain_identifier
        )

    def prepare_source_for_next_chain(
        self, process_chain_identifier: ProcessChainIdentifier
    ):
        self.source.prepare_source_for_next_chain(
            process_chain_identifier=process_chain_identifier
        )

    def check_if_sink_has_orders(self):
        self.sink.check_if_sink_has_orders()

    def plan_production(self) -> UpstreamNewProductionOrder:
        upstream_order = self.sink.plan_production()
        return upstream_order

    def get_upstream_node_name(self) -> str:
        return self.sink.get_upstream_node_name()

    def get_downstream_node_name(self) -> str:
        return self.source.get_downstream_node_name()
