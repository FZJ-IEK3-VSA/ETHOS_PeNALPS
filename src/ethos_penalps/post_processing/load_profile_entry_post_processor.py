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
import pint

from ethos_penalps.utilities.exceptions_and_warnings import (
    LoadProfileInconsistencyWarning,
)
from ethos_penalps.data_classes import (
    LoadProfileDataFrameMetaInformation,
    LoadProfileEntry,
    LoadType,
    ListOfLoadProfileMetaData,
    ListLoadProfileMetaDataEmpty,
    EmptyMetaDataInformation,
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
    def __init__(self) -> None:
        pass

    def create_list_of_load_profile_meta_data(
        self, list_of_load_profiles: list[LoadProfileEntry], object_name: str
    ) -> ListOfLoadProfileMetaData | ListLoadProfileMetaDataEmpty:
        """Creates the ListOfLoadProfileMetaData object from a list of load profile entries.
        The meta data object contains summarized information about the list of load profiles
        which can be used for plotting or analysis.

        Args:
            list_of_load_profiles (list[LoadProfileEntry]): _description_
            object_name (str): _description_

        Returns:
            ListOfLoadProfileMetaData | ListLoadProfileMetaDataEmpty: Is a meta data object contains summarized
             information about the list of load profiles which can be used for plotting or analysis.
        """
        list_of_load_profile_meta_data: (
            ListOfLoadProfileMetaData | ListLoadProfileMetaDataEmpty
        )
        if list_of_load_profiles:
            analysis_data_frame = pandas.DataFrame(list_of_load_profiles)
            power_unit = self._get_power_unit(
                analysis_data_frame=analysis_data_frame, object_name=object_name
            )
            energy_unit = self._get_energy_unit(
                analysis_data_frame=analysis_data_frame, object_name=object_name
            )
            total_energy_demand = self._get_total_energy(
                analysis_data_frame=analysis_data_frame
            )
            maximum_power = self._get_maximum_power(
                analysis_data_frame=analysis_data_frame
            )
            load_type = self._get_load_type(
                list_of_load_profiles=list_of_load_profiles, object_name=object_name
            )
            list_of_load_profile_meta_data = ListOfLoadProfileMetaData(
                object_name=object_name,
                list_of_load_profiles=list_of_load_profiles,
                power_unit=power_unit,
                energy_unit=energy_unit,
                total_energy=total_energy_demand,
                maximum_power=maximum_power,
                load_type=load_type,
            )
        else:
            list_of_load_profile_meta_data = ListLoadProfileMetaDataEmpty(
                object_name=object_name
            )

        return list_of_load_profile_meta_data

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
            ListOfLoadProfileMetaData | ListLoadProfileMetaDataEmpty
        ),
        object_name: str,
    ):

        if type(list_of_load_profile_meta_data) is ListLoadProfileMetaDataEmpty:
            pass
        elif type(list_of_load_profile_meta_data) is ListOfLoadProfileMetaData:

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
        self, list_of_load_profile_meta_data: ListOfLoadProfileMetaData
    ):
        list_of_load_profiles = list_of_load_profile_meta_data.list_of_load_profiles

        for load_profile in list_of_load_profiles:
            power_value_calculated = Units.convert_energy_to_power(
                energy_value=load_profile.energy_quantity,
                energy_unit=load_profile.energy_unit,
                time_step=load_profile.end_time - load_profile.start_time,
                target_power_unit=load_profile.power_unit,
            )
            if power_value_calculated != load_profile.average_power_consumption:
                warnings.warn(
                    message="""The energy and power of a load profile do not fit for object: """
                    + str(list_of_load_profile_meta_data.object_name)
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

    def _compress_power_if_necessary(
        self, list_of_load_profile_meta_data: ListOfLoadProfileMetaData
    ) -> ListOfLoadProfileMetaData:

        if (
            list_of_load_profile_meta_data.maximum_power > 1000
            or list_of_load_profile_meta_data.maximum_power < 1
        ):
            if list_of_load_profile_meta_data.maximum_power > 1000:
                logger.debug("Maximum power it too large. Compress data")
            elif list_of_load_profile_meta_data.maximum_power < 1:
                logger.debug("Maximum power is too small. Compress data")
            compressed_quantity = Units.compress_quantity(
                list_of_load_profile_meta_data.maximum_power,
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
        list_of_load_profile_meta_data: ListOfLoadProfileMetaData,
        target_power_unit: pint.Unit,
    ) -> ListOfLoadProfileMetaData:

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


class ListOfLoadProfileEntryHomogenizer(ListOfLoadProfileEntryAnalyzer):
    def __init__(self) -> None:
        pass

    def homogenize_list_of_load_profiles_entries(
        self,
        list_of_load_profile_entries: list[LoadProfileEntry],
        start_date_time_series: datetime.datetime,
        end_date_time_series: datetime.datetime,
        object_name: str,
        resample_frequency: str = "1min",
    ) -> ListOfLoadProfileMetaData:
        """Homogenizes and adjusts the time step length of the load profile entry list.
        It applies the following checks, conversions and additions:
            - Checks if the load profiles are ordered in temporal occurrence.
            - Adds 0 demand load profiles if there are gaps between load profiles.
            - Adds an empty load profile entry form the start date to
                the first start date of a load profile entry. If the start date
                is earlier than the first load profile entry the start date is
                ignored.
            - Adds an empty load profile entry from the latest profile entry
                to the end time provided. If the end time is earlier than the
                latest load profile entry the end time is ignored.
            - Resamples Load profiles to the resample frequency provided.

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

        # Inverts the list
        inverted_list_of_load_profile_entries = self.invert_list(
            list_to_invert=list_of_load_profile_entries
        )
        # Checks for the consistency of load profiles in the list

        list_of_load_profile_meta_data = self.create_list_of_load_profile_meta_data(
            list_of_load_profiles=inverted_list_of_load_profile_entries,
            object_name=object_name,
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
        list_of_load_profile_meta_data = self.fill_gaps_in_time_series_with_0_values(
            list_of_load_profile_meta_data=list_of_load_profile_meta_data,
            energy_value_to_fill=0,
        )
        self.check_if_list_of_load_profile_entries_has_gaps(
            list_of_load_profile_meta_data=list_of_load_profile_meta_data
        )

        list_of_load_profile_meta_data = self.resample_load_profile_to_target_frequency(
            list_of_load_profile_meta_data=list_of_load_profile_meta_data,
            frequency=resample_frequency,
            start_time=start_date_time_series,
            end_time=end_date_time_series,
        )

        return list_of_load_profile_meta_data

    def invert_list(self, list_to_invert: list):
        return list_to_invert[::-1]

    def fill_from_date_to_start(
        self,
        list_of_load_profile_meta_data: ListOfLoadProfileMetaData,
        start_date: datetime.datetime,
        energy_quantity_at_start: float = 0,
        power_value_to_fill: float = 0,
    ) -> ListOfLoadProfileMetaData:

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
        list_of_load_profile_meta_data: ListOfLoadProfileMetaData,
        end_date: datetime.datetime,
        energy_quantity_at_start: float = 0,
        power_value_to_fill: float = 0,
    ) -> ListOfLoadProfileMetaData:
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
        list_of_load_profile_meta_data: ListOfLoadProfileMetaData,
        energy_value_to_fill: float = 0,
        power_value_to_fill: float = 0,
    ) -> ListOfLoadProfileMetaData:
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
        self, list_of_load_profile_meta_data: ListOfLoadProfileMetaData
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

    def resample_load_profile_to_target_frequency(
        self,
        list_of_load_profile_meta_data: ListOfLoadProfileMetaData,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        frequency: str = "min",
    ) -> ListOfLoadProfileMetaData:
        """_summary_

        :param list_of_load_profile_entries: _description_
        :type list_of_load_profile_entries: list[LoadProfileEntry]
        :param start_time: _description_
        :type start_time: datetime.datetime
        :param end_time: _description_
        :type end_time: datetime.datetime
        :param frequency:
            - T, min minutely frequency
            - S secondly frequency
            - H hourly frequency
            - D calendar day frequency
            - W weekly frequency
            - M month end frequency
            - https://pandas.pydata.org/docs/user_guide/timeseries.html#timeseries-offset-aliases
            - defaults to "min"
        :type frequency: str, optional
        :raises Exception: _description_
        :raises Exception: _description_
        :raises Exception: _description_
        :raises Exception: _description_
        :raises Exception: _description_
        :return: _description_
        :rtype: pandas.DataFrame
        """
        logger.debug("Resampling starts")
        timedelta_frequency = pandas.to_timedelta(frequency)
        end_time_date_range = pandas.date_range(
            start=timedelta_frequency + start_time, end=end_time, freq=frequency
        )

        current_target_start_time: datetime.datetime = start_time
        target_end_date_iter = iter(end_time_date_range)

        current_target_end_date: datetime.datetime = next(target_end_date_iter)
        current_list_of_relevant_input_profile_entries: list[LoadProfileEntry] = []
        output_list_of_load_profile_entries = []
        for (
            current_input_load_profile_entry
        ) in list_of_load_profile_meta_data.list_of_load_profiles:
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
                        energy_unit=list_of_load_profile_meta_data.energy_unit,
                        load_type=list_of_load_profile_meta_data.load_type,
                        average_power_consumption=average_power_consumption,
                        power_unit=list_of_load_profile_meta_data.power_unit,
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

                    # if (
                    #     new_load_profile_entry.energy_quantity
                    #     != energy_calculated_from_power
                    # ):
                    #     raise Exception(
                    #         "Power does not fit the energy of the load profile entry"
                    #     )

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
            list_of_load_profile_meta_data.list_of_load_profiles = (
                output_list_of_load_profile_entries
            )
        return list_of_load_profile_meta_data


class LoadProfileEntryPostProcessor(ListOfLoadProfileEntryHomogenizer):
    def __init__(self) -> None:
        pass

    def convert_time_series_to_resampled_load_profile_meta_data(
        self,
        object_name: str,
        object_type: str,
        list_of_load_profile_entries: list[LoadProfileEntry],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        x_axis_time_period_timedelta: datetime.timedelta = datetime.timedelta(weeks=1),
        resample_frequency: str = "1min",
    ) -> LoadProfileDataFrameMetaInformation | EmptyMetaDataInformation:

        if list_of_load_profile_entries:
            number_of_periods = (end_date - start_date) / x_axis_time_period_timedelta
            if number_of_periods <= 0:
                raise Exception(
                    "No positive number periods. Start time: "
                    + str(start_date)
                    + " End time: "
                    + str(end_date)
                )
            list_of_load_profile_meta_data = (
                self.homogenize_list_of_load_profiles_entries(
                    list_of_load_profile_entries=list_of_load_profile_entries,
                    start_date_time_series=start_date,
                    end_date_time_series=end_date,
                    resample_frequency=resample_frequency,
                    object_name=object_name,
                )
            )
            resampled_load_profile_data_frame = pandas.DataFrame(
                data=list_of_load_profile_meta_data.list_of_load_profiles
            )

            maximum_average_power = resampled_load_profile_data_frame.loc[
                :, "average_power_consumption"
            ].max()
            maximum_energy = resampled_load_profile_data_frame.loc[
                :, "energy_quantity"
            ].max()
            load_profile_meta_data = LoadProfileDataFrameMetaInformation(
                name=object_name,
                object_type=object_type,
                data_frame=resampled_load_profile_data_frame,
                first_start_time=start_date,
                last_end_time=end_date,
                load_type=list_of_load_profile_meta_data.load_type,
                energy_unit=list_of_load_profile_meta_data.energy_unit,
                power_unit=list_of_load_profile_meta_data.power_unit,
                maximum_energy=maximum_energy,
                maximum_average_power=maximum_average_power,
            )
        else:
            load_profile_meta_data = EmptyMetaDataInformation(
                name=object_name, object_type=object_type
            )
        return load_profile_meta_data

    def determine_earliest_start_date_from_list_of_list_of_load_profile_entries(
        self,
        end_date: datetime.datetime,
        period: datetime.timedelta,
        list_of_list_of_load_profile_entries: list[list[LoadProfileEntry]],
    ):
        final_output_start_date = None

        if not list_of_list_of_load_profile_entries:
            raise Exception(
                "Tried to find common start point from empty load profile list"
            )
        for list_of_load_profiles in list_of_list_of_load_profile_entries:
            list_of_load_profile_meta_data = self.create_list_of_load_profile_meta_data(
                list_of_load_profiles=list_of_load_profiles, object_name="Intermediate"
            )
            self.check_load_profile_for_temporal_consistency(
                list_of_load_profile_meta_data=list_of_load_profile_meta_data,
                object_name="Intermediate",
            )
            start_time_of_input_load_profile = (
                list_of_load_profile_meta_data.list_of_load_profiles[0]
            ).start_time
            if final_output_start_date is None:

                final_output_start_date = self.determine_new_start_date(
                    start_date=start_time_of_input_load_profile,
                    end_date=end_date,
                    period=period,
                )
            if isinstance(final_output_start_date, datetime.datetime):
                next_output_start_date = self.determine_new_start_date(
                    start_date=start_time_of_input_load_profile,
                    end_date=end_date,
                    period=period,
                )
                if check_if_date_1_is_before_date_2(
                    date_1=next_output_start_date, date_2=final_output_start_date
                ):
                    final_output_start_date = next_output_start_date
        return final_output_start_date

    def determine_new_start_date(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        period: datetime.timedelta,
    ) -> datetime.datetime:
        complete_time_span_of_series = end_date - start_date
        number_of_periods_float = complete_time_span_of_series / period
        number_of_periods_int = int(math.ceil(number_of_periods_float))
        new_start_date = end_date - number_of_periods_int * period
        return new_start_date
