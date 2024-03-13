import os
import subprocess
import tempfile
import uuid
import webbrowser
from dataclasses import dataclass, field

import pandas
from pdf2image import convert_from_path

from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.process_state_handler import ProcessStateHandler
from ethos_penalps.process_state_switch_selector import (
    BatchStateSwitchSelector,
    ProcessStateSwitchSelector,
    ProvideOutputFromStorageSwitchSelector,
    SingleChoiceSelector,
    StateConnector,
)
from ethos_penalps.stream import BatchStream, ContinuousStream
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.utilities.general_functions import ResultPathGenerator

document_preamble_str = r"""\documentclass[tikz]{standalone}
\usepackage{graphicx} % Required for inserting images
\usepackage{tikz}
\usetikzlibrary{shadows}
\usepackage{xcolor}
\usetikzlibrary{backgrounds}

\usetikzlibrary {arrows.meta,automata,positioning,fit,calc}

\definecolor{ProcessStepBackground}{HTML}{FFFAF0}
\definecolor{IntermediateStateColour}{HTML}{949698}
\tikzstyle{InfinitesimalNode}=[circle,draw=none,inner sep=0pt,minimum size=0pt]
\tikzstyle{ProcessStepNode} =[fill=ProcessStepBackground,rounded corners]
\tikzstyle{IdleState} =[fill=yellow,rounded corners]
\tikzstyle{OutputState} =[fill=red,rounded corners]
\tikzstyle{InputState} =[fill=green,rounded corners]
\tikzstyle{IntermediateState} =[fill=IntermediateStateColour,rounded corners]
\tikzstyle{Source} =[fill=ProcessStepBackground,circle]
\tikzstyle{Sink} =[fill=ProcessStepBackground,circle]

\tikzset{
diagonal fill/.style 2 args={fill=#2, path picture={
\fill[#1, sharp corners] (path picture bounding box.south west) -|
                         (path picture bounding box.north east) -- cycle;}},
reversed diagonal fill/.style 2 args={fill=#2, path picture={
\fill[#1, sharp corners] (path picture bounding box.north west) |- 
                         (path picture bounding box.south east) -- cycle;}}
}

\tikzstyle{InputAndOutputState} =[diagonal fill={red}{green},rounded corners, drop shadow,draw ]

\begin{document}
\begin{tikzpicture}[->,auto,node distance=1cm,on grid,semithick]"""
document_preamble = document_preamble_str + "\n"


document_postamble = r"""\end{tikzpicture}
\end{document}
"""


def get_new_uuid() -> str:
    return str(uuid.uuid4())


@dataclass
class Direction:
    right: bool


@dataclass(kw_only=True)
class EdgeOptions:
    edge_style: str
    start_node_name: str
    target_node_name: str


@dataclass
class ForwardEdge:
    start_node_name: str
    target_node_name: str
    edge_style: str = "->"


@dataclass
class BackwardEdge:
    start_node_name: str
    target_node_name: str
    edge_style: str = "<-"


@dataclass
class IntermediateEdge:
    start_node_name: str
    target_node_name: str
    edge_style: str = "-"


@dataclass
class NodeData:
    unique_name: str
    display_name: str
    process_state_name: str
    edge_list: list[EdgeOptions] = field(default_factory=list)
    tikz_options: str = ""


@dataclass
class EmptyNodeData:
    unique_name: str = field(default_factory=get_new_uuid)
    edge_list: list[EdgeOptions] = field(default_factory=list)
    tikz_options: str = "InfinitesimalNode"


@dataclass(frozen=True, slots=True)
class StatePathConnector:
    start_state_name: str
    target_state_name: str


@dataclass(kw_only=True)
class MatrixRow:
    edge_direction: Direction
    row_width: int
    path_id: uuid.uuid4
    state_path_connector: StatePathConnector
    list_of_path_node_data: list[NodeData | EmptyNodeData] = field(default_factory=list)


@dataclass(kw_only=True)
class ChildMatrixRow(MatrixRow):
    pass


@dataclass
class PathJunction:
    state_path_connector: StatePathConnector
    state_connector: StateConnector
    parrent_path_id: int
    parrent_state_connector: StateConnector
    insert_arround_center: bool
    start_switch_state: str


@dataclass(kw_only=True)
class StatePath:
    state_path_connector: StatePathConnector
    current_state_name: str
    list_of_nodes: list[NodeData]
    last_state_connector: StateConnector | None
    list_of_further_path_junctions: list[PathJunction] = field(default_factory=list)
    unique_id: str = field(default_factory=get_new_uuid)

    def determine_number_of_unique_nodes(self) -> int:
        return len(self.list_of_nodes)

    def get_invert_node_data_list(self) -> list[NodeData]:
        return list(reversed(self.list_of_nodes))


@dataclass(kw_only=True)
class ChildStatePath(StatePath):
    parrent_unique_id: uuid.uuid4
    nodes_names_of_parrent_branch: list[str] = field(default_factory=list)
    unique_node_list: list[NodeData] = field(default_factory=list)
    non_unique_node_list: list[NodeData] = field(default_factory=list)
    all_node_list_with_matrix_nodes: list[NodeData | EmptyNodeData] = field(
        default_factory=list
    )

    def add_names_of_nodes_of_parrent_path(
        self, list_of_nodes_of_parrent_branch: list[NodeData]
    ):
        for node_data in list_of_nodes_of_parrent_branch:
            self.nodes_names_of_parrent_branch.append(node_data.unique_name)

    def determine_number_of_unique_nodes(self):
        unique_name_list = []
        for node in self.list_of_nodes:
            unique_name_list.append(node.unique_name)
        list_of_unique_node_names = list(
            set(unique_name_list) - set(self.nodes_names_of_parrent_branch)
        )
        unique_node_list = []
        for node in self.list_of_nodes:
            if node.unique_name in list_of_unique_node_names:
                unique_node_list.append(node)
        self.unique_node_list = unique_node_list
        number_of_unique_nodes = len(list_of_unique_node_names)
        return number_of_unique_nodes


