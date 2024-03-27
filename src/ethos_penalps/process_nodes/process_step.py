import datetime
from abc import ABC, abstractmethod


from ethos_penalps.data_classes import (
    Commodity,
    OutputBranchIdentifier,
    ProcessChainIdentifier,
    StaticTimePeriod,
    TemporalBranchIdentifier,
)
from ethos_penalps.load_profile_calculator import LoadProfileHandlerSimulation
from ethos_penalps.mass_balance import MassBalance
from ethos_penalps.node_operations import (
    DownstreamAdaptionOrder,
    DownstreamValidationOrder,
    NodeOperation,
    ProductionOrder,
    TerminateProduction,
    UpstreamAdaptionOrder,
    UpstreamNewProductionOrder,
)
from ethos_penalps.process_node_communicator import (
    EmptyProductionBranch,
    ProcessNodeCommunicator,
)
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.petri_net.process_state_handler import ProcessStateHandler
from ethos_penalps.process_step_data import ProcessStepData
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.simulation_data.simulation_data_branch import (
    CompleteOutputBranchData,
    IncompleteOutputBranchData,
    OutputBranchData,
)
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamState,
    ContinuousStream,
    ContinuousStreamState,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.exceptions_and_warnings import MisconfigurationError
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class ProcessStep(ProcessNode):
    """Models a production step within an industrial manufacturing process. It requests output
    streams to provides output streams. The production activity is modelled using a Petri net of states.
    These states must have states that model the different steps of productions. These steps are then attributed with energy to model
    a load profile. The activity of the states is synchronized with the downstream and upstream nodes to model a just in time
    production.
    """

    def __init__(
        self,
        name: str,
        stream_handler: StreamHandler,
        production_plan: ProductionPlan,
        load_profile_handler: LoadProfileHandlerSimulation,
        enterprise_time_data: TimeData,
    ):
        """_summary_

        Args:
            name (str): Name of the process step that is used in some figures
                and for the identification of the process step. Must be unique.
            stream_handler (StreamHandler): Contains all streams that are connected to
                the ProcessStep.
            production_plan (ProductionPlan): Is used to store all the simulation
                results of the ProcessStep.
            load_profile_handler (LoadProfileHandlerSimulation): Contains all the data that is
                used to convert the states from the petri net into load profiles. Also stores
                the load profiles
            enterprise_time_data (TimeData): Contains the start and end time of the simulation.
                Also stores the current temporal state of the Petri net.
        """

        super().__init__(name=name, stream_handler=stream_handler)
        # TODO check if global start and end date is still required
        self.time_data: TimeData = TimeData(
            global_end_date=enterprise_time_data.global_end_date,
            global_start_date=enterprise_time_data.global_start_date,
        )
        self.process_state_handler = ProcessStateHandler(
            process_step_data=ProcessStepData(
                process_step_name=self.name,
                stream_handler=stream_handler,
                time_data=self.time_data,
                load_profile_handler=load_profile_handler,
            )
        )
        self.production_branch_dict: dict[StaticTimePeriod, ProcessNodeCommunicator] = (
            {}
        )
        self.production_plan: ProductionPlan = production_plan
        self.process_node_communicator: ProcessNodeCommunicator = (
            ProcessNodeCommunicator(
                production_plan=self.production_plan,
                process_state_handler=self.process_state_handler,
            )
        )

    def __str__(self) -> str:
        return "Process Step: " + self.name

    def process_input_order(
        self,
        input_node_operation: (
            UpstreamNewProductionOrder
            | DownstreamValidationOrder
            | DownstreamAdaptionOrder
            | UpstreamAdaptionOrder
        ),
    ) -> (
        UpstreamNewProductionOrder
        | DownstreamValidationOrder
        | DownstreamAdaptionOrder
        | UpstreamAdaptionOrder
    ):
        """Manages the incoming node operations. These either request a an output stream,
        an adaption of an input stream, validate that a requested input stream can be delivered
        as requested, requests that an output stream can be adapted as requested or affirms that
        an output stream can be adapted.

        Args:
            input_node_operation (UpstreamNewProductionOrder | DownstreamValidationOrder | DownstreamAdaptionOrder | UpstreamAdaptionOrder ) : The
                meaning of the different types of input operation is explained in the following:

                - UpstreamNewProductionOrder: Request an output stream from this ProcessStep.
                - DownstreamValidationOrder: Validates that a input stream that has been requested
                  by this process step can be delivered as requested.
                - DownstreamAdaptionOrder: The upstream node requests that the previously requested output stream is
                  adapted because the upstream node is busy.
                - UpstreamAdaptionOrder: The downstream node requests that the output stream is produced as proposed in
                  the previous adaption request.


        Returns:
            (UpstreamNewProductionOrder | DownstreamValidationOrder | DownstreamAdaptionOrder | UpstreamAdaptionOrder ): The
                meaning of the different types of output operation is explained in the following:

                - UpstreamNewProductionOrder: Request a an input stream from the upstream node.
                - DownstreamValidationOrder: Validates that the requested output stream is delivered as requested.
                - DownstreamAdaptionOrder: Requests that the Downstream node accepts an adapted output stream because
                  this Process step is busy.
                - UpstreamAdaptionOrder: This process step affirms that the adapted output stream should be provided as proposed
                  by the upstream node.
        """
        logger.debug(
            "The input order type is: %s in process step: %s ",
            type(input_node_operation),
            self.name,
        )

        new_node_operation: (
            UpstreamNewProductionOrder
            | DownstreamValidationOrder
            | DownstreamAdaptionOrder
            | UpstreamAdaptionOrder
        )
        if isinstance(input_node_operation, DownstreamValidationOrder):
            logger.debug("An DownstreamValidationOperation is processed")
            new_node_operation = (
                self.process_node_communicator.process_downstream_validation_operation(
                    downstream_validation_operation=input_node_operation,
                    upstream_node_name=self.get_upstream_node_name(),
                    downstream_node_name=self.get_downstream_node_name(),
                )
            )

        elif isinstance(input_node_operation, UpstreamNewProductionOrder):
            logger.debug("A UpstreamNewProductionOrder is processed")

            new_node_operation = self.process_node_communicator.process_upstream_new_production_operation(
                starting_node_name=self.name,
                upstream_node_name=self.get_upstream_node_name(),
                downstream_node_name=self.get_downstream_node_name(),
                upstream_production_order=input_node_operation,
            )
            if isinstance(new_node_operation, DownstreamValidationOrder):
                self.process_node_communicator.store_branch_to_production_plan()
                self.process_state_handler.process_step_data.state_data_container.complete_output_branch()

        elif isinstance(input_node_operation, DownstreamAdaptionOrder):
            logger.debug("A DownstreamAdaptionOrder is processed")
            new_node_operation: UpstreamAdaptionOrder = (
                self.process_node_communicator.process_downstream_adaption_order(
                    downstream_adaption_operation=input_node_operation,
                    next_node_name=self.get_upstream_node_name(),
                    starting_node_name=self.name,
                )
            )
        elif isinstance(input_node_operation, UpstreamAdaptionOrder):
            logger.debug("A UpstreamAdaptionOrder is processed")
            new_node_operation: UpstreamNewProductionOrder = (
                self.process_node_communicator.process_upstream_adaption_operation(
                    starting_node_name=self.name,
                    upstream_node_name=self.get_upstream_node_name(),
                    upstream_adaption_operation=input_node_operation,
                )
            )
            if isinstance(new_node_operation, DownstreamValidationOrder):
                self.process_node_communicator.store_branch_to_production_plan()
                self.process_state_handler.process_step_data.state_data_container.complete_output_branch()

        else:
            raise Exception(
                "Unexpected node operation "
                + str(new_node_operation)
                + " in process step: "
                + str(self.name)
            )

        return new_node_operation

    def create_down_stream_validation_operation(
        self,
        current_production_branch: ProcessNodeCommunicator,
        downstream_validation_operation: DownstreamValidationOrder,
    ) -> DownstreamValidationOrder:
        """Creates a downstream validation operation that indicates that the output
        stream can be provided as requested.

        Args:
            current_production_branch (ProcessNodeCommunicator): Current production branch.
            downstream_validation_operation (DownstreamValidationOrder): The previous
                downstream validation operation.

        Returns:
            DownstreamValidationOrder: Indicates that the output
        stream can be provided as requested.
        """
        down_stream_node_name = self.get_downstream_node_name()
        down_stream_validation = (
            current_production_branch.create_downstream_validation_order(
                downstream_node_name=down_stream_node_name,
                starting_node_name=self.name,
                input_production_order=downstream_validation_operation,
            )
        )
        logger.debug(
            "A new down stream validation operation has been created: %s",
            down_stream_validation,
        )
        return down_stream_validation

    def get_last_fulfilled_production_branch(
        self,
    ) -> ProcessNodeCommunicator | EmptyProductionBranch:
        """Returns the last complete production branch

        Returns:
            ProcessNodeCommunicator | EmptyProductionBranch: Last complete production
                branch.
        """
        if not self.production_branch_dict:
            production_branch = EmptyProductionBranch()
        else:
            last_production_branch_static_time_period = list(
                self.production_branch_dict
            )[-1]
            production_branch = self.production_branch_dict[
                last_production_branch_static_time_period
            ]
        return production_branch

    def get_downstream_node_name(self) -> str:
        """returns the node name of the downstream node.

        Returns:
            str: Name of the downstream node.
        """
        main_output_stream = self.stream_handler.get_stream(
            self.process_state_handler.process_step_data.main_mass_balance.main_output_stream_name
        )
        return main_output_stream.get_downstream_node_name()

    def get_upstream_node_name(self) -> str:
        """Returns the node name of the upstream node.

        Returns:
            str: Name of the upstream node.
        """
        main_input_stream = self.stream_handler.get_stream(
            self.process_state_handler.process_step_data.main_mass_balance.main_input_stream_name
        )
        return main_input_stream.get_upstream_node_name()

    def create_main_mass_balance(
        self,
        commodity: Commodity,
        input_to_output_conversion_factor: float,
        main_input_stream: ContinuousStream | BatchStream,
        main_output_stream: ContinuousStream | BatchStream,
    ) -> MassBalance:
        """Creates the mass balance of the Process step that is required to convert
        output into input streams. Also hols the storages. Each process step must have
        an own mass balance for a well defined simulation model.

        Args:
            commodity (Commodity): Commodity that is stored by the
                mass balance.
            input_to_output_conversion_factor (float): Converts the input to output mass
                by multiplication.
            main_input_stream (ContinuousStream | BatchStream): Stream that connects
                the current mass balance and process step with the upstream node.
            main_output_stream (ContinuousStream | BatchStream): Stream that connects
                the current mass balance and process step with the downstream node.

        Returns:
            MassBalance: Mass balance of the current ProcessStep
        """

        mass_balance = MassBalance(
            commodity=commodity,
            stream_handler=self.stream_handler,
            time_data=self.time_data,
            input_to_output_conversion_factor=input_to_output_conversion_factor,
            main_input_stream=main_input_stream,
            main_output_stream=main_output_stream,
            state_data_container=self.process_state_handler.process_step_data.state_data_container,
            process_step_name=self.name,
            optional_input_stream_list=[],
        )

        self.process_state_handler.process_step_data.main_mass_balance = mass_balance
        return mass_balance

    def get_input_stream_name(self) -> str:
        """Returns the name of the input stream.

        Returns:
            str: Name of the input stream name.
        """
        return (
            self.process_state_handler.process_step_data.main_mass_balance.main_input_stream_name
        )

    def get_output_stream_name(self) -> str:
        """Returns the name the output stream.

        Returns:
            str: Name of the output stream.
        """
        return (
            self.process_state_handler.process_step_data.main_mass_balance.main_output_stream_name
        )
