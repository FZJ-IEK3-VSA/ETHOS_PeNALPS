import matplotlib.axes._subplots
import pandas
import proplot
from toolz import interleave

from ethos_penalps.data_classes import LoadProfileMetaData
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


def create_line_subplot(
    current_axes,
    load_profile_data_frame_meta_information: LoadProfileMetaData,
    include_legend: bool,
):
    """Creates a line plot from the load profiles.

    Args:
        current_axes (_type_): _description_
        load_profile_data_frame_meta_information (LoadProfileMetaData): _description_
        include_legend (bool): _description_
    """
    load_profile_data_frame = load_profile_data_frame_meta_information.data_frame
    # Calculate time difference for each stream

    # access current subplot

    start_time_df = load_profile_data_frame.loc[
        :, ["start_time", "average_power_consumption"]
    ]
    start_time_df.columns = ["time_point", "average_power_consumption"]
    end_time_df = load_profile_data_frame.loc[
        :, ["end_time", "average_power_consumption"]
    ]
    end_time_df.columns = ["time_point", "average_power_consumption"]

    stacked_data_frame = pandas.DataFrame(
        interleave([start_time_df.values, end_time_df.values])
    )
    stacked_data_frame.columns = ["time_point", "average_power_consumption"]
    current_axes.plot(
        stacked_data_frame["time_point"],
        stacked_data_frame["average_power_consumption"],
    )

    current_axes.set_title(
        load_profile_data_frame_meta_information.name
        + ": "
        + load_profile_data_frame_meta_information.load_type.name
    )
    ymin = stacked_data_frame["average_power_consumption"].min()
    ymax = stacked_data_frame["average_power_consumption"].max()
    current_axes.format(
        ylabel=str(load_profile_data_frame_meta_information.power_unit),
        # ymin=ymin,
        # ymax=ymax,
        ytickminor=False,
        xtickminor=False,
        grid=False,
    )
    if include_legend is True:
        current_axes.legend(loc="b", label="Load Profiles")


def create_multiple_line_plot(
    axes: proplot.gridspec.SubplotGrid,
    list_of_load_profile_data_frame_meta_information: list[LoadProfileMetaData],
    use_same_axes: bool,
    current_axes_number: int = 0,
):
    current_axes_in_grid = axes[current_axes_number]
    twin_axes_list = [current_axes_in_grid]
    first_load_profile = True
    twin_grid_counter = 0
    axes_position = 1
    for (
        load_profile_data_frame_meta_information
    ) in list_of_load_profile_data_frame_meta_information:
        if use_same_axes is True:
            if first_load_profile is False:
                twin_axes_list.append(current_axes_in_grid.twinx())
                current_axes = twin_axes_list[twin_grid_counter]
                current_axes.spines["right"].set_position(("axes", axes_position))
                axes_position = axes_position + 0.2
            else:
                current_axes = twin_axes_list[twin_grid_counter]
        else:
            current_axes = twin_axes_list[0]

        create_line_subplot(
            current_axes=current_axes,
            load_profile_data_frame_meta_information=load_profile_data_frame_meta_information,
            include_legend=False,
        )
        first_load_profile = False
        twin_grid_counter = twin_grid_counter + 1
    current_axes.legend(loc="b", label="Load Profiles")
