import datetime
import logging
import os
from pickletools import read_uint1

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas
import plotly.express as px
import proplot
from matplotlib import cm

from ethos_penalps.data_classes import (
    LoadProfileDataFrameMetaInformation,
    ProcessStepDataFrameMetaInformation,
    StorageDataFrameMetaInformation,
    EmptyMetaDataInformation,
    ProductionOrderMetadata,
)
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream import (
    BatchStream,
    ContinuousStream,
    StreamDataFrameMetaInformation,
)
from ethos_penalps.utilities.data_base_interactions import DataBaseInteractions
from ethos_penalps.utilities.exceptions_and_warnings import UnexpectedDataType
from ethos_penalps.utilities.general_functions import ResultPathGenerator, denormalize
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


def slice_data_frames(
    list_of_meta_data_objects: list[
        StreamDataFrameMetaInformation
        | ProcessStepDataFrameMetaInformation
        | LoadProfileDataFrameMetaInformation
        | StorageDataFrameMetaInformation
        | EmptyMetaDataInformation
        | ProductionOrderMetadata
    ],
    start_date: datetime.datetime,
    end_date: datetime.datetime,
) -> list[
    StreamDataFrameMetaInformation
    | ProcessStepDataFrameMetaInformation
    | LoadProfileDataFrameMetaInformation
    | StorageDataFrameMetaInformation
    | EmptyMetaDataInformation
    | ProductionOrderMetadata
]:
    new_list_of_meta_data_frames = []
    for meta_information in list_of_meta_data_objects:
        if not isinstance(meta_information, StorageDataFrameMetaInformation):
            if isinstance(meta_information, EmptyMetaDataInformation):
                logger.debug(
                    "The data data frame supplied to the data gantt chart generator is empty"
                )
            elif meta_information.data_frame.empty:
                logger.debug(
                    "The data data frame supplied to the data gantt chart generator is empty"
                )

        if isinstance(
            meta_information,
            StreamDataFrameMetaInformation
            | ProcessStepDataFrameMetaInformation
            | LoadProfileDataFrameMetaInformation
            | StorageDataFrameMetaInformation,
        ):
            stream_data_frame = meta_information.data_frame
            meta_information.first_start_time = start_date
            meta_information.last_end_time = end_date
            sliced_data_frame = stream_data_frame.loc[
                stream_data_frame["end_time"] >= start_date
            ]
            sliced_data_frame = sliced_data_frame.loc[
                stream_data_frame["start_time"] <= end_date
            ]
            meta_information.data_frame = sliced_data_frame
            meta_information.first_start_time = sliced_data_frame["start_time"].min()
            meta_information.last_end_time = sliced_data_frame["end_time"].max()
            new_list_of_meta_data_frames.append(meta_information)
        elif isinstance(meta_information, ProductionOrderMetadata):
            # TODO: Slice Order
            new_list_of_meta_data_frames.append(meta_information)
        elif isinstance(meta_information, EmptyMetaDataInformation):
            pass
        else:
            raise Exception("Unexpected datatype")

    return new_list_of_meta_data_frames


