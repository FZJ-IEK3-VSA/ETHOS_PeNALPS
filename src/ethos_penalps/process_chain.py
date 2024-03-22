import cloudpickle

from ethos_penalps.data_classes import (
    Commodity,
    CurrentProcessNode,
    LoopCounter,
    ProcessChainIdentifier,
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
from ethos_penalps.post_processing.report_generator.failed_simulation_report_generator import (
    FailedRunReportGenerator,
)
from ethos_penalps.process_nodes.process_chain_storage import ProcessChainStorage
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.debugging_information import DebuggingInformationLogger
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class ProcessChain:
    def __init__(
        self,
        process_chain_identifier: ProcessChainIdentifier,
        production_plan: ProductionPlan,
        load_profile_handler: LoadProfileHandlerSimulation,
        time_data: TimeData = TimeData(),
        location: str = "",
    ) -> None:
        """The ProcessChain is a collector class for sequentially depending process steps.

        It creates an instance of the ProcessChain which must be stored in a NetworkLevel.
        At least one or arbitrary more ProcessChains must be stored in a NetworkLevel. A chain
        must contain one Sink, Source or a ProcessChainStorage instead of either of those. It must
        also contain at least one ProcessStep or arbitrary more.

        Args:
            process_chain_identifier (ProcessChainIdentifier): The ProcessChainIdentifier is used
                to distinguish several process chains within a NetworkLevel.
            production_plan (ProductionPlan): The production plan stores the activity of
                nodes and streams during the simulation of ETHOS.PeNALPS.
            load_profile_handler (LoadProfileHandlerSimulation): The LoadProfileHandlerSimulation
                stores the specific energy data that is used to create load profiles and to
                store the load profiles that are created during the simulation.
            time_data (TimeData, optional): Contains the start and end time of the simulation.
                Defaults to TimeData().
            location (str, optional): Describes the location of ProcessChain. Defaults to "".

        """
        self.process_chain_identifier: ProcessChainIdentifier = process_chain_identifier
        self.time_data: TimeData = time_data
        self.process_node_dict: dict[str, ProcessNode] = {}
        self.stream_handler: StreamHandler = StreamHandler()
        self.sink: Sink | ProcessChainStorage
        self.location: str = location
        self.production_plan: ProductionPlan = production_plan
        self.load_profile_handler: LoadProfileHandlerSimulation = load_profile_handler
        self.debugging_information_logger = DebuggingInformationLogger()
        self.source: Source | ProcessChainStorage

    def get_process_node_dict_without_sink_and_source(self) -> dict[str, ProcessNode]:
        """Returns a dictionary of the nodes of the process chain without the source
            and sink.

        Returns:
            dict[str, ProcessNode]: _description_
        """
        output_node_dict = dict(self.process_node_dict)
        output_node_dict.pop(self.sink.name, None)
        output_node_dict.pop(self.source.name, None)
        return output_node_dict

    def create_failed_report(self):
        """Creates a report for failed simulation which summarizes the
        simulation.
        """
        failed_report_generator = FailedRunReportGenerator(
            debugging_information_logger=self.debugging_information_logger,
            process_node_dict=self.process_node_dict,
            stream_handler=self.stream_handler,
        )
        failed_report_generator.generate_report()

    def initialize_production_plan(self):
        """Collects steps that are necessary to conduct before each simulation.
        Creates empty entries for each process node and stream in the production plan.
        Collects the energy data from streams.
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
        consider the node during the simulation.

        Args:
            process_node_to_add (ProcessStep | Source | Sink | ProcessChainStorage): A ProcessStep,
              Source or Sink object which inherited from process node

        Raises:
            Exception: _description_

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
        """Returns a process node object based on its name.

        Args:
            process_node_name (str): Name of the node which should
              be returned.

        Returns:
            ProcessNode: A node of the Material flow in the ProcessChain

        """
        return self.process_node_dict[process_node_name]

    def create_process_step(self, name: str) -> ProcessStep:
        """Creates a ProcessStep which represents a production step
        of the ProductionSystem. It converts an input commodity
        into an output commodity.

        Args:
            name (str): Name of the ProcessStep that is used as an identifier
                and should be unique in the model.
        Returns:
            ProcessStep: The new ProcessStep.

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
        """Returns the Sink or ProcessChainStorage of the ProcessChain.

        Raises:
            Exception: Raises an error if no sink has been added
                to the ProcessChain yet.

        Returns:
            Sink | ProcessChainStorage: Sink or ProcessChainStorage of
                the ProcessChain.

        """
        if not hasattr(self, "sink"):
            raise Exception("No sink has been set yet")
        return self.sink

    def create_process_chain_production_plan(
        self, max_number_of_iterations: float | None = None
    ):
        """The method generates a production plan that confidently satisfies all
        orders in the Sink object for each process step between the Source and
        Sink object. Nodes in the ProcessChain create and receive NodeOperations
        from other nodes, either upstream or downstream. The NodeOperations
        synchronize inputs and outputs of sequentially dependent nodes. Once the
        feasible input and output times have been determined, the activity of
        the nodes, streams, and their corresponding load profiles are stored
        in the production plan and LoadProfileHandler, respectively.

        Args:
            max_number_of_iterations (float | None, optional): Sets the maximum number of
                iterations that are allowed in the Simulation. This can be useful to set
                if you are not sure that you model is well defined. Defaults to None.

        Raises:
            Exception: Raises an exception if the maximum number of iterations is surpassed.
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
        current_node = self.get_node_from_node_operation(
            node_operation=current_node_operation
        )
        assert type(current_node) is ProcessStep, (
            ("The next node after sink: " + self.get_sink().name)
            + " is not a ProcessStep. It is of type:"
            + str(type(current_node))
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
            If its TerminateProduction Operation None is returned to
            indicate the end of the simulation of the ProcessChain.

        Args:
            node_operation (NodeOperation): The NodeOperation
                from which the target node should be extracted.

        Raises:
            Exception: _description_

        Returns:
            ProcessNode | None: The target node Object.
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
        """Adds the Sink or ProcessChainStorage that replaced the Sink
            in the ProcessChain

        Args:
            sink (Sink | ProcessChainStorage): The Sink or ProcessChain
                of the ProcessChain.
        """
        self.sink = sink
        self.add_process_node(process_node_to_add=sink)

    def add_source(self, source: Source | ProcessChainStorage):
        """Adds the Source or ProcessChainStorage that replaced the Source
            in the ProcessChain

        Args:
            source (Source | ProcessChainStorage): The Source or ProcessChain
                of the ProcessChain.
        """
        self.add_process_node(process_node_to_add=source)
        self.source = source

    def get_list_of_process_step_names(
        self, include_sink: bool = False, include_source: bool = False
    ) -> list[str]:
        """Returns a list of the names of the ProcessChain.

        Args:
            include_sink (bool, optional): Defines if the sink of
                the ProcessChain should be included. Defaults to False.
            include_source (bool, optional):  Defines if the source of
                the ProcessChain should be included.. Defaults to False.

        Returns:
            list[str]: A list of all names of the nodes of the
                ProcessChain.
        """
        list_of_main_production_route_objects = []
        sink = self.get_sink()
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
