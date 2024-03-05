import datetime

import matplotlib.dates
import matplotlib.figure
import matplotlib.pyplot
import matplotlib.ticker
import numpy
import pandas
import seaborn

from ethos_penalps.data_classes import (
    CarpetPlotMatrix,
    CarpetPlotMatrixEmpty,
    LoadProfileDataFrameMetaInformation,
    LoadProfileEntry,
    LoadType,
    ListOfLoadProfileMetaData,
    ListLoadProfileMetaDataEmpty,
)
from ethos_penalps.post_processing.load_profile_entry_post_processor import (
    LoadProfileEntryPostProcessor,
    ListOfLoadProfileEntryAnalyzer,
)
from ethos_penalps.utilities.exceptions_and_warnings import Misconfiguration
from ethos_penalps.utilities.general_functions import (
    check_if_date_1_is_before_date_2,
    check_if_date_1_is_before_or_at_date_2,
    create_subscript_string_matplotlib,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.units import Units

logger = PeNALPSLogger.get_logger_without_handler()


class LoadProfilePostProcessor:
    def __init__(self) -> None:
        self.load_type: LoadType
        self.energy_unit: str
        self.power_unit: str
        self.start_time_of_input_load_profile: datetime.datetime
        self.end_time_of_input_load_profile: datetime.datetime
        self.processed_list_of_load_profile_entries: list[LoadProfileEntry]
        self.start_date_resampled_load_profile: datetime.datetime
        self.end_date_resampled_load_profile: datetime.datetime

    def convert_lpg_load_profile_to_data_frame_matrix(
        self,
        list_of_load_profile_entries: list[LoadProfileEntry],
        start_date_time_series: datetime.datetime,
        end_date_time_series: datetime.datetime,
        object_name: str,
        x_axis_time_period_timedelta: datetime.timedelta = datetime.timedelta(weeks=1),
        resample_frequency: str = "1min",
    ) -> CarpetPlotMatrix | CarpetPlotMatrixEmpty:
        """Converts a list of load profiles into a CarpetPlotMatrix
        which is used to create carpet plots.
            1. The list of load profiles is homogenized
            2. The list of load profiles is converted into a data frame
            3. The data frame and meta information about the list
                is passed to CarpetPlotMatrix instance.

        Args:
            list_of_load_profile_entries (list[LoadProfileEntry]): The list of load profiles
            start_date_time_series (datetime.datetime): The new start time of the list of load profiles.
                If the start time is later than the earliest time the start date is ignored.
            end_date_time_series (datetime.datetime): The new end time of list of load profiles.
                A zero demand entry is appended to series if the end date provided is later than
                the last load profile entry in the list.
            x_axis_time_period_timedelta (datetime.timedelta, optional): _description_. Defaults to datetime.timedelta(weeks=1).
            resample_frequency (str, optional): _description_. Defaults to "1min".

        Raises:
            Exception: Raises an exception for ill defined start dates, end dates and x_axis_time_period_timedelta

        Returns:
            CarpetPlotMatrix: A dataclass that contains all information that is necessary to create
            a load profile carpet plot.
        """
        if not list_of_load_profile_entries:
            logger.info(
                "An empty list of load profiles has been passed to te load profile processor"
            )

        # Check if the start date, end date and x axis time delta are well defined.
        total_time_period = end_date_time_series - start_date_time_series
        if total_time_period <= datetime.timedelta(hours=0):
            raise Misconfiguration(
                """A negative time period has been defined for the processing of the load profile.
                                   The start date: """
                + str(start_date_time_series)
                + """should be earlier than the end date: """
                + str(end_date_time_series)
            )
        number_of_periods = (total_time_period) / x_axis_time_period_timedelta
        if number_of_periods <= 0:
            raise Misconfiguration(
                """No positive number periods. The x_axis_time_period_timedelta should 
                be positive."""
            )

        load_profile_entry_post_processor = LoadProfileEntryPostProcessor()
        list_of_load_profile_entries = (
            load_profile_entry_post_processor.homogenize_list_of_load_profiles_entries(
                list_of_load_profile_entries=list_of_load_profile_entries,
                start_date_time_series=start_date_time_series,
                end_date_time_series=end_date_time_series,
                resample_frequency=resample_frequency,
            )
        )
        list_of_load_profile_entry_analyzer = ListOfLoadProfileEntryAnalyzer()
        list_of_load_profile_meta_data = (
            list_of_load_profile_entry_analyzer.create_list_of_load_profile_meta_data(
                list_of_load_profiles=list_of_load_profile_entries,
                object_name=object_name,
            )
        )
        carpet_plot_matrix: CarpetPlotMatrix | CarpetPlotMatrixEmpty
        if type(list_of_load_profile_meta_data) is ListOfLoadProfileMetaData:
            resampled_load_profile_data_frame = (
                self.convert_list_of_load_profile_entries_to_data_frame(
                    list_of_load_profile_entries=list_of_load_profile_entries
                )
            )
            load_profile_matrix = (
                self.convert_time_series_to_power_matrix_with_period_columns(
                    input_data_frame=resampled_load_profile_data_frame,
                    x_axis_period_time_delta=x_axis_time_period_timedelta,
                )
            )
            carpet_plot_matrix = CarpetPlotMatrix(
                data_frame=load_profile_matrix,
                start_date_time_series=start_date_time_series,
                end_date_time_series=end_date_time_series,
                x_axis_time_period_timedelta=x_axis_time_period_timedelta,
                resample_frequency=resample_frequency,
                power_unit=list_of_load_profile_meta_data.power_unit,
                energy_unit=list_of_load_profile_meta_data.energy_unit,
                total_energy_demand=list_of_load_profile_meta_data.total_energy,
                object_name=object_name,
            )
        elif type(list_of_load_profile_meta_data) is ListLoadProfileMetaDataEmpty:
            carpet_plot_matrix = CarpetPlotMatrixEmpty(object_name=object_name)

        return carpet_plot_matrix

    def convert_list_of_load_profile_entries_to_data_frame(
        self, list_of_load_profile_entries: list[LoadProfileEntry]
    ) -> pandas.DataFrame:
        output_data_frame = pandas.DataFrame(data=list_of_load_profile_entries)
        output_data_frame.index = output_data_frame.loc[:, "start_time"]
        return output_data_frame

    def convert_lpg_load_profile_to_carpet_plot(
        self,
        list_of_load_profile_entries: list[LoadProfileEntry],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        object_name: str,
        x_axis_time_period_timedelta: datetime.timedelta = datetime.timedelta(weeks=1),
        resample_frequency: str = "1min",
    ):
        carpet_plot_load_profile_matrix = (
            self.convert_lpg_load_profile_to_data_frame_matrix(
                list_of_load_profile_entries=list_of_load_profile_entries,
                start_date_time_series=start_date,
                end_date_time_series=end_date,
                x_axis_time_period_timedelta=x_axis_time_period_timedelta,
                resample_frequency=resample_frequency,
            )
        )
        fig = self.plot_load_profile_carpet_from_data_frame_matrix(
            carpet_plot_load_profile_matrix=carpet_plot_load_profile_matrix,
            load_type_name=self.load_type.name,
        )
        return fig

    def invert_list(self, list_to_invert: list):
        return list_to_invert[::-1]

    def convert_time_series_to_power_matrix_with_period_columns(
        self,
        input_data_frame: pandas.DataFrame,
        x_axis_period_time_delta: datetime.timedelta,
    ):
        """Converts a data frame of load profile entries which are based
        on the LoadProfile dataclass into a matrix representation of the
        same load profile list. The output data frame

        Args:
            input_data_frame (pandas.DataFrame): _description_
            periodic_time_delta (datetime.timedelta): _description_
            x_row_date_format (str, optional): _description_. Defaults to "%M".
            period_name (str, optional): _description_. Defaults to "Hour".

        Raises:
            Exception: _description_
            Exception: _description_

        Returns:
            _type_: _description_
        """

        # Check if separation into time periods is possible
        input_data_frame["start_time"] = pandas.to_datetime(
            input_data_frame["start_time"]
        )
        input_data_frame["end_time"] = pandas.to_datetime(input_data_frame["end_time"])
        start_time = input_data_frame["start_time"].min()
        end_time = input_data_frame["end_time"].max()
        number_of_periods = (end_time - start_time) / x_axis_period_time_delta
        if number_of_periods <= 0:
            raise Exception(
                "No positive number periods. Start time: "
                + str(start_time)
                + " End time: "
                + str(end_time)
            )
        if not number_of_periods.is_integer():
            raise Exception(
                "Start date, end date, and periodic time delta dont fit to an integer number of periods"
                + " start date is: "
                + str(start_time)
                + " end time: "
                + str(end_time)
                + " periodic time delta: "
                + str(x_axis_period_time_delta)
            )

        duration_of_a_single_load_profile_entry = (
            input_data_frame["end_time"].iloc[0]
            - input_data_frame["start_time"].iloc[0]
        )
        start_time_of_period = start_time
        end_time_of_period = (
            start_time_of_period
            + x_axis_period_time_delta
            - duration_of_a_single_load_profile_entry
        )
        # Determine Index of new data_frame
        energy_quantity_data_frame = input_data_frame["average_power_consumption"]
        first_row_index = energy_quantity_data_frame[
            start_time_of_period:end_time_of_period
        ].index

        new_index_list = []

        for old_index in first_row_index:
            old_index: datetime.datetime
            new_index = old_index.to_pydatetime()
            new_index_list.append(new_index)

        # Split dataframe into
        list_of_pandas_series = []
        for current_period in range(int(number_of_periods)):
            new_row = energy_quantity_data_frame[
                start_time_of_period:end_time_of_period
            ]
            new_row.index = new_index_list

            row_name = end_time_of_period
            new_row = new_row.rename(row_name)
            list_of_pandas_series.append(new_row)
            start_time_of_period = (
                end_time_of_period + duration_of_a_single_load_profile_entry
            )
            end_time_of_period = (
                start_time_of_period
                + x_axis_period_time_delta
                - duration_of_a_single_load_profile_entry
            )
        output_data_frame = pandas.concat(list_of_pandas_series, axis=1)

        return output_data_frame

    def convert_time_series_to_energy_matrix_with_period_columns(
        self,
        input_data_frame: pandas.DataFrame,
        periodic_time_delta: datetime.datetime,
        x_row_date_format: str = "%M",
        period_name="Hour",
    ):
        # Check if separation into time periods is possible
        input_data_frame["start_time"] = pandas.to_datetime(
            input_data_frame["start_time"]
        )
        input_data_frame["end_time"] = pandas.to_datetime(input_data_frame["end_time"])
        start_time = input_data_frame["start_time"].min()
        end_time = input_data_frame["end_time"].max()
        number_of_periods = (end_time - start_time) / periodic_time_delta
        if number_of_periods <= 0:
            raise Exception(
                "No positive number periods. Start time: "
                + str(start_time)
                + " End time: "
                + str(end_time)
            )
        if not number_of_periods.is_integer():
            raise Exception(
                "Start date, end date, and periodic time delta dont fit to an integer number of periods"
                + " start date is: "
                + str(start_time)
                + " end time: "
                + str(end_time)
                + " periodic time delta: "
                + str(periodic_time_delta)
            )

        timedelta_of_x_axis_period = (
            input_data_frame["end_time"].iloc[0]
            - input_data_frame["start_time"].iloc[0]
        )
        start_time_of_period = start_time + timedelta_of_x_axis_period
        end_time_of_period = (
            start_time_of_period + periodic_time_delta - timedelta_of_x_axis_period
        )
        # Determine Index of new dataframe
        energy_quantity_data_frame = input_data_frame["energy_quantity"]
        first_row_index = energy_quantity_data_frame[
            start_time_of_period:end_time_of_period
        ].index

        new_index_list = []

        for old_index in first_row_index:
            old_index: datetime.datetime
            new_index = old_index.to_pydatetime()
            new_index_list.append(new_index)

        # Split data_frame into
        list_of_pandas_series = []
        for current_period in range(int(number_of_periods)):
            new_row = energy_quantity_data_frame[
                start_time_of_period:end_time_of_period
            ]
            new_row.index = new_index_list

            row_name = end_time_of_period
            new_row = new_row.rename(row_name)
            list_of_pandas_series.append(new_row)
            start_time_of_period = end_time_of_period + timedelta_of_x_axis_period
            end_time_of_period = (
                start_time_of_period + periodic_time_delta - timedelta_of_x_axis_period
            )
        output_data_frame = pandas.concat(list_of_pandas_series, axis=1)

        return output_data_frame

    def get_energy_amount_from_data_frame(
        self, load_profile_data_frame: pandas.DataFrame
    ) -> float:
        energy_amount = load_profile_data_frame["energy_quantity"].sum()
        return energy_amount

    def get_energy_amount_from_energy_plotting_matrix(
        self, load_profile_data_frame: pandas.DataFrame
    ) -> float:
        load_profile_series = load_profile_data_frame.sum(axis=0)
        total_energy = load_profile_series.sum(axis=0)
        return total_energy

    def get_energy_amount_from_power_matrix(
        self,
        load_profile_data_frame: pandas.DataFrame,
        period_length: datetime.timedelta,
    ) -> float:
        period_length_seconds = period_length.total_seconds()
        load_profile_matrix = load_profile_data_frame.to_numpy()
        energy_matrix = load_profile_matrix * period_length_seconds
        total_energy = numpy.sum(energy_matrix)

        return total_energy

    def plot_load_profile_carpet_from_data_frame_matrix(
        self,
        carpet_plot_load_profile_matrix: CarpetPlotMatrix,
        load_type_name: str,
    ) -> matplotlib.figure.Figure:
        figure, axes = matplotlib.pyplot.subplots(1, 1)
        axes.minorticks_off()

        x_axis_whole_period = (
            carpet_plot_load_profile_matrix.x_axis_time_period_timedelta
        )
        # The abbrevations for strftime string can be found here:
        # https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
        if x_axis_whole_period <= datetime.timedelta(hours=1):
            # Shows hours on the x axis
            x_axis_time_format = "%m.%d:%H"  # Displays month.day:hour
            y_axis_time_format = "%M:%S"  # Displays minute:seconds
            y_axis_label_string = "Minutes of the hour"
            x_axis_label_string = "Hours in day:hour"
        elif x_axis_whole_period <= datetime.timedelta(
            days=1
        ) and x_axis_whole_period > datetime.timedelta(hours=1):
            # Shows days on the x axis
            x_axis_time_format = "%m.%d"  # Displays month.day
            y_axis_time_format = "%H:%M"  # Displays hour:minute
            y_axis_label_string = "Hours of the day"
            x_axis_label_string = "Date M.D"

        elif x_axis_whole_period <= datetime.timedelta(
            weeks=1
        ) and x_axis_whole_period > datetime.timedelta(days=1):
            # Shows week numbers on the x axis
            x_axis_time_format = "%V"  # Displays week numbers
            y_axis_time_format = "%a:%H"  # Shows weekday as string:hour
            y_axis_label_string = "Days of the week"
            x_axis_label_string = "Weeks"
        else:
            pass
        converted_index = []
        load_profile_matrix_data_frame = carpet_plot_load_profile_matrix.data_frame
        start_date = carpet_plot_load_profile_matrix.start_date_time_series
        end_date = carpet_plot_load_profile_matrix.end_date_time_series

        resample_frequency = carpet_plot_load_profile_matrix.resample_frequency
        for index_entry in load_profile_matrix_data_frame.index:
            if isinstance(index_entry, datetime.datetime):
                a = index_entry.to_pydatetime()
                py_date_time_entry = index_entry.to_pydatetime(a)
                converted_index.append(
                    str(py_date_time_entry.strftime(y_axis_time_format))
                )
            else:
                converted_index.append(index_entry)

        load_profile_matrix_data_frame.index = converted_index
        converted_row_index = []
        for row_entry in load_profile_matrix_data_frame.columns:
            if isinstance(row_entry, datetime.datetime):
                a = index_entry.to_pydatetime()
                py_date_time_entry = row_entry.to_pydatetime(a)
                converted_row_index.append(
                    py_date_time_entry.strftime(x_axis_time_format)
                )
            else:
                converted_row_index.append(index_entry)

        load_profile_matrix_data_frame.columns = converted_row_index

        color_bar_label = (
            "Average Power in " + carpet_plot_load_profile_matrix.power_unit
        )
        searborn_plot = seaborn.heatmap(
            load_profile_matrix_data_frame,
            cmap="coolwarm",
            ax=axes,
            center=0,
            cbar_kws={"label": color_bar_label},
            xticklabels="auto",
        )
        # timedelta_frequency = pandas.to_timedelta(resample_frequency)

        # x_axis_time_format = "%Y.%d.%m"
        # list_index = 0
        # y_axis_ticks = []
        # for i in range(int(increment_index)):
        #     list_index = list_index + increment_index
        #     y_axis_ticks.append(list_index)

        # axes.yaxis.set_major_locator(lin_loactor)

        # axes.set_yticks = y_axis_ticks
        # y_label_list = []
        # for y_tick_position in axes.get_yticks():
        #     table_index = y_tick_position - 0.5
        #     y_label_list.append(
        #         converted_index[int(table_index)].strftime(y_axis_time_format)
        #     )

        # @matplotlib.ticker.FuncFormatter
        # def simple_label_formatter(y_coordinate, y_tick_label_counter):
        #     return y_label_list[y_tick_label_counter]

        # axes.yaxis.set_major_formatter(simple_label_formatter)

        # start_date_matrix = load_profile_matrix_data_frame.columns[0]
        # end_date_matrix = load_profile_matrix_data_frame.columns[-1]

        # index = pandas.date_range(
        #     start=start_date_matrix,
        #     end=end_date_matrix,
        #     freq="1d",
        # )
        # start_index = index.get_indexer([start_date], method="nearest")[0]
        # end_index = index.get_indexer([end_date], method="nearest")[0]
        # if len(index) > 1:
        #     axes.set_xlim(xmin=start_index, xmax=end_index)

        # list_of_x_tick_labels = []
        # maximum_number_of_x_ticks = 10
        # current_number_of_ticks = end_index - start_index
        # if current_number_of_ticks < maximum_number_of_x_ticks:
        #     number_of_x_ticks = current_number_of_ticks
        # else:
        #     number_of_x_ticks = maximum_number_of_x_ticks
        # unrounded_ticks_list = numpy.linspace(
        #     start=start_index, stop=end_index, num=number_of_x_ticks
        # )
        # rounded_ticks_list = numpy.floor(unrounded_ticks_list) + 0.5

        # for x_tick in rounded_ticks_list:
        #     list_of_x_tick_labels.append(
        #         load_profile_matrix_data_frame.columns[int(x_tick)].strftime(
        #             x_axis_time_format
        #         )
        #     )
        # index_x_axis = index_x_axis + increment_x_axis

        # axes.set_xticks(ticks=rounded_ticks_list)
        # axes.set_xticklabels(list_of_x_tick_labels, rotation=45, ha="right")

        matplotlib.pyplot.yticks(rotation=0)
        matplotlib.pyplot.xticks(rotation=45, ha="right")
        matplotlib.pyplot.xlabel(x_axis_label_string)
        matplotlib.pyplot.ylabel(y_axis_label_string)

        # # Set title
        total_energy_demand = self.get_energy_amount_from_energy_plotting_matrix(
            load_profile_data_frame=load_profile_matrix_data_frame,
        )
        total_energy_quantity = Units.compress_quantity(
            unit=Units.energy_unit, quantity_value=total_energy_demand
        )

        matplotlib.pyplot.title(
            label=str(round(total_energy_quantity.m, 2))
            + " "
            + create_subscript_string_matplotlib(
                base=str(total_energy_quantity.u),
                subscripted_text=str(load_type_name),
            )
        )

        return figure

    def combine_matrix_data_frames(
        self, list_of_carpet_plot_matrices: list[CarpetPlotMatrix]
    ) -> CarpetPlotMatrix:
        carpet_plot_matrix = list_of_carpet_plot_matrices[0]
        current_df = carpet_plot_matrix.data_frame
        iterator = 1
        start_date_time_series = carpet_plot_matrix.start_date_time_series
        end_date_time_series = carpet_plot_matrix.end_date_time_series
        x_axis_time_period_timedelta = carpet_plot_matrix.x_axis_time_period_timedelta
        resample_frequency = carpet_plot_matrix.resample_frequency
        if len(list_of_carpet_plot_matrices) == 1:
            pass
        else:
            for current_list_row in range(len(list_of_carpet_plot_matrices) - 1):
                current_carpet_plot_matrix = list_of_carpet_plot_matrices[iterator]
                current_df = current_df.add(current_carpet_plot_matrix.data_frame)
                iterator = iterator + 1
        carpet_plot_matrix = CarpetPlotMatrix(
            data_frame=current_df,
            start_date_time_series=start_date_time_series,
            end_date_time_series=end_date_time_series,
            x_axis_time_period_timedelta=x_axis_time_period_timedelta,
            resample_frequency=resample_frequency,
        )

        return carpet_plot_matrix