@dataclass
class MatrixRowPort:
    node_data: NodeData
    node_position: int


@dataclass
class PathPortPair:
    left_parrent_port: MatrixRowPort
    right_parrent_port: MatrixRowPort
    parrent_inter_port_length: int
    left_child_port: MatrixRowPort
    right_child_port: MatrixRowPort
    child_inter_port_length: int


@dataclass
class EdgePath:
    list_of_edge_node_pairs: list[ForwardEdge | BackwardEdge | IntermediateEdge] = (
        field(default_factory=list)
    )


@dataclass
class TikzSubMatrix:
    process_step_name: str
    state_path_connector: StatePathConnector
    center_row: MatrixRow | None = None
    center_encompassing_rows_list: list[MatrixRow] = field(default_factory=list)
    list_of_all_rows: list[MatrixRow] = field(default_factory=list)
    outer_row_list: list[MatrixRow] = field(default_factory=list)
    edge_paths: EdgePath = EdgePath

    def sort_matrix_rows(self):
        self.list_of_all_rows = []
        self.list_of_all_rows.append(self.center_row)

        number_of_paths_to_add = 0
        for center_encompassing_rows in self.center_encompassing_rows_list:
            if (number_of_paths_to_add % 2) == 0:
                self.list_of_all_rows.insert(0, center_encompassing_rows)

            else:
                self.list_of_all_rows.append(center_encompassing_rows)

            number_of_paths_to_add = number_of_paths_to_add + 1
        number_of_paths_to_add = 0
        for outer_row in self.outer_row_list:
            if (number_of_paths_to_add % 2) == 0:
                self.list_of_all_rows.append(outer_row)
            else:
                self.list_of_all_rows.insert(0, outer_row)
            number_of_paths_to_add = number_of_paths_to_add + 1

    def add_inner_sub_matrix_row(self, matrix_row: MatrixRow):
        self.center_encompassing_rows_list.append(matrix_row)

    def add_outer_sub_matrix_row(self, matrix_row: MatrixRow):
        self.outer_row_list.append(matrix_row)

    def add_center_row(self, matrix_row: MatrixRow):
        self.center_row = matrix_row

    def determine_row_ports(
        self,
        parrent_path: StatePath,
        child_path: ChildStatePath,
        invert_parrent_path_direction: bool,
    ) -> PathPortPair:
        unique_parrent_name_list = []

        # Convert node object lists to name lists
        parrent_node_data_list = parrent_path.list_of_nodes
        if invert_parrent_path_direction is True:
            parrent_node_data_list = parrent_path.get_invert_node_data_list()
        for node_data in parrent_node_data_list:
            unique_parrent_name_list.append(node_data.unique_name)
        unique_child_name_list = []
        for node_data in child_path.list_of_nodes:
            unique_child_name_list.append(node_data.unique_name)
        intersection_name_list = list(
            set(unique_parrent_name_list) & set(unique_child_name_list)
        )

        child_path.non_unique_node_list.extend(intersection_name_list)

        # Create table with intersection names path indices
        intersection_name_and_position_dict = {
            "Intersection Name": [],
            "Child Row Node Position": [],
            "Parent Row Node Position": [],
        }
        for intersection_node_name in intersection_name_list:
            parrent_row_root_index = unique_parrent_name_list.index(
                intersection_node_name
            )
            intersection_name_and_position_dict["Parent Row Node Position"].append(
                parrent_row_root_index
            )
            child_row_node_position = unique_child_name_list.index(
                intersection_node_name
            )
            intersection_name_and_position_dict["Child Row Node Position"].append(
                child_row_node_position
            )
            intersection_name_and_position_dict["Intersection Name"].append(
                intersection_node_name
            )

        index_data_frame = pandas.DataFrame(intersection_name_and_position_dict)

        index_data_frame.sort_values(
            "Parent Row Node Position", ascending=True, inplace=True
        )

        left_parent_row_index = index_data_frame["Parent Row Node Position"].iloc[0]
        right_parent_row_index = index_data_frame["Parent Row Node Position"].iloc[-1]
        left_child_row_index = index_data_frame["Child Row Node Position"].iloc[0]
        right_child_row_index = index_data_frame["Child Row Node Position"].iloc[-1]

        left_parrent_port = MatrixRowPort(
            node_data=parrent_node_data_list[left_parent_row_index],
            node_position=left_parent_row_index,
        )
        right_parrent_port = MatrixRowPort(
            node_data=parrent_node_data_list[right_parent_row_index],
            node_position=right_parent_row_index,
        )
        parrent_inter_port_length = right_parent_row_index - left_parent_row_index - 1
        right_child_row_port = MatrixRowPort(
            node_data=child_path.list_of_nodes[right_child_row_index],
            node_position=right_child_row_index,
        )
        left_child_row_port = MatrixRowPort(
            node_data=child_path.list_of_nodes[left_child_row_index],
            node_position=left_child_row_index,
        )
        child_inter_port_length = right_child_row_index - left_child_row_index - 1
        path_port_pair = PathPortPair(
            left_parrent_port=left_parrent_port,
            right_parrent_port=right_parrent_port,
            parrent_inter_port_length=parrent_inter_port_length,
            left_child_port=left_child_row_port,
            right_child_port=right_child_row_port,
            child_inter_port_length=child_inter_port_length,
        )

        return path_port_pair

    def create_matrix_child_row(
        self,
        parrent_path: StatePath,
        child_path: ChildStatePath,
        maximum_row_length: int,
        edge_direction: Direction,
        invert_parrent_path_direction: bool,
    ) -> MatrixRow:
        pair_of_path_ports = self.determine_row_ports(
            parrent_path=parrent_path,
            child_path=child_path,
            invert_parrent_path_direction=invert_parrent_path_direction,
        )
        child_path.determine_number_of_unique_nodes()
        # matrix_row_node_list = [EmptyNodeData()] * maximum_row_length
        matrix_row_node_list = []
        for node_number in range(maximum_row_length):
            matrix_row_node_list.append(EmptyNodeData())
        if len(child_path.unique_node_list) == 0:
            left_child_node = matrix_row_node_list[
                pair_of_path_ports.left_parrent_port.node_position
            ]
            right_child_node = matrix_row_node_list[
                pair_of_path_ports.right_parrent_port.node_position
            ]

            left_node_parrent_row = pair_of_path_ports.left_child_port.node_data
            right_node_parrent_row = pair_of_path_ports.right_child_port.node_data

            child_path.all_node_list_with_matrix_nodes.insert(0, left_node_parrent_row)
            child_path.all_node_list_with_matrix_nodes.append(left_child_node)
            child_path.all_node_list_with_matrix_nodes.append(right_child_node)
            child_path.all_node_list_with_matrix_nodes.append(right_node_parrent_row)

            if pair_of_path_ports.child_inter_port_length < 0:
                child_path.all_node_list_with_matrix_nodes = list(
                    reversed(child_path.all_node_list_with_matrix_nodes)
                )
        elif len(child_path.unique_node_list) == 1:
            left_child_node = matrix_row_node_list[
                pair_of_path_ports.left_parrent_port.node_position
            ]
            right_child_node = child_path.unique_node_list[0]

            matrix_row_node_list[
                pair_of_path_ports.right_parrent_port.node_position
            ] = right_child_node
            left_node_parrent_row = pair_of_path_ports.left_child_port.node_data
            right_node_parrent_row = pair_of_path_ports.right_child_port.node_data

            child_path.all_node_list_with_matrix_nodes.insert(0, left_node_parrent_row)
            child_path.all_node_list_with_matrix_nodes.append(left_child_node)
            child_path.all_node_list_with_matrix_nodes.append(right_child_node)
            child_path.all_node_list_with_matrix_nodes.append(right_node_parrent_row)
            if pair_of_path_ports.child_inter_port_length < 0:
                child_path.all_node_list_with_matrix_nodes = list(
                    reversed(child_path.all_node_list_with_matrix_nodes)
                )

        elif len(child_path.unique_node_list) > 1:
            raise Exception("Not implemented yet")
            # # TODO: handle long backpaths
            # matrix_row_node_list.insert(
            #     pair_of_path_ports.left_root_position, left_node
            # )
            # left_node = child_path.unique_node_list[0]

            # length_of_unique_node_list = len(child_path.unique_node_list)
            # matrix_row_node_list[
            #     pair_of_path_ports.left_root_position : length_of_unique_node_list
            # ] = child_path.unique_node_list[1::]
            # right_node = child_path.unique_node_list[-1]
            # child_path.all_node_list_with_matrix_nodes.insert(
            #     0, pair_of_path_ports.left_root_node
            # )

            # child_path.all_node_list_with_matrix_nodes.extend(
            #     child_path.unique_node_list
            # )
            # child_path.all_node_list_with_matrix_nodes.append(
            #     pair_of_path_ports.right_root_node
            # )

        matrix_row = ChildMatrixRow(
            state_path_connector=child_path.state_path_connector,
            list_of_path_node_data=matrix_row_node_list,
            row_width=len(matrix_row_node_list),
            path_id=child_path.unique_id,
            edge_direction=edge_direction,
        )
        return matrix_row


