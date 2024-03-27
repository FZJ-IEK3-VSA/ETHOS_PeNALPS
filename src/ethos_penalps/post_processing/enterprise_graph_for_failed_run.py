import webbrowser
import os
import logging
import warnings

import graphviz

from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.process_nodes.process_chain_storage import ProcessChainStorage
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.petri_net.process_state import ProcessState
from ethos_penalps.stream import ContinuousStream, BatchStream
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.data_classes import StateConnector


# https://graphviz.readthedocs.io/en/stable/examples.html
# logging.basicConfig(level=os.environ.get("LOGLEVEL", "DEBUG"))
logger = PeNALPSLogger.get_logger_without_handler()


class GraphVizTableCreator:
    """Creates a table in graphviz"""

    def __init__(self) -> None:
        self.table_string: str = ""

    def add_row(self, list_of_columns: list[str]):

        html_str = "{ "
        for column_entry in list_of_columns:
            html_str = html_str + column_entry + "|"

        html_str = html_str[:-1]
        html_str = html_str + "}|"
        self.table_string = self.table_string + html_str

    def create_table_node(self, graph: graphviz.Digraph, table_name: str):
        if hasattr(self, "table_string"):
            self.table_string = self.table_string[:-1]

        graph.node(
            table_name, graphviz.nohtml(self.table_string), shape="record", height=".1"
        )

    def add_first_row(self, list_of_columns: list[str]):
        html_str = "{ "
        for column_entry in list_of_columns:
            html_str = html_str + column_entry + "|"

        html_str = html_str[:-1]
        html_str = html_str + "}|"
        self.table_string = html_str + self.table_string


