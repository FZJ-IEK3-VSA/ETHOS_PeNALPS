import os
import subprocess
import tempfile
import uuid
import webbrowser
from dataclasses import dataclass, field

import numpy
import pandas
from pdf2image import convert_from_path
from pdf2image.exceptions import (
    PDFInfoNotInstalledError,
    PDFPageCountError,
    PDFSyntaxError,
)

from ethos_penalps.organizational_agents.network_level import NetworkLevel
from ethos_penalps.organizational_agents.process_chain import ProcessChain
from ethos_penalps.petri_net.process_state_handler import ProcessStateHandler
from ethos_penalps.petri_net.process_state_switch_selector import (
    BatchStateSwitchSelector,
    ProcessStateSwitchSelector,
    ProvideOutputFromStorageSwitchSelector,
    SingleChoiceSelector,
    StateConnector,
)
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
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
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
    """Represents an empty tikz node which is not displayed"""

    unique_name: str = field(default_factory=get_new_uuid)
    tikz_options: str = "InfinitesimalNode"


@dataclass
class ProcessStepNode:
    """Represents the a process step node"""

    tex_name: str
    name_in_simulation: str
    name_to_display: str


@dataclass
class IntermediateStorage:
    """Represents a storage which connects NetworkLevels"""

    sink: Sink
    source: Source
    unique_name: str


@dataclass(kw_only=True)
class SinkRow:
    """Represents a row in the tikz matrix which contains the sink."""

    main_sink: Sink
    unique_identification_name: str

    def create_tikz_string(self):
        """Creates the string that represents the SinkRow in the
        tex document.

        Returns:
            _type_: _description_
        """
        sink_node = TikzNode(
            name_to_display=self.main_sink.name,
            unique_identification_name=self.unique_identification_name,
            node_options="SourceOrSink",
        )
        tikz_string = sink_node.create_node_string(add_line_break=True)
        return tikz_string


@dataclass(kw_only=True)
class SourceRow:
    """Object that represents the source row
    of the material flow system.

    Returns:
        _type_: _description_
    """

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
    """Object that represents the NetworkLevel Storage
    of the material flow simulation.

    Args:
        SinkRow (_type_): _description_
        SourceRow (_type_): _description_
    """

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
        """Converts the input data into a structured form."""
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
        self.dictionary_of_tikz_process_node_names[self.main_sink.name] = (
            self.unique_sink_name
        )
        self.dictionary_of_tikz_process_node_names[self.main_source.name] = (
            self.unique_source_name
        )
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
                self.dictionary_of_tikz_process_node_names[process_node.name] = (
                    unique_process_node_name
                )
        self.process_step_chain_length = len(self.sorted_process_step_list)


@dataclass(kw_only=True)
class SortedNetworkLevel:
    """Sorted representation of the network level"""

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
    """Representation of the filled process chain."""

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
    """Representation of a NetworkLevel for tikz plotting.

    Returns:
        _type_: _description_
    """

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
    """Converts the list of NetworkLevel into a tikz depiction
    of the material flow model."""

    def __init__(
        self,
        enterprise_name: str,
        list_of_network_level: list[NetworkLevel],
    ) -> None:
        """

        Args:
            enterprise_name (str): Name to be displayed at the top of the graphic
            list_of_network_level (list[NetworkLevel]): List of NetworkLevel which should be displayed.
        """
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
        """Saves the text file to the path provided.

        Args:
            full_path (str): Save destination path.
        """
        with open(file=full_path, encoding="UTF-8", mode="w+") as file:
            file.write(self.full_document_string)
            file.close()
            self.path_to_tex_file = full_path

    def create_tex_file(self, full_path: str) -> str:
        """Creates and save the the tex file

        Args:
            full_path (str): Destination of the tex_file.

        Returns:
            str: path to the created tex file.
        """

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
        """Sorts the network level from source to sink of the whole production system.

        Returns:
            list[SortedNetworkLevel]: _description_
        """
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
        """Creates the tex string paragraph which contains all nodes.

        Args:
            list_of_sorted_network_level (list[SortedNetworkLevel]): List
                of NetworkLevel which should be displayed.

        Returns:
            str: Node section string
        """
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
        """Creates the title string section of the text document.

        Args:
            list_of_sorted_network_level (list[SortedNetworkLevel]): List of
                NetworkLevel which should be displayed.

        Returns:
            str: Title string section of the text document.
        """
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
        """Creates the network level matrix which represents a complete NetworkLevel
        Matrix.

        Args:
            sorted_network_level (SortedNetworkLevel):  List of
                NetworkLevel which should be displayed.

        Returns:
            NetworkLevelMatrix: Network level matrix that
            represents a complete NetworkLevel. It can be converted to a tex string.
        """
        network_level_matrix = NetworkLevelMatrix(
            unique_tikz_name=sorted_network_level.unique_name,
            sorted_network_level=sorted_network_level,
        )

        return network_level_matrix

    def create_network_level_edges(
        self, list_of_sorted_network_level: list[SortedNetworkLevel]
    ) -> str:
        """Creates the edges string section for tex document.

        Args:
            list_of_sorted_network_level (list[SortedNetworkLevel]): List of
                NetworkLevel which should be displayed.

        Returns:
            str: Edge string section for tex document.
        """
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
        """Creates the title node object which can be used
        to create the corresponding tex string.

        Returns:
            TikzNode: Title node object
        """
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
        """Compiles the tex file to a pdf using tectonic.

        Returns:
            str: Returns the path to the pdf.
        """
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
        """Converts a pdf file to png file that can be included into the report.

        Args:
            path_to_pdf (str): Path to the pdf that should be converted.

        Returns:
            str: Path to the converted png file
        """
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
        """Creates the complete enterprise graph.

        Args:
            path_to_results_folder (str): Path to the report folder.
            show_graph (bool, optional): Determines if the created graph should
                be shown. Defaults to True.
            output_format (str, optional): Determines
                the target format of the enterprise figure. Defaults to "pdf".

        Returns:
            str: Path to the enterprise graph.
        """
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