@dataclass
class TikzMatrix:
    process_step_name: str
    list_of_submatrices: list[TikzSubMatrix] = field(default_factory=list)

    def determine_row_width(self) -> int:
        rows_width = len(self.list_of_submatrices[0].list_of_all_rows)
        return rows_width

    def add_sub_matrix(self, sub_matrix: TikzSubMatrix):
        self.list_of_submatrices.append(sub_matrix)


@dataclass
class StatePathHandler:
    list_of_initial_junction_state_connectors: list[StateConnector] = field(
        default_factory=list
    )
    dict_of_all_paths: dict[uuid.uuid4, StatePath] = field(default_factory=dict)
    list_of_remaining_paths: list[StatePathConnector, StatePath] = field(
        default_factory=list
    )
    dict_of_all_juctions: dict[StatePathConnector, PathJunction] = field(
        default_factory=dict
    )
    list_of_remaining_junctions: list[StatePathConnector, PathJunction] = field(
        default_factory=list
    )

    def add_state_path(self, state_path: StatePath):
        self.dict_of_all_paths[state_path.unique_id] = state_path
        self.list_of_remaining_paths.append(state_path)

    def pop_remaining_path(self) -> StatePath:
        return self.list_of_remaining_paths.pop()

    def add_junction(self, path_junction: PathJunction):
        if (
            path_junction.state_connector
            not in self.list_of_initial_junction_state_connectors
        ):
            self.list_of_initial_junction_state_connectors.append(
                path_junction.state_connector
            )
            self.dict_of_all_juctions[path_junction.state_path_connector] = (
                path_junction
            )
            self.list_of_remaining_junctions.append(path_junction)

    def pop_path_junction(self) -> PathJunction:
        return self.list_of_remaining_junctions.pop()

    def get_state_path_by_unqiue_id(self, path_id: uuid.uuid4) -> StatePath:
        return self.dict_of_all_paths[path_id]

    def determine_maximum_path_length(self):
        list_of_state_path_length = []

        for state_path in self.dict_of_all_paths.values():
            if type(state_path) is ChildStatePath:
                parrent_path = self.get_state_path_by_unqiue_id(
                    path_id=state_path.parrent_unique_id
                )
                state_path.add_names_of_nodes_of_parrent_path(
                    list_of_nodes_of_parrent_branch=parrent_path.list_of_nodes
                )
            number_of_unique_nodes = state_path.determine_number_of_unique_nodes()
            list_of_state_path_length.append(number_of_unique_nodes)
        maximum_path_length = max(list_of_state_path_length)

        return maximum_path_length


