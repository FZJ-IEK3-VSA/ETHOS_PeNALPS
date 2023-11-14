import datetime
import pandas
from ethos_penalps.time_data import TimeData
from ethos_penalps.stream import (
    BatchStream,
    ContinuousStream,
    ContinuousStreamState,
    BatchStreamState,
)

from ethos_penalps.stream_handler import StreamHandler

from ethos_penalps.utilities.exceptions_and_warnings import Misconfiguration
from ethos_penalps.data_classes import (
    StaticTimePeriod,
    OutputBranchIdentifier,
    TemporalBranchIdentifier,
    Commodity,
    ProcessChainIdentifier,
)
from ethos_penalps.process_node_communicator import ProcessNodeCommunicator
from ethos_penalps.process_step_data import ProcessStepData
from ethos_penalps.mass_balance import MassBalance
from ethos_penalps.node_operations import (
    NodeOperation,
    DownstreamValidationOrder,
    UpstreamNewProductionOrder,
    TerminateProduction,
    DownstreamAdaptionOrder,
    UpstreamAdaptionOrder,
)
from ethos_penalps.process_node_communicator import EmptyProductionBranch
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.load_profile_calculator import LoadProfileHandler
from ethos_penalps.simulation_data.simulation_data_branch import (
    IncompleteOutputBranchData,
    CompleteOutputBranchData,
    OutputBranchData,
    IncompleteStreamBranchData,
)
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.production_plan import OutputBranchProductionPlan
from ethos_penalps.data_classes import ProductionOrder, OrderCollection
from ethos_penalps.storage import BaseStorage

logger = PeNALPSLogger.get_logger_without_handler()


