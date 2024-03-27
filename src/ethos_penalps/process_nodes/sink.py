import datetime
from abc import ABC, abstractmethod

from ethos_penalps.data_classes import (
    Commodity,
    OrderCollection,
    OutputBranchIdentifier,
    ProcessChainIdentifier,
    StaticTimePeriod,
    StreamBranchIdentifier,
    TemporalBranchIdentifier,
)
from ethos_penalps.load_profile_calculator import LoadProfileHandlerSimulation
from ethos_penalps.node_operations import (
    DownstreamAdaptionOrder,
    DownstreamValidationOrder,
    NodeOperation,
    ProductionOrder,
    TerminateProduction,
    UpstreamAdaptionOrder,
    UpstreamNewProductionOrder,
)
from ethos_penalps.petri_net.process_state_handler import ProcessStateHandler
from ethos_penalps.process_node_communicator import EmptyProductionBranch
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.production_plan import OutputBranchProductionPlan, ProductionPlan
from ethos_penalps.simulation_data.simulation_data_branch import (
    CompleteOutputBranchData,
    CompleteStreamBranchData,
    CompleteTemporalBranchData,
    IncompleteOutputBranchData,
    IncompleteStreamBranchData,
    OutputBranchData,
    StreamBranchData,
    TemporalBranchData,
)
from ethos_penalps.storage import BaseStorage
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamProductionPlanEntry,
    BatchStreamState,
    ContinuousStream,
    ContinuousStreamProductionPlanEntry,
    ContinuousStreamState,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.stream_node_distributor import (
    OrderDistributor,
)
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.exceptions_and_warnings import MisconfigurationError
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class Sink(ProcessNode):
    """The sink is the target of the material flow system.
    It contains all orders for products that should be created during the simulation.
    """

    def __init__(
        self,
        name: str,
        commodity: Commodity,
        stream_handler: StreamHandler,
        production_plan: ProductionPlan,
        time_data: TimeData,
        order_collection: OrderCollection | None = None,
    ) -> None:
        """

        Args:
            name (str): Name of the sink that is used for
                for display and identification. Must be unique.
            commodity (Commodity): The commodity that is stored
                in the sink.
            stream_handler (StreamHandler): Contains all streams
                that are connected to the stream.
            production_plan (ProductionPlan): Is used to store the stream states
                storage states.
            time_data (TimeData): Provides the simulation end date which that is
                required to determine thr start and end date for the storage.
            order_collection (OrderCollection | None, optional): Contains all
                order that are fulfilled during the simulation. Defaults to None.
        """
        super().__init__(stream_handler=stream_handler, name=name)
        self.commodity: Commodity = commodity
        if order_collection is None:
            self.order_collection: OrderCollection = OrderCollection(
                target_mass=0, commodity=commodity
            )
        else:
            self.order_collection: OrderCollection = order_collection
        self.input_stream_state_list: list[ContinuousStreamState] = []
        self.current_input_stream_state: ContinuousStreamState
        self.production_plan: ProductionPlan = production_plan
        self.production_branch_number: float = 0
        self.temporal_branch_number: float = 0
        self.current_production_branch_identifier: OutputBranchIdentifier
        self.current_temporal_branch_identifier: TemporalBranchIdentifier
        self.order_distributor: OrderDistributor = OrderDistributor(
            stream_handler=self.stream_handler,
            production_order_collection=self.order_collection,
            node_name=name,
        )
        self.storage: BaseStorage = BaseStorage(
            process_step_name=name,
            commodity=commodity,
            stream_handler=stream_handler,
            input_to_output_conversion_factor=1,
        )
        self.time_data: TimeData = time_data

    def __str__(self) -> str:
        return "Sink: " + self.name

    def check_if_sink_has_orders(self):
        """Checks if the sink has orders which indicates
        an ill defined simulation.
        """
        if self.order_collection.order_data_frame.empty:
            raise MisconfigurationError(
                "Sink: "
                + self.name
                + " has no orders in its dictionary. A sink required at least one order."
            )

    def plan_production(self) -> UpstreamNewProductionOrder:
        """Creates the next Upstream production order to fulfill the next order.

        Returns:
            UpstreamNewProductionOrder: Next UpstreamNewProductionOrder that
                is requests a new input stream state for the sink.
        """
        logger.debug("Plan production has been called in sink: %s", self.name)
        current_production_order = self.order_distributor.get_current_production_order()

        input_stream_state = self.convert_order_to_stream(
            production_order=current_production_order
        )

        self.current_input_stream_state = input_stream_state
        upstream_order = self.create_upstream_new_production_operation(
            input_stream_state=input_stream_state,
            production_order=current_production_order,
        )

        return upstream_order

    def convert_order_to_stream(
        self, production_order: ProductionOrder
    ) -> ContinuousStreamState | BatchStreamState:
        """Converts an order into stream that can be requested from
        the upstream node.

        Args:
            production_order (ProductionOrder): Contains a target mass
                and deadline for a product that is required by the sink.

        Returns:
            ContinuousStreamState | BatchStreamState: Stream that attempts
                to fulfill the production order.
        """
        logger.debug("Production order is converted  %s", production_order)

        input_stream = self.stream_handler.get_stream(
            self.order_distributor.get_current_stream_name()
        )
        production_target = (
            production_order.production_target - production_order.produced_mass
        )
        if production_target < 0:
            raise Exception(
                "Production target got miss calculated: " + str(production_target)
            )
        stream_state: ContinuousStreamState | BatchStreamState
        # calculate start time
        if isinstance(input_stream, ContinuousStream):
            stream_state = input_stream.create_stream_state_for_commodity_amount(
                commodity_amount=production_target,
                end_time=production_order.production_deadline,
                operation_rate=input_stream.static_data.maximum_operation_rate,
            )

        elif isinstance(input_stream, BatchStream):
            possible_batch_mass = input_stream.consider_maximum_batch_mass(
                target_batch_mass=production_target
            )
            stream_state = input_stream.create_batch_state(
                end_time=production_order.production_deadline,
                batch_mass_value=possible_batch_mass,
            )
        if stream_state.start_time == stream_state.end_time:
            raise Exception(
                "Created an infinitesimal short input stream in sink: ", self.name
            )

        logger.debug(
            "Created stream: %s",
            stream_state,
        )
        return stream_state

    def create_storage_entries(
        self,
        list_of_output_stream_states: (
            list[ContinuousStreamState | BatchStreamState] | None
        ) = None,
    ):
        """Creates the storage entries based on the output streams provided as an argument.

        Args:
            list_of_output_stream_states (list[ContinuousStreamState  |  BatchStreamState]  |  None, optional):
                list of storage entries that should be used to create storage entries. Defaults to None.
        """
        if list_of_output_stream_states is None:
            list_of_output_stream_states = []

        # total_input_mass = self.storage.determine_net_mass(
        #     list_of_input_stream_states=self.input_stream_state_list,
        #     list_of_output_stream_states=[],
        # )
        # self.storage.current_storage_level = total_input_mass

        list_of_storage_entries = self.storage.create_storage_entries_from_start_to_end(
            last_storage_update_time=self.time_data.global_start_date,
            list_of_input_stream_states=self.input_stream_state_list,
            list_of_output_stream_states=list_of_output_stream_states,
        )
        self.production_plan.add_list_of_storage_entries(
            storage_name=self.name,
            commodity=self.commodity,
            list_of_storage_entries=list_of_storage_entries,
        )

    def process_input_order(
        self,
        input_node_operation: DownstreamAdaptionOrder | DownstreamValidationOrder,
    ) -> UpstreamNewProductionOrder | UpstreamAdaptionOrder | TerminateProduction:
        """Handles the received input orders of the Process Step. These can either validate a previously requested stream
        or requests an adaption. An adaption request is always accepted. When an input stream has been validated
        it is checked if more mass must be requested.

        Args:
            input_node_operation (DownstreamAdaptionOrder | DownstreamValidationOrder): On a DownstreamValidationOrder
                it is checked if another input stream must be requested or if the simulation is terminated for the chain.
                On a DownstreamAdaptionOrder the order is updated the requested stream state is updated.


        Returns:
            UpstreamNewProductionOrder | UpstreamAdaptionOrder | TerminateProduction: The UpstreamNewProductionOrder requests
                new input stream. The UpstreamAdaptionOrder confirms that the adaption request is accepted and the terminate
                production signals that simulation is terminated for current process chain.
        """
        logger.debug(
            "Input order: %s is processes in sink: %s", input_node_operation, self.name
        )
        if isinstance(
            input_node_operation,
            DownstreamValidationOrder,
        ):
            self.update_production_order(
                validated_input_stream_state=self.current_input_stream_state,
            )
            order_is_fulfilled = (
                self.order_distributor.check_if_current_order_is_fulfilled()
            )
            if order_is_fulfilled:
                self.order_distributor.update_current_order_number()

            self.store_input_streams_to_production_plan()
            chain_is_satisfied = (
                self.order_distributor.check_if_process_chain_orders_are_satisfied()
            )
            if chain_is_satisfied is True:
                output_node_operation = TerminateProduction(
                    next_node_name=None, starting_node_name=self.name
                )

                logger.debug("All orders are processed and production is terminated")
            elif chain_is_satisfied is False:
                output_node_operation = self.plan_production()

            else:
                raise Exception(
                    "Unexpected order number: ",
                    self.order_distributor.current_splitted_order.current_order_number,
                )
        elif isinstance(input_node_operation, DownstreamAdaptionOrder):
            output_node_operation = self.create_upstream_adaption_operation(
                downstream_adaption_operation=input_node_operation,
            )

        else:
            raise Exception(
                "Unexpected node operation "
                + str(input_node_operation)
                + " in process step: "
                + str(self.name)
            )

        return output_node_operation

    def update_production_order(
        self,
        validated_input_stream_state: ContinuousStreamState | BatchStreamState,
    ):
        """Updates the mass that has been delivered for the current order.

        Args:
            validated_input_stream_state (ContinuousStreamState | BatchStreamState): The
                new stream that has been validated.
        """
        logger.debug("Start production order update")
        input_stream = self.stream_handler.get_stream(
            stream_name=validated_input_stream_state.name
        )
        produced_mass = input_stream.get_produced_amount(
            state=validated_input_stream_state
        )
        self.order_distributor.update_production_order(produced_mass=produced_mass)

    def store_input_streams_to_production_plan(self):
        """Store the current input stream to the production plan
        because it has been validated.
        """
        stream_state = self.current_input_stream_state

        self.input_stream_state_list.append(stream_state)
        stream = self.stream_handler.get_stream(stream_name=stream_state.name)

        stream_production_plan_entry = stream.create_production_plan_entry(
            state=stream_state
        )
        self.production_plan.stream_state_dict[stream_state.name].append(
            stream_production_plan_entry
        )
        self.create_load_profile_entry(stream_entry=stream_production_plan_entry)
        del self.current_input_stream_state

    def create_upstream_adaption_operation(
        self, downstream_adaption_operation: DownstreamAdaptionOrder
    ) -> UpstreamAdaptionOrder:
        """Creates an UpstreamAdaptionOrder that confirms the adaption request that
        was passed to the sink.

        Args:
            downstream_adaption_operation (DownstreamAdaptionOrder): Requests
                an adaption of the previously requested stream.

        Returns:
            UpstreamAdaptionOrder: Confirms the adaption request that
        was passed to the sink.
        """
        self.current_input_stream_state = downstream_adaption_operation.stream_state
        upstream_adaption_operation = UpstreamAdaptionOrder(
            starting_node_name=self.name,
            next_node_name=self.get_upstream_node_name(),
            stream_state=downstream_adaption_operation.stream_state,
            production_order=downstream_adaption_operation.production_order,
            starting_node_output_branch_data=downstream_adaption_operation.target_node_output_branch_data,
            target_node_output_branch_data=downstream_adaption_operation.starting_node_output_branch_data,
        )
        return upstream_adaption_operation

    def create_upstream_new_production_operation(
        self,
        input_stream_state: ContinuousStreamState | BatchStreamState,
        production_order: ProductionOrder,
    ) -> UpstreamNewProductionOrder:
        """Creates a request for an input stream to fulfill a production order.

        Args:
            input_stream_state (ContinuousStreamState | BatchStreamState): The
                stream state that should be requested.
            production_order (ProductionOrder): The order that should be fulfilled
                by the stream.

        Returns:
            UpstreamNewProductionOrder: The order that requests the input stream from the
                upstream node.
        """
        incomplete_output_branch_data = self.create_branch_data()

        upstream_production_order = UpstreamNewProductionOrder(
            starting_node_name=self.name,
            next_node_name=self.get_upstream_node_name(),
            stream_state=input_stream_state,
            production_order=production_order,
            starting_node_output_branch_data=incomplete_output_branch_data,
        )
        return upstream_production_order

    def create_branch_data(self) -> IncompleteOutputBranchData:
        """Creates the branch data that is required by the
        UpstreamNewProductionOrder.

        Returns:
            IncompleteOutputBranchData: Contains information about the
                order and branches that have been created to
                fulfill the order.
        """
        current_input_branch_identifier = TemporalBranchIdentifier(
            branch_number=self.temporal_branch_number
        )
        current_temporal_branch_data = TemporalBranchData(
            identifier=current_input_branch_identifier
        )
        current_stream_name = self.order_distributor.get_current_stream_name()
        stream_branch_identifier = StreamBranchIdentifier(
            stream_name=current_stream_name
        )
        incomplete_stream_branch_data = IncompleteStreamBranchData(
            identifier=stream_branch_identifier,
            list_of_complete_input_branches=[],
            current_incomplete_input_branch=current_temporal_branch_data,
        )
        current_output_branch_identifier = OutputBranchIdentifier(
            branch_number=self.production_branch_number
        )
        branch_data = IncompleteOutputBranchData(
            parent_output_identifier=None,
            parent_input_identifier=None,
            dict_of_complete_stream_branch={},
            production_branch_production_plan=OutputBranchProductionPlan,
            current_stream_branch=incomplete_stream_branch_data,
            identifier=current_output_branch_identifier,
        )
        self.temporal_branch_number = self.temporal_branch_number + 1
        self.production_branch_number = self.production_branch_number + 1
        return branch_data

    def create_new_production_branch_identifier(self) -> OutputBranchIdentifier:
        """Creates a new production branch identifier that identifies
        the output stream was requested.

        Returns:
            OutputBranchIdentifier: Identifies that data was created
                to provide an output stream.
        """
        production_branch_identifier = OutputBranchIdentifier(
            branch_number=self.production_branch_number
        )
        self.production_branch_number = self.production_branch_number + 1
        return production_branch_identifier

    def create_new_temporal_branch_identifier(self) -> TemporalBranchIdentifier:
        """Creates the data that was created to request an input stream.

        Returns:
            TemporalBranchIdentifier: Identifies an output stream.
        """
        temporal_branch_identifier = TemporalBranchIdentifier(
            branch_number=self.temporal_branch_number
        )
        self.temporal_branch_number = self.temporal_branch_number + 1
        return temporal_branch_identifier

    def add_input_stream(
        self,
        input_stream: ContinuousStream | BatchStream,
        process_chain_identifier: ProcessChainIdentifier,
    ):
        """Adds an input stream to the sink. This is required for
        a well defined process model.

        Args:
            input_stream (ContinuousStream | BatchStream): Stream that connects
                the upstream node to this sink.
            process_chain_identifier (ProcessChainIdentifier): Identifies the chain
                of the upstream node.

        """
        if not isinstance(input_stream, (ContinuousStream, BatchStream)):
            raise Exception(
                "Expected input stream of type ContinuousStream but got type: "
                + str(type(input_stream))
            )
        self.order_distributor.add_stream_name(
            stream_name=input_stream.name,
            process_chain_identifier=process_chain_identifier,
        )

    def get_upstream_node_name(self) -> str:
        """Returns the name of the node upstream of the sink of the currently active
        process chain.

        Returns:
            str: Name of the node upstream of the sink of the currently active
            process chain
        """
        input_stream = self.stream_handler.get_stream(
            self.order_distributor.get_current_stream_name()
        )
        upstream_node_name = input_stream.get_upstream_node_name()
        return upstream_node_name

    def get_input_stream_name(self) -> str:
        """Returns the name of the active input stream

        Returns:
            str: Name of the active input stream
        """
        return self.order_distributor.get_current_stream_name()

    def create_load_profile_entry(self, stream_entry):
        """Creates the load profile from a stream entry.

        Args:
            stream_entry (_type_): Stream entry that should be converted
                into a load profile. Requires the energy data to be set.

        """
        self.production_plan.load_profile_handler.create_all_load_profiles_entries_from_stream_entry(
            stream_entry=stream_entry
        )

    def get_order_from_parent_source(
        self, order_collection_from_source: OrderCollection
    ):
        """Adds the orders from a source to the current sink. Is only
        used if the sink is part of Storage.

        Args:
            order_collection_from_source (OrderCollection): Orders
                that should be added this sink.
        """
        self.order_distributor.update_order_collection(
            new_order_collection=order_collection_from_source
        )

    def initialize_sink(self):
        """Aggregates and splits the orders of this sink."""
        self.order_distributor.split_production_order_dict()

    def prepare_sink_for_next_chain(
        self, process_chain_identifier: ProcessChainIdentifier
    ):
        """Sets a new process chain as the active chain to be
        simulated.

        Args:
            process_chain_identifier (ProcessChainIdentifier): Identifier
                of the active simulated process chain.
        """
        self.order_distributor.set_current_splitted_order_by_chain_identifier(
            process_chain_identifier=process_chain_identifier
        )
        self.production_branch_number: float = 0
        self.temporal_branch_number: float = 0
        if hasattr(self, "current_production_branch_identifier"):
            del self.current_production_branch_identifier
        if hasattr(self, "current_temporal_branch_identifier"):
            del self.current_temporal_branch_identifier

    def get_stream_to_process_chain(
        self, process_chain_identifier: ProcessChainIdentifier
    ) -> BatchStream | ContinuousStream:
        """Returns the stream of the  ProcessChain of interest.

        Args:
            process_chain_identifier (ProcessChainIdentifier): Identifies
                the ProcessChain that contains the stream of interest.

        Returns:
            BatchStream | ContinuousStream: Stream that connects the process chain
                and the sink.
        """
        stream_name = self.order_distributor.get_stream_name_chain_identifier(
            process_chain_identifier=process_chain_identifier
        )
        stream = self.stream_handler.get_stream(stream_name=stream_name)
        return stream

    def get_output_stream_name(self) -> None:
        """Does return none because the sink does not have an output stream."""
        return None
