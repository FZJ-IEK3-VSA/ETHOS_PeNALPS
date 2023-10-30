import datetime

import matplotlib
import matplotlib.dates
import matplotlib.pyplot
import numpy as np
import pandas
import proplot

from ethos_penalps.data_classes import (
    LoadProfileDataFrameMetaInformation,
    LoadProfileEntry,
    LoadType,
)


def create_stacked_line_plot(
    list_of_load_profile_meta_data_information: list[
        LoadProfileDataFrameMetaInformation
    ],
    file_path: str | None = None,
):
    proplot.rc["grid.linewidth"] = 0
    proplot.rc["ytick.minor.size"] = 0
    proplot.rc["xtick.minor.size"] = 0
    cycle = ("gray3", "gray5", "gray7")
    y_axis_values = []
    x_axis_values = []
    iterator = 0
    label_list = []
    for (
        load_profile_meta_data_information
    ) in list_of_load_profile_meta_data_information:
        y_axis_values.append([])
        # x_axis_values.append([])
        x_axis_values = []
        label_list.append(load_profile_meta_data_information.name)
        for index, row in load_profile_meta_data_information.data_frame[
            ::-1
        ].iterrows():
            # x_axis_values[iterator].append(row["end_time"])
            # x_axis_values[iterator].append(row["start_time"])
            x_axis_values.append(row["end_time"])
            x_axis_values.append(row["start_time"])

            # x_axis_values.append(iterator)
            # x_axis_values.append(iterator)
            y_axis_values[iterator].append(row["average_power_consumption"])
            y_axis_values[iterator].append(row["average_power_consumption"])

        # x_axis_values[iterator] = matplotlib.dates.date2num(x_axis_values[iterator])
        x_axis_values = matplotlib.dates.date2num(x_axis_values)
        iterator = iterator + 1
    figure = proplot.figure(refwidth=2.1, share=False, grid=False)
    axes = figure.add_subplot(111)
    axes.area(
        x_axis_values,
        np.transpose(y_axis_values),
        stack=True,
        legend_kw={"labels": label_list},
    )
    axes.format(
        xlim=(
            load_profile_meta_data_information.first_start_time,
            load_profile_meta_data_information.last_end_time,
        ),
        # ylim=50,
        xformatter="%H:%M",
        # ylocator="null",
    )
    axes.legend(loc="b", label="Demand Sources", ncols=2)
    axes.set_title(load_profile_meta_data_information.load_type.name)
    axes.set_ylabel(
        "Power /" + str(load_profile_meta_data_information.power_unit.__str__())
    )
    # figure.show()
    # figure.legend(ncols=2)
    if type(file_path) is str:
        figure.savefig(file_path)
    print("done")