class GraphVisualization:
    """Creates an enterprise graph for an ill defined model"""

    def __init__(
        self,
        process_node_dict: dict[str, ProcessNode],
        stream_handler: StreamHandler,
        graph_name: str = "Graph",
        output_file_extension: str = "svg",
        enterprise_name="Enterprise",
    ) -> None:
        self.graph = graphviz.Digraph(
            name=graph_name,
            format=output_file_extension,
        )
        self.graph.attr(compound="true", rankdir="LR", center="true")
        self.process_node_dict: dict[str, ProcessNode] = process_node_dict
        self.output_file_extension = output_file_extension
        self.directory_name = "results"

        self.stream_handler: StreamHandler = stream_handler
        self.path_to_output_file: str
        self.enterprise_name: str = enterprise_name
        self.first_state_of_process_step_cluster: dict[str, str] = {}
        self.last_state_of_process_step_cluster: dict[str, str] = {}

    def create_process_step_node_cluster(
        self,
        enterprise_cluster: graphviz.graphs.Digraph,
        process_step: ProcessStep,
        color="black",
    ):
        """Creates a node Cluster for process step. A cluster is required
        to display the process states within the process step.

        Args:
            enterprise_cluster (graphviz.graphs.Digraph): graphviz container which is
                used to create the final figure
            process_step (ProcessStep): Process step which should included in the graph
            color (str, optional): Color of the process step. Defaults to "black".
        """
        if not process_step.process_state_handler.process_state_dictionary:
            logger.debug(
                "Process Step: %s does not contain any process states",
                process_step.name,
            )
        process_step_name = "cluster_" + process_step.name
        logger.debug("Process step name is: %s", process_step_name)

        with enterprise_cluster.subgraph(name=process_step_name) as cluster:
            cluster.attr(
                label=process_step.name,
                clusterrank="global",
                rank="source",
                color=color,
            )

            self.first_state_of_process_step_cluster[process_step.name] = list(
                process_step.process_state_handler.process_state_dictionary.keys()
            )[0]
            self.last_state_of_process_step_cluster[process_step.name] = list(
                process_step.process_state_handler.process_state_dictionary.keys()
            )[1]

            for (
                process_state_name
            ) in process_step.process_state_handler.process_state_dictionary:
                cluster.node(
                    name=process_state_name,
                    label=process_state_name,
                )
            edge_tuple_list = []
            for (
                process_state_connector
            ) in (
                process_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.process_state_switch_dictionary.keys()
            ):
                edge_tuple_list.append(
                    (
                        process_state_connector.start_state_name,
                        process_state_connector.end_state_name,
                    )
                )
            cluster.edges(edge_tuple_list)

    def create_source_node(
        self,
        enterprise_cluster: graphviz.graphs.Digraph,
        source: Source | ProcessChainStorage,
        color: str,
    ):
        """Creates graphviz node for the source

        Args:
            enterprise_cluster (graphviz.graphs.Digraph): The enterprise cluster
                which build the final figure.
            source (Source | ProcessChainStorage): Source that should be included.
            color (str): Color of the source in the figure.
        """
        enterprise_cluster.node(name=source.name, color=color)

    def create_sink_node(
        self,
        enterprise_cluster: graphviz.graphs.Digraph,
        sink: Sink | ProcessChainStorage,
        color: str,
    ):
        """Creates graphviz node for the sink

        Args:
            enterprise_cluster (graphviz.graphs.Digraph): The enterprise cluster
                which build the final figure.
            sink (Sink | ProcessChainStorage): Sink that should be included.
            color (str): Color of the sink in the figure.
        """

        enterprise_cluster.node(name=sink.name, color=color)

    def add_stream(
        self, stream: ContinuousStream | BatchStream, edge_colour: str = "black"
    ):
        """Creates an edge that connects two nodes.

        Args:
            stream (ContinuousStream | BatchStream): Stream that should be displayed
            edge_colour (str, optional): Display color of the stream. Defaults to "black".
        """
        upstream_node_name = stream.get_upstream_node_name()
        downstream_node_name = stream.get_downstream_node_name()

        upstream_node = self.process_node_dict[upstream_node_name]
        downstream_node = self.process_node_dict[downstream_node_name]

        if isinstance(upstream_node, ProcessStep):
            last_process_state_in_process_step = (
                self.last_state_of_process_step_cluster[upstream_node.name]
            )
            edge_start_node = last_process_state_in_process_step

            # edge_start_node = "cluster_" + upstream_node_name
            ltail = "cluster_" + upstream_node_name

            # upstream_node_name = "cluster_" + upstream_node.name
        elif isinstance(upstream_node, Source) or (upstream_node, Sink):
            edge_start_node = upstream_node.name
            ltail = upstream_node.name

        if isinstance(downstream_node, ProcessStep):
            first_process_state_in_process_step = (
                self.first_state_of_process_step_cluster[downstream_node.name]
            )
            edge_end_node = first_process_state_in_process_step
            l_head = "cluster_" + downstream_node_name

        elif isinstance(downstream_node, Source) or (downstream_node, Sink):
            edge_end_node = downstream_node.name
            l_head = downstream_node.name

        logging.debug(
            "Edges: Upstream node name is: %s and downstream node name is: %s",
            upstream_node_name,
            downstream_node_name,
        )

        self.graph.edge(
            tail_name=edge_start_node + ":e",
            lhead=l_head,
            ltail=ltail,
            head_name=edge_end_node + ":w",
            label="Test label",
            color=edge_colour,
        )

    def create_enterprise_structure_graph(
        self,
        show_graph_after_creation: bool = True,
        stream_state_table_creator: GraphVizTableCreator | None = None,
        node_operation_table_creator: GraphVizTableCreator | None = None,
        production_order_table_creator: GraphVizTableCreator | None = None,
        starting_node_output_branch_data_table_creator: (
            GraphVizTableCreator | None
        ) = None,
        current_node_operation_name: str | None = None,
        active_stream_name: str | None = None,
        graph_directory: str | None = None,
        file_name: str | None = None,
    ):
        """Creates the enterprise graph

        Args:
            show_graph_after_creation (bool, optional): Determines if the graph should be displayed
                after creation. Defaults to True.
            stream_state_table_creator (GraphVizTableCreator | None, optional):
                Objects that can be used to add a table with additional information about the stream
                . Defaults to None.
            node_operation_table_creator (GraphVizTableCreator | None, optional):
                Object that can be used to create a table with additional information
                about the current node operation. Defaults to None.
            production_order_table_creator (GraphVizTableCreator | None, optional): Object that
                creates a table with additional information about the current order . Defaults to None.
            starting_node_output_branch_data_table_creator (GraphVizTableCreator  |  None, optional): Object
                that created a table about the output branch data. Defaults to None.
            current_node_operation_name (str | None, optional): Name of the current node operation
                . Defaults to None.
            active_stream_name (str | None, optional): Name of the active stream
                that should be displayed in a different color. Defaults to None.
            graph_directory (str | None, optional): Storage directory for the graph. Defaults to None.
            file_name (str | None, optional): Filename of the graph. Defaults to None.

        """
        logger.debug("Creation of enterprise structure starts")

        if not self.process_node_dict:
            logger.debug("The enterprise does not contain any process nodes")
        if (
            isinstance(stream_state_table_creator, GraphVizTableCreator)
            or isinstance(node_operation_table_creator, GraphVizTableCreator)
            or isinstance(production_order_table_creator, GraphVizTableCreator)
        ):
            with self.graph.subgraph(
                name="cluster_additional_run_information"
            ) as additional_information_cluster:
                additional_information_cluster.attr(
                    compound="true",
                    label="Additional Information",
                    rankdir="LR",
                    clusterrank="global",
                    rank="source",
                    center="true",
                )

                if isinstance(stream_state_table_creator, GraphVizTableCreator):
                    stream_state_table_creator.create_table_node(
                        graph=additional_information_cluster,
                        table_name="Stream State Table",
                    )

                if isinstance(node_operation_table_creator, GraphVizTableCreator):
                    node_operation_table_creator.create_table_node(
                        graph=additional_information_cluster,
                        table_name="Node Operation Table",
                    )
                if isinstance(production_order_table_creator, GraphVizTableCreator):
                    production_order_table_creator.create_table_node(
                        graph=additional_information_cluster,
                        table_name="Production Order",
                    )
                if isinstance(
                    starting_node_output_branch_data_table_creator, GraphVizTableCreator
                ):
                    starting_node_output_branch_data_table_creator.create_table_node(
                        graph=additional_information_cluster,
                        table_name="starting node branch data",
                    )

        enterprise_graph_name = "cluster_" + self.enterprise_name
        with self.graph.subgraph(name=enterprise_graph_name) as enterprise_cluster:
            enterprise_cluster.attr(label=self.enterprise_name)

            for process_node_name, process_node in self.process_node_dict.items():
                if process_node_name == current_node_operation_name:
                    color = "green"
                else:
                    color = "black"

                if isinstance(process_node, ProcessStep):
                    logger.debug("Create process step node: %s", process_node_name)
                    self.create_process_step_node_cluster(
                        enterprise_cluster=enterprise_cluster,
                        process_step=process_node,
                        color=color,
                    )
                elif isinstance(process_node, Sink):
                    self.create_sink_node(
                        enterprise_cluster=enterprise_cluster,
                        sink=process_node,
                        color=color,
                    )
                elif isinstance(process_node, Source):
                    self.create_source_node(
                        enterprise_cluster=enterprise_cluster,
                        source=process_node,
                        color=color,
                    )
                elif isinstance(process_node, ProcessChainStorage):
                    self.create_source_node(
                        enterprise_cluster=enterprise_cluster,
                        source=process_node,
                        color=color,
                    )
                else:
                    raise Exception(
                        "Unexpected datatype in process node dict " + str(process_node)
                    )

        for stream in self.stream_handler.stream_dict.values():
            if active_stream_name == stream.name:
                self.add_stream(stream=stream, edge_colour="green")
            else:
                self.add_stream(stream=stream)
        self.graph.format = self.output_file_extension

        if graph_directory is None:
            result_path_generator = ResultPathGenerator()
            graph_directory = (
                result_path_generator.create_path_to_file_relative_to_main_file(
                    file_name="",
                    subdirectory_name=self.directory_name,
                    file_extension="",
                )
            )
        else:
            pass

        if file_name is None:
            file_name = self.graph.name + "." + self.output_file_extension
        self.path_to_output_file = os.path.join(
            graph_directory, file_name + "." + self.output_file_extension
        )

        self.graph.render(
            directory=graph_directory,
            view=show_graph_after_creation,
            filename=file_name,
            quiet=True,
        )
