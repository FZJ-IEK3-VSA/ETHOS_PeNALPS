import datetime
import itertools
import numbers
from dataclasses import dataclass, field
from operator import add
from typing import Literal

import datetimerange
import numpy
import pandas

from ethos_penalps.data_classes import Commodity, StorageProductionPlanEntry
from ethos_penalps.simulation_data.container_simulation_data import (
    CurrentProductionStateData,
    PostProductionStateData,
    PreProductionStateData,
    ProductionProcessStateContainer,
    UninitializedCurrentStateData,
    ValidatedPostProductionStateData,
)
from ethos_penalps.stream import (
    BaseStreamState,
    BatchStream,
    BatchStreamState,
    ContinuousStream,
    ContinuousStreamState,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.time_overlap_analyzer import (
    TimeOverLapAnalyzer,
    TimeRange,
    TimeRangeDatetime,
    TimeRangesHandler,
)
from ethos_penalps.utilities.general_functions import (
    check_if_date_1_is_before_date_2,
    check_if_date_1_is_before_or_at_date_2,
    datetime_to_seconds,
    format_timedelta,
    seconds_to_datetime,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.type_aliases import numbers_alias

logger = PeNALPSLogger.get_logger_without_handler()


class BaseStorage:
    """Provides basic functionality to track and update a storage level
    of a node based on input and output streams to that node.
    """

    def __init__(
        self,
        stream_handler: StreamHandler,
        input_to_output_conversion_factor: numbers_alias,
        commodity: Commodity,
        process_step_name: str,
        storage_level_at_start: numbers_alias = 0,
    ) -> None:
        self.stream_handler: StreamHandler = stream_handler
        self.input_to_output_conversion_factor: numbers_alias = input_to_output_conversion_factor
        self.commodity: Commodity = commodity
        self.process_step_name: str = process_step_name
        self.current_storage_level: numbers_alias = storage_level_at_start
        self.total_input: numbers_alias = 0
        self.total_output: numbers_alias = 0

    def create_time_ranges_handler(
        self,
        input_stream_state_list: list[ContinuousStreamState | BatchStreamState],
        output_stream_state_list: list[ContinuousStreamState | BatchStreamState],
    ) -> TimeRangesHandler:
        time_ranges_handler = TimeRangesHandler()

        for stream_state in input_stream_state_list:
            if isinstance(stream_state, ContinuousStreamState):
                time_ranges_handler.add_continuous_time_point(time_point=stream_state.start_time_seconds)
                time_ranges_handler.add_continuous_time_point(time_point=stream_state.end_time_seconds)
            elif isinstance(stream_state, BatchStreamState):
                time_ranges_handler.add_batch_input_state(batch_state=stream_state)

        for stream_state in output_stream_state_list:
            if isinstance(stream_state, ContinuousStreamState):
                time_ranges_handler.add_continuous_time_point(time_point=stream_state.start_time_seconds)
                time_ranges_handler.add_continuous_time_point(time_point=stream_state.end_time_seconds)
            elif isinstance(stream_state, BatchStreamState):
                time_ranges_handler.add_batch_output_state(batch_state=stream_state)

        return time_ranges_handler

    def add_continuous_stream_state_to_net_stream_list(
        self,
        input_stream_state: ContinuousStreamState,
        duration_tuple_list: list[list[numbers_alias]],
        continuous_start_point_to_index_dict: dict[numbers_alias, int],
        continuous_end_point_to_index_dict: dict[numbers_alias, int],
        add_as_input_stream: bool,
    ):

        start_point_index = continuous_start_point_to_index_dict[input_stream_state.start_time_seconds]
        end_point_index = continuous_end_point_to_index_dict[input_stream_state.end_time_seconds]
        list_of_relevant_duration_tuples = duration_tuple_list[start_point_index : end_point_index + 1]
        total_duration_of_stream = input_stream_state.end_time_seconds - input_stream_state.start_time_seconds
        if add_as_input_stream is False:
            total_duration_of_stream = total_duration_of_stream * -1

        for current_tuple in list_of_relevant_duration_tuples:
            time_share = current_tuple[2] / total_duration_of_stream
            mass_share = time_share * input_stream_state.total_mass
            current_tuple[3] = current_tuple[3] + mass_share
        pass

    def add_batch_stream_state_to_net_stream_list(
        self,
        input_stream_state: BatchStreamState,
        duration_tuple_list: list[list[numbers_alias]],
        batch_time_point_to_index_dict: dict[numbers_alias, int],
        add_as_input_stream: bool,
    ):
        if add_as_input_stream is False:
            add_time_point = input_stream_state.start_time_seconds
            mass_added = -input_stream_state.batch_mass_value
        else:
            add_time_point = input_stream_state.end_time_seconds
            mass_added = input_stream_state.batch_mass_value

        duration_tuple_index = batch_time_point_to_index_dict[add_time_point]
        duration_tuple_list[duration_tuple_index][3] = duration_tuple_list[duration_tuple_index][3] + mass_added

    def _create_net_mass_duration_array(
        self,
        input_stream_state_list: list[ContinuousStreamState | BatchStreamState],
        output_stream_state_list: list[ContinuousStreamState | BatchStreamState],
        boundary_time_points: list[float] | None = None,
    ) -> numpy.ndarray:
        """Creates a numpy array with columns [start_seconds, end_seconds, duration, net_mass]
        from the input and output stream states.

        Args:
            input_stream_state_list (list[ContinuousStreamState | BatchStreamState]): List of streams that
                add mass to the storage.
            output_stream_state_list (list[ContinuousStreamState | BatchStreamState]): List of streams
                that remove mass from the storage.
            boundary_time_points: Optional list of additional time points (in seconds)
                to inject into the time ranges handler. This causes segments to be
                split at these points so that continuous stream mass is distributed
                proportionally on each side of the boundary.

        Returns:
            numpy.ndarray: Array with shape (n_segments, 4) containing
                [start_seconds, end_seconds, duration, net_mass] per time segment.
        """
        time_ranges_handler = self.create_time_ranges_handler(
            input_stream_state_list=input_stream_state_list,
            output_stream_state_list=output_stream_state_list,
        )
        if boundary_time_points:
            for time_point in boundary_time_points:
                time_ranges_handler.add_continuous_time_point(time_point=time_point)
        (
            duration_tuple_list,
            batch_time_point_to_index_dict,
            continuous_start_point_to_index_dict,
            continuous_end_point_to_index_dict,
        ) = time_ranges_handler.get_duration_list_list_and_time_point_dictionaries()

        for input_stream_state in input_stream_state_list:
            if isinstance(input_stream_state, ContinuousStreamState):
                self.add_continuous_stream_state_to_net_stream_list(
                    input_stream_state=input_stream_state,
                    duration_tuple_list=duration_tuple_list,
                    continuous_start_point_to_index_dict=continuous_start_point_to_index_dict,
                    continuous_end_point_to_index_dict=continuous_end_point_to_index_dict,
                    add_as_input_stream=True,
                )
            elif isinstance(input_stream_state, BatchStreamState):
                self.add_batch_stream_state_to_net_stream_list(
                    input_stream_state=input_stream_state,
                    duration_tuple_list=duration_tuple_list,
                    batch_time_point_to_index_dict=batch_time_point_to_index_dict,
                    add_as_input_stream=True,
                )

        for output_stream_state in output_stream_state_list:
            if isinstance(output_stream_state, ContinuousStreamState):
                self.add_continuous_stream_state_to_net_stream_list(
                    input_stream_state=output_stream_state,
                    duration_tuple_list=duration_tuple_list,
                    continuous_start_point_to_index_dict=continuous_start_point_to_index_dict,
                    continuous_end_point_to_index_dict=continuous_end_point_to_index_dict,
                    add_as_input_stream=False,
                )
            elif isinstance(output_stream_state, BatchStreamState):
                self.add_batch_stream_state_to_net_stream_list(
                    input_stream_state=output_stream_state,
                    duration_tuple_list=duration_tuple_list,
                    batch_time_point_to_index_dict=batch_time_point_to_index_dict,
                    add_as_input_stream=False,
                )

        return numpy.array(duration_tuple_list)

    def _create_storage_entries_from_duration_array(
        self,
        duration_array: numpy.ndarray,
        storage_level_at_start: numbers_alias,
    ) -> list[StorageProductionPlanEntry]:
        """Creates StorageProductionPlanEntry objects from a duration array using numpy cumsum.

        Args:
            duration_array (numpy.ndarray): Array with columns
                [start_seconds, end_seconds, duration, net_mass].
            storage_level_at_start (numbers_alias): The storage level at the
                beginning of the first entry.

        Returns:
            list[StorageProductionPlanEntry]: List of storage entries.
        """
        net_masses = duration_array[:, 3]
        cumulative_mass = numpy.cumsum(net_masses)
        levels_at_end = storage_level_at_start + cumulative_mass
        levels_at_start = numpy.empty_like(levels_at_end)
        levels_at_start[0] = storage_level_at_start
        levels_at_start[1:] = levels_at_end[:-1]

        start_times_dt = pandas.to_datetime(duration_array[:, 0], unit="s", utc=True).tz_localize(None).to_pydatetime()
        end_times_dt = pandas.to_datetime(duration_array[:, 1], unit="s", utc=True).tz_localize(None).to_pydatetime()

        process_step_name = self.process_step_name
        commodity = self.commodity
        list_storage_production_plan_entries = []
        for i in range(len(duration_array)):
            start_time = start_times_dt[i]
            end_time = end_times_dt[i]
            storage_production_plan_entry = StorageProductionPlanEntry(
                process_step_name=process_step_name,
                start_time=start_time,
                end_time=end_time,
                storage_level_at_start=float(levels_at_start[i]),
                storage_level_at_end=float(levels_at_end[i]),
                commodity=commodity,
                duration=end_time - start_time,
            )
            list_storage_production_plan_entries.append(storage_production_plan_entry)
        return list_storage_production_plan_entries

    def create_storage_entries_from_streams(
        self,
        input_stream_state_list: list[ContinuousStreamState | BatchStreamState],
        output_stream_state_list: list[ContinuousStreamState | BatchStreamState],
        storage_level_at_start: numbers_alias | Literal["auto_offset"],
        check_mass_conservation: bool = False,
        mass_conservation_tolerance: float = 1e-6,
        start_time: datetime.datetime | None = None,
        end_time: datetime.datetime | None = None,
    ) -> tuple[list[StorageProductionPlanEntry], numpy.ndarray, numbers_alias]:
        """Create storage entries from input/output streams in a single call.

        Combines create_net_mass_duration_array and _create_storage_entries_from_duration_array
        with optional auto-offset and mass conservation checking.

        Args:
            input_stream_state_list: Streams that add mass to the storage.
            output_stream_state_list: Streams that remove mass from the storage.
            storage_level_at_start: Explicit starting storage level, or the literal
                ``"auto_offset"`` to compute the minimum starting level that keeps
                the storage level non-negative throughout the simulation.
            check_mass_conservation: If True, verify that
                final_level == start_level + total_input - total_output
                and raise ValueError if the check fails.
            mass_conservation_tolerance: Absolute tolerance for the mass
                conservation check.
            start_time: If provided, streams are cut at this time. Segments
                starting before this time are excluded, and continuous stream
                mass is proportionally distributed so only the portion after
                this time is counted. Used to remove startup behaviour.
            end_time: If provided, streams are cut at this time. Segments
                ending after this time are excluded, and continuous stream
                mass is proportionally distributed so only the portion before
                this time is counted. Used to remove cooldown behaviour.

        Returns:
            Tuple of (entries, duration_array, start_storage_level):
                - entries: List of StorageProductionPlanEntry.
                - duration_array: Numpy array with columns
                  [start_seconds, end_seconds, duration, net_mass].
                - start_storage_level: The storage level used at the start
                  (computed when storage_level_at_start is "auto_offset").
        """
        # Inject boundary time points so that segments are split at the cut
        # points.  Continuous stream mass is then distributed proportionally
        # on each side of the boundary by the existing time-share logic.
        boundary_time_points: list[float] = []
        if start_time is not None:
            boundary_time_points.append(datetime_to_seconds(start_time))
        if end_time is not None:
            boundary_time_points.append(datetime_to_seconds(end_time))

        duration_array = self._create_net_mass_duration_array(
            input_stream_state_list=input_stream_state_list,
            output_stream_state_list=output_stream_state_list,
            boundary_time_points=boundary_time_points or None,
        )

        if start_time is not None or end_time is not None:
            mask = numpy.ones(len(duration_array), dtype=bool)
            if start_time is not None:
                start_seconds = datetime_to_seconds(start_time)
                mask &= duration_array[:, 0] >= start_seconds
            if end_time is not None:
                end_seconds = datetime_to_seconds(end_time)
                mask &= duration_array[:, 1] <= end_seconds
            duration_array = duration_array[mask]

        if storage_level_at_start == "auto_offset":
            cumulative = numpy.cumsum(duration_array[:, 3])
            start_level: numbers_alias = max(0.0, -float(cumulative.min()))
        else:
            start_level = storage_level_at_start

        entries = self._create_storage_entries_from_duration_array(
            duration_array=duration_array,
            storage_level_at_start=start_level,
        )

        if check_mass_conservation and entries:
            # Column three of the duration_array contains the mass. Other columsn are start_seconds, end_seconds and duration.
            total_net_mass = float(duration_array[:, 3].sum())
            expected_end = float(start_level) + total_net_mass
            actual_end = entries[-1].storage_level_at_end
            if abs(actual_end - expected_end) > mass_conservation_tolerance:
                raise ValueError(
                    f"Mass conservation violated: "
                    f"start({start_level}) + net({total_net_mass}) = {expected_end}, "
                    f"but final level is {actual_end}"
                )

        return entries, duration_array, start_level

    def convert_output_to_input_mass(self, output_mass: numbers_alias) -> numbers_alias:
        """Converts the output to input mass.

        Args:
            output_mass (numbers_alias): Mass to be converted.

        Returns:
            numbers_alias: Converted mass.
        """
        input_mass = output_mass / self.input_to_output_conversion_factor
        return input_mass

    def convert_input_to_output_mass(self, input_mass: numbers_alias) -> numbers_alias:
        """Converts input to output mass.

        Args:
            input_mass (numbers_alias): Mass to be converted.

        Returns:
            numbers_alias: Converted mass.
        """
        output_mass = input_mass * self.input_to_output_conversion_factor
        return output_mass


class Storage(BaseStorage):
    """Is used to analyse the internal storage of a Process Step."""

    def __init__(
        self,
        name: str,
        commodity: Commodity,
        stream_handler: StreamHandler,
        input_stream_name: str,
        output_stream_name: str,
        time_data: TimeData,
        input_to_output_conversion_factor: numbers_alias,
        state_data_container: ProductionProcessStateContainer,
        process_step_name: str,
        minimum_storage_level: numbers_alias = 0,
        maximum_storage_level: numbers_alias | None = None,
        minimum_storage_level_at_start_time_of_production_branch: (numbers_alias | None) = None,
        maximum_storage_level_at_start_time_of_production_branch: (numbers_alias | None) = None,
    ) -> None:
        """
        Args:
            name (str): Name of the storage.
            commodity (Commodity): Commodity that is stored by the storage.
                It is assumed that input commodity is automatically converted
                into the output commodity that is stored in the storage.
            stream_handler (StreamHandler): Container of all input and output streams
                to the storage.
            input_stream_name (str): Name of the input stream.
            output_stream_name (str): Name of the output stream.
            time_data (TimeData): Contains data about the current state of the ProcessStep.
            input_to_output_conversion_factor (numbers_alias): The conversion factor
                that converts input mass into output mass.
            state_data_container (ProductionProcessStateContainer): Contains all
                other simulation data of the process step besides the time data.
            process_step_name (str): Name of the ProcessStep that holds this storage.
            minimum_storage_level (numbers_alias, optional): The minimum storage level
                of the storage. Is currently not used. Defaults to 0.
            maximum_storage_level (numbers_alias | None, optional): The maximum allowed storage level
                is currently not used. Defaults to None.
            minimum_storage_level_at_start_time_of_production_branch (numbers_alias  |  None, optional):
                The minimum storage level at the start of a new request for an output stream. Defaults to None.
            maximum_storage_level_at_start_time_of_production_branch (numbers_alias  |  None, optional): The maximum storage level at the start of
                a new request for an output stream. Defaults to None.
        """

        if not isinstance(input_stream_name, str):
            raise Exception("A name of typ string should be supplied for process step identification")

        if not isinstance(output_stream_name, str):
            raise Exception("A name of typ string should be supplied for process step identification")

        self.name: str = name
        self.commodity: Commodity = commodity
        self.stream_handler: StreamHandler = stream_handler
        self.time_data: TimeData = time_data
        self.last_update_time: datetime.datetime = self.time_data.global_end_date
        self.current_update_time: datetime.datetime = self.time_data.global_end_date
        self.input_stream_name: str = input_stream_name
        self.output_stream_name: str = output_stream_name
        self.input_to_output_conversion_factor: numbers_alias = input_to_output_conversion_factor
        self.state_data_container: ProductionProcessStateContainer = state_data_container
        self.process_step_name: str = process_step_name

        self.minimum_storage_level: numbers_alias = minimum_storage_level
        self.maximum_storage_level: numbers_alias | None = maximum_storage_level
        self.minimum_storage_level_at_start_time_of_production_branch: numbers_alias | None = (
            minimum_storage_level_at_start_time_of_production_branch
        )
        self.maximum_storage_level_at_start_time_of_production_branch: numbers_alias | None = (
            maximum_storage_level_at_start_time_of_production_branch
        )
        BaseStorage(
            stream_handler=stream_handler,
            input_to_output_conversion_factor=input_to_output_conversion_factor,
            commodity=commodity,
            process_step_name=process_step_name,
        )

    def determine_missing_input_mass(
        self,
        target_output_mass: numbers_alias,
    ) -> numbers_alias:
        """Determines the mass that is missing in the storage to reach
        the target mass.

        Args:
            target_output_mass (numbers_alias): Target storage level.

        Returns:
            numbers_alias: The mass that is missing to reach the target
                storage level.
        """
        state_data = self.state_data_container.get_validated_pre_or_post_production_state()
        current_storage_level = state_data.current_storage_level
        if self.minimum_storage_level_at_start_time_of_production_branch is None:
            raise Exception("minimum_storage_level_at_start_time_of_production_branch is not set")
        available_mass_in_storage = (
            current_storage_level - self.minimum_storage_level_at_start_time_of_production_branch
        )

        missing_mass = target_output_mass - available_mass_in_storage
        if missing_mass < 0:
            raise Exception("There should not be too much mass in the storage")
        return missing_mass

    def create_batch_dictionary(
        self,
        list_of_storage_date_ranges: list[datetimerange.DateTimeRange],
        list_of_input_stream_states: list[ContinuousStreamState | BatchStreamState],
        list_of_output_stream_states: list[ContinuousStreamState | BatchStreamState],
    ) -> dict[datetime.datetime, numbers_alias]:
        """Creates a dictionary that contains the dates of discrete mass transfer as keys.

        Args:
            list_of_storage_date_ranges (list[datetimerange.DateTimeRange]): The list of datetime ranges
                that considers all time events.
            list_of_input_stream_states (list[ContinuousStreamState  |  BatchStreamState]): List of stream
                states that add mass to the storage.
            list_of_output_stream_states (list[ContinuousStreamState  |  BatchStreamState]): List of stream
                states that remove mass to the storage.

        Returns:
            dict[datetime.datetime, numbers_alias]: A dictionary that contains the dates of discrete mass transfer as keys
        """
        # Positive values --> net input mass
        # Negative Values --> net output mass
        batch_dict: dict[datetime.datetime, numbers_alias] = {}
        for date_range in list_of_storage_date_ranges:
            start_time_of_date_range = date_range.start_datetime
            for input_stream_state in list_of_input_stream_states:
                if isinstance(input_stream_state, BatchStreamState):
                    if input_stream_state.end_time == start_time_of_date_range:
                        input_mass_input_commodity = input_stream_state.batch_mass_value
                        input_mass_output_commodity = self.convert_input_to_output_mass(
                            input_mass=input_mass_input_commodity
                        )
                        batch_dict[input_stream_state.end_time] = input_mass_output_commodity
            for output_stream_state in list_of_output_stream_states:
                if isinstance(output_stream_state, BatchStreamState):
                    if output_stream_state.start_time == start_time_of_date_range:
                        output_batch_mass = -output_stream_state.batch_mass_value
                        if output_stream_state.start_time in batch_dict:
                            output_batch_mass = output_batch_mass + batch_dict[output_stream_state.start_time]

                        batch_dict[output_stream_state.start_time] = output_batch_mass
        return batch_dict

    def create_a_list_of_datetime_ranges_from_list_of_stream_states(
        self,
        list_of_input_stream_states: list[ContinuousStreamState | BatchStreamState],
        list_of_output_stream_states: list[ContinuousStreamState | BatchStreamState],
        exclude_output_times_before_input_end_time: bool,
        exclude_output_times_before_input_start_time: bool,
        last_update_time_storage: datetime.datetime | None = None,
        order_from_end_to_start: bool = True,
    ) -> list[datetimerange.DateTimeRange]:
        """Returns a list of datetime range that considers all discrete changes to the mass flow
        of the storage.

        Args:
            list_of_input_stream_states (list[ContinuousStreamState  |  BatchStreamState]): List of
                stream states that add mass to the storage.
            list_of_output_stream_states (list[ContinuousStreamState  |  BatchStreamState]): List of
                all states that remove mass from the storage.
            exclude_output_times_before_input_end_time (bool): Excludes all output times
                that are earlier than the earliest input end time.
            exclude_output_times_before_input_start_time (bool):  Excludes all output times
                that are earlier than the earliest input start time.
            last_update_time_storage (datetime.datetime | None): The earliest date for which
                a storage level is determined. If None, uses self.time_data.get_storage_last_update_time().
            order_from_end_to_start (bool): Determines the order of the date ranges.

        Returns:
            list[datetimerange.DateTimeRange]: List of datetime range that considers all discrete changes to the mass flow
        of the storage.
        """
        all_input_start_times = []
        all_input_end_times = []

        all_output_start_times = []
        all_output_end_times = []
        for input_stream_state in list_of_input_stream_states:
            all_input_start_times.append(input_stream_state.start_time)
        for input_stream_state in list_of_input_stream_states:
            all_input_end_times.append(input_stream_state.end_time)
        for output_stream_state in list_of_output_stream_states:
            all_output_start_times.append(output_stream_state.start_time)
        for output_stream_state in list_of_output_stream_states:
            all_output_end_times.append(output_stream_state.end_time)
        updated_storage_time = self.time_data.get_storage_last_update_time()
        all_start_and_end_times_list = list(
            itertools.chain(
                all_input_start_times,
                all_input_end_times,
                all_output_start_times,
                all_output_end_times,
                [updated_storage_time],
            )
        )
        if exclude_output_times_before_input_end_time is True:
            first_input_stream_end_time = min(all_input_end_times)
            all_start_and_end_times_list = list(
                filter(
                    lambda datetime_in_list: check_if_date_1_is_before_or_at_date_2(
                        date_1=first_input_stream_end_time, date_2=datetime_in_list
                    ),
                    all_start_and_end_times_list,
                )
            )
        if exclude_output_times_before_input_start_time is True:
            first_input_stream_start_time = min(all_input_start_times)
            all_start_and_end_times_list = list(
                filter(
                    lambda datetime_in_list: check_if_date_1_is_before_or_at_date_2(
                        date_1=first_input_stream_start_time, date_2=datetime_in_list
                    ),
                    all_start_and_end_times_list,
                )
            )

        all_start_and_end_times_list = list(
            filter(
                lambda datetime_in_list: check_if_date_1_is_before_or_at_date_2(
                    date_1=datetime_in_list, date_2=updated_storage_time
                ),
                all_start_and_end_times_list,
            )
        )
        all_start_and_end_times_set = set(all_start_and_end_times_list)
        all_start_and_end_times_set = sorted(all_start_and_end_times_set, reverse=True)

        # Create set of datetime ranges
        last_date_time = None
        list_of_storage_date_ranges: list[datetimerange.DateTimeRange] = []
        for next_date_time in all_start_and_end_times_set:
            if last_date_time is not None:
                list_of_storage_date_ranges.append(
                    datetimerange.DateTimeRange(start_datetime=next_date_time, end_datetime=last_date_time)
                )
            last_date_time = next_date_time
        return list_of_storage_date_ranges

    def create_all_storage_production_plan_entry(
        self,
        exclude_output_times_before_input_end_time: bool,
        exclude_output_times_before_input_start_time: bool,
        back_calculation: bool,
    ):
        """Creates all storage entries for the current output stream request
        when all necessary states have been requested.

        Args:
            exclude_output_times_before_input_end_time (bool): Excludes all output times
                that are earlier than the earliest input end time.
            exclude_output_times_before_input_start_time (bool):  Excludes all output times
                that are earlier than the earliest input start time.
            back_calculation (bool): Determines if the Storage entries are created
                in temporal ascending or descending order.
        """
        # Determine all relevant time ranges for the storage entries

        post_or_validated_state_data = self.state_data_container.get_validated_production_state_data()

        output_stream_state = post_or_validated_state_data.current_output_stream_state
        input_stream_state = post_or_validated_state_data.validated_input_stream_list[-1]
        # list_of_input_stream_states = (
        #     post_or_validated_state_data.validated_input_stream_list
        # )
        list_of_storage_date_ranges = self.create_a_list_of_datetime_ranges_from_list_of_stream_states(
            list_of_input_stream_states=[input_stream_state],
            list_of_output_stream_states=[output_stream_state],
            exclude_output_times_before_input_end_time=exclude_output_times_before_input_end_time,
            exclude_output_times_before_input_start_time=exclude_output_times_before_input_start_time,
        )

        batch_dict = self.create_batch_dictionary(
            list_of_storage_date_ranges=list_of_storage_date_ranges,
            list_of_input_stream_states=[input_stream_state],
            list_of_output_stream_states=[output_stream_state],
        )

        output_stream = self.stream_handler.get_stream(stream_name=output_stream_state.name)
        input_stream = self.stream_handler.get_stream(stream_name=input_stream_state.name)

        # Determine Storage level
        # input_mass = input_stream.get_produced_amount(state=input_stream_state)
        # output_mass = output_stream.get_produced_amount(state=output_stream_state)

        initial_storage_level_at_end_time = post_or_validated_state_data.current_storage_level
        temporary_production_plan = self.state_data_container.get_temporary_production_plan()
        input_stream_date_range = datetimerange.DateTimeRange(
            start_datetime=input_stream_state.start_time,
            end_datetime=input_stream_state.end_time,
        )
        output_stream_state_date_range = datetimerange.DateTimeRange(
            start_datetime=output_stream_state.start_time,
            end_datetime=output_stream_state.end_time,
        )
        for storage_date_range in list_of_storage_date_ranges:
            start_time = storage_date_range.start_datetime
            end_time = storage_date_range.end_datetime
            duration = storage_date_range.timedelta

            if isinstance(input_stream, ContinuousStream):
                if input_stream_date_range.get_timedelta_second() == 0:
                    raise Exception("infinitesimal input stream is requested")
                assert isinstance(input_stream_state, ContinuousStreamState)
                continuous_input_mass_share_input_commodity = input_stream.get_mass_share_in_time_period(
                    stream_state=input_stream_state,
                    numerator_date_range=storage_date_range,
                )
                continuous_input_mass_share_output_commodity = self.convert_input_to_output_mass(
                    input_mass=continuous_input_mass_share_input_commodity,
                )

            else:
                continuous_input_mass_share_output_commodity = 0

            if isinstance(output_stream, ContinuousStream):
                assert isinstance(output_stream_state, ContinuousStreamState)
                continuous_output_mass_share = output_stream.get_mass_share_in_time_period(
                    stream_state=output_stream_state,
                    numerator_date_range=storage_date_range,
                )

            else:
                continuous_output_mass_share = 0

            if back_calculation is True:
                net_add = -(continuous_input_mass_share_output_commodity - continuous_output_mass_share)
            else:
                net_add = continuous_input_mass_share_output_commodity - continuous_output_mass_share
            new_storage_level_at_start = net_add + self.state_data_container.get_storage_level()

            storage_entry = StorageProductionPlanEntry(
                process_step_name=self.process_step_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                storage_level_at_end=self.state_data_container.get_storage_level(),
                storage_level_at_start=new_storage_level_at_start,
                commodity=self.commodity,
            )
            temporary_production_plan.add_storage_entry(
                process_step_name=self.process_step_name,
                storage_entry=storage_entry,
            )
            self.time_data.set_storage_last_update_time(updated_storage_datetime=start_time)
            self.state_data_container.update_storage_level(new_storage_level=new_storage_level_at_start)

            if start_time in batch_dict:
                if back_calculation is True:
                    net_batch_mass_add = -batch_dict[start_time]

                else:
                    net_batch_mass_add = batch_dict[start_time]

                # Subtract net mass due to backwards calculation
                new_storage_level_at_start_with_batch = (
                    +net_batch_mass_add + self.state_data_container.get_storage_level()
                )
                # if new_storage_level <0:
                #     new_storage_level= self.determine_total_input_mass_at_last_input_batch_mass(negative_storage_level=new_storage_level)

                infinite_storage_entry = StorageProductionPlanEntry(
                    process_step_name=self.process_step_name,
                    start_time=start_time,
                    end_time=start_time,
                    duration=datetime.timedelta(hours=0),
                    storage_level_at_end=self.state_data_container.get_storage_level(),
                    storage_level_at_start=new_storage_level_at_start_with_batch,
                    commodity=self.commodity,
                )
                temporary_production_plan.add_storage_entry(
                    process_step_name=self.process_step_name,
                    storage_entry=infinite_storage_entry,
                )

                self.state_data_container.update_storage_level(new_storage_level=new_storage_level_at_start_with_batch)

        self.state_data_container.update_temporary_production_plan(
            updated_temporary_production_plan=temporary_production_plan
        )
