import datetime
import json
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
    LoadProfileDataFrameStats,
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
    dataframe_from_dataclasses,
    time_ceil,
    time_floor,
    time_mod,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.type_aliases import numbers_alias
from ethos_penalps.utilities.units import Units

logger = PeNALPSLogger.get_logger_without_handler()


class DataFrameLoadProfileAnalyzer:
    def _get_first_start_time(self, analysis_data_frame: pandas.DataFrame) -> datetime.datetime:
        """Returns the first start time of the analysis data frame.

        Args:
            analysis_data_frame (pandas.DataFrame): Is build from a list of
            LoadProfileEntry.

        Returns:
            datetime.datetime: First start time of the analysis data frame.
        """

        assert pandas.api.types.is_datetime64_dtype(analysis_data_frame.loc[:, "start_time"])
        start_time_numpy = analysis_data_frame.loc[:, "start_time"].min()
        start_time = start_time_numpy.to_pydatetime()

        return start_time

    def _get_last_end_time(self, analysis_data_frame: pandas.DataFrame) -> datetime.datetime:
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

    def _get_maximum_energy_quantity(self, analysis_data_frame: pandas.DataFrame) -> float:
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

    def _get_power_unit(self, analysis_data_frame: pandas.DataFrame, object_name: str) -> str:

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

    def _get_energy_unit(self, analysis_data_frame: pandas.DataFrame, object_name: str) -> str:
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

    def _get_total_energy(self, analysis_data_frame: pandas.DataFrame) -> float | numpy.int64:
        total_energy_demand = analysis_data_frame.loc[:, "energy_quantity"].sum()

        return total_energy_demand

    def _get_maximum_power(self, analysis_data_frame: pandas.DataFrame) -> float:
        maximum_power = analysis_data_frame.loc[:, "average_power_consumption"].max()
        return maximum_power

    def _get_minimum_power(self, analysis_data_frame: pandas.DataFrame) -> float:
        minimum_power = analysis_data_frame.loc[:, "average_power_consumption"].min()
        return minimum_power

    def _get_load_type(self, analysis_data_frame: pandas.DataFrame) -> LoadType:
        list_of_unique_load_types = analysis_data_frame.loc[:, "load_type"].unique()
        if len(list_of_unique_load_types) > 1:
            warnings.warn(
                message="""The load profile contains multiple load types.
                        It should only contain one unique value. List of load types"""
                + str(list_of_unique_load_types),
                category=LoadProfileInconsistencyWarning,
            )
        if isinstance(list_of_unique_load_types[0], LoadType):
            load_type = list_of_unique_load_types[0]
        elif isinstance(list_of_unique_load_types[0], str):
            try:
                load_type_dict = json.loads(list_of_unique_load_types[0].replace("'", '"'))
                name = load_type_dict["name"]
                uuid = load_type_dict["uuid"]
                load_type = LoadType(name=name, uuid=uuid)
            except Exception:
                try:
                    import re

                    match = re.match(r"LoadType\(name='([^']*)',\s*uuid='([^']*)'\)", list_of_unique_load_types[0])
                    if match:
                        load_type = LoadType(name=match.group(1), uuid=match.group(2))
                    else:
                        load_type = LoadType(name="Could not read load type")
                except Exception:
                    load_type = LoadType(name="Could not read load type")
        else:
            load_type = LoadType(name="Load Type was no String or in memory class.")
        return load_type

    def _extract_stats_from_data_frame(
        self, analysis_data_frame: pandas.DataFrame, object_name: str = ""
    ) -> LoadProfileDataFrameStats:
        return LoadProfileDataFrameStats(
            first_start_time=self._get_first_start_time(analysis_data_frame=analysis_data_frame),
            last_end_time=self._get_last_end_time(analysis_data_frame=analysis_data_frame),
            load_type=DataFrameLoadProfileAnalyzer._get_load_type(self, analysis_data_frame=analysis_data_frame),
            power_unit=self._get_power_unit(analysis_data_frame=analysis_data_frame, object_name=object_name),
            energy_unit=self._get_energy_unit(analysis_data_frame=analysis_data_frame, object_name=object_name),
            maximum_energy=self._get_maximum_energy_quantity(analysis_data_frame=analysis_data_frame),
            maximum_power=self._get_maximum_power(analysis_data_frame=analysis_data_frame),
            minimum_power=self._get_minimum_power(analysis_data_frame=analysis_data_frame),
            total_energy=float(self._get_total_energy(analysis_data_frame=analysis_data_frame)),
        )


