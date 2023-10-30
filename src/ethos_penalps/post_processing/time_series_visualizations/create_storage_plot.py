import datetime

import matplotlib
import matplotlib.axes._axes
import matplotlib.dates
import matplotlib.figure
import matplotlib.patches
import matplotlib.pyplot
import pandas
import proplot
import proplot.gridspec

from ethos_penalps.data_classes import (
    Commodity,
    StorageDataFrameMetaInformation,
    StorageProductionPlanEntry,
)
from ethos_penalps.utilities.units import Units


def create_storage_subplot(
    figure: matplotlib.figure.Figure,
    axes: proplot.gridspec.SubplotGrid,
    storage_meta_data_information: StorageDataFrameMetaInformation,
    subplot_number: float,
):
    # x_start = 0.5
    # x_end = 1
    data_frame = storage_meta_data_information.data_frame
    data_frame.sort_values(by=["start_time", "end_time"], ascending=False, inplace=True)
    data_frame.reset_index(inplace=True, drop=True)
    x_axis_values = []
    y_axis_values = []
    for index, row in data_frame[::-1].iterrows():
        x_axis_values.append(row["start_time"])
        x_axis_values.append(row["end_time"])
        y_axis_values.append(row["storage_level_at_start"])
        y_axis_values.append(row["storage_level_at_end"])

    current_ax = axes[subplot_number]
    # axes.plot_date(x, y, xdate=True, ydate=False)
    current_ax.fill_between(
        matplotlib.dates.date2num(x_axis_values),
        y_axis_values,
        color="blue",
        edgecolor="black",
    )
    # axes.format(xlim=(x_axis_values[-1], x_axis_values[0]))

    current_ax.set_title(
        "Storage of Process Step: "
        + storage_meta_data_information.process_step_name
        + " for Commodity: "
        + str(storage_meta_data_information.commodity.name)
    )
    current_ax.format(
        ylabel="Storage\nlevel in " + str(storage_meta_data_information.mass_unit),
        ytickminor=False,
        xtickminor=False,
        grid=False,
    )


if __name__ == "__main__":
    # fig, axs = matplotlib.pyplot.subplots()
    # axs = proplot.subplots(ncols=1, nrows=1)
    # Set Figure size
    fig = proplot.figure()
    axs = fig.subplots(ncols=1, nrows=1)
    dict_df = {
        "storage_level_at_start": [50, 200, 200],
        "start_time": [
            datetime.datetime(year=2020, month=1, day=1),
            datetime.datetime(year=2020, month=1, day=2),
            datetime.datetime(year=2020, month=1, day=2),
        ],
        "storage_level_at_end": [100, 200, 150],
        "end_time": [
            datetime.datetime(year=2020, month=1, day=2),
            datetime.datetime(year=2020, month=1, day=2),
            datetime.datetime(year=2020, month=1, day=3),
        ],
    }
    df = pandas.DataFrame(dict_df)

    test_commodity = Commodity(name="test commdoity")
    meta_inf = StorageDataFrameMetaInformation(
        first_start_time=datetime.datetime(year=2020, month=1, day=1),
        last_end_time=datetime.datetime(year=2020, month=1, day=2),
        data_frame=df,
        process_step_name="Test step",
        commodity=test_commodity,
        mass_unit=Units.mass_unit,
    )
    create_storage_subplot(
        figure=fig, axes=axs, storage_meta_data_information=meta_inf, subplot_number=0
    )
