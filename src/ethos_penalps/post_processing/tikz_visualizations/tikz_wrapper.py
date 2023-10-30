from dataclasses import dataclass, field

import numpy

from ethos_penalps.utilities.general_functions import get_new_uuid


class TikzAnchorNames:
    south: str = ".south"
    south_west: str = ".south west"
    north: str = ".north"
    east: str = ".east"
    west: str = ".west"


class TikzRelativePositions:
    above: str = "above= of "
    below: str = "below= of "
    right: str = "right= of "
    left: str = "left= of "


@dataclass
@dataclass(kw_only=True)
class TikzEdge:
    start_node_name: str
    target_node_name: str
    edge_style: str = ""
    edge_options: str = ""

    def create_tikz_string(self, add_line_break: bool = True) -> str:
        if add_line_break is True:
            line_break_string = "\n"
        else:
            line_break_string = ""
        edge_tikz_string = (
            r"\draw["
            + self.edge_options
            + "] ("
            + self.start_node_name
            + ") "
            + self.edge_style
            + " ("
            + self.target_node_name
            + ");"
            + line_break_string
        )

        return edge_tikz_string


@dataclass(kw_only=True)
class ForwardEdge(TikzEdge):
    edge_style: str = "->"


@dataclass(kw_only=True)
class BackwardEdge(TikzEdge):
    edge_style: str = "<-"


@dataclass(kw_only=True)
class IntermediateEdge(TikzEdge):
    edge_style: str = "-"


@dataclass
class TikzNode:
    name_to_display: str
    unique_identification_name: str
    node_options: str

    def create_node_string(self, add_line_break: bool = False) -> str:
        node_string = (
            r"\node["
            + self.node_options
            + "]("
            + self.unique_identification_name
            + "){"
            + self.name_to_display
            + "};"
        )
        if add_line_break is True:
            node_string = node_string + "\n"
        return node_string

    def create_node_below_of(
        self, unique_tikz_object_name: str, add_line_break: bool = False
    ) -> str:
        self.node_options = (
            self.node_options
            + ","
            + (
                TikzRelativePositions.below
                + unique_tikz_object_name
                + TikzAnchorNames.south
            )
        )
        node_string = self.create_node_string(add_line_break=add_line_break)
        return node_string

    def create_node_above_of(
        self, unique_tikz_object_name: str, add_line_break: bool = False
    ) -> str:
        self.node_options = (
            self.node_options
            + ","
            + (
                TikzRelativePositions.above
                + unique_tikz_object_name
                + TikzAnchorNames.north
            )
        )
        node_string = self.create_node_string(add_line_break=add_line_break)
        return node_string

    def create_node_left_of(
        self, unique_tikz_object_name: str, add_line_break: bool = False
    ) -> str:
        self.node_options = (
            self.node_options
            + ","
            + (
                TikzRelativePositions.left
                + unique_tikz_object_name
                + TikzAnchorNames.west
            )
        )
        node_string = self.create_node_string(add_line_break=add_line_break)
        return node_string

    def create_node_right_of(
        self, unique_tikz_object_name: str, add_line_break: bool = False
    ) -> str:
        self.node_options = (
            self.node_options
            + ","
            + (
                TikzRelativePositions.right
                + unique_tikz_object_name
                + TikzAnchorNames.east
            )
        )
        node_string = self.create_node_string(add_line_break=add_line_break)
        return node_string


@dataclass
class TikzMatrixRow:
    name_to_display: str
    unique_identification_name: str
    list_of_tikz_nodes: list[TikzNode]

    def create_row_string(self, add_line_break: bool = True) -> str:
        row_string = ""
        number_of_tikz_nodes = len(self.list_of_tikz_nodes)
        for current_node_number in range(number_of_tikz_nodes):
            tikz_node = self.list_of_tikz_nodes[current_node_number]
            row_string = row_string + tikz_node.create_node_string()
            if current_node_number < number_of_tikz_nodes - 1:
                row_string = row_string + "&\n"
        row_string = row_string + r"\\"

        if add_line_break is True:
            row_string = row_string + "\n"
        return row_string


class TikzMatrix:
    def __init__(
        self,
        list_of_tikz_matrix_rows: list[TikzMatrixRow],
        unique_tikz_name: str,
        relative_node_name: str | None = None,
        relative_node_anchor: str = TikzAnchorNames.south,
        relative_position: str = TikzRelativePositions.below,
    ) -> None:
        self.relative_node_name: str | None = relative_node_name
        self.unique_tikz_name: str = unique_tikz_name
        self.relative_node_anchor: str = relative_node_anchor
        self.relative_position: str = relative_position
        self.list_of_tikz_matrix_rows: list[TikzMatrixRow] = list_of_tikz_matrix_rows

        self.fixed_options: str = r"[column sep=10,row sep=10,draw, rounded corners,nodes={rectangle, anchor=center},"
        self.postamble: str = "};\n"

    def add_option(self, option_string: str):
        self.fixed_options = self.fixed_options + option_string + ","

    def create_tikz_string(self) -> str:
        tikz_matrix_string = ""
        tikz_matrix_string = tikz_matrix_string + self.create_preamble()
        tikz_matrix_string = (
            tikz_matrix_string + self.convert_list_rows_to_list_columns()
        )
        tikz_matrix_string = tikz_matrix_string + self.postamble
        return tikz_matrix_string

    def create_matrix_from_rows(self) -> str:
        matrix_string = ""
        for tikz_row in self.list_of_tikz_matrix_rows:
            matrix_string = matrix_string + tikz_row.create_row_string()
        return matrix_string

    def convert_list_rows_to_list_columns(self):
        list_of_node_columns = []
        for tikz_row in self.list_of_tikz_matrix_rows:
            list_of_node_columns.append(tikz_row.list_of_tikz_nodes)

        matrix_of_nodes = numpy.matrix(list_of_node_columns)

        transposed_matrix = matrix_of_nodes.transpose()
        new_list_of_rows: list[TikzMatrixRow] = []
        for new_row_node_list in transposed_matrix.tolist():
            matrix_row = TikzMatrixRow(
                name_to_display="",
                unique_identification_name=str(get_new_uuid()),
                list_of_tikz_nodes=new_row_node_list,
            )
            new_list_of_rows.append(matrix_row)

        matrix_string = ""
        for tikz_row in new_list_of_rows:
            matrix_string = matrix_string + tikz_row.create_row_string()
        return matrix_string

    def create_preamble(self):
        preamble_string = (
            r"\matrix "
            + self.fixed_options
            + self.create_matrix_position_option()
            + "]("
            + self.unique_tikz_name
            + "){\n"
        )
        return preamble_string

    def create_matrix_position_option(
        self,
    ) -> str:
        if self.relative_node_name is None:
            position_option_string = ""
        else:
            position_option_string = (
                self.relative_position
                + self.relative_node_name
                + self.relative_node_anchor
            )
        return position_option_string