class ListOfLoadProfileEntryAnalyzer(DataFrameLoadProfileAnalyzer):
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
        list_of_load_profile_meta_data: ListOfLoadProfileEntryMetaData | EmptyLoadProfileMetadata
        if list_of_load_profiles:
            load_profile_data_frame = dataframe_from_dataclasses(list_of_load_profiles)
            power_unit = self._get_power_unit(analysis_data_frame=load_profile_data_frame, object_name=object_name)
            energy_unit = self._get_energy_unit(analysis_data_frame=load_profile_data_frame, object_name=object_name)
            load_type = self._get_load_type(list_of_load_profiles=list_of_load_profiles, object_name=object_name)
            list_of_load_profile_meta_data = ListOfLoadProfileEntryMetaData(
                name=object_name,
                object_type=object_type,
                list_of_load_profiles=list_of_load_profiles,
                power_unit=power_unit,
                energy_unit=energy_unit,
                load_type=load_type,
            )
        else:
            list_of_load_profile_meta_data = EmptyLoadProfileMetadata(name=object_name, object_type=object_type)

        return list_of_load_profile_meta_data

    def _get_load_type(self, list_of_load_profiles: list[LoadProfileEntry], object_name: str) -> LoadType:

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

    def check_load_profile_for_temporal_consistency(
        self,
        list_of_load_profile_meta_data: (ListOfLoadProfileEntryMetaData | EmptyLoadProfileMetadata),
        object_name: str,
    ):

        if type(list_of_load_profile_meta_data) is EmptyLoadProfileMetadata:
            pass
        elif type(list_of_load_profile_meta_data) is ListOfLoadProfileEntryMetaData:
            list_of_load_profile_entries = list_of_load_profile_meta_data.list_of_load_profiles
            analysis_data_frame_start = dataframe_from_dataclasses(list_of_load_profile_entries)
            analysis_data_frame_start.sort_values("start_time", ascending=True, inplace=True)
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

            analysis_data_frame_start.sort_values("end_time", ascending=True, inplace=True)
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
            ListOfLoadProfileEntryMetaData | LoadProfileMetaData | LoadProfileMetaDataResampled
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
            if not math.isclose(power_value_calculated, load_profile.average_power_consumption):
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
        list_of_load_profile_meta_data: (LoadProfileMetaData | LoadProfileMetaDataResampled),
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

        if list_of_load_profile_meta_data.maximum_power > 1000 or list_of_load_profile_meta_data.maximum_power < 1:
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
            logger.debug("Maximum power is in a reasonable range. No compression necessary.")

        return list_of_load_profile_meta_data

    def _convert_power_units(
        self,
        list_of_load_profile_meta_data: (LoadProfileMetaData | LoadProfileMetaDataResampled),
        target_power_unit: pint.Unit,
    ) -> LoadProfileMetaData | LoadProfileMetaDataResampled:

        output_load_profile_entry_list = []
        for load_profile_entry in list_of_load_profile_meta_data.list_of_load_profiles:
            old_power_quantity = load_profile_entry.average_power_consumption * Units.get_unit(
                load_profile_entry.power_unit
            )
            new_power_quantity = old_power_quantity.to(target_power_unit)
            new_load_profile_entry = load_profile_entry._adjust_power_unit(
                new_power_value=new_power_quantity.m,
                new_power_unit=str(target_power_unit),
            )
            output_load_profile_entry_list.append(new_load_profile_entry)
        list_of_load_profile_meta_data.list_of_load_profiles = output_load_profile_entry_list
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
            inverted_list_of_load_profile_entries = self.invert_list(list_to_invert=list_of_load_profile_entries)
            # Checks for the consistency of load profiles in the list

            list_of_load_profile_meta_data = self.create_list_of_load_profile_entry_meta_data(
                list_of_load_profiles=inverted_list_of_load_profile_entries,
                object_name=object_name,
                object_type=object_type,
            )
            assert type(list_of_load_profile_meta_data) is ListOfLoadProfileEntryMetaData

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

            data_frame = dataframe_from_dataclasses(
                list_of_load_profile_meta_data.list_of_load_profiles,
            )
            stats = self._extract_stats_from_data_frame(analysis_data_frame=data_frame, object_name=object_name)
            load_profile_meta_data = LoadProfileMetaData(
                name=object_name,
                object_type=object_type,
                list_of_load_profiles=list_of_load_profile_meta_data.list_of_load_profiles,
                data_frame=data_frame,
                last_end_time=stats.last_end_time,
                first_start_time=stats.first_start_time,
                power_unit=list_of_load_profile_meta_data.power_unit,
                energy_unit=list_of_load_profile_meta_data.energy_unit,
                maximum_energy=stats.maximum_energy,
                load_type=list_of_load_profile_meta_data.load_type,
                maximum_power=stats.maximum_power,
                minimum_power=stats.minimum_power,
                total_energy=stats.total_energy,
            )

        else:
            load_profile_meta_data = EmptyLoadProfileMetadata(name=object_name, object_type=object_type)

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

        if check_if_date_1_is_before_date_2(date_1=start_date, date_2=first_entry.start_time):
            new_first_load_profile = LoadProfileEntry(
                load_type=list_of_load_profile_meta_data.load_type,
                start_time=start_date,
                end_time=first_entry.start_time,
                energy_quantity=energy_quantity_at_start,
                energy_unit=list_of_load_profile_meta_data.energy_unit,
                average_power_consumption=power_value_to_fill,
                power_unit=list_of_load_profile_meta_data.power_unit,
            )

            list_of_load_profile_meta_data.list_of_load_profiles.insert(0, new_first_load_profile)

        return list_of_load_profile_meta_data

    def fill_to_end_date(
        self,
        list_of_load_profile_meta_data: ListOfLoadProfileEntryMetaData,
        end_date: datetime.datetime,
        energy_quantity_at_start: float = 0,
        power_value_to_fill: float = 0,
    ) -> ListOfLoadProfileEntryMetaData:
        last_entry = list_of_load_profile_meta_data.list_of_load_profiles[-1]

        if check_if_date_1_is_before_date_2(date_1=last_entry.end_time, date_2=end_date):
            new_first_load_profile = LoadProfileEntry(
                load_type=list_of_load_profile_meta_data.load_type,
                start_time=last_entry.end_time,
                end_time=end_date,
                energy_quantity=energy_quantity_at_start,
                energy_unit=list_of_load_profile_meta_data.energy_unit,
                average_power_consumption=power_value_to_fill,
                power_unit=list_of_load_profile_meta_data.power_unit,
            )
            list_of_load_profile_meta_data.list_of_load_profiles.append(new_first_load_profile)
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
                if check_if_date_1_is_before_date_2(date_1=previous_end_time, date_2=current_start_time):
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
                    output_list_of_load_profile_entries.append(load_profile_entry_to_insert)
            output_list_of_load_profile_entries.append(load_profile_entry)
            previous_load_profile_entry = load_profile_entry
            list_index_input_list = list_index_input_list + 1
            list_index_output_list = list_index_output_list + 1

        list_of_load_profile_meta_data.list_of_load_profiles = output_list_of_load_profile_entries

        return list_of_load_profile_meta_data

    def check_if_list_of_load_profile_entries_has_gaps(
        self,
        list_of_load_profile_meta_data: (
            ListOfLoadProfileEntryMetaData | LoadProfileMetaDataResampled | LoadProfileMetaData
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
        self._power_unit_cache: dict[str, str] = {}

    def _get_power_unit_string(self, energy_unit: str) -> str:
        """Cached conversion of energy unit to compact power unit string."""
        if energy_unit not in self._power_unit_cache:
            self._power_unit_cache[energy_unit] = str(
                (
                    ((1 * Units.get_unit(unit_string=energy_unit)) / (1 * Units.get_unit(unit_string="s")))
                    .to("W")
                    .to_compact()
                )
            )
        return self._power_unit_cache[energy_unit]

    def resample_load_profile_meta_data(
        self,
        load_profile_meta_data: LoadProfileMetaData,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        resample_frequency: str = "1min",
    ) -> LoadProfileMetaDataResampled:
        """Resample irregular load profile entries onto a uniform time grid.

        Distributes energy from irregularly-spaced input entries into
        equal-width output bins (time steps) using vectorized numpy operations.
        Assumes constant power within each input entry.


        Sections
        --------
        -- Create output grid
        -- Convert times to nanoseconds
        -- Compute bin alignment
        -- Filter to overlapping entries
        -- Distribute energy into bins
            -- Single-bin entries
            -- Multi-bin entries (first partial, last partial, full bins)
        -- Build output (DataFrame, entry list, metadata)
        """

        # -- Create output grid --
        timedelta_frequency = pandas.to_timedelta(resample_frequency)
        target_time_points = pandas.date_range(start=start_date, end=end_date, freq=resample_frequency)
        number_of_segments = len(target_time_points) - 1
        target_delta_seconds = timedelta_frequency.total_seconds()
        load_profile_power_unit = self._get_power_unit_string(load_profile_meta_data.energy_unit)

        # -- Convert times to nanoseconds --
        # Integer nanoseconds avoid floating-point rounding in modulo/division.
        epoch_nano_seconds = numpy.datetime64("1970-01-01", "ns")
        target_delta_nano_seconds = numpy.int64(target_delta_seconds * 1e9)
        grid_start_nano_seconds = (target_time_points.values[0] - epoch_nano_seconds).astype(numpy.int64)
        end_date_nano_seconds = (target_time_points.values[-1] - epoch_nano_seconds).astype(numpy.int64)

        number_entries = len(load_profile_meta_data.list_of_load_profiles)

        if number_entries > 0:
            df = load_profile_meta_data.data_frame
            starts_raw = df["start_time"].values.astype("datetime64[ns]")
            ends_raw = df["end_time"].values.astype("datetime64[ns]")
            energies = df["energy_quantity"].values.astype(numpy.float64)

            starts_nano_seconds = (starts_raw - epoch_nano_seconds).astype(numpy.int64)
            ends_nano_seconds = (ends_raw - epoch_nano_seconds).astype(numpy.int64)
            durations_nano_seconds = ends_nano_seconds - starts_nano_seconds
        else:
            starts_nano_seconds = numpy.empty(0, dtype=numpy.int64)
            ends_nano_seconds = numpy.empty(0, dtype=numpy.int64)
            energies = numpy.empty(0, dtype=numpy.float64)
            durations_nano_seconds = numpy.empty(0, dtype=numpy.int64)

        # -- Compute bin alignment --
        # mod: offset of each time within its bin (0 = exactly on a bin edge)
        # ceil: next bin edge at or after the time
        start_mod_nano_seconds = starts_nano_seconds % target_delta_nano_seconds
        end_mod_nano_seconds = ends_nano_seconds % target_delta_nano_seconds

        start_ceil_nano_seconds = numpy.where(
            start_mod_nano_seconds != 0,
            starts_nano_seconds + (target_delta_nano_seconds - start_mod_nano_seconds),
            starts_nano_seconds,
        )
        end_ceil_nano_seconds = numpy.where(
            end_mod_nano_seconds != 0,
            ends_nano_seconds + (target_delta_nano_seconds - end_mod_nano_seconds),
            ends_nano_seconds,
        )

        # -- Filter to overlapping entries --
        valid = (
            (start_ceil_nano_seconds <= end_date_nano_seconds)
            & (end_ceil_nano_seconds > grid_start_nano_seconds)
            & (durations_nano_seconds > 0)
        )
        start_ceil_nano_seconds = start_ceil_nano_seconds[valid]
        end_ceil_nano_seconds = end_ceil_nano_seconds[valid]
        start_mod_nano_seconds = start_mod_nano_seconds[valid]
        end_mod_nano_seconds = end_mod_nano_seconds[valid]
        energies = energies[valid]
        durations_nano_seconds = durations_nano_seconds[valid]

        durations_s = durations_nano_seconds.astype(numpy.float64) / 1e9

        # -- Distribute energy into bins --
        # n_steps: how many bin boundaries the entry crosses
        n_steps = ((end_ceil_nano_seconds - start_ceil_nano_seconds) // target_delta_nano_seconds).astype(numpy.int64)
        energy_bins = numpy.zeros(number_of_segments, dtype=numpy.float64)

        # -- Single-bin entries (n_steps == 0) --
        # Entry fits entirely within one bin; all energy goes there.
        single = n_steps == 0
        if numpy.any(single):
            bin_indices = (
                (end_ceil_nano_seconds[single] - grid_start_nano_seconds) // target_delta_nano_seconds
            ).astype(numpy.int64) - 1
            mask = (bin_indices >= 0) & (bin_indices < number_of_segments)
            numpy.add.at(energy_bins, bin_indices[mask], energies[single][mask])

        # -- Multi-bin entries (n_steps > 0) --
        # Energy is split proportionally by time overlap with each bin.
        multi = ~single
        if numpy.any(multi):
            m_start_ceil_ns = start_ceil_nano_seconds[multi]
            m_end_ceil_ns = end_ceil_nano_seconds[multi]
            m_start_mod_ns = start_mod_nano_seconds[multi]
            m_end_mod_ns = end_mod_nano_seconds[multi]
            m_energies = energies[multi]
            m_durations_s = durations_s[multi]
            m_n_steps = n_steps[multi]

            # -- First partial bin --
            # Entry starts mid-bin: fraction = (bin_edge - start) / duration
            has_first_partial = m_start_mod_ns != 0
            if numpy.any(has_first_partial):
                first_partial_ns = (target_delta_nano_seconds - m_start_mod_ns[has_first_partial]).astype(numpy.float64)
                first_frac = first_partial_ns / 1e9 / m_durations_s[has_first_partial]
                first_energy = first_frac * m_energies[has_first_partial]
                first_bin_idx = (
                    (m_start_ceil_ns[has_first_partial] - grid_start_nano_seconds) // target_delta_nano_seconds
                ).astype(numpy.int64) - 1
                mask = (first_bin_idx >= 0) & (first_bin_idx < number_of_segments)
                numpy.add.at(energy_bins, first_bin_idx[mask], first_energy[mask])

            # -- Last partial bin --
            # Entry ends mid-bin: fraction = (end - bin_edge) / duration
            has_last_partial = m_end_mod_ns != 0
            if numpy.any(has_last_partial):
                last_frac = (m_end_mod_ns[has_last_partial].astype(numpy.float64) / 1e9) / m_durations_s[
                    has_last_partial
                ]
                last_energy = last_frac * m_energies[has_last_partial]
                last_bin_idx = (
                    (m_end_ceil_ns[has_last_partial] - grid_start_nano_seconds) // target_delta_nano_seconds
                ).astype(numpy.int64) - 1
                mask = (last_bin_idx >= 0) & (last_bin_idx < number_of_segments)
                numpy.add.at(energy_bins, last_bin_idx[mask], last_energy[mask])

            # -- Full bins --
            # Each full bin gets energy * (bin_width / duration)
            full_steps = numpy.where(m_end_mod_ns == 0, m_n_steps, m_n_steps - 1)
            has_full = full_steps > 0
            if numpy.any(has_full):
                f_energies = m_energies[has_full]
                f_durations_s = m_durations_s[has_full]
                f_start_ceil_ns = m_start_ceil_ns[has_full]
                f_full_steps = full_steps[has_full]

                energy_per_step = f_energies * (target_delta_seconds / f_durations_s)
                first_full_ns = f_start_ceil_ns + target_delta_nano_seconds
                first_full_idx = ((first_full_ns - grid_start_nano_seconds) // target_delta_nano_seconds).astype(
                    numpy.int64
                ) - 1

                for i in range(len(f_full_steps)):
                    idx_start = max(0, int(first_full_idx[i]))
                    idx_end = min(number_of_segments, int(first_full_idx[i] + f_full_steps[i]))
                    if idx_start < idx_end:
                        energy_bins[idx_start:idx_end] += energy_per_step[i]

        # -- Build output --
        power_values = energy_bins / target_delta_seconds

        grid_start_times = target_time_points[:-1].to_pydatetime()
        grid_end_times = target_time_points[1:].to_pydatetime()

        lt = load_profile_meta_data.load_type
        eu = load_profile_meta_data.energy_unit

        output_data_frame = pandas.DataFrame(
            {
                "load_type": pandas.Categorical([lt] * number_of_segments),
                "start_time": grid_start_times,
                "end_time": grid_end_times,
                "energy_quantity": energy_bins,
                "energy_unit": pandas.Categorical([eu] * number_of_segments),
                "average_power_consumption": power_values,
                "power_unit": pandas.Categorical([load_profile_power_unit] * number_of_segments),
            }
        )

        energy_list = energy_bins.tolist()
        power_list = power_values.tolist()
        output_list_of_load_profile_entries: list[LoadProfileEntry] = [
            LoadProfileEntry(
                load_type=lt,
                start_time=current_start_time,
                end_time=current_end_time,
                energy_quantity=current_energy,
                energy_unit=eu,
                average_power_consumption=current_power,
                power_unit=load_profile_power_unit,
            )
            for current_start_time, current_end_time, current_energy, current_power in zip(
                grid_start_times, grid_end_times, energy_list, power_list
            )
        ]

        maximum_power = float(power_values.max()) if number_of_segments > 0 else 0.0
        minimum_power = float(power_values.min()) if number_of_segments > 0 else 0.0
        total_energy = float(energy_bins.sum())
        first_start_time = grid_start_times[0] if number_of_segments > 0 else start_date
        last_end_time = grid_end_times[-1] if number_of_segments > 0 else end_date

        load_profile_meta_data_resampled = LoadProfileMetaDataResampled(
            name=load_profile_meta_data.name,
            object_type=load_profile_meta_data.object_type,
            list_of_load_profiles=output_list_of_load_profile_entries,
            data_frame=output_data_frame,
            power_unit=load_profile_power_unit,
            energy_unit=load_profile_meta_data.energy_unit,
            load_type=load_profile_meta_data.load_type,
            time_step=timedelta_frequency,
            maximum_power=maximum_power,
            minimum_power=minimum_power,
            resample_frequency=resample_frequency,
            total_energy=total_energy,
            first_start_time=first_start_time,
            last_end_time=last_end_time,
        )

        if last_end_time != end_date:
            raise Exception("")
        if first_start_time != start_date:
            raise Exception("")
        return load_profile_meta_data_resampled
