import datetime
import math
import warnings

import matplotlib
import matplotlib.dates
import matplotlib.figure
import matplotlib.pyplot
import matplotlib.ticker
import numpy
import pandas
import pandas.api.types
import pint

from ethos_penalps.data_classes import (
    EmptyLoadProfileMetadata,
    EmptyMetaDataInformation,
    ListOfLoadProfileEntryMetaData,
    LoadProfileEntry,
    LoadProfileMetaData,
    LoadProfileMetaDataResampled,
    LoadType,
)
from ethos_penalps.utilities.exceptions_and_warnings import (
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


class ListOfLoadProfileEntryAnalyzer:
    """Can be used to analyze list of LoadProfileEntry objects"""

    def __init__(self) -> None:
        pass

    def create_list_of_load_profile_entry_meta_data(
        self,
        list_of_load_profiles: list[LoadProfileEntry],
        object_name: str,
        object_type: str,
    ) -> ListOfLoadProfileEntryMetaData | EmptyLoadProfileMetadata:
        """Creates the ListOfLoadProfileEntryMetaData object from a list of load profile entries.
        It contains the list of load profiles and some summarized information:

            - Common Power Unit
            - Common LoadType
            - Common Energy Unit

        It is expected that the list of load profile is homogeneous concerning the load type,
        energy unit and the power unit.

        Args:
            list_of_load_profiles (list[LoadProfileEntry]): list of load profiles
                with mutual load type, energy unit and power unit.
            object_name (str): Name of the object that caused the load profile.
                It can be either a stream oder a process step.

        Returns:
            ListOfLoadProfileEntryMetaData | EmptyLoadProfileMetadata: Is a meta data object contains summarized
             information about the list of load profiles which can be used for plotting or analysis.
        """
        list_of_load_profile_meta_data: (
            ListOfLoadProfileEntryMetaData | EmptyLoadProfileMetadata
        )
        if list_of_load_profiles:
            load_profile_data_frame = pandas.DataFrame(list_of_load_profiles)
            power_unit = self._get_power_unit(
                analysis_data_frame=load_profile_data_frame, object_name=object_name
            )
            energy_unit = self._get_energy_unit(
                analysis_data_frame=load_profile_data_frame, object_name=object_name
            )
            load_type = self._get_load_type(
                list_of_load_profiles=list_of_load_profiles, object_name=object_name
            )
            list_of_load_profile_meta_data = ListOfLoadProfileEntryMetaData(
                name=object_name,
                object_type=object_type,
                list_of_load_profiles=list_of_load_profiles,
                power_unit=power_unit,
                energy_unit=energy_unit,
                load_type=load_type,
            )
        else:
            list_of_load_profile_meta_data = EmptyLoadProfileMetadata(
                name=object_name, object_type=object_type
            )

        return list_of_load_profile_meta_data

    def _get_first_start_time(
        self, analysis_data_frame: pandas.DataFrame
    ) -> datetime.datetime:
        """Returns the first start time of the analysis data frame.

        Args:
            analysis_data_frame (pandas.DataFrame): Is build from a list of
            LoadProfileEntry.

        Returns:
            datetime.datetime: First start time of the analysis data frame.
        """

        assert pandas.api.types.is_datetime64_dtype(
            analysis_data_frame.loc[:, "start_time"]
        )
        start_time_numpy = analysis_data_frame.loc[:, "start_time"].min()
        start_time = start_time_numpy.to_pydatetime()

        return start_time

    def _get_last_end_time(
        self, analysis_data_frame: pandas.DataFrame
    ) -> datetime.datetime:
        """Returns the last end time of the analysis data frame.

        Args:
            analysis_data_frame (pandas.DataFrame): Is build from a list of
            LoadProfileEntry.

        Returns:
            datetime.datetime: Last end time of the analysis data frame.
        """

        end_time_numpy = analysis_data_frame.loc[:, "end_time"].max()
        end_time = end_time_numpy.to_pydatetime()
        return end_time

    def _get_maximum_energy_quantity(
        self, analysis_data_frame: pandas.DataFrame
    ) -> float:
        """Returns the value of the biggest energy quantity in the analysis
        data frame.

        Args:
            analysis_data_frame (pandas.DataFrame): Is build from a list of
            LoadProfileEntry.

        Returns:
            float: Value of the biggest energy quantity in the analysis
            data frame.
        """

        max_energy_quantity_array = analysis_data_frame.loc[:, "energy_quantity"].max()
        max_energy_quantity = float(max_energy_quantity_array)
        return max_energy_quantity

    def _get_load_type(
        self, list_of_load_profiles: list[LoadProfileEntry], object_name: str
    ) -> LoadType:

        list_of_load_types = []
        for load_profile_entry in list_of_load_profiles:
            list_of_load_types.append(load_profile_entry.load_type)

        unique_list_of_load_types = list(set(list_of_load_types))
        if len(unique_list_of_load_types) > 1:
            warnings.warn(
                message="""The load profile of object: """
                + str(object_name)
                + """ contains multiple load types.
                        It should only contain one unique value.""",
                category=LoadProfileInconsistencyWarning,
            )
        load_type = unique_list_of_load_types[0]

        return load_type

    def _get_power_unit(
        self, analysis_data_frame: pandas.DataFrame, object_name: str
    ) -> str:

        power_unit_array = analysis_data_frame.loc[:, "power_unit"].unique()
        if len(power_unit_array) > 1:
            warnings.warn(
                message="""The load profile of object:"""
                + str(object_name)
                + """ Contains multiple power units.
                        It should only contain one unique value.""",
                category=LoadProfileInconsistencyWarning,
            )
        power_unit = power_unit_array[0]

        return power_unit

    def _get_energy_unit(
        self, analysis_data_frame: pandas.DataFrame, object_name: str
    ) -> str:
        energy_unit_array = analysis_data_frame.loc[:, "energy_unit"].unique()
        if len(energy_unit_array) > 1:
            warnings.warn(
                message="""The load profile of object: """
                + str(object_name)
                + """ contains multiple energy units.
                        It should only contain one unique value.""",
                category=LoadProfileInconsistencyWarning,
            )
        energy_unit = energy_unit_array[0]
        return energy_unit

    def _get_total_energy(
        self, analysis_data_frame: pandas.DataFrame
    ) -> float | numpy.int64:
        total_energy_demand = analysis_data_frame.loc[:, "energy_quantity"].sum()
        return total_energy_demand

    def _get_maximum_power(self, analysis_data_frame: pandas.DataFrame) -> float:
        maximum_power = analysis_data_frame.loc[:, "average_power_consumption"].sum()
        return maximum_power

    def check_load_profile_for_temporal_consistency(
        self,
        list_of_load_profile_meta_data: (
            ListOfLoadProfileEntryMetaData | EmptyLoadProfileMetadata
        ),
        object_name: str,
    ):

        if type(list_of_load_profile_meta_data) is EmptyLoadProfileMetadata:
            pass
        elif type(list_of_load_profile_meta_data) is ListOfLoadProfileEntryMetaData:

            list_of_load_profile_entries = (
                list_of_load_profile_meta_data.list_of_load_profiles
            )
            analysis_data_frame_start = pandas.DataFrame(list_of_load_profile_entries)
            analysis_data_frame_start.sort_values(
                "start_time", ascending=True, inplace=True
            )
            if (
                analysis_data_frame_start.index.is_monotonic_increasing
                or analysis_data_frame_start.index.is_monotonic_decreasing
            ):
                pass
            else:
                warnings.warn(
                    message="""The start time of load profiles of object: """
                    + str(object_name)
                    + """ for load type: """
                    + str(list_of_load_profile_meta_data.load_type.name)
                    + """ are not well ordered""",
                    category=LoadProfileInconsistencyWarning,
                )

            analysis_data_frame_start.sort_values(
                "end_time", ascending=True, inplace=True
            )
            if (
                analysis_data_frame_start.index.is_monotonic_increasing
                or analysis_data_frame_start.index.is_monotonic_decreasing
            ):
                pass
            else:
                warnings.warn(
                    message="""The end time of load profiles of object: """
                    + str(object_name)
                    + """ for load type: """
                    + str(list_of_load_profile_meta_data.load_type.name)
                    + """ are not well ordered""",
                    category=LoadProfileInconsistencyWarning,
                )

    def check_if_power_and_energy_match(
        self,
        list_of_load_profile_meta_data: (
            ListOfLoadProfileEntryMetaData
            | LoadProfileMetaData
            | LoadProfileMetaDataResampled
        ),
    ):

        list_of_load_profiles = list_of_load_profile_meta_data.list_of_load_profiles

        for load_profile in list_of_load_profiles:
            power_value_calculated = Units.convert_energy_to_power(
                energy_value=load_profile.energy_quantity,
                energy_unit=load_profile.energy_unit,
                time_step=load_profile.end_time - load_profile.start_time,
                target_power_unit=load_profile.power_unit,
            )
            if not math.isclose(
                power_value_calculated, load_profile.average_power_consumption
            ):
                warnings.warn(
                    message="""The energy and power of a load profile do not fit for object: """
                    + str(list_of_load_profile_meta_data.name)
                    + """ and load type: """
                    + str(list_of_load_profile_meta_data.load_type.name)
                    + """.
                    The expected power value is: """
                    + str(power_value_calculated)
                    + """ but the entry has the value: """
                    + str(load_profile.average_power_consumption)
                    + """. The complete entry is:\n"""
                    + str(load_profile),
                    category=LoadProfileInconsistencyWarning,
                )

    def _compress_power_in_meta_data_if_necessary(
        self,
        list_of_load_profile_meta_data: (
            LoadProfileMetaData | LoadProfileMetaDataResampled
        ),
    ) -> LoadProfileMetaData | LoadProfileMetaDataResampled:
        """Adjust the power entries of the LoadProfileMetaData according to the highest
        power consumption. Adjusts the power unit if the highest power consumption
        is bigger than 10^3 or smaller than 10^-3 of the current power unit.

        Args:
            list_of_load_profile_meta_data (LoadProfileMetaData  |  LoadProfileMetaDataResampled):
                Contains the ListOfLoadProfiles and the power unit to be adjusted.

        Returns:
            LoadProfileMetaData | LoadProfileMetaDataResampled: The adjusted version of the input
                meta data.
        """

        if (
            list_of_load_profile_meta_data.maximum_power > 1000
            or list_of_load_profile_meta_data.maximum_power < 1
        ):
            if list_of_load_profile_meta_data.maximum_power > 1000:
                logger.debug("Maximum power it too large. Compress data")
            elif list_of_load_profile_meta_data.maximum_power < 1:
                logger.debug("Maximum power is too small. Compress data")
            compressed_quantity = Units.compress_quantity(
                quantity_value=list_of_load_profile_meta_data.maximum_power,
                unit=Units.get_unit(list_of_load_profile_meta_data.power_unit),
            )
            list_of_load_profile_meta_data = self._convert_power_units(
                list_of_load_profile_meta_data=list_of_load_profile_meta_data,
                target_power_unit=compressed_quantity.u,
            )
        else:
            logger.debug(
                "Maximum power is in a reasonable range. No compression necessary."
            )

        return list_of_load_profile_meta_data

    def _convert_power_units(
        self,
        list_of_load_profile_meta_data: (
            LoadProfileMetaData | LoadProfileMetaDataResampled
        ),
        target_power_unit: pint.Unit,
    ) -> LoadProfileMetaData | LoadProfileMetaDataResampled:

        output_load_profile_entry_list = []
        for load_profile_entry in list_of_load_profile_meta_data.list_of_load_profiles:
            old_power_quantity = (
                load_profile_entry.average_power_consumption
                * Units.get_unit(load_profile_entry.power_unit)
            )
            new_power_quantity = old_power_quantity.to(target_power_unit)
            new_load_profile_entry = load_profile_entry._adjust_power_unit(
                new_power_value=new_power_quantity.m,
                new_power_unit=str(target_power_unit),
            )
            output_load_profile_entry_list.append(new_load_profile_entry)
        list_of_load_profile_meta_data.list_of_load_profiles = (
            output_load_profile_entry_list
        )
        list_of_load_profile_meta_data.power_unit = str(target_power_unit)
        return list_of_load_profile_meta_data


class LoadProfileMetaDataCreator(ListOfLoadProfileEntryAnalyzer):
    def __init__(self) -> None:
        pass

    def create_load_profile_meta_data(
        self,
        list_of_load_profile_entries: list[LoadProfileEntry],
        start_date_time_series: datetime.datetime,
        end_date_time_series: datetime.datetime,
        object_name: str,
        object_type: str,
    ) -> LoadProfileMetaData | EmptyLoadProfileMetadata:
        """It applies the following checks, conversions and additions:
            - Checks if the load profiles are ordered in temporal occurrence.
            - Adds 0 demand load profiles if there are gaps between load profiles.
            - Adds an empty load profile entry form the start date to
                the first start date of a load profile entry. If the start date
                is earlier than the first load profile entry the start date is
                ignored.

        Args:
            list_of_load_profile_entries (list[LoadProfileEntry]): _description_
            start_date_time_series (datetime.datetime): _description_
            end_date_time_series (datetime.datetime): _description_
            object_name (str): _description_
            object_type (str): _description_

        Returns:
            LoadProfileMetaData | EmptyLoadProfileMetadata: _description_
        """

        load_profile_meta_data: LoadProfileMetaData | EmptyLoadProfileMetadata
        if list_of_load_profile_entries:
            # Inverts the list
            inverted_list_of_load_profile_entries = self.invert_list(
                list_to_invert=list_of_load_profile_entries
            )
            # Checks for the consistency of load profiles in the list

            list_of_load_profile_meta_data = (
                self.create_list_of_load_profile_entry_meta_data(
                    list_of_load_profiles=inverted_list_of_load_profile_entries,
                    object_name=object_name,
                    object_type=object_type,
                )
            )
            assert (
                type(list_of_load_profile_meta_data) is ListOfLoadProfileEntryMetaData
            )

            list_of_load_profile_meta_data = self.fill_from_date_to_start(
                list_of_load_profile_meta_data=list_of_load_profile_meta_data,
                start_date=start_date_time_series,
                energy_quantity_at_start=0,
            )
            list_of_load_profile_meta_data = self.fill_to_end_date(
                list_of_load_profile_meta_data=list_of_load_profile_meta_data,
                end_date=end_date_time_series,
                energy_quantity_at_start=0,
            )
            list_of_load_profile_meta_data = (
                self.fill_gaps_in_time_series_with_0_values(
                    list_of_load_profile_meta_data=list_of_load_profile_meta_data,
                    energy_value_to_fill=0,
                )
            )
            self.check_if_list_of_load_profile_entries_has_gaps(
                list_of_load_profile_meta_data=list_of_load_profile_meta_data
            )

            data_frame = pandas.DataFrame(
                list_of_load_profile_meta_data.list_of_load_profiles
            )
            last_end_time = self._get_last_end_time(analysis_data_frame=data_frame)
            first_start_time = self._get_first_start_time(
                analysis_data_frame=data_frame
            )
            maximum_energy = self._get_maximum_energy_quantity(
                analysis_data_frame=data_frame
            )
            maximum_power = self._get_maximum_power(analysis_data_frame=data_frame)
            total_energy = self._get_total_energy(analysis_data_frame=data_frame)
            load_profile_meta_data = LoadProfileMetaData(
                name=object_name,
                object_type=object_type,
                list_of_load_profiles=list_of_load_profile_meta_data.list_of_load_profiles,
                data_frame=data_frame,
                last_end_time=last_end_time,
                first_start_time=first_start_time,
                power_unit=list_of_load_profile_meta_data.power_unit,
                energy_unit=list_of_load_profile_meta_data.energy_unit,
                maximum_energy=maximum_energy,
                load_type=list_of_load_profile_meta_data.load_type,
                maximum_power=maximum_power,
                total_energy=total_energy,
            )

        else:
            load_profile_meta_data = EmptyLoadProfileMetadata(
                name=object_name, object_type=object_type
            )

        return load_profile_meta_data

    def invert_list(self, list_to_invert: list):
        return list_to_invert[::-1]

    def fill_from_date_to_start(
        self,
        list_of_load_profile_meta_data: ListOfLoadProfileEntryMetaData,
        start_date: datetime.datetime,
        energy_quantity_at_start: float = 0,
        power_value_to_fill: float = 0,
    ) -> ListOfLoadProfileEntryMetaData:

        first_entry = list_of_load_profile_meta_data.list_of_load_profiles[0]

        if check_if_date_1_is_before_date_2(
            date_1=start_date, date_2=first_entry.start_time
        ):
            new_first_load_profile = LoadProfileEntry(
                load_type=list_of_load_profile_meta_data.load_type,
                start_time=start_date,
                end_time=first_entry.start_time,
                energy_quantity=energy_quantity_at_start,
                energy_unit=list_of_load_profile_meta_data.energy_unit,
                average_power_consumption=power_value_to_fill,
                power_unit=list_of_load_profile_meta_data.power_unit,
            )

            list_of_load_profile_meta_data.list_of_load_profiles.insert(
                0, new_first_load_profile
            )

        return list_of_load_profile_meta_data

    def fill_to_end_date(
        self,
        list_of_load_profile_meta_data: ListOfLoadProfileEntryMetaData,
        end_date: datetime.datetime,
        energy_quantity_at_start: float = 0,
        power_value_to_fill: float = 0,
    ) -> ListOfLoadProfileEntryMetaData:
        last_entry = list_of_load_profile_meta_data.list_of_load_profiles[-1]

        if check_if_date_1_is_before_date_2(
            date_1=last_entry.end_time, date_2=end_date
        ):
            new_first_load_profile = LoadProfileEntry(
                load_type=list_of_load_profile_meta_data.load_type,
                start_time=last_entry.end_time,
                end_time=end_date,
                energy_quantity=energy_quantity_at_start,
                energy_unit=list_of_load_profile_meta_data.energy_unit,
                average_power_consumption=power_value_to_fill,
                power_unit=list_of_load_profile_meta_data.power_unit,
            )
            list_of_load_profile_meta_data.list_of_load_profiles.append(
                new_first_load_profile
            )
        return list_of_load_profile_meta_data

    def fill_gaps_in_time_series_with_0_values(
        self,
        list_of_load_profile_meta_data: ListOfLoadProfileEntryMetaData,
        energy_value_to_fill: float = 0,
        power_value_to_fill: float = 0,
    ) -> ListOfLoadProfileEntryMetaData:
        # Assumes that the load profiles are ordered from past to future
        output_list_of_load_profile_entries = []
        previous_load_profile_entry = None
        list_index_input_list = 0
        list_index_output_list = 0
        for load_profile_entry in list_of_load_profile_meta_data.list_of_load_profiles:
            if previous_load_profile_entry is not None:
                previous_end_time = previous_load_profile_entry.end_time
                current_start_time = load_profile_entry.start_time
                if check_if_date_1_is_before_date_2(
                    date_1=previous_end_time, date_2=current_start_time
                ):
                    load_profile_entry_to_insert = LoadProfileEntry(
                        load_type=list_of_load_profile_meta_data.load_type,
                        energy_unit=list_of_load_profile_meta_data.energy_unit,
                        energy_quantity=energy_value_to_fill,
                        start_time=previous_end_time,
                        end_time=current_start_time,
                        average_power_consumption=power_value_to_fill,
                        power_unit=list_of_load_profile_meta_data.power_unit,
                    )
                    list_index_output_list = list_index_output_list + 1
                    output_list_of_load_profile_entries.append(
                        load_profile_entry_to_insert
                    )
            output_list_of_load_profile_entries.append(load_profile_entry)
            previous_load_profile_entry = load_profile_entry
            list_index_input_list = list_index_input_list + 1
            list_index_output_list = list_index_output_list + 1

        list_of_load_profile_meta_data.list_of_load_profiles = (
            output_list_of_load_profile_entries
        )

        return list_of_load_profile_meta_data

    def check_if_list_of_load_profile_entries_has_gaps(
        self,
        list_of_load_profile_meta_data: (
            ListOfLoadProfileEntryMetaData
            | LoadProfileMetaDataResampled
            | LoadProfileMetaData
        ),
    ):
        row_number = 0
        previous_entry = None

        for load_profile_entry in list_of_load_profile_meta_data.list_of_load_profiles:
            if not isinstance(load_profile_entry, LoadProfileEntry):
                raise Exception("Unexpected  input in input list")
            if previous_entry is not None:
                if previous_entry.end_time != load_profile_entry.start_time:
                    warnings.warn(
                        message="There is a gap between last and current entry. Last entry "
                        + str(previous_entry)
                        + " current entry: "
                        + str(load_profile_entry)
                        + " at row: "
                        + str(row_number),
                        category=LoadProfileInconsistencyWarning,
                    )

            previous_entry = load_profile_entry
            row_number = row_number + 1


class LoadProfileEntryPostProcessor(LoadProfileMetaDataCreator):
    def __init__(self) -> None:
        pass

    def resample_load_profile_meta_data(
        self,
        load_profile_meta_data: LoadProfileMetaData,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        x_axis_time_period_timedelta: datetime.timedelta = datetime.timedelta(days=1),
        resample_frequency: str = "1min",
    ) -> LoadProfileMetaDataResampled:
        """Resamples list of LoadProfileEntry of the LoadProfileMetaData to a uniform time grid.

            - Adds an empty load profile entry from the latest profile entry
                to the end time provided. If the end time is earlier than the
                latest load profile entry the end time is ignored.
            - Resamples Load profiles to the resample frequency provided.

        Args:
            load_profile_meta_data (LoadProfileMetaData): _description_
            start_date (datetime.datetime): _description_
            end_date (datetime.datetime): _description_
            x_axis_time_period_timedelta (datetime.timedelta, optional): _description_. Defaults to datetime.timedelta(days=1).
            resample_frequency (str, optional): _description_. Defaults to "1min".

        Raises:
            Exception: _description_

        Returns:
            LoadProfileMetaDataResampled: _description_
        """
        """

        Args:
            list_of_load_profile_entries (list[LoadProfileEntry]): A list of load profile entries
                to be homogenized. The load profile entries must be sorted from future to past.
            start_date_time_series (datetime.datetime): The new start time of the list of load profiles.
                If the start time is later than the earliest time the start date is ignored.
            end_date_time_series (datetime.datetime): The new end time of list of load profiles.
                A zero demand entry is appended to series if the end date provided is later than
                the last load profile entry in the list.
            resample_frequency (str, optional): Is the target frequency of the output load profile list.
                It is must be provided in the the pandas resample style:

                - T, min minutely frequency
                - S secondly frequency
                - H hourly frequency
                - D calendar day frequency
                - W weekly frequency
                - M month end frequency
                - https://pandas.pydata.org/docs/user_guide/timeseries.html#timeseries-offset-aliases
                - defaults to "min"
                
                Defaults to "1min".

        Returns:
            list[LoadProfileEntry]: Homogenized list of load profiles.
        """
        load_profile_meta_data: LoadProfileMetaData

        number_of_periods = (end_date - start_date) / x_axis_time_period_timedelta
        if number_of_periods <= 0:
            raise Exception(
                "No positive number periods. Start time: "
                + str(start_date)
                + " End time: "
                + str(end_date)
            )
        logger.debug("Resampling starts")
        timedelta_frequency = pandas.to_timedelta(resample_frequency)
        end_time_date_range = pandas.date_range(
            start=timedelta_frequency + start_date,
            end=end_date,
            freq=resample_frequency,
        )

        current_target_start_time: datetime.datetime = start_date
        target_end_date_iter = iter(end_time_date_range)

        current_target_end_date: datetime.datetime = next(target_end_date_iter)
        current_list_of_relevant_input_profile_entries: list[LoadProfileEntry] = []
        output_list_of_load_profile_entries = []
        load_profile_power_unit = str(
            (
                (
                    (1 * Units.get_unit(unit_string=load_profile_meta_data.energy_unit))
                    / (1 * Units.get_unit(unit_string="s"))
                )
                .to("W")
                .to_compact()
            )
        )
        for (
            current_input_load_profile_entry
        ) in load_profile_meta_data.list_of_load_profiles:
            current_list_of_relevant_input_profile_entries.append(
                current_input_load_profile_entry
            )
            if check_if_date_1_is_before_date_2(
                date_1=current_target_end_date,
                date_2=current_input_load_profile_entry.start_time,
            ):
                raise Exception(
                    "Current input profile entry starts at: "
                    + str(current_input_load_profile_entry.start_time)
                    + " after target end at: "
                    + str(current_target_end_date)
                    + " something has been skipped"
                )
            # Check if next previous input load profile entry is required for aggregation
            if check_if_date_1_is_before_date_2(
                date_1=current_input_load_profile_entry.end_time,
                date_2=current_target_end_date,
            ):
                pass
                # Aggregation is required
                # The current input load profile entry ends before target end date
                # Further input entries need to be considered
            elif check_if_date_1_is_before_or_at_date_2(
                date_1=current_target_end_date,
                date_2=current_input_load_profile_entry.end_time,
            ):
                # No further input load profile entry is required for aggregation
                # The next input entry ends after the target end time

                # Check if the current load profile entry starts before the target entry end

                while check_if_date_1_is_before_or_at_date_2(
                    date_1=current_target_end_date,
                    date_2=current_input_load_profile_entry.end_time,
                ):
                    # Create new entries the current input stream entry starts before the end entry of the target

                    # Agglomerate all input entries which occur during the target start and end time
                    # Agglomerate all input entries which occur during the target start and end time
                    target_energy_quantity = 0
                    for (
                        input_load_profile_entry
                    ) in current_list_of_relevant_input_profile_entries:
                        # Check if considered start time on the input entry needs to be reduced
                        if check_if_date_1_is_before_date_2(
                            date_1=input_load_profile_entry.start_time,
                            date_2=current_target_start_time,
                        ):
                            # Stream starts before target start time
                            # Only considers energy consumed after start of target start time
                            relevant_start_time_current_target_entry = (
                                current_target_start_time
                            )
                        elif check_if_date_1_is_before_or_at_date_2(
                            date_1=current_target_start_time,
                            date_2=input_load_profile_entry.start_time,
                        ):
                            relevant_start_time_current_target_entry = (
                                input_load_profile_entry.start_time
                            )
                        else:
                            raise Exception("unexpected")
                        if check_if_date_1_is_before_date_2(
                            date_1=current_target_end_date,
                            date_2=input_load_profile_entry.end_time,
                        ):
                            # Stream ends after target end time
                            # Only considers energy consumed before target end time
                            relevant_end_time_current_target_entry = (
                                current_target_end_date
                            )
                        elif check_if_date_1_is_before_or_at_date_2(
                            date_1=input_load_profile_entry.end_time,
                            date_2=current_target_end_date,
                        ):
                            relevant_end_time_current_target_entry = (
                                input_load_profile_entry.end_time
                            )
                        else:
                            raise Exception("unexpected")

                        considered_time_difference = (
                            relevant_end_time_current_target_entry
                            - relevant_start_time_current_target_entry
                        )
                        full_input_time_difference = (
                            input_load_profile_entry.end_time
                            - input_load_profile_entry.start_time
                        )
                        share_of_relevant_energy = (
                            considered_time_difference / full_input_time_difference
                        )
                        if share_of_relevant_energy > 1:
                            raise Exception("Fraction should not be bigger than one")
                        relevant_energy_quantity = (
                            input_load_profile_entry.energy_quantity
                            * share_of_relevant_energy
                        )
                        target_energy_quantity = (
                            target_energy_quantity + relevant_energy_quantity
                        )

                    average_power_consumption = (
                        target_energy_quantity
                        / (
                            current_target_end_date - current_target_start_time
                        ).total_seconds()
                    )
                    new_load_profile_entry = LoadProfileEntry(
                        start_time=current_target_start_time,
                        end_time=current_target_end_date,
                        energy_quantity=target_energy_quantity,
                        energy_unit=load_profile_meta_data.energy_unit,
                        load_type=load_profile_meta_data.load_type,
                        average_power_consumption=average_power_consumption,
                        power_unit=load_profile_power_unit,
                    )
                    calculated_time_difference = (
                        new_load_profile_entry.end_time
                        - new_load_profile_entry.start_time
                    )
                    if timedelta_frequency != calculated_time_difference:
                        raise Exception(
                            "Resampled time frequency does not fit the target frequency"
                        )
                    energy_calculated_from_power = (
                        new_load_profile_entry.average_power_consumption
                        * (
                            new_load_profile_entry.end_time
                            - new_load_profile_entry.start_time
                        ).total_seconds()
                    )

                    if not math.isclose(
                        new_load_profile_entry.energy_quantity,
                        energy_calculated_from_power,
                    ):
                        raise Exception(
                            """Power does not fit the energy of the load profile entry. The 
                            load profile is"""
                            + str(new_load_profile_entry)
                        )

                    output_list_of_load_profile_entries.append(new_load_profile_entry)
                    # Update target start and end time
                    current_target_start_time = current_target_end_date
                    try:
                        current_target_end_date = next(target_end_date_iter)
                        # Update list of relevant input load profile entries
                        previous_list_of_relevant_input_profile_entries = (
                            current_list_of_relevant_input_profile_entries
                        )
                        current_list_of_relevant_input_profile_entries = []
                        for (
                            relevant_load_profile_entry
                        ) in previous_list_of_relevant_input_profile_entries:
                            if check_if_date_1_is_before_date_2(
                                date_1=current_target_start_time,
                                date_2=relevant_load_profile_entry.end_time,
                            ):
                                current_list_of_relevant_input_profile_entries.append(
                                    relevant_load_profile_entry
                                )
                    except:
                        break
        load_profile_meta_data.list_of_load_profiles = (
            output_list_of_load_profile_entries
        )
        output_data_frame = pandas.DataFrame(output_list_of_load_profile_entries)
        maximum_power = self._get_maximum_power(analysis_data_frame=output_data_frame)
        total_energy = self._get_total_energy(analysis_data_frame=output_data_frame)
        list_of_load_profile_meta_data_resampled = LoadProfileMetaDataResampled(
            name=load_profile_meta_data.name,
            object_type=load_profile_meta_data.object_type,
            list_of_load_profiles=output_list_of_load_profile_entries,
            data_frame=output_data_frame,
            power_unit=load_profile_power_unit,
            energy_unit=load_profile_meta_data.energy_unit,
            load_type=load_profile_meta_data.load_type,
            time_step=timedelta_frequency,
            maximum_power=maximum_power,
            resample_frequency=resample_frequency,
            total_energy=total_energy,
        )
        return list_of_load_profile_meta_data_resampled