def create_stream_gantt_charts(
    data_frame_list: list[StreamDataFrameMetaInformation],
    reverse_y_graph_order=False,
    output_file_path: str | None = None,
    start_time_column_name: str = "start_time",
    end_time_column_name: str = "end_time",
    row_name: str = "Object name",
    colour_column_name: str = "Colour",
    maximum_limit_has_been_set_column="Maximum limit has been set",
    min_value_column_name: str = "minimum_operation_rate",
    max_value_column_name: str = "maximum_operation_rate",
    cmap_name: str = "Greens",
    number_of_colorbar_ticks: float = 4,
    show_graph: bool = False,
):
    """
    Create a stream gantt chart.

    :param data_frame: Contains the data used to plot the gantt chart. Each row must contain one entry for the columns:
        - Start time

            - Describes the start time of an task which is represented by an individual block in the graph

        - End time

            - Describes the end time of an task which is represented by an individual block in the graph
        - Object name

            - Corresponds to a row in the Graph

        - Color columns

            - Constitutes the different colors that a block can have in the graph

        - Object type

            - Determines on which side of the graph the name of the Object name is displayed
            - can be either "Stream" or "Process step"

        - Maximum limit has been set # TODO: Implement visualization for limited streams

            - is either 1 or 0. 1 indicates that an external limit has been set. 0 indicates that nor external limit has been set

    :type data_frame: pd.DataFrame
    :param reverse_y_graph_order: Reverses the vertical order of streams displayed if set to True, defaults to False
    :type reverse_y_graph_order: bool, optional
    :param output_file_path: Can be used to provide a full path including file name and file extension to store the Gantt chart.
        If set to None an image folder is created and the file is stored as an .svg graphic with a timestamp, defaults to None
    :type output_file_path: str | None, optional
    :param start_time_column_name: Provides the column name in the data frame which contains the start times of the streams, defaults to "Start time"
    :type start_time_column_name: str, optional
    :param end_time_column_name: Provides the column name in the data frame which contains the end times of the streams, defaults to "End time"
    :type end_time_column_name: str, optional
    :param row_name: Provides the column name in the data frame object names. Each unique object is represented by an own row or rather subplot , defaults to "Object name"
    :type row_name: str, optional
    :param color_column_name: Provides the column name in the data frame which contains an rgb tuple for each bar in the graph.
        The rgb tuple is expected to represent a value between the min and max value, defaults to "Color"
    :type color_column_name: str, optional
    :param maximum_limit_has_been_set_column: Provides the column name in the data frame which contains the information if the stream has been restricted , defaults to "Maximum limit has been set"
    :type maximum_limit_has_been_set_column: str, optional
    :param min_value_column_name: Provides the column name in the data frame which contains the minimum operation rate of each bar, defaults to "Minimum operation rate"
    :type min_value_column_name: str, optional
    :param max_value_column_name: Provides the column name in the data frame which contains the maximum operation rate of each bar, defaults to "Maximum operation rate"
    :type max_value_column_name: str, optional
    :param cmap_name: Contains the name of the matplotlib color bar which is used in the plotting. Should be the same used to determine the rgb values in the colour column, defaults to "Greens"
    :type cmap_name: str, optional
    :param number_of_colorbar_ticks: Represents the number of ticks at the color bar , defaults to 4
    :type number_of_colorbar_ticks: float, optional
    """
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

    # Determine number of subplots

    # Create figure and subpots
    fig = proplot.figure()
    axs = fig.subplots(ncols=1, nrows=len(data_frame_list))
    # Set Figure size
    fig.set_size_inches(19, 6, forward=True)

    # Get global start and end date

    # Set bar y start point and y width
    bar_lower_y_height = 0
    bar_width = 1

    # Define subplot-number
    subplot_number = 0
    if reverse_y_graph_order == True:
        unique_object_names = unique_object_names[::-1]
    # Loop over uniqe objects in dataframe
    for stream_data_frame_meta_information in data_frame_list:
        create_stream_subplot(
            axs=axs,
            fig=fig,
            stream_data_frame_meta_information=stream_data_frame_meta_information,
            subplot_number=subplot_number,
        )

        min_start_date_current_data_frame = (
            stream_data_frame_meta_information.first_start_time
        )
        max_end_date_current_data_frame = (
            stream_data_frame_meta_information.last_end_time
        )
        if subplot_number == 0:
            global_start_date = min_start_date_current_data_frame
            global_end_date = max_end_date_current_data_frame
        else:
            if min_start_date_current_data_frame < global_start_date:
                global_start_date = min_start_date_current_data_frame
            if max_end_date_current_data_frame > global_end_date:
                global_end_date = max_end_date_current_data_frame
        # Set subplot title to object name and increment subplot number

        subplot_number = subplot_number + 1

    axs.format(xlim=(global_start_date, global_end_date))
    axs.format(
        suptitle="Streamchart from the "
        + str(global_start_date)
        + " until "
        + str(global_end_date)
    )
    # Save figure to path
    if output_file_path == None:
        result_path_generator = ResultPathGenerator()
        output_file_path = (
            result_path_generator.create_path_to_file_relative_to_main_file(
                file_name="stream_gantt_chart",
                subdirectory_name="results",
                file_extension=".eps",
            )
        )
    plt.savefig(output_file_path, format="eps")
    # Show figure
    if show_graph is True:
        plt.show(block=True)
    return fig


