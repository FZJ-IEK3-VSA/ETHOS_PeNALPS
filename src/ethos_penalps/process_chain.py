import datetime
from dataclasses import dataclass, field

import cloudpickle

from ethos_penalps.data_classes import (
    Commodity,
    CurrentProcessNode,
    LoopCounter,
    ProcessChainIdentifier,
)
from ethos_penalps.utilities.debugging_information import DebuggingInformationLogger
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
from ethos_penalps.post_processing.report_generator.process_chain_report_generator import (
    ReportGeneratorProcessChain,
)
from ethos_penalps.post_processing.report_generator.report_options import (
    ReportGeneratorOptions,
    standard_simulation_report,
)
from ethos_penalps.process_nodes.process_chain_storage import ProcessChainStorage
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.post_processing.report_generator.failed_simulation_report_generator import (
    FailedRunReportGenerator,
)
from ethos_penalps.utilities.debugging_information import (
    DebuggingInformationLogger,
    NodeOperationViewer,
)

logger = PeNALPSLogger.get_logger_without_handler()


class ProcessChain:
    """The Process Chain is a collector class for sequentially depending process steps.
    When an enterprise is fully defined the simulation can be started with create_production_plan.
    Also contains methods for report generation of the enterprise definition and report generation
    """

    def __init__(
        self,
        process_chain_identifier: ProcessChainIdentifier,
        production_plan: ProductionPlan,
        load_profile_handler: LoadProfileHandlerSimulation,
        time_data: TimeData = TimeData(),
        location: str = "",
    ) -> None:
        self.process_chain_identifier: ProcessChainIdentifier = process_chain_identifier
        self.time_data: TimeData = time_data
        self.process_node_dict: dict[str, ProcessNode] = {}
        self.stream_handler: StreamHandler = StreamHandler()
        self.sink: Sink | ProcessChainStorage
        self.location: str = location
        self.load_profile_handler: LoadProfileHandlerSimulation = (
            LoadProfileHandlerSimulation()
        )
        self.production_plan: ProductionPlan = production_plan
        self.load_profile_handler: LoadProfileHandlerSimulation = load_profile_handler
        self.debugging_information_logger = DebuggingInformationLogger()
        self.source: Source | ProcessChainStorage

    def get_process_node_dict_without_sink_and_source(self) -> dict[str, ProcessNode]:
        output_node_dict = dict(self.process_node_dict)
        output_node_dict.pop(self.sink.name, None)
        output_node_dict.pop(self.source.name, None)
        return output_node_dict

    def create_failed_report(self):
        failed_report_generator = FailedRunReportGenerator(
            debugging_information_logger=self.debugging_information_logger,
            process_node_dict=self.process_node_dict,
            stream_handler=self.stream_handler,
        )
        failed_report_generator.generate_report()

    def pickle_dump_production_plan(
        self,
        file_name: str = "production_plan",
        subdirectory_name: str = "production_plan",
        add_time_stamp_to_filename: bool = True,
    ):
        result_path_generator = ResultPathGenerator()
        result_path = result_path_generator.create_path_to_file_relative_to_main_file(
            file_name=file_name,
            subdirectory_name=subdirectory_name,
            add_time_stamp_to_filename=add_time_stamp_to_filename,
            file_extension=".pckl",
        )
        with open(result_path, "wb") as file:
            cloudpickle.dump(self.production_plan, file, protocol=None)

    def pickle_load_production_plan(self, path_to_pickle_file: str):
        with open(path_to_pickle_file, "rb") as input_file:
            self.production_plan = cloudpickle.load(input_file)

    def initialize_production_plan(self):
        """Collects steps that are necessary to conduct before each simulation.
        Creates empty entries for each process node and stream in the production plan.
        Collects the energy data from streams
        """
        for process_node_name in self.process_node_dict:
            process_node = self.get_process_node(process_node_name=process_node_name)
            if isinstance(process_node, ProcessStep):
                if process_node_name in self.production_plan.process_step_states_dict:
                    pass
                else:
                    self.production_plan.process_step_states_dict[process_node_name] = (
                        []
                    )
        for stream_name in self.stream_handler.stream_dict:
            if stream_name in self.production_plan.stream_state_dict:
                pass
            else:
                self.production_plan.stream_state_dict[stream_name] = []

        self.collect_stream_energy_data()
        self.collect_process_state_energy_data()

    def collect_stream_energy_data(self):
        """Collects the energy data from streams into the load profile handler.
        This allows calculation of the energy data from a central object
        """
        for stream in self.stream_handler.stream_dict.values():
            self.load_profile_handler.stream_energy_data_collection.add_stream_energy_data(
                stream_energy_data=stream.stream_energy_data
            )

    def collect_process_state_energy_data(self):
        for process_node in self.process_node_dict.values():
            if isinstance(process_node, ProcessStep):
                process_step_name = process_node.name
                for (
                    process_state
                ) in (
                    process_node.process_state_handler.process_state_dictionary.values()
                ):
                    self.load_profile_handler.add_process_state_energy_data(
                        process_step_name=process_step_name,
                        process_state_name=process_state.process_state_name,
                        process_state_energy_data=process_state.process_state_energy_data,
                    )

    def add_process_node(
        self, process_node_to_add: ProcessStep | Source | Sink | ProcessChainStorage
    ):
        """Adds a process node object to the process_node_dict of EnterpriseStructure to
        consider the node during the simulation

        :param process_node_to_add: A ProcessStep, Source or Sink object which inherited from process node
        :type process_node_to_add: ProcessStep | Source | Sink
        :raises Exception: _description_
        """
        if process_node_to_add.name in self.process_node_dict:
            raise Exception(
                "Process node with name: "
                + str(process_node_to_add.name)
                + " is already in process node dictionary"
            )
        self.process_node_dict[process_node_to_add.name] = process_node_to_add
        if isinstance(process_node_to_add, Sink):
            self.sink = process_node_to_add

    def get_process_node(self, process_node_name: str) -> ProcessNode:
        """Returns a process node object based on its name

        :param process_node_name: Name of the process node.
        :type process_node_name: str
        :return: _description_
        :rtype: ProcessNode
        """
        return self.process_node_dict[process_node_name]

    def create_process_step(self, name: str) -> ProcessStep:
        """Creates a process step.

        :param name: _description_
        :type name: str
        :return: _description_
        :rtype: ProcessStep
        """
        process_step = ProcessStep(
            name=name,
            stream_handler=self.stream_handler,
            production_plan=self.production_plan,
            load_profile_handler=self.load_profile_handler,
            enterprise_time_data=self.time_data,
        )
        self.add_process_node(process_node_to_add=process_step)
        return process_step

    def get_sink(self) -> Sink | ProcessChainStorage:
        """Returns a Sink

        :raises Exception: _description_
        :return: _description_
        :rtype: Sink
        """
        if not hasattr(self, "sink"):
            raise Exception("No sink has been set yet")
        return self.sink

    def create_process_chain_production_plan(
        self, max_number_of_iterations: float | None = None
    ):
        """Creates a production plan to produce all orders in the Sink object. Each process step between the Source
        and Sink object is considered. Process step can create a node operation for the upstream or downstream node.
        These operations are used creates a network of so called production and temporal branches. These are used
        to ensure that all process steps work in temporal and logically coherent way to fulfill an  order in the Sink.
        When a valid production plan entry is created the related energy consumption for the time period is created
        and stored in the LoadProfileHandler.
        """
        logger.info(
            "Create production plan of: %s", self.process_chain_identifier.chain_name
        )
        # Loops over each order in the list
        self.initialize_production_plan()
        current_node = self.get_sink()
        LoopCounter.loop_number = 0
        # Starts the first production iteration which does not required a node operation
        current_node.check_if_sink_has_orders()
        current_node_operation = current_node.plan_production()
        current_node: ProcessStep = self.get_node_from_node_operation(
            node_operation=current_node_operation
        )
        CurrentProcessNode.node_name = current_node.name
        # loops over current node list
        while not isinstance(current_node_operation, TerminateProduction):
            logger.debug(current_node)
            logger.debug("Input node operation is: %s", str(current_node_operation))
            logger.debug("Loop counter is: %s", str(LoopCounter.loop_number))

            self.debugging_information_logger.add_node_operation(
                node_operation=current_node_operation
            )
            current_node_operation: (
                UpstreamNewProductionOrder
                | DownstreamValidationOrder
                | DownstreamAdaptionOrder
                | UpstreamAdaptionOrder
                | TerminateProduction
            ) = current_node.process_input_order(
                input_node_operation=current_node_operation,
            )

            logger.debug("Output node operation: %s", str(current_node_operation))

            current_node: Source | Sink | ProcessStep | ProcessChainStorage | None = (
                self.get_node_from_node_operation(node_operation=current_node_operation)
            )

            if hasattr(current_node, "name"):
                CurrentProcessNode.node_name = current_node.name
            else:
                CurrentProcessNode.node_name = "No next node"
            if max_number_of_iterations is not None:
                if LoopCounter.loop_number >= max_number_of_iterations:
                    logger.info(
                        "Maximum number of iterations has been reached: %s",
                        max_number_of_iterations,
                    )
                    raise Exception(
                        "Production could no be planned in maximum number of iterations"
                    )
            LoopCounter.loop_number = LoopCounter.loop_number + 1

        logger.info("Creation of production plan is terminated")

    def get_node_from_node_operation(
        self, node_operation: NodeOperation
    ) -> ProcessNode | None:
        """Returns a target ProcessNode object of a NodeOperation Object.

        :param node_operation: _description_
        :type node_operation: NodeOperation
        :raises Exception: _description_
        :return: _description_
        :rtype: ProcessNode | None
        """
        logger.debug("get node_operation has been called")
        if isinstance(node_operation.next_node_name, str):
            node = self.get_process_node(
                process_node_name=node_operation.next_node_name
            )
        elif (
            isinstance(node_operation, TerminateProduction)
            and node_operation.next_node_name is None
        ):
            node = None

        else:
            raise Exception(
                "Unexpected datatype for next nodename: "
                + str(node_operation.next_node_name)
                + "and node operation: "
                + str(node_operation)
            )

        return node

    def add_sink(self, sink: Sink | ProcessChainStorage):
        self.sink = sink
        self.add_process_node(process_node_to_add=sink)

    def add_source(self, source: Source | ProcessChainStorage):
        self.add_process_node(process_node_to_add=source)
        self.source = source

    # def create_sink_from_source(self, source: Source) -> Sink:
    #     production_order_dict = (
    #         source.create_production_order_collection_from_input_states()
    #     )
    #     sink = Sink(
    #         name=source.name,
    #         commodity=source.commodity,
    #         stream_handler=self.stream_handler,
    #         order_collection=production_order_dict,
    #         production_plan=self.production_plan,
    #     )
    #     return sink

    def get_main_sink(self) -> Sink:
        return self.sink

    def get_list_of_process_step_names(
        self, include_sink: bool = False, include_source: bool = False
    ) -> list[str]:
        """Returns a list of the names of the main object node chain.

        :return: _description_
        :rtype: list[str]
        """
        list_of_main_production_route_objects = []
        sink = self.get_main_sink()
        if include_sink is True:
            list_of_main_production_route_objects.append(sink.name)
        first_stream = sink.get_stream_to_process_chain(
            process_chain_identifier=self.process_chain_identifier
        )

        list_of_main_production_route_objects.append(first_stream.name)
        upstream_node_name = first_stream.get_upstream_node_name()
        upstream_node = self.process_node_dict[upstream_node_name]
        list_of_main_production_route_objects.append(upstream_node.name)
        while isinstance(upstream_node, ProcessStep):
            main_input_stream_name = (
                upstream_node.process_state_handler.process_step_data.main_mass_balance.main_input_stream_name
            )
            logger.debug("Stream name: %s", main_input_stream_name)
            list_of_main_production_route_objects.append(main_input_stream_name)

            main_input_stream = self.stream_handler.get_stream(
                stream_name=main_input_stream_name
            )
            upstream_node_name = main_input_stream.get_upstream_node_name()
            list_of_main_production_route_objects.append(upstream_node_name)
            logger.debug("Upstream node name: %s", upstream_node_name)
            upstream_node = self.process_node_dict[upstream_node_name]
            if include_source is True and isinstance(upstream_node, Source):
                list_of_main_production_route_objects.append(upstream_node)

        return list_of_main_production_route_objects


class ProcessChainFactor(ProcessChain):
    def create_replicas(self):
        pass


if __name__ == "__main__":
    pass
