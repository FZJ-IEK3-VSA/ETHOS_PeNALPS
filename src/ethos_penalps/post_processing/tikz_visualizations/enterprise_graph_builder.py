import os
import subprocess
import uuid
import webbrowser
from dataclasses import dataclass, field

import numpy
import pandas

from ethos_penalps.network_level import NetworkLevel
from ethos_penalps.post_processing.tikz_visualizations.tikz_wrapper import (
    BackwardEdge,
    ForwardEdge,
    IntermediateEdge,
    TikzAnchorNames,
    TikzEdge,
    TikzMatrix,
    TikzMatrixRow,
    TikzNode,
    TikzRelativePositions,
)
from ethos_penalps.process_chain import ProcessChain
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
from ethos_penalps.utilities.exceptions_and_warnings import UnexpectedCase
from ethos_penalps.utilities.general_functions import ResultPathGenerator, get_new_uuid

document_preamble_str = r"""\documentclass[tikz]{standalone}
\usepackage{graphicx} % Required for inserting images
\usepackage{tikz}
\usetikzlibrary{shadows}
\usepackage{xcolor}
\usetikzlibrary{backgrounds}
\usetikzlibrary {shapes.geometric}

\usetikzlibrary {arrows.meta,automata,positioning,fit,calc}

\definecolor{ProcessStepBackground}{HTML}{FFFAF0}
\definecolor{IntermediateStateColour}{HTML}{949698}

\tikzstyle{NetworkLevel} =[draw,trapezium,trapezium stretches body,trapezium left angle=100, trapezium right angle=100]
\tikzstyle{InfinitesimalNode}=[circle,draw=none,inner sep=0pt,minimum size=0pt]
\tikzstyle{ProcessStepNode} =[draw,fill=ProcessStepBackground,rounded corners,text width=2 cm,align=center]
\tikzstyle{IdleState} =[fill=yellow,rounded corners]
\tikzstyle{OutputState} =[fill=red,rounded corners]
\tikzstyle{InputState} =[fill=green,rounded corners]
\tikzstyle{IntermediateState} =[fill=IntermediateStateColour,rounded corners]
\tikzstyle{Source} =[fill=ProcessStepBackground,shape border rotate=90,aspect=0.1,draw]
\tikzstyle{Sink} =[fill=ProcessStepBackground,shape border rotate=90,aspect=0.1,draw]
\tikzstyle{SourceOrSink} =[fill=ProcessStepBackground,cylinder, shape border rotate=90,aspect=0.1,draw,text width=2 cm,align=center]
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


class TikzNameHandler:
    """This class tracks the unique identification names
    that are used in the tikz graph.

    """

    def __init__(self) -> None:
        self.list_of_unique_names: list = []

    def create_unique_tikz_identification_name(self, input_name: str) -> str:
        converted_name = input_name.replace(" ", "-")
        converted_name = converted_name.replace("_", "-")
        if converted_name in self.list_of_unique_names:
            converted_name = converted_name + str(get_new_uuid())
        self.list_of_unique_names.append(converted_name)
        return converted_name


@dataclass
class EmptyTikzNode:
    unique_name: str = field(default_factory=get_new_uuid)
    tikz_options: str = "InfinitesimalNode"


@dataclass
class ProcessStepNode:
    tex_name: str
    name_in_simulation: str
    name_to_display: str


@dataclass
class IntermediateStorage:
    sink: Sink
    source: Source
    unique_name: str


@dataclass(kw_only=True)
class SinkRow:
    main_sink: Sink
    unique_identification_name: str

    def create_tikz_string(self):
        sink_node = TikzNode(
            name_to_display=self.main_sink.name,
            unique_identification_name=self.unique_identification_name,
            node_options="SourceOrSink",
        )
        tikz_string = sink_node.create_node_string(add_line_break=True)
        return tikz_string


@dataclass(kw_only=True)
class SourceRow:
    main_source: Source
    unique_identification_name: str
    unique_name_of_object_below_source: str

    def create_tikz_string(self):
        source_node = TikzNode(
            name_to_display=self.main_source.name,
            unique_identification_name=self.unique_identification_name,
            node_options="SourceOrSink",
        )
        tikz_string = source_node.create_node_above_of(
            unique_tikz_object_name=self.unique_name_of_object_below_source,
            add_line_break=True,
        )
        return tikz_string


@dataclass(kw_only=True)
class SourceAndSinkRow(SinkRow, SourceRow):
    def __post_init__(self):
        self.name_to_display: str = self.main_sink.name

    def create_tikz_string(self):
        source_or_sink_node = TikzNode(
            name_to_display=self.name_to_display,
            unique_identification_name=self.unique_identification_name,
            node_options="SourceOrSink",
        )
        tikz_string = source_or_sink_node.create_node_above_of(
            unique_tikz_object_name=self.unique_name_of_object_below_source,
            add_line_break=True,
        )
        return tikz_string


@dataclass(kw_only=True)
class SortedProcessChainLevel:
    """This class keeps tack of the sorted nodes
    in a process chain.
    """

    process_chain: ProcessChain
    main_sink: Sink
    main_source: Source
    tikz_name_handler: TikzNameHandler
    unique_source_name: str
    unique_sink_name: str

    def __post_init__(self):
        self.unique_chain_name = (
            self.tikz_name_handler.create_unique_tikz_identification_name(
                input_name=self.process_chain.process_chain_identifier.chain_name
            )
        )
        self.sorted_process_step_list: ProcessNode = []
        self.list_of_tikz_process_steps: TikzNode = []
        self.list_of_optional_sinks = []
        self.list_of_optional_sources = []
        self.dictionary_of_tikz_process_node_names: dict[str, str] = {}
        self.dictionary_of_tikz_process_node_names[
            self.main_sink.name
        ] = self.unique_sink_name
        self.dictionary_of_tikz_process_node_names[
            self.main_source.name
        ] = self.unique_source_name
        for process_node in self.process_chain.process_node_dict.values():
            if type(process_node) is ProcessStep:
                self.sorted_process_step_list.append(process_node)

                unique_process_node_name = (
                    self.tikz_name_handler.create_unique_tikz_identification_name(
                        input_name=process_node.name
                    )
                )
                self.list_of_tikz_process_steps.append(
                    TikzNode(
                        name_to_display=process_node.name,
                        unique_identification_name=unique_process_node_name,
                        node_options="ProcessStepNode",
                    )
                )
                self.dictionary_of_tikz_process_node_names[
                    process_node.name
                ] = unique_process_node_name
        self.process_step_chain_length = len(self.sorted_process_step_list)


@dataclass(kw_only=True)
class SortedNetworkLevel:
    network_level: NetworkLevel
    tikz_name_handler: TikzNameHandler
    previous_source_row: SourceRow | None

    def __post_init__(self):
        self.unique_name = (
            self.tikz_name_handler.create_unique_tikz_identification_name(
                input_name=str(self.network_level.uuid)
            )
        )

        unique_source_name: str = (
            self.tikz_name_handler.create_unique_tikz_identification_name(
                input_name=self.network_level.main_source.name
            )
        )
        self.source_row: SourceAndSinkRow | SourceRow = SourceRow(
            main_source=self.network_level.main_source,
            unique_identification_name=unique_source_name,
            unique_name_of_object_below_source=self.unique_name,
        )

        if self.previous_source_row is None:
            unique_sink_name: str = (
                self.tikz_name_handler.create_unique_tikz_identification_name(
                    input_name=self.network_level.main_sink.name
                )
            )
            self.sink_row = SinkRow(
                main_sink=self.network_level.main_sink,
                unique_identification_name=unique_sink_name,
            )
        else:
            self.sink_row: SourceAndSinkRow = SourceAndSinkRow(
                main_sink=self.network_level.main_sink,
                main_source=self.previous_source_row.main_source,
                unique_identification_name=self.previous_source_row.unique_identification_name,
                unique_name_of_object_below_source=self.previous_source_row.unique_name_of_object_below_source,
            )

        self.list_of_sorted_process_chains: list[SortedProcessChainLevel] = []
        list_process_step_chain_length: list[int] = []
        for process_chain in self.network_level.list_of_process_chains:
            sorted_process_chain_level = SortedProcessChainLevel(
                process_chain=process_chain,
                main_sink=self.network_level.main_sink,
                main_source=self.network_level.main_source,
                tikz_name_handler=self.tikz_name_handler,
                unique_source_name=self.source_row.unique_identification_name,
                unique_sink_name=self.sink_row.unique_identification_name,
            )
            list_process_step_chain_length.append(
                sorted_process_chain_level.process_step_chain_length
            )

            self.list_of_sorted_process_chains.append(sorted_process_chain_level)

        self.maximum_chain_length = max(list_process_step_chain_length)


@dataclass(kw_only=True)
class FilledProcessStepChain:
    name_to_display: str
    maximum_chain_length: int
    unique_chain_name: str
    list_of_process_step_tikz_nodes: list[TikzNode]

    def __post_init__(self):
        self.filled_list_of_tikz_nodes: list[TikzNode]
        current_process_step_length = len(self.list_of_process_step_tikz_nodes)
        number_of_nodes_to_add = self.maximum_chain_length - current_process_step_length
        if number_of_nodes_to_add < 0:
            raise Exception()
        for current_number in range(number_of_nodes_to_add):
            empty_tikz_node = EmptyTikzNode()
            self.filled_list_of_tikz_nodes.append(empty_tikz_node)


@dataclass
class NetworkLevelMatrix:
    unique_tikz_name: str
    sorted_network_level: SortedNetworkLevel

    def __post_init__(self):
        self.list_of_filled_process_chain: list[FilledProcessStepChain] = []
        for (
            sorted_process_chain
        ) in self.sorted_network_level.list_of_sorted_process_chains:
            filled_process_chain = FilledProcessStepChain(
                name_to_display=sorted_process_chain.process_chain.process_chain_identifier.chain_name,
                maximum_chain_length=self.sorted_network_level.maximum_chain_length,
                unique_chain_name=sorted_process_chain.unique_chain_name,
                list_of_process_step_tikz_nodes=sorted_process_chain.list_of_tikz_process_steps,
            )
            self.list_of_filled_process_chain.append(filled_process_chain)

    def create_tikz_matrix_string(self) -> str:
        list_of_tikz_rows = []
        for filled_process_chain in self.list_of_filled_process_chain:
            tikz_row = TikzMatrixRow(
                name_to_display=filled_process_chain.name_to_display,
                unique_identification_name=filled_process_chain.unique_chain_name,
                list_of_tikz_nodes=filled_process_chain.list_of_process_step_tikz_nodes,
            )
            list_of_tikz_rows.append(tikz_row)
        tikz_matrix = TikzMatrix(
            list_of_tikz_matrix_rows=list_of_tikz_rows,
            unique_tikz_name=self.unique_tikz_name,
            relative_node_name=self.sorted_network_level.sink_row.unique_identification_name,
            relative_node_anchor=TikzAnchorNames.north,
            relative_position=TikzRelativePositions.above,
        )
        tikz_matrix.add_option("NetworkLevel")
        tikz_matrix_string = tikz_matrix.create_tikz_string()
        return tikz_matrix_string


class EnterpriseGraphBuilderTikz:
    def __init__(
        self,
        enterprise_name: str,
        list_of_network_level: list[NetworkLevel],
    ) -> None:
        self.full_document_string: str
        self.path_to_tex_file: str
        self.list_of_network_level: list[NetworkLevel] = list_of_network_level
        self.enterprise_name: str = enterprise_name
        self.unique_process_node_name_dict: dict[str, str] = {}
        self.unique_process_state_names: dict[str, dict[str, str] | str] = {}
        self.title_node_identifier: str = "TitleNode"
        self.display_names_dict: dict[str, str] = {}
        self.list_of_unique_names: list[str] = []
        self.tikz_name_handler: TikzNameHandler = TikzNameHandler()

    def save_tex_file(self, full_path: str):
        with open(file=full_path, encoding="UTF-8", mode="w+") as file:
            file.write(self.full_document_string)
            file.close()
            self.path_to_tex_file = full_path

    def create_tex_file(self, full_path: str):
        list_of_sorted_network_level = self.create_list_of_sorted_network_level()
        network_node_string = self.create_network_level_nodes(
            list_of_sorted_network_level=list_of_sorted_network_level
        )
        title_node_string = self.create_title_string(
            list_of_sorted_network_level=list_of_sorted_network_level
        )
        stream_string_section = self.create_network_level_edges(
            list_of_sorted_network_level=list_of_sorted_network_level
        )

        self.full_document_string = (
            document_preamble
            + network_node_string
            + title_node_string
            + stream_string_section
            + document_postamble
        )

        self.save_tex_file(full_path=full_path)
        return full_path

    def create_list_of_sorted_network_level(self) -> list[SortedNetworkLevel]:
        previous_sorted_network_level = None
        list_of_sorted_network_level: list[SortedNetworkLevel] = []
        for network_level in self.list_of_network_level:
            if previous_sorted_network_level is None:
                previous_source_row = None
            else:
                previous_source_row = previous_sorted_network_level.source_row
            sorted_network_level = SortedNetworkLevel(
                network_level=network_level,
                tikz_name_handler=self.tikz_name_handler,
                previous_source_row=previous_source_row,
            )
            list_of_sorted_network_level.append(sorted_network_level)
            previous_sorted_network_level = sorted_network_level
        return list_of_sorted_network_level

    def create_network_level_nodes(
        self, list_of_sorted_network_level: list[SortedNetworkLevel]
    ) -> str:
        node_section_string = ""
        for sorted_network_level in list_of_sorted_network_level:
            if type(sorted_network_level.sink_row) is SinkRow:
                node_section_string = (
                    node_section_string
                    + sorted_network_level.sink_row.create_tikz_string()
                )
            elif type(sorted_network_level.sink_row) is SourceAndSinkRow:
                pass
            network_level_matrix = self.create_network_level_matrix(
                sorted_network_level=sorted_network_level
            )
            node_section_string = (
                node_section_string + network_level_matrix.create_tikz_matrix_string()
            )
            node_section_string = (
                node_section_string
                + sorted_network_level.source_row.create_tikz_string()
            )

        # title_node = self.create_title_node()
        # node_section_string = node_section_string + title_node.create_node_above_of(
        #     unique_tikz_object_name=source_row.unique_identification_name,
        #     add_line_break=True,
        # )
        return node_section_string

    def create_title_string(
        self, list_of_sorted_network_level: list[SortedNetworkLevel]
    ) -> str:
        title_node = self.create_title_node()
        last_sorted_network_level = list_of_sorted_network_level[-1]
        node_section_string = title_node.create_node_above_of(
            unique_tikz_object_name=last_sorted_network_level.source_row.unique_identification_name,
            add_line_break=True,
        )
        return node_section_string

    def create_network_level_matrix(
        self,
        sorted_network_level: SortedNetworkLevel,
    ) -> NetworkLevelMatrix:
        network_level_matrix = NetworkLevelMatrix(
            unique_tikz_name=sorted_network_level.unique_name,
            sorted_network_level=sorted_network_level,
        )

        return network_level_matrix

    def create_network_level_edges(
        self, list_of_sorted_network_level: list[SortedNetworkLevel]
    ) -> str:
        stream_string_section = ""
        for sorted_network_level in list_of_sorted_network_level:
            for (
                sorted_process_chain
            ) in sorted_network_level.list_of_sorted_process_chains:
                for (
                    stream
                ) in (
                    sorted_process_chain.process_chain.stream_handler.stream_dict.values()
                ):
                    if type(stream) is BatchStream:
                        edge_option = "dashed"
                    else:
                        edge_option = ""

                    unique_start_process_node_name = (
                        sorted_process_chain.dictionary_of_tikz_process_node_names[
                            stream.static_data.start_process_step_name
                        ]
                    )
                    unique_target_process_node_name = (
                        sorted_process_chain.dictionary_of_tikz_process_node_names[
                            stream.static_data.end_process_step_name
                        ]
                    )
                    stream_edge = ForwardEdge(
                        start_node_name=unique_start_process_node_name,
                        target_node_name=unique_target_process_node_name,
                        edge_options=edge_option,
                    )
                    stream_string_section = (
                        stream_string_section
                        + stream_edge.create_tikz_string(add_line_break=True)
                    )
        return stream_string_section

    def create_title_node(self) -> TikzNode:
        unique_identification_name = (
            self.tikz_name_handler.create_unique_tikz_identification_name(
                input_name=self.title_node_identifier
            )
        )
        tikz_node = TikzNode(
            name_to_display=self.enterprise_name,
            unique_identification_name=unique_identification_name,
            node_options="",
        )

        return tikz_node

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
        subprocess.run(
            [
                "pdftopng",
                path_to_pdf,
                path_to_png,
            ],
            check=True,
        )
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
        path_to_tex_file = os.path.join(text_folder_path, "enterprise_text_file.tex")
        path_to_tex_file = self.create_tex_file(full_path=path_to_tex_file)

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
