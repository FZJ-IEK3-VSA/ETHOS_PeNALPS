import datetime
import logging
import os
from pickletools import read_uint1

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import proplot
from matplotlib import cm

from ethos_penalps.data_classes import (
    LoadProfileDataFrameMetaInformation,
    ProcessStepDataFrameMetaInformation,
)
from ethos_penalps.post_processing.time_series_visualizations.stream_gantt_chart import (
    create_stream_subplot,
    slice_data_frames,
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


def create_process_state_gantt_charts(
    list_of_process_state_data_frames: list[ProcessStepDataFrameMetaInformation],
    reverse_y_graph_order=False,
    output_file_path: str | None = None,
    start_time_column_name: str = "start_time",
    end_time_column_name: str = "end_time",
    block_type: str = "process_state_name",
    cmap_name: str = "Set1",
    show_graph: bool = True,
):
    """
    creates a process state gantt chart

    :param data_frame: Contains the data used to plot the gantt chart. Each row must contain one entry for the columns:
        - Start time: Describes the start time of an task which is represented by an individual block in the graph
        - End time: Describes the end time of an task which is represented by an individual block in the graph
        - Object name: Corresponds to a row in the Graph
        - Color columns: Constitutes the different colours that a block can have in the graph
        - Object type: Determines on which side of the graph the name of the Object name is displayed. Can be either "Stream" or "Process step"
        - Maximum limit has been set # TODO: Implement visualization for limited streams
        - is either 1 or 0. 1 indicates that an external limit has been set. 0 indicates that nor external limit has been set
    :type data_frame: pd.DataFrame
    :param reverse_y_graph_order: Reverses the vertical order of streams displayed if set to True, defaults to False
    :type reverse_y_graph_order: bool, optional
    :param output_file_path: Can be used to provide a full path including file name and file extension to store the Gantt chart.
    """
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

    # Determine number of subplots
    # unique_object_names = data_frame[row_name].unique()
    number_of_process_steps = len(list_of_process_state_data_frames)
    # Create figure and subpots
    fig = proplot.figure()
    axs = fig.subplots(ncols=1, nrows=number_of_process_steps)
    # Set Figure size
    fig.set_size_inches(19, 6, forward=True)

    # Get global start and end date

    # Set bar y start point and y width
    bar_lower_y_height = 0
    bar_width = 1

    # Define subplot-number
    subplot_number = 0
    if reverse_y_graph_order == True:
        list_of_process_state_data_frames = list_of_process_state_data_frames[::-1]
    # Loop over uniqe objects in dataframe
    for data_frame_meta_information in list_of_process_state_data_frames:
        if data_frame_meta_information.data_frame.empty:
            continue
        current_ax = create_process_state_subplot(
            axs=axs,
            subplot_number=subplot_number,
            process_state_meta_data=data_frame_meta_information,
        )
        min_start_date_current_data_frame = data_frame_meta_information.first_start_time
        max_end_date_current_data_frame = data_frame_meta_information.last_end_time
        if subplot_number == 0:
            global_start_date = min_start_date_current_data_frame
            global_end_date = max_end_date_current_data_frame
        else:
            if min_start_date_current_data_frame < global_start_date:
                global_start_date = min_start_date_current_data_frame
            if max_end_date_current_data_frame > global_end_date:
                global_end_date = max_end_date_current_data_frame
        subplot_number = subplot_number + 1

    axs.format(xlim=(global_start_date, global_end_date))
    axs.format(
        suptitle="Process state chart from the "
        + str(global_start_date)
        + " until "
        + str(global_end_date)
    )

    # Save figure to path
    if output_file_path is None:
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


def create_process_state_subplot(
    axs: proplot.gridspec.SubplotGrid,
    process_state_meta_data: ProcessStepDataFrameMetaInformation,
    subplot_number: float,
    start_time_column_name: str = "start_time",
    cmap_name="Set1",
    block_type: str = "process_state_name",
    bar_lower_y_height: float = 0,
    bar_width: float = 1,
    end_time_column_name: str = "end_time",
):
    data_frame = process_state_meta_data.data_frame

    # subplot_number = subplot_number + 1

    # Calculate time difference for each stream
    data_frame["Time difference"] = (
        data_frame[end_time_column_name] - data_frame[start_time_column_name]
    )
    # Create column with touple (start_time : datetime.datetime, time_difference : datetime:timedelta)
    data_frame["barh tuple"] = list(
        zip(
            data_frame[start_time_column_name],
            data_frame["Time difference"],
        )
    )
    process_step_name = process_state_meta_data.process_step_name
    # access current subplot
    current_ax = axs[subplot_number]
    # remove y_ticks and set y limit to width of a bar
    cmap = matplotlib.cm.get_cmap(cmap_name)
    colors = cmap.colors
    current_ax.format(
        ylocator=proplot.Locator("none"),
        ylim=(bar_lower_y_height, +bar_lower_y_height + bar_width),
        ytickminor=False,
        xtickminor=False,
        grid=False,
    )

    color_iterator = 0
    process_state_names = process_state_meta_data.list_of_process_state_names
    for process_state_name in process_state_names:
        # get all data frame entries of the object to be plotted
        temporary_process_step_data_frame = data_frame[
            data_frame[block_type].isin([process_state_name])
        ]

        # Plot bars
        current_ax.broken_barh(
            temporary_process_step_data_frame["barh tuple"],
            (bar_lower_y_height, bar_width),
            label=process_state_name,
            color=colors[color_iterator],
        )
        color_iterator = color_iterator + 1

    current_ax.legend(loc="b", label="Process States")

    # Set subplot title to object name and increment subplot number
    current_ax.set_title("Process step: " + process_step_name)
    subplot_number = subplot_number + 1
