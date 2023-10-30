import datetime
import math

import matplotlib.dates
import matplotlib.figure
import matplotlib.pyplot
import matplotlib.ticker
import numpy
import pandas
import pint
import seaborn

from ethos_penalps.data_classes import (
    LoadProfileDataFrameMetaInformation,
    LoadProfileEntry,
    LoadType,
)
from ethos_penalps.utilities.general_functions import (
    check_if_date_1_is_before_date_2,
    check_if_date_1_is_before_or_at_date_2,
    create_subscript_string_matplotlib,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.units import Units

itcs_logger = PeNALPSLogger.get_logger_without_handler()


class LoadProfileEntryPostProcessor:
    def __init__(self) -> None:
        self.load_type: LoadType
        self.energy_unit: str
        self.power_unit: str
        self.start_time_of_input_load_profile: datetime.datetime
        self.end_time_of_input_load_profile: datetime.datetime
        self.processed_list_of_load_profile_entries: list[LoadProfileEntry]
        self.start_date_resampled_load_profile: datetime.datetime
        self.end_date_resampled_load_profile: datetime.datetime

    def convert_time_series_to_resampled_load_profile_meta_data(
        self,
        object_name: str,
        object_type: str,
        list_of_load_profile_entries: list[LoadProfileEntry],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        x_axis_time_period_timedelta: datetime.timedelta = datetime.timedelta(weeks=1),
        resample_frequency: str = "1min",
    ) -> LoadProfileDataFrameMetaInformation:
        if not list_of_load_profile_entries:
            print("Plot empty load profile")

        number_of_periods = (end_date - start_date) / x_axis_time_period_timedelta
        if number_of_periods <= 0:
            raise Exception(
                "No positive number periods. Start time: "
                + str(start_date)
                + " End time: "
                + str(end_date)
            )
        list_of_resampled_load_profiles_entries = (
            self.homogenize_list_of_load_profiles_entries(
                list_of_load_profile_entries=list_of_load_profile_entries,
                start_date_time_series=start_date,
                end_date_time_series=end_date,
                resample_frequency=resample_frequency,
            )
        )
        resampled_load_profile_data_frame = pandas.DataFrame(
            data=list_of_resampled_load_profiles_entries
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
            load_type=self.load_type,
            energy_unit=Units.energy_unit,
            power_unit=Units.power_unit,
            maximum_energy=maximum_energy,
            maximum_average_power=maximum_average_power,
        )
        return load_profile_meta_data

    def homogenize_list_of_load_profiles_entries(
        self,
        list_of_load_profile_entries: list[LoadProfileEntry],
        start_date_time_series: datetime.datetime,
        end_date_time_series: datetime.datetime,
        resample_frequency: str = "1min",
    ) -> list[LoadProfileEntry]:
        inverted_list_of_load_profile_entries = self.invert_list(
            list_to_invert=list_of_load_profile_entries
        )
        self.check_load_profile_for_consistency_and_extract_information(
            list_of_load_profile_entries=inverted_list_of_load_profile_entries
        )
        start_filled_list_of_load_profile_entries = self.fill_from_date_to_start(
            list_of_load_profile_entries=inverted_list_of_load_profile_entries,
            start_date=start_date_time_series,
            energy_quantity_at_start=0,
        )
        start_and_end_filled_list_of_load_profile_entries = self.fill_to_end_date(
            list_of_load_profile_entries=start_filled_list_of_load_profile_entries,
            end_date=end_date_time_series,
            energy_quantity_at_start=0,
        )
        list_of_load_profile_entries_with_consistent_time_series = self.fill_gaps_in_time_series_with_0_values(
            list_of_load_profile_entries=start_and_end_filled_list_of_load_profile_entries,
            energy_value_to_fill=0,
        )
        self.check_if_list_of_load_profile_entries_has_gaps(
            list_of_load_profile_entries=list_of_load_profile_entries_with_consistent_time_series
        )

        list_of_load_profile_entries = self.resample_load_profile_to_target_frequency(
            list_of_load_profile_entries=list_of_load_profile_entries_with_consistent_time_series,
            frequency=resample_frequency,
            start_time=start_date_time_series,
            end_time=end_date_time_series,
        )
        return list_of_load_profile_entries

    def fill_from_date_to_start(
        self,
        list_of_load_profile_entries: list[LoadProfileEntry],
        start_date: datetime.datetime,
        energy_quantity_at_start: float = 0,
        power_value_to_fill: float = 0,
    ) -> list[LoadProfileEntry]:
        first_entry = list_of_load_profile_entries[0]
        # if check_if_date_1_is_before_date_2(
        #     date_1=first_entry.start_time, date_2=start_date
        # ):
        #     raise Exception(
        #         "New Start date is after the start time of the first entry. First entry: "
        #         + str(first_entry.start_time)
        #         + " target start time: "
        #         + str(start_date)
        #     )
        if check_if_date_1_is_before_date_2(
            date_1=start_date, date_2=first_entry.start_time
        ):
            new_first_load_profile = LoadProfileEntry(
                load_type=self.load_type,
                start_time=start_date,
                end_time=first_entry.start_time,
                energy_quantity=energy_quantity_at_start,
                energy_unit=self.energy_unit,
                average_power_consumption=power_value_to_fill,
                power_unit=self.power_unit,
            )
            list_of_load_profile_entries.insert(0, new_first_load_profile)

        return list_of_load_profile_entries

    def fill_to_end_date(
        self,
        list_of_load_profile_entries: list[LoadProfileEntry],
        end_date: datetime.datetime,
        energy_quantity_at_start: float = 0,
        power_value_to_fill: float = 0,
    ) -> list[LoadProfileEntry]:
        last_entry = list_of_load_profile_entries[-1]
        # if check_if_date_1_is_before_date_2(
        #     date_1=end_date, date_2=last_entry.end_time
        # ):
        #     raise Exception(
        #         "Target end date is before end date of last entry. Target end date:"
        #         + str(end_date)
        #         + " last entry: "
        #         + str(last_entry.end_time)
        #     )
        if check_if_date_1_is_before_date_2(
            date_1=last_entry.end_time, date_2=end_date
        ):
            new_first_load_profile = LoadProfileEntry(
                load_type=self.load_type,
                start_time=last_entry.end_time,
                end_time=end_date,
                energy_quantity=energy_quantity_at_start,
                energy_unit=self.energy_unit,
                average_power_consumption=power_value_to_fill,
                power_unit=self.power_unit,
            )
            list_of_load_profile_entries.append(new_first_load_profile)
        return list_of_load_profile_entries

    def resample_load_profile_to_target_frequency(
        self,
        list_of_load_profile_entries: list[LoadProfileEntry],
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        frequency: str = "min",
    ) -> list[LoadProfileEntry]:
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
        itcs_logger.debug("Resampling starts")
        timedelta_frequency = pandas.to_timedelta(frequency)
        end_time_date_range = pandas.date_range(
            start=timedelta_frequency + start_time, end=end_time, freq=frequency
        )

        current_target_start_time: datetime.datetime = start_time
        target_end_date_iter = iter(end_time_date_range)

        current_target_end_date: datetime.datetime = next(target_end_date_iter)
        current_list_of_relevant_input_profile_entries: list[LoadProfileEntry] = []
        output_list_of_load_profile_entries = []
        for current_input_load_profile_entry in list_of_load_profile_entries:
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

                    ## Agglomerate all input entries which occur during the target start and end time
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
                        energy_unit=self.energy_unit,
                        load_type=self.load_type,
                        average_power_consumption=average_power_consumption,
                        power_unit=self.power_unit,
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
        return output_list_of_load_profile_entries

    def get_energy_amount_from_list_of_load_profile_entries(
        self, list_of_load_profile_entries: list[LoadProfileEntry]
    ) -> float:
        total_energy_amount = 0
        for load_profile_entry in list_of_load_profile_entries:
            total_energy_amount = (
                total_energy_amount + load_profile_entry.energy_quantity
            )
        return total_energy_amount

    def fill_gaps_in_time_series_with_0_values(
        self,
        list_of_load_profile_entries: list[LoadProfileEntry],
        energy_value_to_fill: float = 0,
        power_value_to_fill: float = 0,
    ) -> list[LoadProfileEntry]:
        # Assumes that the load profiles are ordered from past to future
        output_list_of_load_profile_entries = []
        previous_load_profile_entry = None
        list_index_input_list = 0
        list_index_output_list = 0
        for load_profile_entry in list_of_load_profile_entries:
            if previous_load_profile_entry is not None:
                previous_end_time = previous_load_profile_entry.end_time
                current_start_time = load_profile_entry.start_time
                if check_if_date_1_is_before_date_2(
                    date_1=previous_end_time, date_2=current_start_time
                ):
                    load_profile_entry_to_insert = LoadProfileEntry(
                        load_type=self.load_type,
                        energy_unit=self.energy_unit,
                        energy_quantity=energy_value_to_fill,
                        start_time=previous_end_time,
                        end_time=current_start_time,
                        average_power_consumption=power_value_to_fill,
                        power_unit=self.power_unit,
                    )
                    list_index_output_list = list_index_output_list + 1
                    output_list_of_load_profile_entries.append(
                        load_profile_entry_to_insert
                    )
            output_list_of_load_profile_entries.append(load_profile_entry)

            previous_load_profile_entry = load_profile_entry
            list_index_input_list = list_index_input_list + 1
            list_index_output_list = list_index_output_list + 1

        return output_list_of_load_profile_entries

    def check_load_profile_for_consistency_and_extract_information(
        self,
        list_of_load_profile_entries: list[LoadProfileEntry],
    ):
        if not list_of_load_profile_entries:
            raise Exception("There are no load profile entries in the list to check")
        self.load_type = list_of_load_profile_entries[0].load_type
        self.energy_unit = list_of_load_profile_entries[0].energy_unit
        self.power_unit = list_of_load_profile_entries[0].power_unit
        self.start_time_of_input_load_profile = list_of_load_profile_entries[
            0
        ].start_time
        self.end_time_of_input_load_profile = list_of_load_profile_entries[-1].end_time
        previous_load_profile_entry = None
        for load_profile_entry in list_of_load_profile_entries:
            if load_profile_entry.load_type != self.load_type:
                raise Exception(
                    "Load type changes in load profile from: "
                    + str(self.load_type)
                    + " to: "
                    + str(load_profile_entry.load_type)
                )
            if load_profile_entry.energy_unit != self.energy_unit:
                raise Exception(
                    "Energy unit changes in load profile from: "
                    + str(self.energy_unit)
                    + " to: "
                    + str(load_profile_entry.energy_unit)
                )
            if check_if_date_1_is_before_date_2(
                date_1=load_profile_entry.end_time, date_2=load_profile_entry.start_time
            ):
                raise Exception(
                    "Load profile entry starts at: "
                    + str(load_profile_entry.start_time)
                    + " before it ends at: "
                    + str(load_profile_entry.end_time)
                )
            if check_if_date_1_is_before_date_2(
                date_1=load_profile_entry.start_time,
                date_2=self.start_time_of_input_load_profile,
            ):
                raise Exception(
                    "Load profile entry starts at: "
                    + str(load_profile_entry.start_time)
                    + " before the first entry at: "
                    + str(self.start_time_of_input_load_profile)
                )
            if load_profile_entry.end_time > self.end_time_of_input_load_profile:
                raise Exception(
                    "Load profile entry ends at: "
                    + str(load_profile_entry.end_time)
                    + " before the last entry at: "
                    + str(self.end_time_of_input_load_profile)
                )
            if previous_load_profile_entry is not None:
                if load_profile_entry.end_time < previous_load_profile_entry.start_time:
                    raise Exception(
                        "Overlap in current load profile entry: "
                        + str(load_profile_entry)
                        + " and previous load profile entry: "
                        + str(previous_load_profile_entry)
                    )
        itcs_logger.debug("Check is successful")

    def invert_list(self, list_to_invert: list):
        return list_to_invert[::-1]

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
            inverted_list_of_list_of_load_profile_entries = self.invert_list(
                list_to_invert=list_of_load_profiles
            )
            self.check_load_profile_for_consistency_and_extract_information(
                list_of_load_profile_entries=inverted_list_of_list_of_load_profile_entries
            )
            if final_output_start_date is None:
                final_output_start_date = self.determine_new_start_date(
                    start_date=self.start_time_of_input_load_profile,
                    end_date=end_date,
                    period=period,
                )
            if isinstance(final_output_start_date, datetime.datetime):
                next_output_start_date = self.determine_new_start_date(
                    start_date=self.start_time_of_input_load_profile,
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

    def check_if_list_of_load_profile_entries_has_gaps(
        self, list_of_load_profile_entries: list[LoadProfileEntry]
    ):
        row_number = 0
        previous_entry = None

        for load_profile_entry in list_of_load_profile_entries:
            if not isinstance(load_profile_entry, LoadProfileEntry):
                raise Exception("Unexpected  input in input list")
            if previous_entry is not None:
                if previous_entry.end_time != load_profile_entry.start_time:
                    raise Exception(
                        "There is a gap between last and current entry. Last entry "
                        + str(previous_entry)
                        + " current entry: "
                        + str(load_profile_entry)
                        + " at row: "
                        + str(row_number)
                    )

            previous_entry = load_profile_entry
            row_number = row_number + 1
