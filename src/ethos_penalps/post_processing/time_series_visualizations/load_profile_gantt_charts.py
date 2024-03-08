import datetime
import logging
import os
from pickletools import read_uint1


import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import proplot
from matplotlib import cm

from ethos_penalps.data_classes import (
    LoadProfileMetaData,
    ProcessStepDataFrameMetaInformation,
)

from ethos_penalps.utilities.units import Units
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


def create_load_profile_gantt_chart(
    fig,
    axs,
    load_profile_meta_data: LoadProfileMetaData,
    subplot_number: float,
    start_time_column_name: str = "start_time",
    cmap_name: str = "OrRd",
    max_value_column_name: str = "maximum_energy",
    colour_column_name: str = "Colour",
    bar_lower_y_height: float = 0,
    bar_width: float = 1,
    end_time_column_name: str = "end_time",
    number_of_colorbar_ticks: float = 4,
):
    data_frame = load_profile_meta_data.data_frame

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
    bar_lower_y_height = 0
    bar_width = 1
    # access current subplot
    current_ax = axs[subplot_number]
    # remove y_ticks and set y limit to width of a bar
    current_ax.format(
        ylocator=proplot.Locator("none"),
        ylim=(bar_lower_y_height, +bar_lower_y_height + bar_width),
    )

    load_profile_data_frame = load_profile_meta_data.data_frame
    # # get all dataframe entries of the object to be plotted
    # temporary_process_step_data_frame = data_frame[
    #     data_frame[row_name].isin([object_name])
    # ]

    # Plot bars
    barh_axes = current_ax.broken_barh(
        load_profile_data_frame["barh tuple"],
        (bar_lower_y_height, bar_width),
        label=load_profile_meta_data.object_type + load_profile_meta_data.name,
        facecolors=load_profile_data_frame[colour_column_name],
        # edgecolors="black",
    )
    # Create colour bar plots
    # Determine minimum and maximum operation rate of the current object

    min_value = 0
    max_value = load_profile_meta_data.maximum_power
    cmap = matplotlib.cm.get_cmap(cmap_name)

    # Create list of colourbar tick numbers
    normalized_tick_values = list(np.linspace(0, 1, number_of_colorbar_ticks))
    # Create list of values which are represented by the colour

    denormalized_tick_values = []
    max_power_quantity = Units.compress_quantity(
        quantity_value=max_value, unit=load_profile_meta_data.power_unit
    )
    for tick_value in normalized_tick_values:
        denormalized_tick_values.append(
            str(
                round(
                    denormalize(
                        tick_value,
                        min_value,
                        float(max_power_quantity.m),
                    ),
                    1,
                )
            )
        )

    # plot colourbar
    # current_ax.colorbar(barh_axes)
    current_ax.colorbar(
        cmap,
        loc="b",
        ax=current_ax,
        locator=proplot.Locator("fixed", np.linspace(0, 1, number_of_colorbar_ticks)),
        ticklabels=denormalized_tick_values,
        label="Average Power in " + str(max_power_quantity.u),
        width=0.1,
    )
    current_ax.set_title(
        str(load_profile_meta_data.load_type.name)
        + " Load Profile of "
        + load_profile_meta_data.object_type
        + ": "
        + load_profile_meta_data.name
    )