class ProcessStateMatrixBuilder:
    def __init__(
        self,
        process_state_handler: ProcessStateHandler,
        unique_process_state_names,
        display_names_dict,
    ) -> None:
        self.state_path_handler: StatePathHandler = StatePathHandler()
        self.unique_process_state_names: dict[str, dict[str, str] | str] = (
            unique_process_state_names
        )
        self.display_names_dict: dict[str, dict[str, str] | str] = display_names_dict
        self.process_state_handler: ProcessStateHandler = process_state_handler
        self.output_stream_state_name = (
            process_state_handler.output_stream_providing_state_name
        )
        self.idle_state_name = process_state_handler.idle_process_state_name

    def create_edges_in_submatrix(
        self,
    ):
        # Create edges for center row

        for state_path in self.state_path_handler.dict_of_all_paths.values():
            last_node = None
            # direction = self.determine_edge_direction(
            #     state_path_connector=state_path.state_path_connector
            # )
            if type(state_path) is ChildStatePath:
                for number_of_edges in range(
                    len(state_path.all_node_list_with_matrix_nodes) - 1
                ):
                    start_node = state_path.all_node_list_with_matrix_nodes[
                        number_of_edges
                    ]
                    target_node = state_path.all_node_list_with_matrix_nodes[
                        number_of_edges + 1
                    ]
                    self.create_edge_from_node_pair(
                        node_to_add_edge=start_node,
                        start_node=start_node,
                        target_node=target_node,
                        direction=Direction(right=False),
                    )

            elif type(state_path) is StatePath:
                for path_node_data in state_path.get_invert_node_data_list():
                    if last_node is not None:
                        self.create_edge_from_node_pair(
                            node_to_add_edge=last_node,
                            start_node=last_node,
                            target_node=path_node_data,
                            direction=Direction(right=True),
                        )
                    last_node = path_node_data

    def create_edge_from_node_pair(
        self,
        node_to_add_edge: NodeData | EmptyNodeData,
        start_node: NodeData | EmptyNodeData,
        target_node: NodeData | EmptyNodeData,
        direction: Direction,
    ):
        if type(target_node) is EmptyNodeData and direction.right is True:
            node_to_add_edge.edge_list.append(
                IntermediateEdge(
                    start_node_name=start_node.unique_name,
                    target_node_name=target_node.unique_name,
                )
            )
        elif type(start_node) is EmptyNodeData and direction.right is False:
            node_to_add_edge.edge_list.append(
                IntermediateEdge(
                    start_node_name=start_node.unique_name,
                    target_node_name=target_node.unique_name,
                )
            )
        else:
            if direction.right is True:
                node_to_add_edge.edge_list.append(
                    ForwardEdge(
                        start_node_name=start_node.unique_name,
                        target_node_name=target_node.unique_name,
                    )
                )
            elif direction.right is False:
                node_to_add_edge.edge_list.append(
                    BackwardEdge(
                        start_node_name=start_node.unique_name,
                        target_node_name=target_node.unique_name,
                    )
                )

    def create_process_state_matrix(
        self,
    ) -> TikzMatrix:
        """Loops over all process states"""
        # Is the output string generated
        tikz_matrix = TikzMatrix(
            process_step_name=self.process_state_handler.process_step_data.process_step_name
        )

        self.create_sub_matrix_main_paths()
        self.create_paths_from_junctions()
        sub_matrix = self.create_sub_matrix_rows_from_paths()
        tikz_matrix.add_sub_matrix(sub_matrix=sub_matrix)
        return tikz_matrix

    def create_sub_matrix_main_paths(self):
        "Node collection starts at output stream providing state"
        output_stream_state_name = (
            self.process_state_handler.output_stream_providing_state_name
        )

        idle_to_output_path = StatePath(
            list_of_nodes=[],
            last_state_connector=None,
            state_path_connector=StatePathConnector(
                start_state_name=self.idle_state_name,
                target_state_name=output_stream_state_name,
            ),
            current_state_name=output_stream_state_name,
        )
        self.state_path_handler.add_state_path(state_path=idle_to_output_path)

        idle_to_output_path = self.loop_over_node(
            terminate_at_state_connector_start=False,
            state_path=idle_to_output_path,
        )
        output_to_idle_path = ChildStatePath(
            state_path_connector=StatePathConnector(
                start_state_name=output_stream_state_name,
                target_state_name=self.idle_state_name,
            ),
            current_state_name=self.idle_state_name,
            list_of_nodes=[],
            last_state_connector=None,
            parrent_unique_id=idle_to_output_path.unique_id,
        )
        self.state_path_handler.add_state_path(state_path=output_to_idle_path)
        self.loop_over_node(
            state_path=output_to_idle_path,
            terminate_at_state_connector_start=False,
        )

    def create_paths_from_junctions(self, maximum_iterator: int = 100):
        # Create vertical orientation
        junction_iterator = 0
        while self.state_path_handler.list_of_remaining_junctions:
            current_junction = self.state_path_handler.pop_path_junction()

            parrent_path = self.state_path_handler.get_state_path_by_unqiue_id(
                path_id=current_junction.parrent_path_id
            )
            current_state_path = ChildStatePath(
                state_path_connector=current_junction.state_path_connector,
                list_of_nodes=[],
                last_state_connector=current_junction.state_connector,
                current_state_name=current_junction.start_switch_state,
                parrent_unique_id=parrent_path.unique_id,
            )

            current_state_path = self.loop_over_node(
                terminate_at_state_connector_start=False,
                state_path=current_state_path,
            )
            self.state_path_handler.add_state_path(state_path=current_state_path)

            junction_iterator = junction_iterator + 1
            if junction_iterator > maximum_iterator:
                raise Exception("There were too many iterations in the junction")

    def create_sub_matrix_rows_from_paths(
        self,
    ) -> TikzSubMatrix:
        output_stream_state_name = (
            self.process_state_handler.output_stream_providing_state_name
        )
        main_sub_matrix = TikzSubMatrix(
            process_step_name=self.process_state_handler.process_step_data.process_step_name,
            state_path_connector=StatePathConnector(
                start_state_name=self.process_state_handler.idle_process_state_name,
                target_state_name=output_stream_state_name,
            ),
        )
        maximum_path_length = self.state_path_handler.determine_maximum_path_length()

        for state_path in self.state_path_handler.dict_of_all_paths.values():
            edge_direction = self.determine_edge_direction(
                state_path_connector=state_path.state_path_connector
            )
            if type(state_path) is StatePath:
                if edge_direction.right is False:
                    list_of_path_node_data = state_path.list_of_nodes
                else:
                    list_of_path_node_data = list(reversed(state_path.list_of_nodes))
                matrix_row = MatrixRow(
                    edge_direction=edge_direction,
                    list_of_path_node_data=list_of_path_node_data,
                    row_width=len(state_path.list_of_nodes),
                    state_path_connector=state_path.state_path_connector,
                    path_id=state_path.unique_id,
                )
                main_sub_matrix.add_center_row(matrix_row=matrix_row)
            elif type(state_path) is ChildStatePath:
                parrent_state_path = (
                    self.state_path_handler.get_state_path_by_unqiue_id(
                        path_id=state_path.parrent_unique_id
                    )
                )

                matrix_row = main_sub_matrix.create_matrix_child_row(
                    parrent_path=parrent_state_path,
                    child_path=state_path,
                    maximum_row_length=maximum_path_length,
                    edge_direction=edge_direction,
                    invert_parrent_path_direction=True,
                )
                main_sub_matrix.add_inner_sub_matrix_row(matrix_row=matrix_row)
        main_sub_matrix.sort_matrix_rows()
        return main_sub_matrix

    def determine_edge_direction(
        self,
        state_path_connector: StatePathConnector,
    ) -> Direction:
        if (
            state_path_connector.start_state_name
            == self.process_state_handler.idle_process_state_name
            and state_path_connector.target_state_name
            == self.process_state_handler.output_stream_providing_state_name
        ):
            direction = Direction(right=True)
        elif (
            state_path_connector.start_state_name
            == self.process_state_handler.output_stream_providing_state_name
            and state_path_connector.target_state_name
            == self.process_state_handler.idle_process_state_name
        ):
            direction = Direction(right=False)
        elif (
            state_path_connector.start_state_name
            == self.process_state_handler.input_stream_providing_state_name
            and state_path_connector.target_state_name
            == self.process_state_handler.input_stream_providing_state_name
        ):
            direction = Direction(right=True)
        else:
            raise Exception("Unexpected Path")
        return direction

    def loop_over_node(
        self,
        terminate_at_state_connector_start: bool,
        state_path: StatePath,
        maximum_number_of_iterations: int = 100,
    ) -> StatePath:
        if state_path.last_state_connector is None:
            node_data = self.create_process_state_node(
                process_state_handler=self.process_state_handler,
                state_path=state_path,
            )
            state_path.list_of_nodes.append(node_data)
            state_path = self.switch_to_next_node(
                current_state_path=state_path,
                switch_from_specific_state=state_path.current_state_name,
            )
        else:
            node_data = self.create_process_state_node(
                process_state_handler=self.process_state_handler,
                state_path=state_path,
            )
            state_path.list_of_nodes.append(node_data)
            state_path.current_state_name = (
                state_path.last_state_connector.start_state_name
            )

        # current_state_connector = state_path.last_state_connector

        iteration_counter = 0
        while (
            # getattr(state_path.last_state_connector, state_connector_position)
            state_path.current_state_name
            != state_path.state_path_connector.start_state_name
        ):
            node_data = self.create_process_state_node(
                process_state_handler=self.process_state_handler,
                state_path=state_path,
            )
            state_path = self.switch_to_next_node(
                current_state_path=state_path,
            )

            state_path.list_of_nodes.append(node_data)

            # current_state_connector = state_path.last_state_connector
            # state_path.last_state_connector = current_state_connector

            iteration_counter = iteration_counter + 1

            if iteration_counter > maximum_number_of_iterations:
                raise Exception(
                    "Too many iterations in creation of process state network of process step: "
                    + self.process_state_handler.process_step_data.process_step_name
                )
        node_data = self.create_process_state_node(
            process_state_handler=self.process_state_handler,
            state_path=state_path,
        )
        state_path.list_of_nodes.append(node_data)

        return state_path

    def switch_to_next_node(
        self,
        current_state_path: StatePath,
        switch_from_specific_state: str | None = None,
    ):
        if switch_from_specific_state is None:
            process_state_switch_selector = self.process_state_handler.process_state_switch_selector_handler.get_switch_selector_to_previous_state(
                current_process_state_name=current_state_path.current_state_name
            )
        elif type(switch_from_specific_state) is str:
            process_state_switch_selector = self.process_state_handler.process_state_switch_selector_handler.get_switch_selector_to_previous_state(
                current_process_state_name=switch_from_specific_state
            )

        if isinstance(process_state_switch_selector, SingleChoiceSelector):
            state_connector = (
                process_state_switch_selector.process_state_switch.state_connector
            )
            current_state_path.last_state_connector = state_connector

        elif isinstance(process_state_switch_selector, BatchStateSwitchSelector):
            path_junction = PathJunction(
                state_path_connector=StatePathConnector(
                    start_state_name=current_state_path.current_state_name,
                    target_state_name=self.process_state_handler.input_stream_providing_state_name,
                ),
                state_connector=process_state_switch_selector.further_input_is_required_switch.state_connector,
                parrent_path_id=current_state_path.unique_id,
                insert_arround_center=True,
                start_switch_state=current_state_path.current_state_name,
                parrent_state_connector=current_state_path.state_path_connector,
            )
            current_state_path.list_of_further_path_junctions.append(path_junction)
            self.state_path_handler.add_junction(path_junction=path_junction)
            current_state_path.last_state_connector = (
                process_state_switch_selector.input_is_satisfied_switch.state_connector
            )

        elif isinstance(
            process_state_switch_selector, ProvideOutputFromStorageSwitchSelector
        ):
            path_junction = PathJunction(
                state_path_connector=StatePathConnector(
                    start_state_name=self.process_state_handler.idle_process_state_name,
                    target_state_name=self.process_state_handler.output_stream_providing_state_name,
                ),
                state_connector=process_state_switch_selector.output_is_supplied_from_storage_switch.state_connector,
                parrent_path_id=current_state_path.unique_id,
                start_switch_state=current_state_path.current_state_name,
                insert_arround_center=True,
                parrent_state_connector=current_state_path.state_path_connector,
            )
            current_state_path.list_of_further_path_junctions.append(path_junction)
            self.state_path_handler.add_junction(path_junction=path_junction)
            current_state_path.last_state_connector = (
                process_state_switch_selector.input_stream_is_required_switch.state_connector
            )

        else:
            raise Exception("Not implemented yet")

        current_state_path.current_state_name = (
            current_state_path.last_state_connector.start_state_name
        )
        return current_state_path

    def create_process_state_node(
        self, process_state_handler: ProcessStateHandler, state_path: StatePath
    ) -> NodeData:
        process_step_name = process_state_handler.process_step_data.process_step_name
        node_data = NodeData(
            unique_name=self.unique_process_state_names[process_step_name][
                state_path.current_state_name
            ],
            display_name=self.display_names_dict[process_step_name][
                state_path.current_state_name
            ],
            process_state_name=state_path.current_state_name,
        )
        return node_data


