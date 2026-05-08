import datetime
import itertools
import logging
import os
import warnings
from typing import Literal

import matplotlib
import matplotlib.pyplot
import matplotlib.pyplot as plt
import plotly.express as px
import proplot
from matplotlib import cm

from ethos_penalps.data_classes import (
    EmptyLoadProfileMetadata,
    EmptyMetaDataInformation,
    LoadProfileMetaData,
    LoadProfileMetaDataFromDisk,
    LoadProfileMetaDataResampled,
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
from ethos_penalps.post_processing.time_series_visualizations.order_plot import (
    create_order_gantt_plot,
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

logger = PeNALPSLogger.get_logger_without_handler()


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
                output_stream = self.stream_handler.get_stream(stream_name=main_output_stream_name)
                downstream_node_name = output_stream.get_downstream_node_name()
                downstream_node = self.process_node_dict[downstream_node_name]
                if isinstance(downstream_node, Sink):
                    list_of_object_names.append(main_output_stream_name)
        return list_of_object_names

    def create_load_profile_gantt_chart_from_load_profile_meta_data(
        self,
        load_profile_meta_data: LoadProfileMetaData,
        save_path: str | None = None,
    ):
        sliced_list_of_meta_data = slice_data_frames(
            list_of_meta_data_objects=[load_profile_meta_data],
            start_date=load_profile_meta_data.first_start_time,
            end_date=load_profile_meta_data.last_end_time,
        )

        list_of_unbound_stream_data_frame = convert_unbound_operation_rate_to_maximum_operation_rate(
            list_of_meta_data=sliced_list_of_meta_data
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

    def create_gantt_chart_from_list_of_meta_data(
        self,
        list_of_meta_data: list[
            StorageDataFrameMetaInformation
            | LoadProfileMetaData
            | LoadProfileMetaDataResampled
            | ProcessStepDataFrameMetaInformation
            | StreamDataFrameMetaInformation
            | ProductionOrderMetadata
            | EmptyLoadProfileMetadata
            | EmptyMetaDataInformation
        ],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        gantt_chart_title: str = "",
        output_file_path: str | None = None,
        dpi: int | None = 300,
        image_format: str = "png",
        label_language: Literal["german", "english"] = "english",
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
            output_file_path=output_file_path,
            dpi=dpi,
            image_format=image_format,
            label_language=label_language,
        )

        return figure

    def preprocess_meta_data(
        self,
        list_of_meta_data: list[
            StorageDataFrameMetaInformation
            | LoadProfileMetaData
            | LoadProfileMetaDataResampled
            | ProcessStepDataFrameMetaInformation
            | StreamDataFrameMetaInformation
            | ProductionOrderMetadata
            | EmptyMetaDataInformation
            | EmptyLoadProfileMetadata
        ],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[
        StorageDataFrameMetaInformation
        | LoadProfileMetaData
        | LoadProfileMetaDataResampled
        | ProcessStepDataFrameMetaInformation
        | StreamDataFrameMetaInformation
        | ProductionOrderMetadata
        | EmptyMetaDataInformation
        | EmptyLoadProfileMetadata
    ]:
        sliced_list_of_meta_data = slice_data_frames(
            list_of_meta_data_objects=list_of_meta_data,
            start_date=start_date,
            end_date=end_date,
        )

        list_of_unbound_stream_data_frame = convert_unbound_operation_rate_to_maximum_operation_rate(
            list_of_meta_data=sliced_list_of_meta_data
        )

        list_of_preprocessed_meta_data = create_color_column(meta_data_list=list_of_unbound_stream_data_frame)
        return list_of_preprocessed_meta_data


def create_gantt_chart(
    list_of_data_frame_meta_data: list[
        ProcessStepDataFrameMetaInformation
        | StreamDataFrameMetaInformation
        | LoadProfileMetaData
        | LoadProfileMetaDataResampled
        | StorageDataFrameMetaInformation
        | ProductionOrderMetadata
    ],
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    reverse_y_graph_order=False,
    output_file_path: str | None = None,
    show_graph: bool = False,
    gantt_chart_title: str = "Process Gantt Chart",
    dpi: int | None = 300,
    image_format: str = "png",
    label_language: Literal["german", "english"] = "english",
) -> matplotlib.pyplot.Figure | None:
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

    # Determine number of subplots

    number_of_process_steps = len(list_of_data_frame_meta_data)
    # Create figure and subpots
    fig = proplot.figure(refwidth="14cm", refheight="0.5cm", sharey=0, sharex="all")
    axs = fig.subplots(
        ncols=1,
        nrows=number_of_process_steps,
    )

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
                label_language=label_language,
            )
            all_data_frames_were_empty = False
        elif isinstance(data_frame_meta_information, StreamDataFrameMetaInformation):
            create_stream_subplot(
                axs=axs,
                fig=fig,
                subplot_number=subplot_number,
                stream_data_frame_meta_information=data_frame_meta_information,
                label_language=label_language,
            )
            all_data_frames_were_empty = False
        elif isinstance(
            data_frame_meta_information,
            (LoadProfileMetaData, LoadProfileMetaDataResampled, LoadProfileMetaDataFromDisk),
        ):
            if isinstance(data_frame_meta_information, (LoadProfileMetaData, LoadProfileMetaDataFromDisk)):
                is_resampled = False
            elif isinstance(data_frame_meta_information, LoadProfileMetaDataResampled):
                is_resampled = True
            list_of_load_profiles_meta_data_information.append(data_frame_meta_information)
            create_multiple_line_plot(
                axes=axs,
                list_of_load_profile_data_frame_meta_information=[data_frame_meta_information],
                use_same_axes=False,
                current_axes_number=subplot_number,
                is_resampled=is_resampled,
            )
            all_data_frames_were_empty = False
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
                label_language=label_language,
            )
            all_data_frames_were_empty = False
        elif isinstance(data_frame_meta_information, ProductionOrderMetadata):
            create_order_gantt_plot(
                fig=fig,
                current_axs=axs,
                order_meta_data=data_frame_meta_information,
                subplot_number=subplot_number,
            )
            all_data_frames_were_empty = False
        else:
            raise Exception("Unexpected datatype")

        subplot_number = subplot_number + 1

    # for plot_number in range(1, subplot_number):
    #     # axs[plot_number].sharex(axs[plot_number - 1])
    #     axs[plot_number].sharey(False)
    if all_data_frames_were_empty:
        warnings.warn("All data frames were empty. There is nothing to plot")
        fig = None
    else:
        if start_date != end_date:
            axs.format(xlim=(start_date, end_date))

        axs.format(suptitle=gantt_chart_title)
        if label_language == "english":
            xlabel = "Time"
        elif label_language == "german":
            xlabel = "Zeit"

        axs.format(xrotation=45, xlabel=xlabel)

        # Save figure to path
        if isinstance(output_file_path, str):
            plt.savefig(output_file_path, format=image_format, dpi=dpi)
        # Show figure
        if show_graph is True:
            plt.show(block=True)

    return fig


def create_color_column(
    meta_data_list: list[
        StreamDataFrameMetaInformation
        | LoadProfileMetaData
        | LoadProfileMetaDataResampled
        | StorageDataFrameMetaInformation
        | ProcessStepDataFrameMetaInformation
        | ProductionOrderMetadata
    ],
    current_value_column_name: str = "current_operation_rate_value",
) -> list[
    StreamDataFrameMetaInformation
    | LoadProfileMetaData
    | LoadProfileMetaDataResampled
    | StorageDataFrameMetaInformation
    | ProcessStepDataFrameMetaInformation
    | ProductionOrderMetadata
]:
    meta_data_list = convert_unbound_operation_rate_to_maximum_operation_rate(list_of_meta_data=meta_data_list)
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
                current_value_column_name: str = "total_mass"
            data_frame = meta_data.data_frame
            max_value = data_frame[max_value_column_name].max()
            min_value = data_frame[min_value_column_name].min()
            norm = matplotlib.colors.Normalize(vmin=min_value, vmax=max_value)
            cmap = matplotlib.cm.get_cmap(colormap_string)
            data_frame["Colour"] = data_frame.apply(lambda row: cmap(norm(row[current_value_column_name])), axis=1)
        elif isinstance(meta_data, ProcessStepDataFrameMetaInformation):
            pass
        elif isinstance(meta_data, StorageDataFrameMetaInformation | ProductionOrderMetadata):
            pass
        elif isinstance(meta_data, (LoadProfileMetaData, LoadProfileMetaDataResampled, LoadProfileMetaDataFromDisk)):
            colormap_string = "OrRd"
            current_value_column_name = "average_power_consumption"
            data_frame = meta_data.data_frame
            max_value = meta_data.maximum_power
            min_value = meta_data.minimum_power
            norm = matplotlib.colors.Normalize(vmin=min_value, vmax=max_value)
            cmap = matplotlib.cm.get_cmap(colormap_string)
            data_frame["Colour"] = data_frame.apply(lambda row: cmap(norm(row[current_value_column_name])), axis=1)
        else:
            raise UnexpectedDataType(
                current_data_type=meta_data,
                expected_data_type=StreamDataFrameMetaInformation,
            )
    return meta_data_list


def convert_unbound_operation_rate_to_maximum_operation_rate(
    list_of_meta_data: list[
        StreamDataFrameMetaInformation
        | LoadProfileMetaData
        | LoadProfileMetaDataResampled
        | StorageDataFrameMetaInformation
        | ProcessStepDataFrameMetaInformation
        | ProductionOrderMetadata
    ],
) -> list[
    StreamDataFrameMetaInformation
    | LoadProfileMetaData
    | StorageDataFrameMetaInformation
    | ProcessStepDataFrameMetaInformation
    | ProductionOrderMetadata
    | LoadProfileMetaDataResampled
]:
    for meta_information in list_of_meta_data:
        if isinstance(meta_information, ProcessStepDataFrameMetaInformation):
            pass
        elif isinstance(meta_information, StreamDataFrameMetaInformation):
            data_frame = meta_information.data_frame
            if "maximum_operation_rate" in data_frame.columns:
                if data_frame["maximum_operation_rate"].isnull().values.any():
                    data_frame["Maximum limit has been set"] = 0

                    data_frame["maximum_operation_rate"] = data_frame["current_operation_rate_value"].max()
                else:
                    data_frame["Maximum limit has been set"] = 1
            elif "maximum_batch_mass_value" in data_frame.columns:
                if data_frame["maximum_batch_mass_value"].isnull().values.any():
                    data_frame["Maximum limit has been set"] = 0

                    data_frame["maximum_batch_mass_value"] = data_frame["batch_mass_value"].max()
                else:
                    data_frame["Maximum limit has been set"] = 1
        elif isinstance(
            meta_information, (LoadProfileMetaData, LoadProfileMetaDataResampled, LoadProfileMetaDataFromDisk)
        ):
            pass
        elif isinstance(meta_information, StorageDataFrameMetaInformation | ProductionOrderMetadata):
            pass
        else:
            raise UnexpectedDataType(
                current_data_type=meta_information,
                expected_data_type=StreamDataFrameMetaInformation,
            )
    return list_of_meta_data
