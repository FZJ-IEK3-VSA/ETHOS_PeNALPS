import datetime

import matplotlib.dates
import matplotlib.figure
import matplotlib.pyplot
import matplotlib.ticker
import numpy
import pandas
import seaborn
import warnings
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
from ethos_penalps.utilities.exceptions_and_warnings import (
    MisconfigurationError,
    LoadProfileInconsistencyWarning,
)
from ethos_penalps.utilities.general_functions import (
    check_if_date_1_is_before_date_2,
    check_if_date_1_is_before_or_at_date_2,
    create_subscript_string_matplotlib,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.units import Units

logger = PeNALPSLogger.get_logger_without_handler()


class CarpetPlotLoadProfileGenerator(LoadProfileEntryPostProcessor):
    """This class is used to create carpet plots from a
    list of load profile entries.
    """

    def __init__(self) -> None:
        pass

    def convert_lpg_load_profile_to_carpet_plot(
        self,
        list_of_load_profile_entries: list[LoadProfileEntry],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        object_name: str,
        x_axis_time_period_timedelta: datetime.timedelta = datetime.timedelta(weeks=1),
        resample_frequency: str = "1min",
    ) -> matplotlib.figure.Figure | None:
        carpet_plot_load_profile_matrix = (
            self.convert_lpg_load_profile_to_data_frame_matrix(
                list_of_load_profile_entries=list_of_load_profile_entries,
                start_date_time_series=start_date,
                end_date_time_series=end_date,
                x_axis_time_period_timedelta=x_axis_time_period_timedelta,
                resample_frequency=resample_frequency,
                object_name=object_name,
            )
        )
        if type(carpet_plot_load_profile_matrix) is CarpetPlotMatrixEmpty:
            logger.debug("No load profile to plot for object: %s", object_name)
            figure = None
        elif type(carpet_plot_load_profile_matrix) is CarpetPlotMatrix:
            figure = self.plot_load_profile_carpet_from_data_frame_matrix(
                carpet_plot_load_profile_matrix=carpet_plot_load_profile_matrix,
            )
        else:
            raise Exception("Unexpected datatype")
        return figure

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
        if list_of_load_profile_entries:

            # Check if the start date, end date and x axis time delta are well defined.
            total_time_period = end_date_time_series - start_date_time_series
            if total_time_period <= datetime.timedelta(hours=0):
                raise MisconfigurationError(
                    """A negative time period has been defined for the processing of the load profile.
                                    The start date: """
                    + str(start_date_time_series)
                    + """should be earlier than the end date: """
                    + str(end_date_time_series)
                )
            number_of_periods = (total_time_period) / x_axis_time_period_timedelta
            if number_of_periods <= 0:
                raise MisconfigurationError(
                    """No positive number periods. The x_axis_time_period_timedelta should
                    be positive."""
                )

            list_of_load_profile_meta_data = (
                self.homogenize_list_of_load_profiles_entries(
                    list_of_load_profile_entries=list_of_load_profile_entries,
                    start_date_time_series=start_date_time_series,
                    end_date_time_series=end_date_time_series,
                    resample_frequency=resample_frequency,
                    object_name=object_name,
                )
            )

            carpet_plot_matrix: CarpetPlotMatrix | CarpetPlotMatrixEmpty
            if type(list_of_load_profile_meta_data) is ListOfLoadProfileMetaData:

                carpet_plot_matrix = (
                    self.convert_load_profile_meta_data_to_carpet_plot_matrix(
                        list_of_load_profile_meta_data=list_of_load_profile_meta_data,
                        x_axis_period_time_delta=x_axis_time_period_timedelta,
                        start_date_time_series=start_date_time_series,
                        end_date_time_series=end_date_time_series,
                        resample_frequency=resample_frequency,
                        object_name=object_name,
                    )
                )

            elif type(list_of_load_profile_meta_data) is ListLoadProfileMetaDataEmpty:
                logger.debug(
                    "The homogenization yielded an empty load profile data frame"
                )
                carpet_plot_matrix = CarpetPlotMatrixEmpty(object_name=object_name)
        else:
            logger.debug(
                "An empty list of load profiles has been passed to te load profile processor"
            )
            carpet_plot_matrix = CarpetPlotMatrixEmpty(object_name=object_name)

        return carpet_plot_matrix

    def invert_list(self, list_to_invert: list):
        return list_to_invert[::-1]

    def convert_load_profile_meta_data_to_carpet_plot_matrix(
        self,
        list_of_load_profile_meta_data: ListOfLoadProfileMetaData,
        x_axis_period_time_delta: datetime.timedelta,
        start_date_time_series: datetime.datetime,
        end_date_time_series: datetime.datetime,
        resample_frequency: str,
        object_name: str,
    ) -> CarpetPlotMatrix:
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
        input_data_frame = pandas.DataFrame(
            data=list_of_load_profile_meta_data.list_of_load_profiles
        )
        input_data_frame.index = input_data_frame.loc[:, "start_time"]

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
        carpet_plot_matrix = CarpetPlotMatrix(
            data_frame=output_data_frame,
            start_date_time_series=start_date_time_series,
            end_date_time_series=end_date_time_series,
            x_axis_time_period_timedelta=x_axis_period_time_delta,
            resample_frequency=resample_frequency,
            power_unit=list_of_load_profile_meta_data.power_unit,
            energy_unit=list_of_load_profile_meta_data.energy_unit,
            total_energy_demand=list_of_load_profile_meta_data.total_energy,
            object_name=object_name,
            load_type=list_of_load_profile_meta_data.load_type,
        )

        return carpet_plot_matrix

    # def convert_time_series_to_energy_matrix_with_period_columns(
    #     self,
    #     input_data_frame: pandas.DataFrame,
    #     periodic_time_delta: datetime.datetime,
    #     x_row_date_format: str = "%M",
    #     period_name="Hour",
    # ):
    #     # Check if separation into time periods is possible
    #     input_data_frame["start_time"] = pandas.to_datetime(
    #         input_data_frame["start_time"]
    #     )
    #     input_data_frame["end_time"] = pandas.to_datetime(input_data_frame["end_time"])
    #     start_time = input_data_frame["start_time"].min()
    #     end_time = input_data_frame["end_time"].max()
    #     number_of_periods = (end_time - start_time) / periodic_time_delta
    #     if number_of_periods <= 0:
    #         raise Exception(
    #             "No positive number periods. Start time: "
    #             + str(start_time)
    #             + " End time: "
    #             + str(end_time)
    #         )
    #     if not number_of_periods.is_integer():
    #         raise Exception(
    #             "Start date, end date, and periodic time delta dont fit to an integer number of periods"
    #             + " start date is: "
    #             + str(start_time)
    #             + " end time: "
    #             + str(end_time)
    #             + " periodic time delta: "
    #             + str(periodic_time_delta)
    #         )

    #     timedelta_of_x_axis_period = (
    #         input_data_frame["end_time"].iloc[0]
    #         - input_data_frame["start_time"].iloc[0]
    #     )
    #     start_time_of_period = start_time + timedelta_of_x_axis_period
    #     end_time_of_period = (
    #         start_time_of_period + periodic_time_delta - timedelta_of_x_axis_period
    #     )
    #     # Determine Index of new dataframe
    #     energy_quantity_data_frame = input_data_frame["energy_quantity"]
    #     first_row_index = energy_quantity_data_frame[
    #         start_time_of_period:end_time_of_period
    #     ].index

    #     new_index_list = []

    #     for old_index in first_row_index:
    #         old_index: datetime.datetime
    #         new_index = old_index.to_pydatetime()
    #         new_index_list.append(new_index)

    #     # Split data_frame into
    #     list_of_pandas_series = []
    #     for current_period in range(int(number_of_periods)):
    #         new_row = energy_quantity_data_frame[
    #             start_time_of_period:end_time_of_period
    #         ]
    #         new_row.index = new_index_list

    #         row_name = end_time_of_period
    #         new_row = new_row.rename(row_name)
    #         list_of_pandas_series.append(new_row)
    #         start_time_of_period = end_time_of_period + timedelta_of_x_axis_period
    #         end_time_of_period = (
    #             start_time_of_period + periodic_time_delta - timedelta_of_x_axis_period
    #         )
    #     output_data_frame = pandas.concat(list_of_pandas_series, axis=1)

    #     return output_data_frame

    def get_energy_amount_from_data_frame(
        self, load_profile_data_frame: pandas.DataFrame
    ) -> float:
        energy_amount = load_profile_data_frame["energy_quantity"].sum()
        return energy_amount

    def get_energy_amount_from_power_matrix(
        self,
        carpet_plot_matrix: CarpetPlotMatrix,
    ) -> float:
        carpet_plot_matrix_data_frame = carpet_plot_matrix.data_frame
        period_length = pandas.to_timedelta(carpet_plot_matrix.resample_frequency)
        period_length_seconds = period_length.total_seconds()
        carpet_plot_matrix_numpy = carpet_plot_matrix_data_frame.to_numpy()
        energy_matrix = carpet_plot_matrix_numpy * period_length_seconds
        total_energy = numpy.sum(energy_matrix)

        return total_energy

    def combine_matrix_data_frames(
        self,
        list_of_carpet_plot_matrices: list[CarpetPlotMatrix],
        combined_matrix_name: str,
    ) -> CarpetPlotMatrix:
        carpet_plot_matrix = list_of_carpet_plot_matrices[0]
        current_df = carpet_plot_matrix.data_frame
        iterator = 1
        start_date_time_series = carpet_plot_matrix.start_date_time_series
        end_date_time_series = carpet_plot_matrix.end_date_time_series
        x_axis_time_period_timedelta = carpet_plot_matrix.x_axis_time_period_timedelta
        resample_frequency = carpet_plot_matrix.resample_frequency
        list_of_power_units = []
        list_of_energy_units = []
        list_of_total_energy_demand = []
        list_of_load_types = []
        if len(list_of_carpet_plot_matrices) == 1:
            current_carpet_plot_matrix = list_of_carpet_plot_matrices[0]
            list_of_power_units.append(current_carpet_plot_matrix.power_unit)
            list_of_energy_units.append(current_carpet_plot_matrix.energy_unit)
            list_of_total_energy_demand.append(
                current_carpet_plot_matrix.total_energy_demand
            )
            list_of_load_types.append(current_carpet_plot_matrix.load_type)
        else:
            for current_list_row in range(len(list_of_carpet_plot_matrices) - 1):
                current_carpet_plot_matrix = list_of_carpet_plot_matrices[iterator]
                list_of_power_units.append(current_carpet_plot_matrix.power_unit)
                list_of_energy_units.append(current_carpet_plot_matrix.energy_unit)
                list_of_total_energy_demand.append(
                    current_carpet_plot_matrix.total_energy_demand
                )
                current_df = current_df.add(current_carpet_plot_matrix.data_frame)
                list_of_load_types.append(current_carpet_plot_matrix.load_type)
                iterator = iterator + 1
        unique_power_unit_list = list(set(list_of_power_units))
        if len(unique_power_unit_list) > 1:
            warnings.warn(
                message="Tried to combine multiple power units.",
                category=LoadProfileInconsistencyWarning,
            )
        combined_power_unit = unique_power_unit_list[0]
        unique_energy_unit_list = list(set(list_of_energy_units))
        if len(unique_energy_unit_list) > 1:
            warnings.warn(
                message="Tried to combine multiple energy units.",
                category=LoadProfileInconsistencyWarning,
            )
        unique_list_of_load_types = list(set(list_of_load_types))
        combined_energy_unit = unique_energy_unit_list[0]
        total_energy_demand = sum(list_of_total_energy_demand)
        carpet_plot_matrix = CarpetPlotMatrix(
            data_frame=current_df,
            start_date_time_series=start_date_time_series,
            end_date_time_series=end_date_time_series,
            x_axis_time_period_timedelta=x_axis_time_period_timedelta,
            resample_frequency=resample_frequency,
            object_name=combined_matrix_name,
            power_unit=combined_power_unit,
            total_energy_demand=total_energy_demand,
            energy_unit=combined_energy_unit,
            load_type=unique_list_of_load_types[0],
        )
        return carpet_plot_matrix

    def plot_load_profile_carpet_from_data_frame_matrix(
        self,
        carpet_plot_load_profile_matrix: CarpetPlotMatrix,
    ) -> matplotlib.figure.Figure:
        """Create load profile carpet plot from CarpetPlotMatrix object

        Args:
            carpet_plot_load_profile_matrix (CarpetPlotMatrix): _description_

        Returns:
            matplotlib.figure.Figure: _description_
        """

        # Create figure
        figure, axes = matplotlib.pyplot.subplots(1, 1)
        axes.minorticks_off()

        x_axis_whole_period = (
            carpet_plot_load_profile_matrix.x_axis_time_period_timedelta
        )

        # Determine format of x and y ticks,and x and y axis label
        # The abbreviations for strftime string can be found here:
        # https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
        if x_axis_whole_period <= datetime.timedelta(hours=1):
            # Shows hours on the x axis
            x_axis_time_format = "%m.%d:%H"  # Displays month.day:hour
            y_axis_time_format = "%M:%S"  # Displays minute:seconds
            y_axis_label_string = "Time in minute:second"
            x_axis_label_string = "Time in month.day:hour"
        elif x_axis_whole_period <= datetime.timedelta(
            days=1
        ) and x_axis_whole_period > datetime.timedelta(hours=1):
            # Shows days on the x axis
            x_axis_time_format = "%m.%d"  # Displays month.day
            y_axis_time_format = "%H:%M"  # Displays hour:minute
            y_axis_label_string = "Time in Hour:Minute"
            x_axis_label_string = "Time in Month.Day"

        elif x_axis_whole_period <= datetime.timedelta(
            weeks=1
        ) and x_axis_whole_period > datetime.timedelta(days=1):
            # Shows week numbers on the x axis
            x_axis_time_format = "%V"  # Displays week numbers
            y_axis_time_format = "%a:%H"  # Shows weekday as string:hour
            y_axis_label_string = "Time in Weekday"
            x_axis_label_string = "Time in calendar week"
        else:
            pass
        converted_index = []
        load_profile_matrix_data_frame = carpet_plot_load_profile_matrix.data_frame

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
                a = row_entry.to_pydatetime()
                py_date_time_entry = row_entry.to_pydatetime(a)
                converted_row_index.append(
                    py_date_time_entry.strftime(x_axis_time_format)
                )
            else:
                converted_row_index.append(row_entry)

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

        # Set x, y label and x ticks and y ticks
        matplotlib.pyplot.xlabel(x_axis_label_string)
        matplotlib.pyplot.ylabel(y_axis_label_string)
        matplotlib.pyplot.yticks(rotation=0)
        matplotlib.pyplot.xticks(rotation=45, ha="right")

        # Set title
        total_energy_demand = carpet_plot_load_profile_matrix.total_energy_demand
        energy_unit = Units.get_unit(
            unit_string=carpet_plot_load_profile_matrix.energy_unit
        )
        total_energy_quantity = Units.compress_quantity(
            unit=energy_unit,
            quantity_value=total_energy_demand,
        )
        matplotlib.pyplot.title(
            label=str(round(total_energy_quantity.m, 2))
            + " "
            + create_subscript_string_matplotlib(
                base=str(total_energy_quantity.u),
                subscripted_text=str(carpet_plot_load_profile_matrix.load_type.name),
            )
        )

        return figure
