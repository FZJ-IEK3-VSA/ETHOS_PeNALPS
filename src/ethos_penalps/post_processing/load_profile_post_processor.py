import datetime
import math


import matplotlib.dates
import matplotlib.figure
import matplotlib.pyplot
import matplotlib.ticker
import numpy
import pandas
import seaborn

from dataclasses import dataclass
from ethos_penalps.data_classes import (
    LoadProfileDataFrameMetaInformation,
    LoadProfileEntry,
    LoadType,
)
from ethos_penalps.utilities.units import Units
from ethos_penalps.post_processing.load_profile_entry_post_processor import (
    LoadProfileEntryPostProcessor,
)

from ethos_penalps.utilities.units import Units
from ethos_penalps.utilities.general_functions import (
    check_if_date_1_is_before_date_2,
    check_if_date_1_is_before_or_at_date_2,
    create_subscript_string_matplotlib,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

itcs_logger = PeNALPSLogger.get_logger_without_handler()


@dataclass
class CarpetPlotMatrix:
    data_frame: pandas.DataFrame
    start_date_time_series: datetime.datetime
    end_date_time_series: datetime.datetime
    x_axis_time_period_timedelta: datetime.timedelta
    resample_frequency: str = "1min"


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
        x_axis_time_period_timedelta: datetime.timedelta = datetime.timedelta(weeks=1),
        resample_frequency: str = "1min",
    ) -> CarpetPlotMatrix:
        if not list_of_load_profile_entries:
            print("Plot empty load profile")
        number_of_periods = (
            end_date_time_series - start_date_time_series
        ) / x_axis_time_period_timedelta
        if number_of_periods <= 0:
            raise Exception(
                "No positive number periods. Start time: "
                + str(start_date_time_series)
                + " End time: "
                + str(end_date_time_series)
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

        resampled_load_profile_data_frame = (
            self.convert_list_of_load_profile_entries_to_data_frame(
                list_of_load_profile_entries=list_of_load_profile_entries
            )
        )
        load_profile_matrix = (
            self.convert_time_series_to_power_matrix_with_period_columns(
                input_data_frame=resampled_load_profile_data_frame,
                periodic_time_delta=x_axis_time_period_timedelta,
            )
        )
        carpet_plot_matrix = CarpetPlotMatrix(
            data_frame=load_profile_matrix,
            start_date_time_series=start_date_time_series,
            end_date_time_series=end_date_time_series,
            x_axis_time_period_timedelta=x_axis_time_period_timedelta,
            resample_frequency=resample_frequency,
        )

        return carpet_plot_matrix

    def convert_list_of_load_profile_entries_to_data_frame(
        self, list_of_load_profile_entries: list[LoadProfileEntry]
    ) -> pandas.DataFrame:
        output_data_frame = pandas.DataFrame(data=list_of_load_profile_entries)
        output_data_frame.index = output_data_frame.loc[:, "end_time"]
        return output_data_frame

    def convert_lpg_load_profile_to_carpet_plot(
        self,
        list_of_load_profile_entries: list[LoadProfileEntry],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
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
        periodic_time_delta: datetime.timedelta,
        x_row_date_format: str = "%M",
        period_name="Hour",
    ):
        """_summary_

        :param input_data_frame: _description_
        :type input_data_frame: pandas.DataFrame
        :param periodic_time_delta: _description_
        :type periodic_time_delta: datetime.timedelta
        :param x_row_date_format: _description_, defaults to "%M"
        :type x_row_date_format: str, optional
        :param period_name: _description_, defaults to "Hour"
        :type period_name: str, optional
        :raises Exception: _description_
        :raises Exception: _description_
        :return: _description_
        :rtype: _type_
        """
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
            start_time_of_period = end_time_of_period + timedelta_of_x_axis_period
            end_time_of_period = (
                start_time_of_period + periodic_time_delta - timedelta_of_x_axis_period
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
        converted_index = []
        load_profile_matrix = carpet_plot_load_profile_matrix.data_frame
        start_date = carpet_plot_load_profile_matrix.start_date_time_series
        end_date = carpet_plot_load_profile_matrix.end_date_time_series
        x_axis_whole_period = (
            carpet_plot_load_profile_matrix.x_axis_time_period_timedelta
        )
        resample_frequency = carpet_plot_load_profile_matrix.resample_frequency
        for index_entry in load_profile_matrix.index:
            if isinstance(index_entry, datetime.datetime):
                a = index_entry.to_pydatetime()
                # print(a, type(a))
                py_date_time_entry = index_entry.to_pydatetime(a)
                # cut_py_date_time_entry = py_date_time_entry.time()
                # converted_index.append(py_date_time_entry.strftime(y_axis_time_format))
                converted_index.append(py_date_time_entry)
            else:
                converted_index.append(index_entry)
        load_profile_matrix.index = converted_index

        load_profile_matrix_numpy = load_profile_matrix.to_numpy()

        searborn_plot = seaborn.heatmap(
            load_profile_matrix_numpy,
            cmap="coolwarm",
            ax=axes,
            # vmin=0,
            center=0,
            # yticklabels=converted_index,
            # yticklabels=False,
            cbar_kws={"label": "Average Power in MW"},
        )
        timedelta_frequency = pandas.to_timedelta(resample_frequency)
        total_energy_demand = self.get_energy_amount_from_energy_plotting_matrix(
            load_profile_data_frame=load_profile_matrix,
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

        number_of_y_rows = len(converted_index)
        if x_axis_whole_period <= datetime.timedelta(hours=1):
            # Time delta 1 hour
            y_axis_time_format = "%M:%S"
            y_axis_label_string = "Minutes of the hour"
            x_axis_label_string = "Hours"
            increment_index = number_of_y_rows / 12
            lin_loactor = matplotlib.ticker.LinearLocator(13)
        elif x_axis_whole_period <= datetime.timedelta(
            days=1
        ) and x_axis_whole_period > datetime.timedelta(hours=1):
            # Timedelta is 1 hour
            y_axis_time_format = "%H:%M"
            y_axis_label_string = "Hours of the day"
            x_axis_label_string = "Days"

            increment_index = number_of_y_rows / 24
            lin_loactor = matplotlib.ticker.LinearLocator(25)
        elif x_axis_whole_period <= datetime.timedelta(
            weeks=1
        ) and x_axis_whole_period > datetime.timedelta(days=1):
            # Time delta 1 week
            y_axis_time_format = "%a-%H:%M"
            y_axis_label_string = "Days of the week"
            x_axis_label_string = "Weeks"
            increment_index = number_of_y_rows / 21
            lin_loactor = matplotlib.ticker.LinearLocator(
                22,
            )
        x_axis_time_format = "%Y.%d.%m"
        list_index = 0
        y_axis_ticks = []
        for i in range(int(increment_index)):
            list_index = list_index + increment_index
            y_axis_ticks.append(list_index)

        axes.yaxis.set_major_locator(lin_loactor)

        axes.set_yticks = y_axis_ticks
        y_label_list = []
        for y_tick_position in axes.get_yticks():
            table_index = y_tick_position - 0.5
            y_label_list.append(
                converted_index[int(table_index)].strftime(y_axis_time_format)
            )

        @matplotlib.ticker.FuncFormatter
        def simple_label_formatter(y_coordinate, y_tick_label_counter):
            return y_label_list[y_tick_label_counter]

        axes.yaxis.set_major_formatter(simple_label_formatter)

        start_date_matrix = load_profile_matrix.columns[0]
        end_date_matrix = load_profile_matrix.columns[-1]

        index = pandas.date_range(
            start=start_date_matrix,
            end=end_date_matrix,
            freq="1d",
        )
        start_index = index.get_indexer([start_date], method="nearest")[0]
        end_index = index.get_indexer([end_date], method="nearest")[0]
        # if len(index) > 1:
        #     axes.set_xlim(xmin=start_index, xmax=end_index)

        list_of_x_tick_labels = []
        maximum_number_of_x_ticks = 10
        current_number_of_ticks = end_index - start_index
        if current_number_of_ticks < maximum_number_of_x_ticks:
            number_of_x_ticks = current_number_of_ticks
        else:
            number_of_x_ticks = maximum_number_of_x_ticks
        unrounded_ticks_list = numpy.linspace(
            start=start_index, stop=end_index, num=number_of_x_ticks
        )
        rounded_ticks_list = numpy.floor(unrounded_ticks_list) + 0.5

        for x_tick in rounded_ticks_list:
            list_of_x_tick_labels.append(
                load_profile_matrix.columns[int(x_tick)].strftime(x_axis_time_format)
            )
            # index_x_axis = index_x_axis + increment_x_axis

        axes.set_xticks(ticks=rounded_ticks_list)
        axes.set_xticklabels(list_of_x_tick_labels, rotation=45, ha="right")

        matplotlib.pyplot.yticks(rotation=0)
        matplotlib.pyplot.xlabel(x_axis_label_string)
        matplotlib.pyplot.ylabel(y_axis_label_string)

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
