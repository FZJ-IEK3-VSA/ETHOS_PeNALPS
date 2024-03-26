import warnings
from dataclasses import fields

from ethos_penalps.data_classes import LoopCounter
from ethos_penalps.node_operations import DownstreamAdaptionOrder, NodeOperation
from ethos_penalps.post_processing.enterprise_graph_for_failed_run import (
    GraphVisualization,
    GraphVizTableCreator,
)
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.stream_handler import StreamHandler


class DebuggingInformationLogger:
    def __init__(self) -> None:
        self.node_operation_dict: dict[str, NodeOperation] = {}

    def add_node_operation(self, node_operation: NodeOperation):
        self.node_operation_dict[LoopCounter.loop_number] = node_operation


class NodeOperationViewer:
    """Is used to visualizes the NodeOperations that are created
    by the agents during the simulation. This is mainly used for debugging
    purposes.
    """

    def __init__(
        self,
        debugging_information_logger: DebuggingInformationLogger,
        process_node_dict: dict[str, ProcessNode],
        stream_handler: StreamHandler,
        graph_directory: str,
    ) -> None:
        self.debugging_information_logger: DebuggingInformationLogger = (
            debugging_information_logger
        )
        self.process_node_dict: dict[ProcessNode] = process_node_dict
        self.stream_handler: StreamHandler = stream_handler
        self.graph_directory: str = graph_directory
        self.list_of_paths_to_images: list[str] = []

    def create_node_visualization(
        self,
        node_operation: NodeOperation,
        loop_number: float,
        file_name: str = "Node_visualization",
    ):
        graph_visualization = GraphVisualization(
            process_node_dict=self.process_node_dict,
            stream_handler=self.stream_handler,
            output_file_extension="svg",
        )
        node_operation_table_creator = GraphVizTableCreator()

        stream_state_table_creator = None
        production_order_table_creator = None
        active_stream_name = None
        starting_node_output_branch_data_table_creator = None
        for field in fields(node_operation):
            if field.name == "stream_state":
                stream_state_table_creator = GraphVizTableCreator()
                stream_state = getattr(node_operation, field.name)

                stream_state_table_creator.add_row(["Stream state"])
                for stream_state_field in fields(stream_state):
                    stream_state_table_creator.add_row(
                        [
                            str(stream_state_field.name),
                            str(getattr(stream_state, stream_state_field.name)),
                        ]
                    )

                active_stream_name = stream_state.name
            elif field.name == "operation_type":
                node_operation_table_creator.add_first_row(
                    [str(getattr(node_operation, field.name))]
                )
            elif field.name == "production_order":
                production_order_table_creator = GraphVizTableCreator()
                production_order_table_creator.add_first_row(
                    list_of_columns=["Production order"]
                )
                production_order = getattr(node_operation, field.name)
                for production_order_field in fields(production_order):
                    production_order_table_creator.add_row(
                        [
                            str(production_order_field.name),
                            str(getattr(production_order, production_order_field.name)),
                        ]
                    )
            elif field.name == "starting_node_output_branch_data":
                # starting_node_output_branch_data_table_creator = GraphVizTableCreator()
                # starting_node_output_branch_data_table_creator.add_first_row(
                #     ["starting_node_output_branch_data"]
                # )
                # production_order = getattr(node_operation, field.name)
                # for production_order_field in fields(production_order):
                #     starting_node_output_branch_data_table_creator.add_row(
                #         [
                #             str(production_order_field.name),
                #             str(getattr(production_order, production_order_field.name)),
                #         ]
                #     )
                pass
            elif field.name == "target_node_output_branch_data":
                pass
            else:
                node_operation_table_creator.add_row(
                    [str(field.name), str(getattr(node_operation, field.name))]
                )
        node_operation_table_creator.add_row(["Loop number", str(loop_number)])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            graph_visualization.create_enterprise_structure_graph(
                show_graph_after_creation=False,
                stream_state_table_creator=stream_state_table_creator,
                node_operation_table_creator=node_operation_table_creator,
                production_order_table_creator=production_order_table_creator,
                current_node_operation_name=node_operation.starting_node_name,
                starting_node_output_branch_data_table_creator=starting_node_output_branch_data_table_creator,
                active_stream_name=active_stream_name,
                graph_directory=self.graph_directory,
                file_name=file_name,
            )
        self.list_of_paths_to_images.append(graph_visualization.path_to_output_file)

    def create_all_node_visualizations(self):
        for (
            loop_number,
            node_operation,
        ) in self.debugging_information_logger.node_operation_dict.items():
            self.create_node_visualization(
                node_operation=node_operation,
                loop_number=loop_number,
                file_name=str(loop_number) + "Node_visualization",
            )
