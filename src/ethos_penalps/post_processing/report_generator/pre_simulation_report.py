import os

from ethos_penalps.post_processing.enterprise_graph_for_failed_run import (
    GraphVisualization,
)
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.stream_handler import StreamHandler


class PreSimulationReport:
    """Creates a report about the model before the simulation which
    can be used to analyze if the model is set up as expected.
    """

    def __init__(
        self,
        process_node_dict: dict[str, ProcessNode],
        stream_handler: StreamHandler,
        enterprise_name: str,
        report_directory: str,
    ) -> None:
        """

        Args:
            process_node_dict (dict[str, ProcessNode]): Contains the unprocessed simulation results.
            stream_handler (StreamHandler): Contains all streams of the model.
            enterprise_name (str): Name of the modeled enterprise.
            report_directory (str): Path to the report output directory.
        """
        self.graph_visualization = GraphVisualization(
            process_node_dict=process_node_dict,
            stream_handler=stream_handler,
            graph_name=enterprise_name,
            output_file_extension="svg",
            enterprise_name=enterprise_name,
        )
        self.process_node_dict: dict[str, ProcessNode] = process_node_dict
        self.stream_handler: StreamHandler = stream_handler
        self.report_directory: str = report_directory

    def generate_report(self, show_graph_after_creation=True):
        self.graph_visualization.create_enterprise_structure_graph(
            show_graph_after_creation=show_graph_after_creation,
            graph_directory=self.report_directory,
        )
