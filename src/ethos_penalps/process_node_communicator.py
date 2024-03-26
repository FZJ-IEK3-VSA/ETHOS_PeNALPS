import datetime
import uuid
from dataclasses import dataclass

from ethos_penalps.data_classes import (
    OutputBranchIdentifier,
    StaticTimePeriod,
    TemporalBranchIdentifier,
)
from ethos_penalps.mass_balance import MassBalance
from ethos_penalps.node_operations import (
    DownstreamAdaptionOrder,
    DownstreamValidationOrder,
    ProductionOrder,
    UpstreamAdaptionOrder,
    UpstreamNewProductionOrder,
)
from ethos_penalps.process_state import OutputStreamProvidingState
from ethos_penalps.process_state_handler import ProcessStateHandler
from ethos_penalps.process_state_network_navigator import (
    OutputStreamAdaptionDecider,
    ProcessStateNetworkNavigator,
)
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.simulation_data.container_branch_data import (
    CompleteTemporalBranchData,
    IncompleteOutputBranchData,
    TemporalBranchData,
)
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamState,
    ContinuousStream,
    ContinuousStreamState,
)
from ethos_penalps.utilities.exceptions_and_warnings import (
    IllogicalFunctionCall,
    IllogicalSimulationState,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class ProcessNodeCommunicator:
    """The ProcessNodeCommunicator manages the communication of the ProcessStep.

    It creates and reacts to the following communication types:

        - UpstreamNewProductionOrder:
            Requests a new output stream state from the target node
        - DownstreamValidationOrder
            Affirms that an output stream will be provided as requested.
        - DownstreamAdaptionOrder
            Requests an adaption of the previously requested stream.
        - UpstreamAdaptionOrder
            Affirms the adaption of the previously requested stream.

    """

    def __init__(
        self,
        production_plan: ProductionPlan,
        process_state_handler: ProcessStateHandler,
    ) -> None:
        """

        Args:
            production_plan (ProductionPlan): Is used to store all the activity of the
                process step and its input stream during simulation. The ProductionPlan
                instance is shared amon all nodes.
            process_state_handler (ProcessStateHandler): Is a container class that is used
                to store all ContinuosStreams and BatchStreams.
        """
        self.output_stream_state: ContinuousStreamState | BatchStreamState
        self.production_plan: ProductionPlan = production_plan
        self.process_state_handler: ProcessStateHandler = process_state_handler
        self.process_state_navigator: ProcessStateNetworkNavigator = (
            ProcessStateNetworkNavigator(
                production_plan=self.production_plan,
                process_state_handler=process_state_handler,
            )
        )

    def check_if_temporal_branches_are_fulfilled(self):
        """Checks is all requests for input streams have been validated. This
        is  a check for a faulty simulation."""
        all_temporal_branch_are_fulfilled = True

        output_branch_data = (
            self.process_state_handler.process_step_data.state_data_container.get_output_branch_data()
        )
        for stream_branch in output_branch_data.dict_of_complete_stream_branch.values():
            if not stream_branch.list_of_complete_input_branches:
                raise IllogicalSimulationState("No stream branches available to check")
            for temporal_branch in stream_branch.list_of_complete_input_branches:
                if not stream_branch.list_of_complete_input_branches:
                    raise IllogicalSimulationState(
                        "No temporal branches available to check"
                    )
                if type(temporal_branch) is not CompleteTemporalBranchData:
                    all_temporal_branch_are_fulfilled = False

        logger.debug(
            "Temporal branches are fulfilled: %s", all_temporal_branch_are_fulfilled
        )
        if all_temporal_branch_are_fulfilled is False:
            raise IllogicalSimulationState(
                "Not all temporal branches are validated even though they should be"
            )

    def check_if_stream_branch_is_fulfilled(self) -> bool:
        """Check if all different streams have been requested and can be provided
        as requested. This method is still in development.

        Returns:
            bool: Returns True if all Streams can be provided as requested.
        """
        input_stream_providing_state = (
            self.process_state_handler.get_input_stream_providing_state()
        )
        stream_branch_if_fulfilled = (
            input_stream_providing_state.determine_if_stream_branch_if_fulfilled()
        )

        logger.debug(
            "Stream branch is already fulfilled: %s",
            stream_branch_if_fulfilled,
        )
        return stream_branch_if_fulfilled

    def check_if_production_branch_is_fulfilled(self) -> bool:
        """Determines if enough input streams have been requested to provide
        the requested OutputStreamState

        Returns:
            bool: Returns true if enough input stream states have been requested.
        """
        input_stream_providing_state = (
            self.process_state_handler.get_input_stream_providing_state()
        )
        production_branch_if_fulfilled = (
            input_stream_providing_state.determine_if_production_branch_is_fulfilled()
        )

        logger.debug(
            "Production branch is already fulfilled: %s",
            production_branch_if_fulfilled,
        )
        return production_branch_if_fulfilled

    def complete_stream_branch(self):
        """Confirms that a stream branch is fulfilled."""
        self.process_state_handler.process_step_data.state_data_container.complete_stream_branch()

    def complete_temporal_branch(self):
        """Confirms that a temporal branch is fulfilled."""
        self.process_state_navigator.process_state_handler.process_step_data.state_data_container.complete_temporal_branch()

    def complete_output_branch(self):
        """Prepares the simulation data for the next output stream request,
        when all necessary input streams are requested.
        """
        self.process_state_navigator.process_state_handler.process_step_data.state_data_container.complete_output_branch()
        self.process_state_handler.switch_to_idle_state()
        self.process_state_navigator.create_process_state_entries()
        self.process_state_handler.process_step_data.state_data_container.clear_up_after_input_branch()
        self.store_branch_to_production_plan()

    def process_downstream_adaption_order(
        self,
        downstream_adaption_operation: DownstreamAdaptionOrder,
        next_node_name: str,
        starting_node_name: str,
    ) -> UpstreamAdaptionOrder:
        """This method is called when the upstream node requires an adaption of this node.
        The current temporal branch is reset and the process states are set to harmonize the
        input and output stream state. After successful harmonization an UpstreamAdaptionOrder is created.

        Args:
            downstream_adaption_operation (DownstreamAdaptionOrder):  The DownstreamAdaptionOrder contains information about
                a possible input stream state. This order is created when the input stream state requested in a
                UpstreamNewProductionOrder can not provided by the upstream order.
            next_node_name (str): Name of the upstream node. It is required to create the next UpstreamAdaptionOrder
            starting_node_name (str): Name of the current node.

        Returns:
            UpstreamAdaptionOrder: The next Order that confirms the adaption of the previously
                requested output stream.
        """

        logger.debug("Start to process downstream adaption order")

        starting_node_output_branch_data = (
            self.process_state_handler.process_step_data.state_data_container.get_incomplete_branch_data()
        )

        input_stream_state = (
            self.process_state_navigator.combine_input_and_output_stream(
                new_input_stream_state=downstream_adaption_operation.stream_state
            )
        )

        upstream_production_order = UpstreamAdaptionOrder(
            next_node_name=next_node_name,
            starting_node_name=starting_node_name,
            stream_state=input_stream_state,
            production_order=downstream_adaption_operation.production_order,
            starting_node_output_branch_data=starting_node_output_branch_data,
            target_node_output_branch_data=downstream_adaption_operation.target_node_output_branch_data,
        )
        return upstream_production_order

    def process_downstream_validation_operation(
        self,
        downstream_validation_operation: DownstreamValidationOrder,
        upstream_node_name: str,
        downstream_node_name: str,
    ) -> DownstreamValidationOrder | UpstreamNewProductionOrder:
        """Checks if further input streams must be requested to fulfill the request of the output streams
        that was passed to this node.

        Args:
            downstream_validation_operation (DownstreamValidationOrder): The incoming DownstreamValidationOrder
                from the Upstream Node.
            upstream_node_name (str): Name of the UpstreamNode.
            downstream_node_name (str): Name of the DownstreamNode.

        Returns:
            DownstreamValidationOrder | UpstreamNewProductionOrder: The next order is either the
                a DownstreamValidationOrder or a UpstreamNewProductionOrder. The DownstreamValidationOrder
                is passed Downstream, when enough input stream states have been requested. A UpstreamNewProductionOrder
                is passed Upstream if further input streams are required.
        """
        self.process_state_navigator.validate_temporal_branch()
        self.check_if_temporal_branches_are_fulfilled()

        stream_branch_is_fulfilled = self.check_if_stream_branch_is_fulfilled()
        output_operation: DownstreamValidationOrder | UpstreamNewProductionOrder
        if stream_branch_is_fulfilled:
            self.complete_stream_branch()
            production_branch_is_fulfilled = (
                self.check_if_production_branch_is_fulfilled()
            )

            if production_branch_is_fulfilled is True:
                output_operation = self.create_downstream_validation_order(
                    downstream_node_name=downstream_node_name,
                    starting_node_name=self.process_state_navigator.process_state_handler.process_step_data.process_step_name,
                    input_production_order=downstream_validation_operation,
                )

            elif production_branch_is_fulfilled is False:
                raise NotImplementedError

        else:
            output_operation = self.fulfill_stream_branch(
                next_node_name=upstream_node_name,
                starting_node_name=self.process_state_navigator.process_state_handler.process_step_data.process_step_name,
                downstream_validation_operation=downstream_validation_operation,
            )

        logger.debug("Start to check if production branch is fulfilled")

        return output_operation

    def process_upstream_new_production_operation(
        self,
        starting_node_name: str,
        upstream_node_name: str,
        downstream_node_name: str,
        upstream_production_order: UpstreamNewProductionOrder,
    ) -> (
        UpstreamNewProductionOrder | DownstreamAdaptionOrder | DownstreamValidationOrder
    ):
        """Determines if the current node can provide the requested output stream.
        If the required state can be provided the required input is requested by a new
        UpstreamNewProductionOrder. If the requested state can not be provided an adaption
        of the output stream is requested by the creation of a UpstreamNewProductionOrder.
        Initializes the production branch.

        Args:
            starting_node_name (str): Current process step name
            upstream_node_name: (str): Name of the upstream node
            downstream_node_name: (str): Name of the downstream node.
            upstream_production_order: (UpstreamNewProductionOrder): Input order that triggered
                the call of this method.


        Returns:
            UpstreamNewProductionOrder | DownstreamAdaptionOrder | DownstreamValidationOrder: The next
            order is either a UpstreamNewProductionOrder, DownstreamAdaptionOrder or a DownstreamValidationOrder.
            The UpstreamNewProductionOrder is created if an additional input stream is required. The
            DownstreamAdaptionOrder is created if the requested output stream must be shifted. The
            DownstreamValidationOrder is requested if the output stream can be provided from the internal
            storage.
        """

        if not isinstance(upstream_production_order, UpstreamNewProductionOrder):
            raise Exception(
                "Did not expect: " + upstream_production_order + " as input operation"
            )
        self.process_state_handler.prepare_for_new_production_branch(
            new_output_stream_state=upstream_production_order.stream_state,
            incomplete_output_branch_data=upstream_production_order.starting_node_output_branch_data,
        )
        self.process_state_handler.process_step_data.state_data_container.prepare_new_stream_branch(
            stream_name=self.process_state_handler.process_step_data.main_mass_balance.main_input_stream_name
        )
        self.process_state_handler.process_step_data.state_data_container.prepare_new_temporal_branch()
        self.process_state_navigator.store_current_simulation_data()
        output_stream_adaption_decider = (
            self.process_state_navigator.determine_if_output_stream_requires_adaption()
        )

        new_production_order: (
            UpstreamNewProductionOrder
            | DownstreamAdaptionOrder
            | DownstreamValidationOrder
        )
        if output_stream_adaption_decider.adaption_is_necessary is True:
            logger.debug("Adaption of output stream is necessary")

            new_production_order = self.create_downstream_adaption_order(
                starting_node_name=starting_node_name,
                down_stream_node_name=downstream_node_name,
                upstream_production_order=upstream_production_order,
            )

        elif output_stream_adaption_decider.adaption_is_necessary is False:
            logger.debug("Adaption of output stream is not necessary")
            output_stream_providing_state = (
                self.process_state_handler.get_output_stream_providing_state()
            )
            storage_can_be_supplied_directly = (
                output_stream_providing_state.check_if_storage_can_supply_output_directly()
            )

            if storage_can_be_supplied_directly is False:
                new_production_order = self.create_next_upstream_production_order(
                    next_node_name=upstream_node_name,
                    starting_node_name=starting_node_name,
                    input_upstream_production_order=upstream_production_order,
                )
            else:
                self.process_state_navigator.provide_output_stream_from_storage()
                self.process_state_navigator.validate_temporal_branch_without_input_stream()

                new_production_order = self.create_downstream_validation_order(
                    downstream_node_name=downstream_node_name,
                    starting_node_name=starting_node_name,
                    input_production_order=upstream_production_order,
                )

        return new_production_order

    def process_upstream_adaption_operation(
        self,
        starting_node_name: str,
        upstream_node_name: str,
        upstream_adaption_operation: UpstreamAdaptionOrder,
    ) -> UpstreamNewProductionOrder | DownstreamValidationOrder:
        """Determines the required input stream to an output stream which has been adapted before.

        Args:
            starting_node_name (str): Name of the current node.
            upstream_node_name (str): Name of the upstream node that receives the new order.
            upstream_adaption_operation (UpstreamAdaptionOrder): The input order
                that causes the new output order.

        Returns:
            UpstreamNewProductionOrder | DownstreamValidationOrder: This methods either creates
                either a UpstreamNewProductionOrder or a DownstreamValidationOrder. The UpstreamNewProductionOrder
                is created if an additional input stream is required. The DownstreamValidationOrder is created if
                a sufficient input streams have been requested to provide the output stream state.

        """

        output_stream_providing_state = (
            self.process_state_handler.get_output_stream_providing_state()
        )
        storage_can_be_supplied_directly = (
            output_stream_providing_state.check_if_storage_can_supply_output_directly()
        )
        new_production_order: DownstreamValidationOrder | UpstreamNewProductionOrder
        if storage_can_be_supplied_directly is True:
            self.process_state_navigator.provide_output_stream_from_storage()
            self.process_state_navigator.validate_temporal_branch_without_input_stream()
            new_production_order = DownstreamValidationOrder(
                next_node_name=upstream_adaption_operation.starting_node_name,
                starting_node_name=starting_node_name,
                starting_node_output_branch_data=upstream_adaption_operation.target_node_output_branch_data,
                target_node_output_branch_identifier=upstream_adaption_operation.starting_node_output_branch_data.parent_output_identifier,
                target_node_temporal_identifier=upstream_adaption_operation.starting_node_output_branch_data.parent_input_identifier,
                production_order=upstream_adaption_operation.production_order,
            )

        else:
            input_stream_state = (
                self.process_state_navigator.determine_input_stream_from_output_stream()
            )

            new_production_order = UpstreamNewProductionOrder(
                next_node_name=upstream_node_name,
                starting_node_name=starting_node_name,
                stream_state=input_stream_state,
                production_order=upstream_adaption_operation.production_order,
                starting_node_output_branch_data=upstream_adaption_operation.target_node_output_branch_data,
            )
        return new_production_order

    def create_downstream_adaption_order(
        self,
        starting_node_name: str,
        down_stream_node_name: str,
        upstream_production_order: UpstreamNewProductionOrder,
    ) -> DownstreamAdaptionOrder:
        """Creates a DownStreamAdaptionOrder that adapts of the output stream
        state that was requested from the downstream node.

        Args:
            starting_node_name (str): Name of the current node.
            down_stream_node_name (str): Name of the downstream node that receives the new
                order.
            upstream_production_order (UpstreamNewProductionOrder): The incoming order.

        Returns:
            DownstreamAdaptionOrder: Order that adapts of the output stream
        state that was requested from the downstream node.

        """

        state_data = (
            self.process_state_handler.process_step_data.state_data_container.get_pre_production_state_data()
        )
        starting_node_branch_data = (
            self.process_state_handler.process_step_data.state_data_container.get_output_branch_data()
        )

        return DownstreamAdaptionOrder(
            next_node_name=down_stream_node_name,
            starting_node_name=starting_node_name,
            stream_state=state_data.current_output_stream_state,
            production_order=upstream_production_order.production_order,
            starting_node_output_branch_data=starting_node_branch_data,
            target_node_output_branch_data=upstream_production_order.starting_node_output_branch_data,
        )

    def create_next_upstream_production_order(
        self,
        next_node_name: str,
        starting_node_name: str,
        input_upstream_production_order: UpstreamNewProductionOrder,
    ) -> UpstreamNewProductionOrder:
        """Creates an UpstreamNewProduction order that requests an output stream of the
        upstream node.

        Args:
            next_node_name (str): Name of the upstream node, that receives the upstream
                order.
            starting_node_name (str): Name of the current node.
            input_upstream_production_order (UpstreamNewProductionOrder): Order that
                requested the current output stream.

        Returns:
            UpstreamNewProductionOrder: Order that requests an output stream of the
        upstream node.
        """
        input_stream_state = (
            self.process_state_navigator.determine_input_stream_from_output_stream()
        )
        incomplete_output_branch_data = (
            self.process_state_handler.process_step_data.state_data_container.get_incomplete_branch_data()
        )

        upstream_production_order = UpstreamNewProductionOrder(
            next_node_name=next_node_name,
            starting_node_name=starting_node_name,
            stream_state=input_stream_state,
            production_order=input_upstream_production_order.production_order,
            starting_node_output_branch_data=incomplete_output_branch_data,
        )
        return upstream_production_order

    def store_branch_to_production_plan(self):
        temporary_production_plan = (
            self.process_state_navigator.process_state_handler.process_step_data.state_data_container.get_temporary_production_plan()
        )
        self.production_plan.add_temporary_production_plan(
            temporary_production_plan=temporary_production_plan
        )

        self.production_plan.convert_temporary_production_plan_to_load_profile(
            temporary_production_plan=temporary_production_plan
        )

        logger.debug("Production branch is stored to production plan")

    def fulfill_stream_branch(
        self,
        next_node_name: str,
        starting_node_name: str,
        downstream_validation_operation: DownstreamValidationOrder,
    ) -> UpstreamNewProductionOrder:
        """Starts the process to request another input stream state
        because the previous input stream state did not provide sufficient mass.

        Args:
            next_node_name (str): The upstream node that provides the new input stream state.
            starting_node_name (str): The current process step.
            downstream_validation_operation (DownstreamValidationOrder): The order that
                validated the previously requested input stream state. it provides
                the final product order that should be fulfilled by the output stream.

        Returns:
            UpstreamNewProductionOrder: This order contains the request for an additional
                input stream state.
        """
        self.process_state_handler.process_step_data.state_data_container.prepare_new_temporal_branch()
        self.process_state_navigator.store_current_simulation_data()
        input_stream_state = self.process_state_navigator.fulfill_temporal_branch()
        incomplete_branch_data = (
            self.process_state_handler.process_step_data.state_data_container.get_incomplete_branch_data()
        )
        upstream_new_production_order = UpstreamNewProductionOrder(
            next_node_name=next_node_name,
            starting_node_name=starting_node_name,
            production_order=downstream_validation_operation.production_order,
            stream_state=input_stream_state,
            starting_node_output_branch_data=incomplete_branch_data,
        )
        return upstream_new_production_order

    def create_downstream_validation_order(
        self,
        downstream_node_name: str,
        starting_node_name: str,
        input_production_order: UpstreamNewProductionOrder | DownstreamValidationOrder,
    ) -> DownstreamValidationOrder:
        """Creates a DownstreamValidationOrder to signal that the requested output stream
        can be provided as requested.

        Args:
            downstream_node_name (str): Name of the DownStreamNode.
            starting_node_name (str): Name of the starting Node.
            input_production_order (UpstreamNewProductionOrder | DownstreamValidationOrder): Incoming
                order to the ProcessNode.

        Returns:
            DownstreamValidationOrder: DownstreamValidationOrder to signal that the requested output stream
        can be provided as requested
        """
        self.complete_output_branch()
        complete_branch_data = (
            self.process_state_handler.process_step_data.state_data_container.get_complete_branch_data()
        )

        if type(input_production_order) is UpstreamNewProductionOrder:
            downstream_validation_order = DownstreamValidationOrder(
                next_node_name=downstream_node_name,
                starting_node_name=starting_node_name,
                starting_node_output_branch_data=complete_branch_data,
                target_node_output_branch_identifier=complete_branch_data.parent_output_identifier,
                target_node_temporal_identifier=complete_branch_data.parent_input_identifier,
                production_order=input_production_order.production_order,
            )
        elif type(input_production_order) is DownstreamValidationOrder:
            downstream_validation_order = DownstreamValidationOrder(
                next_node_name=downstream_node_name,
                starting_node_name=starting_node_name,
                starting_node_output_branch_data=complete_branch_data,
                target_node_output_branch_identifier=complete_branch_data.parent_output_identifier,
                target_node_temporal_identifier=complete_branch_data.parent_input_identifier,
                production_order=input_production_order.production_order,
            )
        return downstream_validation_order


class EmptyProductionBranch:
    """Represents an empty ProductionBranch and the beginning of a new output stream request"""

    def __init__(self) -> None:
        pass