class Source(ProcessNode):
    def __init__(
        self,
        name: str,
        commodity: Commodity,
        stream_handler: StreamHandler,
        time_data: TimeData,
        production_plan: ProductionPlan,
    ) -> None:
        super().__init__(stream_handler=stream_handler, name=name)
        self.commodity: Commodity = commodity
        self.production_plan: ProductionPlan = production_plan
        self.dict_of_output_stream_names: dict[ProcessChainIdentifier, str] = {}
        self.time_data: TimeData = time_data
        self.current_output_stream_name: str
        self.production_branch_number: float = 0
        self.temporal_branch_number: float = 0
        self.list_of_output_stream_states: list[
            ContinuousStreamState | BatchStreamState
        ] = []
        self.storage: BaseStorage = BaseStorage(
            process_step_name=name,
            commodity=commodity,
            stream_handler=stream_handler,
            input_to_output_conversion_factor=1,
        )

    def __str__(self) -> str:
        return "Source: " + self.name

    def add_output_stream(
        self,
        output_stream: ContinuousStream | BatchStream,
        process_chain_identifier: ProcessChainIdentifier,
    ):
        if not isinstance(output_stream, ContinuousStream | BatchStream):
            raise Exception(
                "Expected output stream of type ContinuousStream but got type: "
                + str(type(output_stream))
            )

        self.dict_of_output_stream_names[process_chain_identifier] = output_stream.name

    def create_storage_entries(self):
        stream_net_mass = self.storage.determine_net_mass(
            list_of_input_stream_states=[],
            list_of_output_stream_states=self.list_of_output_stream_states,
        )
        self.storage.current_storage_level = -stream_net_mass
        list_of_storage_entries = self.storage.create_storage_entries_from_start_to_end(
            last_storage_update_time=self.time_data.global_start_date,
            list_of_input_stream_states=[],
            list_of_output_stream_states=self.list_of_output_stream_states,
        )

        self.production_plan.add_list_of_storage_entries(
            storage_name=self.name,
            commodity=self.commodity,
            list_of_storage_entries=list_of_storage_entries,
        )

    def set_current_output_stream(
        self,
        process_chain_identifier: ProcessChainIdentifier,
    ):
        self.current_output_stream_name = self.dict_of_output_stream_names[
            process_chain_identifier
        ]

    def prepare_source_for_next_chain(
        self,
        process_chain_identifier: ProcessChainIdentifier,
    ):
        self.set_current_output_stream(
            process_chain_identifier=process_chain_identifier
        )
        self.production_branch_number: float = 0
        self.temporal_branch_number: float = 0

    def get_downstream_node_name(self) -> str:
        output_stream = self.stream_handler.get_stream(
            stream_name=self.current_output_stream_name
        )
        downstream_node_name = output_stream.get_downstream_node_name()
        return downstream_node_name

    def create_complete_branch_data(
        self, upstream_new_production_order: UpstreamNewProductionOrder
    ) -> CompleteOutputBranchData:
        self.production_branch_number = self.production_branch_number + 1
        output_branch_identifier = OutputBranchIdentifier(
            branch_number=self.production_branch_number
        )
        output_branch_data = OutputBranchData(
            identifier=output_branch_identifier,
            parent_output_identifier=upstream_new_production_order.starting_node_output_branch_data.parent_output_identifier,
            parent_input_identifier=upstream_new_production_order.starting_node_output_branch_data.parent_input_identifier,
            dict_of_complete_stream_branch={},
            production_branch_production_plan=OutputBranchProductionPlan(),
        )
        complete_branch_data = CompleteOutputBranchData(
            output_branch_data=output_branch_data,
            start_time=upstream_new_production_order.stream_state.start_time,
            end_time=upstream_new_production_order.stream_state.end_time,
        )
        return complete_branch_data

    def process_input_order(
        self, input_node_operation: NodeOperation
    ) -> DownstreamValidationOrder:
        logger.debug(
            "Input order: %s is processed in source: %s",
            input_node_operation,
            self.name,
        )
        if isinstance(input_node_operation, UpstreamNewProductionOrder):
            self.list_of_output_stream_states.append(input_node_operation.stream_state)
            down_stream_validation = self.create_downstream_validation_operation(
                upstream_new_production_order=input_node_operation
            )
        else:
            raise Exception(
                "Unexpected node operation "
                + str(input_node_operation)
                + " in Source: "
                + str(self.name)
            )
        return down_stream_validation

    def create_production_order_collection_from_input_states(
        self,
    ) -> OrderCollection:
        order_number = 0
        production_order_dict = {}
        for stream_state in reversed(self.list_of_output_stream_states):
            stream = self.stream_handler.get_stream(stream_name=stream_state.name)
            total_stream_mass = stream.get_produced_amount(state=stream_state)
            production_order = ProductionOrder(
                production_target=total_stream_mass,
                production_deadline=stream_state.start_time,
                order_number=order_number,
                commodity=stream.static_data.commodity,
            )
            production_order_dict[order_number] = production_order
            order_number = order_number + 1
        order_data_frame = pandas.DataFrame(data=list(production_order_dict.values()))
        order_data_frame.sort_values(
            by="production_deadline", ascending=False, inplace=True
        )
        order_data_frame.reset_index(inplace=True, drop=True)

        target_mass = order_data_frame.loc[:, ["production_target"]].sum()[
            "production_target"
        ]
        order_collection = OrderCollection(
            target_mass=target_mass,
            commodity=self.commodity,
            order_data_frame=order_data_frame,
        )
        return order_collection

    def create_downstream_validation_operation(
        self, upstream_new_production_order: UpstreamNewProductionOrder
    ) -> DownstreamValidationOrder:
        down_stream_node_name = self.get_downstream_node_name()
        complete_branch_data = self.create_complete_branch_data(
            upstream_new_production_order=upstream_new_production_order
        )
        incoming_stream_branch: IncompleteStreamBranchData = (
            upstream_new_production_order.starting_node_output_branch_data.current_stream_branch
        )
        down_stream_validation = DownstreamValidationOrder(
            next_node_name=down_stream_node_name,
            starting_node_name=self.name,
            starting_node_output_branch_data=complete_branch_data,
            target_node_output_branch_identifier=upstream_new_production_order.starting_node_output_branch_data.identifier,
            target_node_temporal_identifier=incoming_stream_branch.identifier,
            production_order=upstream_new_production_order.production_order,
        )
        logger.debug(
            "A new down stream validation operation has been created in: %s . Next node is: %s",
            self.name,
            down_stream_node_name,
        )
        return down_stream_validation

    def get_input_stream_name(self) -> None:
        return None

    def get_output_stream_name(self) -> str:
        return self.current_output_stream_name
