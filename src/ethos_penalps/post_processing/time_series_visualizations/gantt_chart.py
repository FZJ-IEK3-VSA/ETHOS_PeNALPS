import datetime
import itertools
import logging
import os
from pickletools import read_uint1

import matplotlib
import matplotlib.pyplot
import matplotlib.pyplot as plt
import plotly.express as px
import proplot
from matplotlib import cm

from ethos_penalps.data_classes import (
    LoadProfileDataFrameMetaInformation,
    ProcessStepDataFrameMetaInformation,
    ProductionOrderMetadata,
    StorageDataFrameMetaInformation,
    StorageProductionPlanEntry,
)
from ethos_penalps.post_processing.time_series_visualizations.create_storage_plot import (
    create_storage_subplot,
)
from ethos_penalps.post_processing.time_series_visualizations.line_chart import (
    create_line_subplot,
    create_multiple_line_plot,
)
from ethos_penalps.post_processing.time_series_visualizations.load_profile_gantt_charts import (
    create_load_profile_gantt_chart,
)
from ethos_penalps.post_processing.time_series_visualizations.process_state_gantt_chart import (
    create_process_state_subplot,
)
from ethos_penalps.post_processing.time_series_visualizations.stream_gantt_chart import (
    create_stream_subplot,
    slice_data_frames,
)
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream import (
    BatchStream,
    ContinuousStream,
    StreamDataFrameMetaInformation,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.utilities.data_base_interactions import DataBaseInteractions
from ethos_penalps.utilities.exceptions_and_warnings import UnexpectedDataType
from ethos_penalps.utilities.general_functions import ResultPathGenerator, denormalize
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.post_processing.time_series_visualizations.order_plot import (
    create_order_gantt_plot,
)

logger = PeNALPSLogger.get_logger_without_handler()

import warnings


class GanttChartGenerator:
    def __init__(
        self,
        production_plan: ProductionPlan,
        process_node_dict: dict,
        stream_handler: StreamHandler | None,
    ):
        self.production_plan: ProductionPlan = production_plan
        self.process_node_dict: dict[str, ProcessNode] = process_node_dict
        self.stream_handler: StreamHandler | None = stream_handler

    def get_sink_name(self):
        for process_node in self.process_node_dict.values():
            if isinstance(process_node, Sink):
                sink_name = process_node.name
        return sink_name

    def create_gantt_chart_for_object_name_list(
        self,
        object_name_list: list[str],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        include_stream_load_profiles: bool,
        include_process_state_load_profiles: bool,
        include_storage_gantt_chart: bool,
        maximum_number_of_rows: int,
    ) -> list[proplot.Figure]:
        self.initialize_data_frames()
        self.production_plan.load_profile_handler.load_profile_collection.convert_all_load_lists_to_gantt_chart_data_frames(
            convert_process_state_load_profiles=include_stream_load_profiles,
            convert_stream_load_profile_entries=include_process_state_load_profiles,
            start_date=start_date,
            end_date=end_date,
        )

        figure_list = []
        list_of_list_of_meta_data = self.production_plan.get_list_object_meta_data(
            list_of_object_names=object_name_list,
            include_stream_load_profiles=include_stream_load_profiles,
            include_process_state_load_profiles=include_process_state_load_profiles,
            maximum_number_of_rows=maximum_number_of_rows,
            include_internal_storage_gantt_chart=include_storage_gantt_chart,
        )

        list_of_meta_data = list(
            itertools.chain.from_iterable(list_of_list_of_meta_data)
        )
        list_of_meta_data = list_of_meta_data[::-1]
        list_of_preprocessed_meta_data = self.preprocess_meta_data(
            list_of_meta_data=list_of_meta_data,
            start_date=start_date,
            end_date=end_date,
        )

        figure = create_gantt_chart(
            list_of_data_frame_meta_data=list_of_preprocessed_meta_data,
            show_graph=False,
            start_date=start_date,
            end_date=end_date,
        )
        figure_list.append(figure)
        return figure_list

    def initialize_data_frames(self):
        if not self.production_plan.dict_of_process_step_data_frames:
            self.production_plan.convert_process_state_dictionary_to_list_of_data_frames()

        if not self.production_plan.dict_of_stream_meta_data_data_frames:
            self.production_plan.convert_stream_entries_to_meta_data_data_frames()

        if not self.production_plan.dict_of_storage_meta_data_data_frames:
            self.production_plan.convert_list_of_storage_entries_to_meta_data()

    def get_name_of_process_step_and_adjacent_streams(
        self,
        process_step_name: str,
        include_input_stream: bool,
        include_output_stream: bool,
        only_include_output_stream_to_sink: bool,
    ):
        list_of_object_names = []

        process_step = self.process_node_dict[process_step_name]
        if isinstance(process_step, ProcessStep):
            if include_input_stream is True:
                main_input_stream_name = (
                    process_step.process_state_handler.process_step_data.main_mass_balance.main_input_stream_name
                )
                list_of_object_names.append(main_input_stream_name)
            list_of_object_names.append(process_step_name)
            if include_output_stream is True:
                main_output_stream_name = (
                    process_step.process_state_handler.process_step_data.main_mass_balance.main_output_stream_name
                )
                list_of_object_names.append(main_output_stream_name)
            if only_include_output_stream_to_sink is True:
                main_output_stream_name = (
                    process_step.process_state_handler.process_step_data.main_mass_balance.main_output_stream_name
                )
                output_stream = self.stream_handler.get_stream(
                    stream_name=main_output_stream_name
                )
                downstream_node_name = output_stream.get_downstream_node_name()
                downstream_node = self.process_node_dict[downstream_node_name]
                if isinstance(downstream_node, Sink):
                    list_of_object_names.append(main_output_stream_name)
        return list_of_object_names

    def create_load_profile_gantt_chart_from_load_profile_meta_data(
        self,
        load_profile_meta_data: LoadProfileDataFrameMetaInformation,
        save_path: str | None = None,
    ):
        sliced_list_of_meta_data = slice_data_frames(
            list_of_meta_data_objects=[load_profile_meta_data],
            start_date=load_profile_meta_data.first_start_time,
            end_date=load_profile_meta_data.last_end_time,
        )

        list_of_unbound_stream_data_frame = (
            convert_unbound_operation_rate_to_maximum_operation_rate(
                list_of_meta_data=sliced_list_of_meta_data
            )
        )

        list_of_stream_data_frames_with_colour_column = create_color_column(
            meta_data_list=list_of_unbound_stream_data_frame
        )

        figure = create_gantt_chart(
            list_of_data_frame_meta_data=list_of_stream_data_frames_with_colour_column,
            show_graph=False,
        )
        if isinstance(save_path, str):
            figure.savefig(save_path, format="svg")

    def create_gantt_charts_for_each_process_step(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        include_input_streams: bool = True,
        include_each_output_stream: bool = True,
        only_include_output_stream_to_sink: bool = True,
        include_storage_gantt_chart: bool = True,
        include_stream_load_profiles: bool = True,
        include_process_state_load_profiles: bool = True,
        maximum_number_of_rows: int = 10,
    ):
        self.initialize_data_frames()
        list_of_list_of_object_names = []
        for process_node_name in self.process_node_dict:
            process_node = self.process_node_dict[process_node_name]
            if isinstance(process_node, ProcessStep):
                list_of_object_names = self.get_name_of_process_step_and_adjacent_streams(
                    process_step_name=process_node_name,
                    include_input_stream=include_input_streams,
                    include_output_stream=include_each_output_stream,
                    only_include_output_stream_to_sink=only_include_output_stream_to_sink,
                )
                list_of_list_of_object_names.append(list_of_object_names)

        figure_list = []
        for list_of_object_names in list_of_list_of_object_names:
            list_of_list_of_meta_data = self.production_plan.get_list_object_meta_data(
                list_of_object_names=list_of_object_names,
                include_stream_load_profiles=include_stream_load_profiles,
                include_process_state_load_profiles=include_process_state_load_profiles,
                maximum_number_of_rows=maximum_number_of_rows,
                include_internal_storage_gantt_chart=include_storage_gantt_chart,
            )

            list_of_meta_data = list(
                itertools.chain.from_iterable(list_of_list_of_meta_data)
            )
            sliced_list_of_meta_data = slice_data_frames(
                list_of_meta_data_objects=list_of_meta_data,
                start_date=start_date,
                end_date=end_date,
            )

            list_of_unbound_stream_data_frame = (
                convert_unbound_operation_rate_to_maximum_operation_rate(
                    list_of_meta_data=sliced_list_of_meta_data
                )
            )

            list_of_stream_data_frames_with_colour_column = create_color_column(
                meta_data_list=list_of_unbound_stream_data_frame
            )

            figure = create_gantt_chart(
                list_of_data_frame_meta_data=list_of_stream_data_frames_with_colour_column,
                show_graph=False,
            )
            figure_list.append(figure)
        return figure_list

    def create_gantt_chart_from_list_of_meta_data(
        self,
        list_of_meta_data: list[
            StorageDataFrameMetaInformation
            | LoadProfileDataFrameMetaInformation
            | ProcessStepDataFrameMetaInformation
            | StreamDataFrameMetaInformation
            | ProductionOrderMetadata
        ],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        gantt_chart_title: str = "",
    ) -> proplot.Figure | None:
        processes_list_of_meta_data = self.preprocess_meta_data(
            list_of_meta_data=list_of_meta_data,
            start_date=start_date,
            end_date=end_date,
        )

        figure = create_gantt_chart(
            list_of_data_frame_meta_data=processes_list_of_meta_data,
            show_graph=False,
            start_date=start_date,
            end_date=end_date,
            gantt_chart_title=gantt_chart_title,
        )

        return figure

    def preprocess_meta_data(
        self,
        list_of_meta_data: list[
            StorageDataFrameMetaInformation
            | LoadProfileDataFrameMetaInformation
            | ProcessStepDataFrameMetaInformation
            | StreamDataFrameMetaInformation
            | ProductionOrderMetadata
        ],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[
        StorageDataFrameMetaInformation
        | LoadProfileDataFrameMetaInformation
        | ProcessStepDataFrameMetaInformation
        | StreamDataFrameMetaInformation
        | ProductionOrderMetadata
    ]:
        sliced_list_of_meta_data = slice_data_frames(
            list_of_meta_data_objects=list_of_meta_data,
            start_date=start_date,
            end_date=end_date,
        )

        list_of_unbound_stream_data_frame = (
            convert_unbound_operation_rate_to_maximum_operation_rate(
                list_of_meta_data=sliced_list_of_meta_data
            )
        )

        list_of_preprocessed_meta_data = create_color_column(
            meta_data_list=list_of_unbound_stream_data_frame
        )
        return list_of_preprocessed_meta_data


def create_gantt_chart(
    list_of_data_frame_meta_data: list[
        ProcessStepDataFrameMetaInformation
        | StreamDataFrameMetaInformation
        | LoadProfileDataFrameMetaInformation
        | StorageDataFrameMetaInformation
        | ProductionOrderMetadata
    ],
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    reverse_y_graph_order=False,
    output_file_path: str | None = None,
    show_graph: bool = False,
    gantt_chart_title: str = "Process Gantt Chart",
) -> matplotlib.pyplot.Figure | None:
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

    # Determine number of subplots

    number_of_process_steps = len(list_of_data_frame_meta_data)
    # Create figure and subpots
    fig = proplot.figure(refwidth=8, refheight=0.25)
    axs = fig.subplots(ncols=1, nrows=number_of_process_steps)
    # Set Figure size

    # Get global start and end date

    # Define subplot-number
    subplot_number = 0
    if reverse_y_graph_order is True:
        list_of_data_frame_meta_data = list_of_data_frame_meta_data[::-1]
    # Loop over unique objects in data frame
    all_data_frames_were_empty = True

    list_of_load_profiles_meta_data_information = []
    for data_frame_meta_information in list_of_data_frame_meta_data:
        if not isinstance(data_frame_meta_information, StorageDataFrameMetaInformation):
            if data_frame_meta_information.data_frame.empty:
                continue
            all_data_frames_were_empty = False
        if isinstance(data_frame_meta_information, ProcessStepDataFrameMetaInformation):
            create_process_state_subplot(
                axs=axs,
                subplot_number=subplot_number,
                process_state_meta_data=data_frame_meta_information,
            )
        elif isinstance(data_frame_meta_information, StreamDataFrameMetaInformation):
            create_stream_subplot(
                axs=axs,
                fig=fig,
                subplot_number=subplot_number,
                stream_data_frame_meta_information=data_frame_meta_information,
            )
        elif isinstance(
            data_frame_meta_information, LoadProfileDataFrameMetaInformation
        ):
            list_of_load_profiles_meta_data_information.append(
                data_frame_meta_information
            )
            create_multiple_line_plot(
                axes=axs,
                list_of_load_profile_data_frame_meta_information=[
                    data_frame_meta_information
                ],
                use_same_axes=False,
                current_axes_number=subplot_number,
            )
            # create_load_profile_gantt_chart(
            #     fig=fig,
            #     axs=axs,
            #     load_profile_meta_data=data_frame_meta_information,
            #     subplot_number=subplot_number,
            # )
        elif isinstance(data_frame_meta_information, StorageDataFrameMetaInformation):
            create_storage_subplot(
                figure=fig,
                axes=axs,
                storage_meta_data_information=data_frame_meta_information,
                subplot_number=subplot_number,
            )
        elif isinstance(data_frame_meta_information, ProductionOrderMetadata):
            create_order_gantt_plot(
                fig=fig,
                current_axs=axs,
                order_meta_data=data_frame_meta_information,
                subplot_number=subplot_number,
            )
        else:
            raise Exception("Unexpected datatype")

        subplot_number = subplot_number + 1
    if all_data_frames_were_empty:
        warnings.warn("All data frames were empty. There is nothing to plot")
        fig = None
    else:
        if start_date != end_date:
            axs.format(xlim=(start_date, end_date))

        axs.format(suptitle=gantt_chart_title)
        axs.format(xrotation=45)

        # Save figure to path
        if isinstance(output_file_path, str):
            plt.savefig(output_file_path, format="png")
        # Show figure
        if show_graph is True:
            plt.show(block=True)

    return fig


def create_color_column(
    meta_data_list: list[
        StreamDataFrameMetaInformation
        | LoadProfileDataFrameMetaInformation
        | StorageDataFrameMetaInformation
        | ProcessStepDataFrameMetaInformation
        | ProductionOrderMetadata
    ],
    current_value_column_name: str = "current_operation_rate_value",
) -> list[
    StreamDataFrameMetaInformation
    | LoadProfileDataFrameMetaInformation
    | StorageDataFrameMetaInformation
    | ProcessStepDataFrameMetaInformation
    | ProductionOrderMetadata
]:
    meta_data_list = convert_unbound_operation_rate_to_maximum_operation_rate(
        list_of_meta_data=meta_data_list
    )
    for meta_data in meta_data_list:
        if isinstance(meta_data, StreamDataFrameMetaInformation):
            colormap_string = "Greens"
            min_value_column_name: str = "minimum_operation_rate"
            max_value_column_name: str = "maximum_operation_rate"
            if meta_data.stream_type == ContinuousStream.stream_type:
                min_value_column_name: str = "minimum_operation_rate"
                max_value_column_name: str = "maximum_operation_rate"
                current_value_column_name: str = "current_operation_rate_value"
            elif meta_data.stream_type == BatchStream.stream_type:
                min_value_column_name: str = "minimum_batch_mass_value"
                max_value_column_name: str = "maximum_batch_mass_value"
                current_value_column_name: str = "batch_mass_value"
            data_frame = meta_data.data_frame
            max_value = data_frame[max_value_column_name].max()
            min_value = data_frame[min_value_column_name].min()
            norm = matplotlib.colors.Normalize(vmin=min_value, vmax=max_value)
            cmap = matplotlib.cm.get_cmap(colormap_string)
            data_frame["Colour"] = data_frame.apply(
                lambda row: cmap(norm(row[current_value_column_name])), axis=1
            )
        elif isinstance(meta_data, ProcessStepDataFrameMetaInformation):
            pass
        elif isinstance(
            meta_data, StorageDataFrameMetaInformation | ProductionOrderMetadata
        ):
            pass
        elif isinstance(
            meta_data,
            LoadProfileDataFrameMetaInformation,
        ):
            colormap_string = "OrRd"
            current_value_column_name = "average_power_consumption"
            data_frame = meta_data.data_frame
            max_value = meta_data.maximum_average_power
            min_value = 0
            norm = matplotlib.colors.Normalize(vmin=min_value, vmax=max_value)
            cmap = matplotlib.cm.get_cmap(colormap_string)
            data_frame["Colour"] = data_frame.apply(
                lambda row: cmap(norm(row[current_value_column_name])), axis=1
            )
        else:
            raise UnexpectedDataType(
                current_data_type=meta_data,
                expected_data_type=StreamDataFrameMetaInformation,
            )
    return meta_data_list


def convert_unbound_operation_rate_to_maximum_operation_rate(
    list_of_meta_data: list[
        StreamDataFrameMetaInformation
        | LoadProfileDataFrameMetaInformation
        | StorageDataFrameMetaInformation
        | ProcessStepDataFrameMetaInformation
        | ProductionOrderMetadata
    ],
) -> list[
    StreamDataFrameMetaInformation
    | LoadProfileDataFrameMetaInformation
    | StorageDataFrameMetaInformation
    | ProcessStepDataFrameMetaInformation
    | ProductionOrderMetadata
]:
    for meta_information in list_of_meta_data:
        if isinstance(meta_information, ProcessStepDataFrameMetaInformation):
            pass
        elif isinstance(meta_information, StreamDataFrameMetaInformation):
            data_frame = meta_information.data_frame
            if "maximum_operation_rate" in data_frame.columns:
                if data_frame["maximum_operation_rate"].isnull().values.any():
                    data_frame["Maximum limit has been set"] = 0

                    data_frame["maximum_operation_rate"] = data_frame[
                        "current_operation_rate_value"
                    ].max()
                else:
                    data_frame["Maximum limit has been set"] = 1
            elif "maximum_batch_mass_value" in data_frame.columns:
                if data_frame["maximum_batch_mass_value"].isnull().values.any():
                    data_frame["Maximum limit has been set"] = 0

                    data_frame["maximum_batch_mass_value"] = data_frame[
                        "batch_mass_value"
                    ].max()
                else:
                    data_frame["Maximum limit has been set"] = 1
        elif isinstance(meta_information, LoadProfileDataFrameMetaInformation):
            pass
        elif isinstance(
            meta_information, StorageDataFrameMetaInformation | ProductionOrderMetadata
        ):
            pass
        else:
            raise UnexpectedDataType(
                current_data_type=meta_information,
                expected_data_type=StreamDataFrameMetaInformation,
            )
    return list_of_meta_data
