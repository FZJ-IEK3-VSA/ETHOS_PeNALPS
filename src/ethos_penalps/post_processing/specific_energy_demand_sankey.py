import itertools
import pathlib
from abc import ABC
from dataclasses import dataclass

import matplotlib.figure
import matplotlib.pyplot
import matplotlib.sankey
import pandas

from ethos_penalps.utilities.type_aliases import numbers_alias


@dataclass(kw_only=True)
class SankeyFlowsBasic(ABC):
    list_of_flows: list[float]
    list_of_labels: list[str]
    normalization_factor: float
    unit_string: str
    number_of_decimal_points: int

    def __post_init__(self):
        self.number_of_flow_values = len(self.list_of_flows)
        if self.number_of_flow_values != len(self.list_of_labels):
            raise Exception("Then length of flows does not match the length")

    @property
    def list_of_normalized_flows(self) -> list[float]:
        list_of_normalized_flows = [x / self.normalization_factor for x in self.list_of_flows]
        return list_of_normalized_flows

    @property
    def list_of_labels_with_value_and_unit(self) -> list[str]:
        list_of_new_labels = []

        for current_index, current_label in enumerate(self.list_of_labels):
            current_flow = self.list_of_flows[current_index]

            adjusted_label = (
                current_label + "\n" + str(round(current_flow, self.number_of_decimal_points)) + " " + self.unit_string
            )
            list_of_new_labels.append(adjusted_label)
        return list_of_new_labels

    def create_path_length_list(self, path_start_value: float, path_increment: float):

        path_length_list = []
        current_path_value = path_start_value
        for entry_iterator in range(self.number_of_flow_values):
            path_length_list.append(current_path_value)
            if entry_iterator % 2 == 0:
                current_path_value = current_path_value + path_increment
                # Even
        return path_length_list


@dataclass(kw_only=True)
class SankeyFlowInput(SankeyFlowsBasic):
    @property
    def orientation_list(self):
        orientation_list = []
        orientation_iterator = -1
        for entry_iterator in range(self.number_of_flow_values):
            orientation_list.append(orientation_iterator)
            orientation_iterator = orientation_iterator * -1
        return orientation_list


@dataclass(kw_only=True)
class SankeyFlowOutput(SankeyFlowsBasic):
    @property
    def orientation_list(self):
        orientation_list = []

        if self.number_of_flow_values == 1:
            orientation_list = [0]
        else:
            orientation_iterator = -1
            for entry_iterator in range(self.number_of_flow_values):
                orientation_list.append(orientation_iterator)
                orientation_iterator = orientation_iterator * -1
        return orientation_list


@dataclass(kw_only=True)
class SankeyLevel:
    list_of_input_flows_values: list[float]
    list_of_input_labels: list[str]
    list_of_output_flows_values: list[float]
    list_of_output_labels: list[str]
    normalization_factor: float
    unit_string: str
    number_of_decimal_points: int
    path_start_value: float = 0.1
    path_increment: float = 0.3

    def __post_init__(self):
        self.input_flow: SankeyFlowInput = SankeyFlowInput(
            list_of_flows=self.list_of_input_flows_values,
            list_of_labels=self.list_of_input_labels,
            normalization_factor=self.normalization_factor,
            unit_string=self.unit_string,
            number_of_decimal_points=self.number_of_decimal_points,
        )
        self.output_flow: SankeyFlowOutput = SankeyFlowOutput(
            list_of_flows=self.list_of_output_flows_values,
            list_of_labels=self.list_of_output_labels,
            normalization_factor=self.normalization_factor,
            unit_string=self.unit_string,
            number_of_decimal_points=self.number_of_decimal_points,
        )

    @property
    def list_flow_normalized_values(self) -> list[float]:
        list_of_input_flows_values = []
        list_of_input_flows_values.extend(self.input_flow.list_of_normalized_flows)
        list_of_negative_output_flow_values = [x * -1 for x in self.output_flow.list_of_normalized_flows]
        list_of_input_flows_values.extend(list_of_negative_output_flow_values)
        return list_of_input_flows_values

    @property
    def list_label_with_unit_and_value(self) -> list[str]:
        list_of_flow_values = []
        list_of_flow_values.extend(self.input_flow.list_of_labels_with_value_and_unit)
        list_of_flow_values.extend(self.output_flow.list_of_labels_with_value_and_unit)
        return list_of_flow_values

    @property
    def list_of_orientation(self) -> list[int]:
        list_of_input_flows_values = []
        list_of_input_flows_values.extend(self.input_flow.orientation_list)
        list_of_input_flows_values.extend(self.output_flow.orientation_list)
        return list_of_input_flows_values

    def create_path_length_list(self) -> list[float]:

        path_length_list = []
        input_path_list = self.input_flow.create_path_length_list(
            path_start_value=self.path_start_value,
            path_increment=self.path_increment,
        )
        path_length_list.extend(input_path_list)
        output_path_list = self.output_flow.create_path_length_list(
            path_start_value=self.path_start_value,
            path_increment=self.path_increment,
        )
        path_length_list.extend(output_path_list)
        return path_length_list


class SpecificEnergySankeyCreator:
    def __init__(self, list_of_sankey_flows: list[SankeyLevel]) -> None:
        self.list_of_sankey_level: list[SankeyLevel] = list_of_sankey_flows

    def create_standard_sankey(self, unit_string: str = " GJ/t", title: str = "") -> matplotlib.figure:

        number_of_decimal_points = 2

        trunk_length = 2
        offset = 0.5
        gap = 0.9
        radius = 0.001 / 2
        figure = self.create_sankey_basic(
            trunk_length=trunk_length,
            offset=offset,
            number_of_decimal_points=number_of_decimal_points,
            title=title,
            gap=gap,
            radius=radius,
        )
        return figure

    def create_sankey_basic(
        self,
        number_of_decimal_points: int,
        trunk_length: float,
        offset: float = 2,
        title: str = "",
        scale: float = 0.6,
        gap: float = 8,
        radius: float = 0.1,
    ) -> matplotlib.figure:

        figure = matplotlib.pyplot.figure()

        ax = figure.add_subplot(1, 1, 1, xticks=[], yticks=[])
        ax.set_title(title)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)
        # decimal_point_formatter = r"%." + str(number_of_decimal_points) + "f"
        sankey = matplotlib.sankey.Sankey(
            ax=ax,
            scale=scale,
            offset=offset,
            head_angle=120,
            gap=gap,
            # format=decimal_point_formatter,
            # unit=unit_string,
            unit=None,
            radius=radius,
        )

        for sankey_level in self.list_of_sankey_level:
            sankey.add(
                flows=sankey_level.list_flow_normalized_values,
                labels=sankey_level.list_label_with_unit_and_value,
                orientations=sankey_level.list_of_orientation,
                pathlengths=sankey_level.create_path_length_list(),
                trunklength=trunk_length,
            )

        diagrams = sankey.finish()
        diagrams[0].text.set_fontweight("bold")
        return figure
