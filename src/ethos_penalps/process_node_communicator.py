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
    """A OutputBranch is based on an output_stream_state. The purpose of a production branch is
    to keep track at what time which kind of inputs are required to provide the output stream which is requested by this Production Branch.
    It should also check for coherence with possible previous production Branches.

    The core functionality of the branch is to call the generation of the respective input stream state.
    When the node operation comes from a downstream node the method
    """

    def __init__(
        self,
        production_plan: ProductionPlan,
        process_state_handler: ProcessStateHandler,
    ) -> None:
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

    def check_if_production_branch_is_fulfilled(self):
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
        self.process_state_handler.process_step_data.state_data_container.complete_stream_branch()

    def complete_temporal_branch(self):
        self.process_state_navigator.process_state_handler.process_step_data.state_data_container.complete_temporal_branch()

    def complete_output_branch(self):
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

        :param downstream_adaption_operation: The DownstreamAdaptionOrder contains information about
            a possible input stream state. This order is created when the input stream state requested in a
            UpstreamNewProductionOrder can not provided by the upstream order.
        :type downstream_adaption_operation: DownstreamAdaptionOrder
        :param next_node_name: Name of the upstream node. It is required to create the next UpstreamAdaptionOrder
        :type next_node_name: str
        :param starting_node_name: Name of the current node.
        :type starting_node_name: str
        :return: _description_
        :rtype: UpstreamAdaptionOrder
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
        """Validates that the required input for the current temporal branch can be provided

        :param downstream_validation_operation: _description_
        :type downstream_validation_operation: DownstreamValidationOrder
        """
        self.process_state_navigator.validate_temporal_branch()
        self.check_if_temporal_branches_are_fulfilled()

        stream_branch_is_fulfilled = self.check_if_stream_branch_is_fulfilled()
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

    def validate_stream_branch(self):
        self.process_state_navigator.process_state_handler.process_step_data.state_data_container.complete_stream_branch()

    def process_upstream_new_production_operation(
        self,
        starting_node_name: str,
        upstream_node_name: str,
        downstream_node_name: str,
        upstream_production_order: UpstreamNewProductionOrder,
    ) -> UpstreamNewProductionOrder | DownstreamAdaptionOrder:
        """Determines if the current node can provide the requested output stream.
        If the required state can be provided the required input is requested by a new
        UpstreamNewProductionOrder. If the requested state can not be provided an adaption
        of the output stream is requested by the creation of a UpstreamNewProductionOrder.
        Initializes the production branch.

        :param starting_node_name: The name of the current node to which this branch belongs.
        :type starting_node_name: str
        :param upstream_node_name: _description_
        :type upstream_node_name: str
        :param downstream_node_name: _description_
        :type downstream_node_name: str
        :param upstream_production_order: _description_
        :type upstream_production_order: UpstreamNewProductionOrder
        :raises Exception: _description_
        :return: _description_
        :rtype: UpstreamNewProductionOrder | DownstreamAdaptionOrder
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

        :param starting_node_name: _description_
        :type starting_node_name: str
        :param upstream_node_name: _description_
        :type upstream_node_name: str
        :param upstream_adaption_operation: _description_
        :type upstream_adaption_operation: UpstreamAdaptionOrder
        :return: _description_
        :rtype: UpstreamNewProductionOrder
        """

        output_stream_providing_state = (
            self.process_state_handler.get_output_stream_providing_state()
        )
        storage_can_be_supplied_directly = (
            output_stream_providing_state.check_if_storage_can_supply_output_directly()
        )

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
        """Creates a DownStreamAdaptionOrder based on the new output_stream_state


        :param starting_node_name: _description_
        :type starting_node_name: str
        :param down_stream_node_name: _description_
        :type down_stream_node_name: str
        :param current_temporal_branch: _description_
        :type current_temporal_branch: TemporalBranch
        :param upstream_production_order: _description_
        :type upstream_production_order: UpstreamNewProductionOrder
        :return: _description_
        :rtype: DownstreamAdaptionOrder
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
    def __init__(self) -> None:
        pass