def create_stream_subplot(
    axs: proplot.gridspec.SubplotGrid,
    fig: proplot.Figure,
    subplot_number: int,
    stream_data_frame_meta_information: StreamDataFrameMetaInformation,
    start_time_column_name: str = "start_time",
    min_value_column_name: str = "minimum_operation_rate",
    max_value_column_name: str = "maximum_operation_rate",
    end_time_column_name: str = "end_time",
    row_name: str = "Object name",
    colour_column_name: str = "Colour",
    cmap_name: str = "Greens",
    number_of_colorbar_ticks: float = 4,
):
    stream_data_frame = stream_data_frame_meta_information.data_frame
    # Calculate time difference for each stream
    stream_data_frame["Time difference"] = (
        stream_data_frame[end_time_column_name]
        - stream_data_frame[start_time_column_name]
    )
    # Create column with touple (start_time : datetime.datetime, time_difference : datetime:timedelta)
    stream_data_frame["barh tuple"] = list(
        zip(
            stream_data_frame[start_time_column_name],
            stream_data_frame["Time difference"],
        )
    )
    bar_lower_y_height = 0
    bar_width = 1
    # access current subplot
    current_ax = axs[subplot_number]
    # remove y_ticks and set y limit to width of a bar
    current_ax.format(
        ylocator=proplot.Locator("none"),
        ylim=(bar_lower_y_height, +bar_lower_y_height + bar_width),
        ytickminor=False,
        xtickminor=False,
        grid=False,
    )

    # # get all dataframe entries of the object to be plotted
    # temporary_process_step_data_frame = data_frame[
    #     data_frame[row_name].isin([object_name])
    # ]

    # Plot bars
    current_ax.broken_barh(
        stream_data_frame["barh tuple"],
        (bar_lower_y_height, bar_width),
        label=stream_data_frame_meta_information.stream_name,
        facecolors=stream_data_frame[colour_column_name],
        # edgecolors="black",
    )
    # Create colour bar plots
    # Determine minimum and maximum operation rate of the current object
    if stream_data_frame_meta_information.stream_type == ContinuousStream.stream_type:
        min_value_column_name = "minimum_operation_rate"
        max_value_column_name = "maximum_operation_rate"
    elif stream_data_frame_meta_information.stream_type == BatchStream.stream_type:
        min_value_column_name = "minimum_batch_mass_value"
        max_value_column_name = "maximum_batch_mass_value"

    min_value = stream_data_frame[min_value_column_name].min()
    max_value = stream_data_frame[max_value_column_name].max()
    cmap = matplotlib.cm.get_cmap(cmap_name)

    # Create list of colourbar tick numbers
    normalized_tick_values = list(np.linspace(0, 1, number_of_colorbar_ticks))
    # Create list of values which are represented by the colour
    denormalized_tick_values = []
    for tick_value in normalized_tick_values:
        denormalized_tick_values.append(
            str(round(denormalize(tick_value, min_value, max_value), 1))
        )

    if stream_data_frame_meta_information.stream_type == "BatchStream":
        colorbar_label = "Mass per batch in: " + str(
            stream_data_frame_meta_information.mass_unit
        )
    if stream_data_frame_meta_information.stream_type == "ContinuousStream":
        colorbar_label = "Mass in: " + str(stream_data_frame_meta_information.mass_unit)
    # plot colourbar
    current_ax.colorbar(
        cmap,
        loc="b",
        ax=current_ax,
        locator=proplot.Locator("fixed", np.linspace(0, 1, number_of_colorbar_ticks)),
        ticklabels=denormalized_tick_values,
        label=colorbar_label,
        width=0.1,
    )
    current_ax.set_title(
        "Stream: " + stream_data_frame_meta_information.name_to_display
    )