class GraphBuilder:
    def __init__(
        self,
        process_node_dict: dict[str, ProcessNode],
        enterprise_name: str,
        stream_handler: StreamHandler,
    ) -> None:
        self.full_document_string: str
        self.path_to_tex_file: str
        self.stream_handler: StreamHandler = stream_handler
        self.process_node_dict: dict[str, ProcessNode] = process_node_dict
        self.enterprise_name: str = enterprise_name
        self.unique_process_node_name_dict: dict[str, str] = {}
        self.unique_process_state_names: dict[str, dict[str, str] | str] = {}
        self.title_node_name: str = "TitleNode"
        self.display_names_dict: dict[str, str] = {}
        self.sorted_node_dict: dict[str, ProcessNode] = {}

    def save_tex_file(self, full_path: str):
        with open(file=full_path, encoding="UTF-8", mode="w+") as file:
            file.write(self.full_document_string)
            file.close()
            self.path_to_tex_file = full_path

    def create_texfile(self, full_path: str):
        self.create_unique_node_names()
        self.create_display_names()

        node_section_string = self.create_node_section()
        self.full_document_string = (
            document_preamble + node_section_string + document_postamble
        )

        self.save_tex_file(full_path=full_path)
        return full_path

    def create_node_section(self):
        node_section_string = ""
        node_section_string = self.create_title_node()
        first_node = True
        node_above = self.title_node_name
        self.sort_node_dict_by_streams()
        for process_node_name in self.sorted_node_dict:
            process_node = self.process_node_dict[process_node_name]

            if isinstance(process_node, Source):
                source_string = self.create_source_node(
                    process_node=process_node, node_above=node_above
                )
                node_section_string = node_section_string + source_string
            elif isinstance(process_node, ProcessStep):
                process_state_matrix_builder = ProcessStateMatrixBuilder(
                    process_state_handler=process_node.process_state_handler,
                    unique_process_state_names=self.unique_process_state_names,
                    display_names_dict=self.display_names_dict,
                )

                tikz_matrix = process_state_matrix_builder.create_process_state_matrix()
                self.identify_node_types(
                    matrix=tikz_matrix,
                    process_state_handler=process_node.process_state_handler,
                )
                process_state_matrix_builder.create_edges_in_submatrix()
                process_state_node_string = self.convert_list_matrix_to_tex_string(
                    tikz_matrix=tikz_matrix,
                    node_above=node_above,
                    process_step_name=process_node.name,
                    first_node=first_node,
                )
                edge_string = self.create_state_tikz_edges(
                    state_path_handler=process_state_matrix_builder.state_path_handler
                )
                node_section_string = (
                    node_section_string + process_state_node_string + edge_string
                )
            elif isinstance(process_node, Sink):
                sink_string = self.create_source_node(
                    process_node=process_node, node_above=node_above
                )
                node_section_string = node_section_string + sink_string

            first_node = False
            node_above = self.unique_process_node_name_dict[process_node.name]
        connecting_edge_line = self.create_stream_edge_section()

        node_section_string = node_section_string + "\n" + connecting_edge_line
        return node_section_string

    def sort_node_dict_by_streams(self):
        self.sorted_node_dict = {}
        source_name = self.get_source_name()
        current_node = self.process_node_dict[source_name]
        maximum_iterations = 100
        current_iterration = 0
        while (
            type(current_node) is not Sink and current_iterration < maximum_iterations
        ):
            if type(current_node) is ProcessStep:
                down_stream_node_name = current_node.get_downstream_node_name()
            elif type(current_node) is Source:
                output_stream = self.stream_handler.get_stream(
                    stream_name=current_node.current_output_stream_name
                )
                down_stream_node_name = output_stream.get_downstream_node_name()
            self.sorted_node_dict[current_node.name] = current_node
            current_node = self.process_node_dict[down_stream_node_name]
            current_iterration = current_iterration + 1
        self.sorted_node_dict[current_node.name] = current_node

    def get_source_name(self):
        for process_node in self.process_node_dict.values():
            if type(process_node) is Source:
                source_name = process_node.name
        return source_name

    def create_stream_edge_section(self) -> str:
        stream_section_str = ""
        for stream in self.stream_handler.stream_dict.values():
            start_node_name = stream.static_data.start_process_step_name
            target_node_name = stream.static_data.end_process_step_name
            unqiue_start_node_name = self.unique_process_node_name_dict[start_node_name]
            unqiue_target_node_name = self.unique_process_node_name_dict[
                target_node_name
            ]
            if type(stream) is ContinuousStream:
                draw_option = r"[->]"
            elif type(stream) is BatchStream:
                draw_option = r"[->,dashed]"
            current_stream_edge = (
                r"\draw"
                + draw_option
                + "("
                + unqiue_start_node_name
                + ".south) -- ("
                + unqiue_target_node_name
                + ".north);\n"
            )
            stream_section_str = stream_section_str + current_stream_edge
        return stream_section_str

    def identify_node_types(
        self, matrix: TikzMatrix, process_state_handler: ProcessStateHandler
    ) -> TikzMatrix:
        for submatrix in matrix.list_of_submatrices:
            for matrix_row in submatrix.list_of_all_rows:
                for node_data in matrix_row.list_of_path_node_data:
                    if type(node_data) is EmptyNodeData:
                        node_data.tikz_options = "InfinitesimalNode"
                    else:
                        if (
                            node_data.process_state_name
                            == process_state_handler.input_stream_providing_state_name
                            and node_data.process_state_name
                            == process_state_handler.output_stream_providing_state_name
                        ):
                            node_data.tikz_options = "InputAndOutputState"
                        else:
                            if (
                                node_data.process_state_name
                                == process_state_handler.idle_process_state_name
                            ):
                                node_data.tikz_options = "IdleState"
                            elif (
                                node_data.process_state_name
                                == process_state_handler.input_stream_providing_state_name
                            ):
                                node_data.tikz_options = "InputState"
                            elif (
                                node_data.process_state_name
                                == process_state_handler.output_stream_providing_state_name
                            ):
                                node_data.tikz_options = "OutputState"

                            else:
                                node_data.tikz_options = "IntermediateState"
        return matrix

    def create_unique_node_names(self):
        """Remove whitespaces from node names"""
        for process_node_name in self.process_node_dict:
            process_node = self.process_node_dict[process_node_name]

            if isinstance(process_node, ProcessStep):
                unique_process_node_name = process_node_name.replace(" ", "-")
                unique_process_node_name = unique_process_node_name.replace("_", "-")
                self.unique_process_node_name_dict[process_node_name] = (
                    unique_process_node_name
                )
                self.unique_process_state_names[process_node_name] = {}
                for (
                    process_state_name
                ) in process_node.process_state_handler.process_state_dictionary:
                    unique_process_state_name = process_state_name.replace(" ", "-")
                    unique_process_state_name = unique_process_state_name.replace(
                        "_", "-"
                    )
                    self.unique_process_state_names[process_node_name][
                        process_state_name
                    ] = unique_process_state_name
            elif isinstance(process_node, (Source, Sink)):
                unique_process_node_name = process_node_name.replace(" ", "")
                unique_process_node_name = unique_process_node_name.replace("_", "-")
                self.unique_process_node_name_dict[process_node_name] = (
                    unique_process_node_name
                )

    def create_display_names(self):
        """Remove whitespaces from node names"""
        for process_node_name in self.process_node_dict:
            process_node = self.process_node_dict[process_node_name]
            if isinstance(process_node, ProcessStep):
                self.display_names_dict[process_node_name] = {}
                for (
                    process_state_name
                ) in process_node.process_state_handler.process_state_dictionary:
                    name_to_display = process_state_name.replace("_", "-")
                    self.display_names_dict[process_node_name][
                        process_state_name
                    ] = name_to_display
            elif isinstance(process_node, (Source, Sink)):
                name_to_display = process_node_name.replace("_", "-")

                self.display_names_dict[process_node_name] = name_to_display

    def create_title_node(self) -> str:
        title_node_line = (
            r"\node[draw=none,rectangle]("
            + self.title_node_name
            + r"){"
            + self.enterprise_name
            + r"};"
        )
        return title_node_line

    def create_source_node(self, process_node: Source | Sink, node_above: str) -> str:
        if type(process_node) is Source:
            node_option = "Source"
        elif type(process_node) is Sink:
            node_option = "Sink"
        title_node_line = (
            r"\node[draw,"
            + node_option
            + ",below=of "
            + node_above
            + ".south]("
            + self.unique_process_node_name_dict[process_node.name]
            + r"){"
            + self.display_names_dict[process_node.name]
            + r"};"
            + "\n"
        )
        return title_node_line

    def convert_list_matrix_to_tex_string(
        self,
        tikz_matrix: TikzMatrix,
        node_above: str,
        process_step_name: str,
        first_node: bool,
    ) -> str:
        matrix_string = (
            r"\matrix [column sep=10,row sep=10,draw,ProcessStepNode,"
            + r"below= of "
            + node_above
            + r".south,rounded corners,nodes={rectangle, anchor=center}]("
            + self.unique_process_node_name_dict[process_step_name]
            + "){"
            + "\n"
        )

        rows_width = tikz_matrix.determine_row_width()
        half_row_number = round(rows_width / 2)

        """Create Title"""
        for column in range(rows_width):
            if column == half_row_number:
                matrix_string = matrix_string + r"\node[text opacity=0]{B};&"
            else:
                matrix_string = matrix_string + "&"
        matrix_string = matrix_string + r"\\" + "\n"

        """Loop over rows"""
        for sub_matrix in tikz_matrix.list_of_submatrices:
            # sub_matrix.sort_matrix_rows()
            for matrix_row in sub_matrix.list_of_all_rows:
                for node_data_entry in matrix_row.list_of_path_node_data:
                    if type(node_data_entry) is NodeData:
                        new_string = (
                            r"  \node[state,rectangle,"
                            + node_data_entry.tikz_options
                            + "]("
                            + node_data_entry.unique_name
                            + r"){"
                            + node_data_entry.display_name
                            + "}; &\n"
                        )
                    elif type(node_data_entry) is EmptyNodeData:
                        new_string = (
                            r"  \node[draw=none,InfinitesimalNode]("
                            + node_data_entry.unique_name
                            + "){}; &"
                            + "\n"
                        )

                    matrix_string = matrix_string + new_string
                matrix_string = matrix_string + r"\\"
        matrix_string = matrix_string + "\n};\n"

        label_node_string = (
            r"\node[below= 0 cm of "
            + self.unique_process_node_name_dict[process_step_name]
            + ".north]{"
            + process_step_name
            + "};\n"
        )
        matrix_string = matrix_string + label_node_string
        return matrix_string

    def create_state_tikz_edges(self, state_path_handler: StatePathHandler) -> str:
        edge_string = ""
        for state_path in state_path_handler.dict_of_all_paths.values():
            if type(state_path) is StatePath:
                node_list = state_path.list_of_nodes
            elif type(state_path) is ChildStatePath:
                node_list = state_path.all_node_list_with_matrix_nodes
            for current_node_data in node_list:
                for edge_options in current_node_data.edge_list:
                    edge_string = (
                        edge_string
                        + r"\draw["
                        + edge_options.edge_style
                        + "] ("
                        + edge_options.start_node_name
                        + ") -- ("
                        + edge_options.target_node_name
                        + ");\n"
                    )
        return edge_string

    def compile_pdf(self) -> str:
        subprocess.run(
            [
                "tectonic",
                "-X",
                "-c",
                "minimal",
                "compile",
                self.path_to_tex_file,
            ],
            check=True,
        )
        path_to_pdf = self.path_to_tex_file[:-4] + ".pdf"

        return path_to_pdf

    def convert_pdf_to_png(self, path_to_pdf: str) -> str:
        path_to_png = path_to_pdf[:-4] + ".png"
        with tempfile.TemporaryDirectory() as path:
            list_of_pillow_images = convert_from_path(path_to_pdf)

            for image in list_of_pillow_images:
                converted_image = image.convert("RGBA")
                converted_image.save(path_to_png)
        return path_to_png

    def create_enterprise_graph(
        self,
        path_to_results_folder: str,
        show_graph: bool = True,
        output_format: str = "pdf",
    ) -> str:
        result_path_generator = ResultPathGenerator()
        text_folder_path = result_path_generator.create_subdirectory_relative_to_parent(
            parent_directory_path=path_to_results_folder,
            new_directory_name="tex_folder",
        )
        path_to_tex_file = os.path.join(text_folder_path, ".enterprise_text_file.tex")
        path_to_tex_file = self.create_texfile(full_path=path_to_tex_file)

        path_to_pdf = self.compile_pdf()
        if output_format == "png":
            path_to_output_file = self.convert_pdf_to_png(path_to_pdf=path_to_pdf)
        elif output_format == "pdf":
            path_to_output_file = path_to_pdf
        if show_graph is True:
            webbrowser.open(path_to_output_file)
        return path_to_output_file


# TODO: Implement automatic Node layout for wrong layouts
# https://tikz.net/automatic-placing-dynamic-styling-of-nodes-in-a-graph/
