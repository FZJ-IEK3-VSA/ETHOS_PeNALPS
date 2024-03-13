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
from ethos_penalps.process_state_handler import ProcessStateHandler
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
    """Is a class which represents an individual process step of an industry process.
    Its two main components are the process_state_handler and the production_branch_dict.
    The production branch dict contains production branches which are used to check the coherence of the production activity
    of this process step and the upstream and downstream nodes. The process states handler contains all features which determine
    the temporal and logical behavior of a process step during production and idle time.
    """

    def __init__(
        self,
        name: str,
        stream_handler: StreamHandler,
        production_plan: ProductionPlan,
        load_profile_handler: LoadProfileHandlerSimulation,
        enterprise_time_data: TimeData,
    ):
        """Initiates the instance of a process step

        :param name: _description_
        :type name: str
        :param stream_handler: _description_
        :type stream_handler: StreamHandler
        :param production_plan: _description_
        :type production_plan: ProductionPlan
        :param load_profile_handler: _description_
        :type load_profile_handler: LoadProfileHandler
        :param enterprise_time_data: _description_
        :type enterprise_time_data: TimeData
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

    def process_input_order(self, input_node_operation: NodeOperation) -> NodeOperation:
        """Conducts the incoming node operations. Currently DownstreamValidationOperation and UpstreamNewProductionOrder are supported

        1. For DownstreamValidationOperation it is checked if the production branch of the current node is fulfilled.
            - branch_is_fulfilled==True:
                1. The current branch is stored to the production plan
                2. A new DownstreamValidationOperation is created for the downstream node
            - branch_is_fulfilled==False:
                1. A new UpstreamNewProductionOrders is created to produce the missing product
        2. From a new UpstreamNewProductionOrder
            1. A new Production branch is created
            2. A new UpstreamNewProductionOrder is created and returned


        :return: _description_
        :rtype: list[ProductionOrder]
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
        main_output_stream = self.stream_handler.get_stream(
            self.process_state_handler.process_step_data.main_mass_balance.main_output_stream_name
        )
        return main_output_stream.get_downstream_node_name()

    def get_upstream_node_name(self) -> str:
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
        "Mass balance is an output mass balance"

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
        return (
            self.process_state_handler.process_step_data.main_mass_balance.main_input_stream_name
        )

    def get_output_stream_name(self):
        return (
            self.process_state_handler.process_step_data.main_mass_balance.main_output_stream_name
        )
