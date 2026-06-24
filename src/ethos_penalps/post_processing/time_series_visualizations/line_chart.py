import matplotlib.axes._subplots
import pandas
import proplot
from toolz import interleave

from ethos_penalps.data_classes import LoadProfileMetaData, LoadProfileMetaDataResampled
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


def _format_load_profile_tick(value: float) -> str:
    if value == 0:
        return "0"
    abs_v = abs(value)
    if abs_v >= 100:
        return f"{value:.0f}"
    if abs_v >= 10:
        return f"{value:.1f}"
    if abs_v >= 1:
        return f"{value:.2f}"
    return f"{value:.3f}"


def _resolve_load_profile_yticks(
    data_min: float, data_max: float
) -> tuple[list[float], list[str]]:
    """Min/max ticks at 3 sig figs; collapse to a single midpoint tick when the
    data is essentially flat (range < 5% of magnitude) or labels coincide after
    rounding -- in both cases the two ticks would visually overlap on the short
    load-profile subplots."""
    if data_min == data_max:
        return [data_min], [_format_load_profile_tick(data_min)]
    reference = max(abs(data_min), abs(data_max))
    if reference > 0 and (data_max - data_min) / reference < 0.05:
        midpoint = 0.5 * (data_min + data_max)
        return [midpoint], [_format_load_profile_tick(midpoint)]
    label_min = _format_load_profile_tick(data_min)
    label_max = _format_load_profile_tick(data_max)
    if label_min == label_max:
        midpoint = 0.5 * (data_min + data_max)
        return [midpoint], [_format_load_profile_tick(midpoint)]
    return [data_min, data_max], [label_min, label_max]


def create_line_subplot(
    current_axes,
    load_profile_data_frame_meta_information: (LoadProfileMetaData | LoadProfileMetaDataResampled),
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

    start_time_df = load_profile_data_frame.loc[:, ["start_time", "average_power_consumption"]]
    start_time_df.columns = ["time_point", "average_power_consumption"]
    end_time_df = load_profile_data_frame.loc[:, ["end_time", "average_power_consumption"]]
    end_time_df.columns = ["time_point", "average_power_consumption"]

    stacked_data_frame = pandas.DataFrame(interleave([start_time_df.values, end_time_df.values]))
    stacked_data_frame.columns = ["time_point", "average_power_consumption"]
    current_axes.plot(
        stacked_data_frame["time_point"],
        stacked_data_frame["average_power_consumption"],
    )

    if load_profile_data_frame_meta_information.plot_string is None:
        title_string = (
            load_profile_data_frame_meta_information.name
            + ": "
            + load_profile_data_frame_meta_information.load_type.name
        )
    else:
        title_string = load_profile_data_frame_meta_information.plot_string
    current_axes.set_title(title_string)
    # ymin = stacked_data_frame["average_power_consumption"].min()
    if load_profile_data_frame_meta_information.minimum_power_display is None:
        base_ymin = load_profile_data_frame_meta_information.minimum_power
    else:
        base_ymin = load_profile_data_frame_meta_information.minimum_power_display
    ymin = base_ymin - load_profile_data_frame_meta_information.maximum_power * 0.2
    ymax = load_profile_data_frame_meta_information.maximum_power * 1.2
    data_min = load_profile_data_frame_meta_information.minimum_power
    data_max = load_profile_data_frame_meta_information.maximum_power
    # Pin yticks to the data extents so the expanded ymin/ymax don't crowd the
    # short subplot with extra auto-ticks (e.g. 17.5/20/22.5 around a constant 20).
    yticks, yticklabels = _resolve_load_profile_yticks(data_min, data_max)
    current_axes.format(
        ylabel=str(load_profile_data_frame_meta_information.power_unit),
        # ylabel="MW",
        ymin=ymin,
        ymax=ymax,
        yticks=yticks,
        yticklabels=yticklabels,
        ytickminor=False,
        xtickminor=False,
        grid=False,
    )
    if include_legend is True:
        current_axes.legend(loc="b", label="Load Profiles")


def create_multiple_line_plot(
    axes: proplot.gridspec.SubplotGrid,
    list_of_load_profile_data_frame_meta_information: list[LoadProfileMetaData | LoadProfileMetaDataResampled],
    use_same_axes: bool,
    is_resampled: bool,
    current_axes_number: int = 0,
):
    current_axes_in_grid = axes[current_axes_number]
    twin_axes_list = [current_axes_in_grid]
    first_load_profile = True
    twin_grid_counter = 0
    axes_position = 1
    for load_profile_data_frame_meta_information in list_of_load_profile_data_frame_meta_information:
        # if use_same_axes is True:
        #     if first_load_profile is False:
        #         twin_axes_list.append(current_axes_in_grid.twinx())
        #         current_axes = twin_axes_list[twin_grid_counter]
        #         current_axes.spines["right"].set_position(("axes", axes_position))
        #         axes_position = axes_position + 0.2
        #     else:
        #         current_axes = twin_axes_list[twin_grid_counter]
        # else:
        #     current_axes = twin_axes_list[0]
        current_axes = axes[current_axes_number]
        create_line_subplot(
            current_axes=current_axes,
            load_profile_data_frame_meta_information=load_profile_data_frame_meta_information,
            include_legend=False,
        )
        first_load_profile = False
        twin_grid_counter = twin_grid_counter + 1
    if is_resampled is True:
        legend_label = "Load Profiles Resampled"
    elif is_resampled is False:
        legend_label = "Load Profiles"
    # current_axes.legend(loc="b", label=legend_label)
