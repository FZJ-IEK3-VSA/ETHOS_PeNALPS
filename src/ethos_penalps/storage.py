import datetime
import itertools
import numbers

import datetimerange
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
from ethos_penalps.utilities.general_functions import (
    check_if_date_1_is_before_date_2,
    check_if_date_1_is_before_or_at_date_2,
    format_timedelta,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class BaseStorage:
    """Provides basic functionality to track and update a storage level
    of a node based on input and output streams to that node.
    """

    def __init__(
        self,
        stream_handler: StreamHandler,
        input_to_output_conversion_factor: numbers.Number,
        commodity: Commodity,
        process_step_name: str,
        storage_level_at_start: numbers.Number = 0,
    ) -> None:
        self.stream_handler: StreamHandler = stream_handler
        self.input_to_output_conversion_factor: numbers.Number = (
            input_to_output_conversion_factor
        )
        self.commodity: Commodity = commodity
        self.process_step_name: str = process_step_name
        self.current_storage_level: numbers.Number = storage_level_at_start
        self.total_input: numbers.Number = 0
        self.total_output: numbers.Number = 0

    def create_storage_entries_from_start_to_end(
        self,
        list_of_input_stream_states: list[BaseStreamState],
        list_of_output_stream_states: list[BaseStreamState],
        last_storage_update_time: datetime.datetime,
    ) -> list[StorageProductionPlanEntry]:
        """Creates a list of StorageProductionPlanEntry from a list of StreamStates
        for the input and output. The streams are sorted from the ascending temporal order.

        Args:
            list_of_input_stream_states (list[BaseStreamState]): List of streams that
                add mass to the storage.
            list_of_output_stream_states (list[BaseStreamState]): List of streams
                that remove mass from the storage.
            last_storage_update_time (datetime.datetime): The first date for which a storage
                level should be determined.

        Returns:
            list[StorageProductionPlanEntry]: List of StorageProductionPlanEntry that
                describe the storage level.
        """
        list_of_storage_entries = []
        list_of_date_time_ranges = self.create_a_list_of_datetime_ranges_from_list_of_stream_states(
            list_of_input_stream_states=list_of_input_stream_states,
            list_of_output_stream_states=list_of_output_stream_states,
            exclude_output_times_before_input_end_time=False,
            exclude_output_times_before_input_start_time=False,
            last_update_time_storage=last_storage_update_time,
            order_from_end_to_start=False,
            # back_calculation=True,
        )

        for storage_date_time_range in list_of_date_time_ranges:
            storage_entry = self.create_storage_entry_from_start_to_end(
                list_of_input_stream_states=list_of_input_stream_states,
                list_of_output_stream_states=list_of_output_stream_states,
                storage_date_range=storage_date_time_range,
            )

            list_of_storage_entries.append(storage_entry)

        return list_of_storage_entries

    # def create_storage_entries_from_end_to_start(
    #     self,
    #     list_of_input_stream_states: list[BaseStreamState],
    #     list_of_output_stream_states: list[BaseStreamState],
    #     last_storage_update_time: datetime.datetime,
    #     storage_level_at_global_start: numbers.Number,
    # ) -> list[StorageProductionPlanEntry]:
    #     list_of_storage_entries = []
    #     list_of_date_time_ranges = self.create_a_list_of_datetime_ranges_from_list_of_stream_states(
    #         list_of_input_stream_states=list_of_input_stream_states,
    #         list_of_output_stream_states=list_of_output_stream_states,
    #         exclude_output_times_before_input_end_time=True,
    #         exclude_output_times_before_input_start_time=False,
    #         last_update_time_storage=last_storage_update_time,
    #         order_from_end_to_start=True
    #         # back_calculation=True,
    #     )
    #     total_net = self.determine_net_mass(
    #         list_of_input_stream_states=list_of_input_stream_states,
    #         list_of_output_stream_states=list_of_output_stream_states,
    #     )
    #     self.current_storage_level = -total_net + storage_level_at_global_start
    #     for storage_date_time_range in list_of_date_time_ranges:
    #         storage_entry = self.create_storage_entry_from_end_to_start(
    #             list_of_input_stream_states=list_of_input_stream_states,
    #             list_of_output_stream_states=list_of_output_stream_states,
    #             storage_date_range=storage_date_time_range,
    #         )
    #         list_of_storage_entries.append(storage_entry)

    #     return list_of_storage_entries

    def determine_net_mass(
        self,
        list_of_input_stream_states: list[ContinuousStreamState | BatchStreamState],
        list_of_output_stream_states: list[ContinuousStreamState | BatchStreamState],
    ) -> numbers.Number:
        """Returns the net mass of all input and output stream states.

        Args:
            list_of_input_stream_states (list[ContinuousStreamState  |  BatchStreamState]): List of
                stream states that add mass to the storage.
            list_of_output_stream_states (list[ContinuousStreamState  |  BatchStreamState]): List of
                all states that remove mass from the storage.

        Returns:
            numbers.Number: The mass that is added or removed from the storage in total. + mass is added
                ,- mass is removed

        """
        net_mass = 0
        for input_stream_state in list_of_input_stream_states:
            if isinstance(input_stream_state, ContinuousStreamState):
                net_mass = net_mass + input_stream_state.total_mass
            elif isinstance(input_stream_state, BatchStreamState):
                net_mass = net_mass + input_stream_state.batch_mass_value
        for output_stream_state in list_of_output_stream_states:
            if isinstance(output_stream_state, ContinuousStreamState):
                net_mass = net_mass - output_stream_state.total_mass
            elif isinstance(output_stream_state, BatchStreamState):
                net_mass = net_mass - output_stream_state.batch_mass_value
        return net_mass

    def create_a_list_of_datetime_ranges_from_list_of_stream_states(
        self,
        list_of_input_stream_states: list[ContinuousStreamState | BatchStreamState],
        list_of_output_stream_states: list[ContinuousStreamState | BatchStreamState],
        exclude_output_times_before_input_end_time: bool,
        exclude_output_times_before_input_start_time: bool,
        last_update_time_storage: datetime.datetime,
        order_from_end_to_start: bool,
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
            last_update_time_storage (datetime.datetime): The earliest date for which
                a storage level is determined.
            order_from_end_to_start (bool): Determines the order of the date ranges.

        Returns:
            list[datetimerange.DateTimeRange]: List of datetime range that considers all discrete changes to the mass flow
        of the storage.
        """
        all_continuous_times = []
        all_batch_times = []
        input_start_times = []
        input_end_times = []
        for input_stream_state in list_of_input_stream_states:
            if isinstance(input_stream_state, ContinuousStreamState):
                all_continuous_times.append(input_stream_state.start_time)
                all_continuous_times.append(input_stream_state.end_time)

            elif isinstance(input_stream_state, BatchStreamState):
                # Only mass relevant batch times are created
                # Output -> end time
                # all_batch_times.append(input_stream_state.start_time)
                all_batch_times.append(input_stream_state.end_time)
            input_start_times.append(input_stream_state.start_time)
            input_end_times.append(input_stream_state.end_time)
        for output_stream_state in list_of_output_stream_states:
            if isinstance(output_stream_state, ContinuousStreamState):
                all_continuous_times.append(output_stream_state.start_time)
                all_continuous_times.append(output_stream_state.end_time)
            elif isinstance(output_stream_state, BatchStreamState):
                all_batch_times.append(output_stream_state.start_time)
                # Only mass relevant batch times are created
                # Output -> start time
                # all_batch_times.append(output_stream_state.end_time)

        updated_storage_time = last_update_time_storage
        all_continuous_times.append(updated_storage_time)
        all_start_and_end_times_list = list(set(all_continuous_times))
        for current_batch_times in list(set(all_batch_times)):
            if current_batch_times in all_start_and_end_times_list:
                all_start_and_end_times_list.append(current_batch_times)
            else:
                # Add Batch times two times so that a 0 second datetime range is created
                all_start_and_end_times_list.append(current_batch_times)
                all_start_and_end_times_list.append(current_batch_times)

        # Sort from last to first date
        if order_from_end_to_start is True:
            all_start_and_end_times_list.sort(reverse=True)
        else:
            all_start_and_end_times_list.sort(reverse=False)

        if exclude_output_times_before_input_end_time is True:
            if input_end_times:
                first_input_stream_end_time = min(input_end_times)
                all_start_and_end_times_list = list(
                    filter(
                        lambda datetime_in_list: check_if_date_1_is_before_or_at_date_2(
                            date_1=first_input_stream_end_time, date_2=datetime_in_list
                        ),
                        all_start_and_end_times_list,
                    )
                )
        if exclude_output_times_before_input_start_time is True:
            first_input_stream_start_time = min(input_start_times)
            all_start_and_end_times_list = list(
                filter(
                    lambda datetime_in_list: check_if_date_1_is_before_or_at_date_2(
                        date_1=first_input_stream_start_time, date_2=datetime_in_list
                    ),
                    all_start_and_end_times_list,
                )
            )

        # Create set of datetime ranges
        last_date_time = None
        list_of_storage_date_ranges: list[datetimerange.DateTimeRange] = []

        for next_date_time in all_start_and_end_times_list:
            if last_date_time is not None:
                if order_from_end_to_start is True:
                    current_datetime_range = datetimerange.DateTimeRange(
                        start_datetime=next_date_time,
                        end_datetime=last_date_time,
                    )
                else:
                    current_datetime_range = datetimerange.DateTimeRange(
                        start_datetime=last_date_time,
                        end_datetime=next_date_time,
                    )

                list_of_storage_date_ranges.append(current_datetime_range)
            last_date_time = next_date_time
        return list_of_storage_date_ranges

    def create_storage_entry_from_start_to_end(
        self,
        list_of_input_stream_states: list[ContinuousStreamState | BatchStreamState],
        list_of_output_stream_states: list[ContinuousStreamState | BatchStreamState],
        storage_date_range: datetimerange.DateTimeRange,
    ) -> StorageProductionPlanEntry:
        """Creates a single StorageProductionPlanEntry from a list of input and output streams
        for a given storage date range.

        Args:
            list_of_input_stream_states (list[ContinuousStreamState  |  BatchStreamState]): List of
                stream states that add mass to the storage.
            list_of_output_stream_states (list[ContinuousStreamState  |  BatchStreamState]): List of
                all states that remove mass from the storage.
            storage_date_range (datetimerange.DateTimeRange): The time range of the output StorageProductionPlanEntry.

        Returns:
            StorageProductionPlanEntry: Describes the storage level in the storage_date_range.
        """
        net_mass = self.determine_net_mass_in_date_range(
            list_of_input_stream_states=list_of_input_stream_states,
            list_of_output_stream_states=list_of_output_stream_states,
            storage_date_range=storage_date_range,
            from_start_to_end=True,
        )
        storage_level_at_start = self.current_storage_level
        new_storage_level_at_end = net_mass + self.current_storage_level
        storage_entry = StorageProductionPlanEntry(
            process_step_name=self.process_step_name,
            start_time=storage_date_range.start_datetime,
            end_time=storage_date_range.end_datetime,
            duration=storage_date_range,
            storage_level_at_end=new_storage_level_at_end,
            storage_level_at_start=storage_level_at_start,
            commodity=self.commodity,
        )
        self.current_storage_level = new_storage_level_at_end
        return storage_entry

    # def create_storage_entry_from_end_to_start(
    #     self,
    #     list_of_input_stream_states: list[ContinuousStreamState | BatchStreamState],
    #     list_of_output_stream_states: list[ContinuousStreamState | BatchStreamState],
    #     storage_date_range: datetimerange.DateTimeRange,
    # ) -> StorageProductionPlanEntry:
    #     net_mass = self.determine_net_mass_in_date_range(
    #         list_of_input_stream_states=list_of_input_stream_states,
    #         list_of_output_stream_states=list_of_output_stream_states,
    #         storage_date_range=storage_date_range,
    #         from_start_to_end=False,
    #     )
    #     storage_level_at_end_of_period = self.current_storage_level
    #     storage_level_at_start = net_mass + self.current_storage_level

    #     storage_entry = StorageProductionPlanEntry(
    #         process_step_name=self.process_step_name,
    #         start_time=storage_date_range.start_datetime,
    #         end_time=storage_date_range.end_datetime,
    #         duration=storage_date_range,
    #         storage_level_at_end=storage_level_at_end_of_period,
    #         storage_level_at_start=storage_level_at_start,
    #         commodity=self.commodity,
    #     )
    #     self.current_storage_level = storage_level_at_start
    #     return storage_entry

    def determine_net_mass_in_date_range(
        self,
        list_of_input_stream_states: list[ContinuousStreamState | BatchStreamState],
        list_of_output_stream_states: list[ContinuousStreamState | BatchStreamState],
        storage_date_range: datetimerange.DateTimeRange,
        from_start_to_end: bool,
    ) -> numbers.Number:
        """Determines the net mass in the date range.

        Args:
            list_of_input_stream_states (list[ContinuousStreamState  |  BatchStreamState]): List of
                stream states that add mass to the storage.
            list_of_output_stream_states (list[ContinuousStreamState  |  BatchStreamState]): List of
                all states that remove mass from the storage.
            storage_date_range (datetimerange.DateTimeRange): Defines the date range for the net mass
                analysis.
            from_start_to_end (bool): Determines the direction of analysis.


        Returns:
            numbers.Number: Net mass in the date range.
        """
        continuous_input_mass_share_output_commodity = 0
        batch_input_mass_share_output_commodity = 0
        for input_stream_state in list_of_input_stream_states:
            input_stream = self.stream_handler.get_stream(
                stream_name=input_stream_state.name
            )
            if isinstance(input_stream, ContinuousStream):
                if input_stream_state.date_time_range.get_timedelta_second() == 0:
                    raise Exception(
                        "infinitesimal continuous input stream is requested"
                    )
                continuous_input_mass_share_input_commodity = (
                    input_stream.get_mass_share_in_time_period(
                        numerator_date_range=storage_date_range,
                        stream_state=input_stream_state,
                    )
                )

                continuous_input_mass_share_output_commodity = (
                    continuous_input_mass_share_output_commodity
                    + (
                        self.convert_input_to_output_mass(
                            input_mass=continuous_input_mass_share_input_commodity
                        )
                    )
                )
            elif isinstance(input_stream, BatchStream):
                batch_input_mass_share_input_commodity = (
                    input_stream.get_mass_share_in_time_period(
                        stream_state=input_stream_state,
                        is_input_stream=True,
                        target_date_range=storage_date_range,
                    )
                )
                batch_input_mass_share_output_commodity = (
                    batch_input_mass_share_output_commodity
                    + self.convert_input_to_output_mass(
                        input_mass=batch_input_mass_share_input_commodity
                    )
                )
            else:
                raise Exception("Unexpected datatype")
        self.total_input = (
            self.total_input
            + batch_input_mass_share_output_commodity
            + continuous_input_mass_share_output_commodity
        )
        continuous_output_mass_share = 0
        batch_output_mass_output_commodity = 0
        for output_stream_state in list_of_output_stream_states:
            output_stream = self.stream_handler.get_stream(
                stream_name=output_stream_state.name
            )
            if isinstance(output_stream, ContinuousStream):
                continuous_output_stream_mass_share = (
                    output_stream.get_mass_share_in_time_period(
                        numerator_date_range=storage_date_range,
                        stream_state=output_stream_state,
                    )
                )
                continuous_output_mass_share = (
                    continuous_output_mass_share + continuous_output_stream_mass_share
                )
            elif isinstance(output_stream, BatchStream):
                batch_output_mass_output_commodity = (
                    batch_output_mass_output_commodity
                    + output_stream.get_mass_share_in_time_period(
                        stream_state=output_stream_state,
                        is_input_stream=False,
                        target_date_range=storage_date_range,
                    )
                )

            else:
                raise Exception("Unexpected datatype")
        if from_start_to_end is True:
            net_add = (
                batch_input_mass_share_output_commodity
                + continuous_input_mass_share_output_commodity
                - continuous_output_mass_share
                - batch_output_mass_output_commodity
            )
        else:
            net_add = (
                -batch_input_mass_share_output_commodity
                - continuous_input_mass_share_output_commodity
                + continuous_output_mass_share
                + batch_output_mass_output_commodity
            )
        self.total_output = (
            self.total_output
            + continuous_output_mass_share
            + batch_output_mass_output_commodity
        )
        return net_add

    def convert_output_to_input_mass(
        self, output_mass: numbers.Number
    ) -> numbers.Number:
        input_mass = output_mass / self.input_to_output_conversion_factor
        return input_mass

    def convert_input_to_output_mass(
        self, input_mass: numbers.Number
    ) -> numbers.Number:
        output_mass = input_mass * self.input_to_output_conversion_factor
        return output_mass

    # def determine_maximum_date_range(
    #     self,
    #     list_of_input_stream_states: list[ContinuousStreamState | BatchStreamState],
    #     list_of_output_stream_state: list[ContinuousStreamState | BatchStreamState],
    # ) -> datetimerange.DateTimeRange:
    #     net_mass = 0
    #     list_of_all_stream_states = []
    #     list_of_all_stream_states.extend(list_of_input_stream_states)
    #     list_of_all_stream_states.extend(list_of_output_stream_state)
    #     stream_data_frame = pandas.DataFrame(data=list_of_all_stream_states)
    #     first_start_time = stream_data_frame.loc["start_time", :].min()
    #     last_end_time = stream_data_frame.loc["end_time", :].max()
    #     datetime_range = datetimerange.DateTimeRange(
    #         start_datetime=first_start_time, end_datetime=last_end_time
    #     )
    #     return datetime_range


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
        input_to_output_conversion_factor: numbers.Number,
        state_data_container: ProductionProcessStateContainer,
        process_step_name: str,
        minimum_storage_level: numbers.Number = 0,
        maximum_storage_level: numbers.Number | None = None,
        minimum_storage_level_at_start_time_of_production_branch: (
            numbers.Number | None
        ) = None,
        maximum_storage_level_at_start_time_of_production_branch: (
            numbers.Number | None
        ) = None,
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
            input_to_output_conversion_factor (numbers.Number): The conversion factor
                that converts input mass into output mass.
            state_data_container (ProductionProcessStateContainer): Contains all
                other simulation data of the process step besides the time data.
            process_step_name (str): Name of the ProcessStep that holds this storage.
            minimum_storage_level (numbers.Number, optional): The minimum storage level
                of the storage. Is currently not used. Defaults to 0.
            maximum_storage_level (numbers.Number | None, optional): The maximum allowed storage level
                is currently not used. Defaults to None.
            minimum_storage_level_at_start_time_of_production_branch (numbers.Number  |  None, optional):
                The minimum storage level at the start of a new request for an output stream. Defaults to None.
            maximum_storage_level_at_start_time_of_production_branch (numbers.Number  |  None, optional): The maximum storage level at the start of
                a new request for an output stream. Defaults to None.
        """

        if not isinstance(input_stream_name, str):
            raise Exception(
                "A name of typ string should be supplied for process step identification"
            )

        if not isinstance(output_stream_name, str):
            raise Exception(
                "A name of typ string should be supplied for process step identification"
            )

        self.name: str = name
        self.commodity: Commodity = commodity
        self.stream_handler: StreamHandler = stream_handler
        self.time_data: TimeData = time_data
        self.last_update_time: datetime.datetime = self.time_data.global_end_date
        self.current_update_time: datetime.datetime = self.time_data.global_end_date
        self.input_stream_name: str = input_stream_name
        self.output_stream_name: str = output_stream_name
        self.input_to_output_conversion_factor: numbers.Number = (
            input_to_output_conversion_factor
        )
        self.state_data_container: ProductionProcessStateContainer = (
            state_data_container
        )
        self.process_step_name: str = process_step_name

        self.minimum_storage_level: numbers.Number = minimum_storage_level
        self.maximum_storage_level: numbers.Number | None = maximum_storage_level
        self.minimum_storage_level_at_start_time_of_production_branch: (
            numbers.Number | None
        ) = minimum_storage_level_at_start_time_of_production_branch
        self.maximum_storage_level_at_start_time_of_production_branch: (
            numbers.Number | None
        ) = maximum_storage_level_at_start_time_of_production_branch

    def determine_missing_input_mass(
        self,
        target_output_mass: numbers.Number,
    ) -> numbers.Number:
        """Determines the mass that is missing in the storage to reach
        the target mass.

        Args:
            target_output_mass (numbers.Number): Target storage level.

        Returns:
            numbers.Number: The mass that is missing to reach the target
                storage level.
        """
        state_data = (
            self.state_data_container.get_validated_pre_or_post_production_state()
        )
        current_storage_level = state_data.current_storage_level
        available_mass_in_storage = (
            current_storage_level
            - self.minimum_storage_level_at_start_time_of_production_branch
        )

        missing_mass = target_output_mass - available_mass_in_storage
        if missing_mass < 0:
            raise Exception("There should not be too much mass in the storage")
        return missing_mass

    def convert_output_to_input_mass(
        self, output_mass: numbers.Number
    ) -> numbers.Number:
        """Converts the output to input mass.

        Args:
            output_mass (numbers.Number): Mass to be converted.

        Returns:
            numbers.Number: Converted mass.
        """
        input_mass = output_mass / self.input_to_output_conversion_factor
        return input_mass

    def convert_input_to_output_mass(
        self, input_mass: numbers.Number
    ) -> numbers.Number:
        """Converts input to output mass.

        Args:
            input_mass (numbers.Number): Mass to be converted.

        Returns:
            numbers.Number: Converted mass.
        """
        output_mass = input_mass * self.input_to_output_conversion_factor
        return output_mass

    def create_batch_dictionary(
        self,
        list_of_storage_date_ranges: list[datetimerange.DateTimeRange],
        list_of_input_stream_states: list[ContinuousStreamState | BatchStreamState],
        list_of_output_stream_states: list[ContinuousStreamState | BatchStreamState],
    ) -> dict[datetime.datetime, numbers.Number]:
        """Creates a dictionary that contains the dates of discrete mass transfer as keys.

        Args:
            list_of_storage_date_ranges (list[datetimerange.DateTimeRange]): The list of datetime ranges
                that considers all time events.
            list_of_input_stream_states (list[ContinuousStreamState  |  BatchStreamState]): List of stream
                states that add mass to the storage.
            list_of_output_stream_states (list[ContinuousStreamState  |  BatchStreamState]): List of stream
                states that remove mass to the storage.

        Returns:
            dict[datetime.datetime, numbers.Number]: A dictionary that contains the dates of discrete mass transfer as keys
        """
        # Positive values --> net input mass
        # Negative Values --> net output mass
        batch_dict: dict[datetime.datetime, numbers.Number] = {}
        for date_range in list_of_storage_date_ranges:
            start_time_of_date_range = date_range.start_datetime
            for input_stream_state in list_of_input_stream_states:
                if isinstance(input_stream_state, BatchStreamState):
                    if input_stream_state.end_time == start_time_of_date_range:
                        input_mass_input_commodity = input_stream_state.batch_mass_value
                        input_mass_output_commodity = self.convert_input_to_output_mass(
                            input_mass=input_mass_input_commodity
                        )
                        batch_dict[input_stream_state.end_time] = (
                            input_mass_output_commodity
                        )
            for output_stream_state in list_of_output_stream_states:
                if isinstance(output_stream_state, BatchStreamState):
                    if output_stream_state.start_time == start_time_of_date_range:
                        output_batch_mass = -output_stream_state.batch_mass_value
                        if output_stream_state.start_time in batch_dict:
                            output_batch_mass = (
                                output_batch_mass
                                + batch_dict[output_stream_state.start_time]
                            )

                        batch_dict[output_stream_state.start_time] = output_batch_mass
        return batch_dict

    def create_a_list_of_datetime_ranges_from_list_of_stream_states(
        self,
        list_of_input_stream_states: list[ContinuousStreamState | BatchStreamState],
        list_of_output_stream_states: list[ContinuousStreamState | BatchStreamState],
        exclude_output_times_before_input_end_time: bool,
        exclude_output_times_before_input_start_time: bool,
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
            last_update_time_storage (datetime.datetime): The earliest date for which
                a storage level is determined.
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
                    datetimerange.DateTimeRange(
                        start_datetime=next_date_time, end_datetime=last_date_time
                    )
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

        post_or_validated_state_data = (
            self.state_data_container.get_validated_production_state_data()
        )

        output_stream_state = post_or_validated_state_data.current_output_stream_state
        input_stream_state = post_or_validated_state_data.validated_input_stream_list[
            -1
        ]
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

        output_stream = self.stream_handler.get_stream(
            stream_name=output_stream_state.name
        )
        input_stream = self.stream_handler.get_stream(
            stream_name=input_stream_state.name
        )

        # Determine Storage level
        # input_mass = input_stream.get_produced_amount(state=input_stream_state)
        # output_mass = output_stream.get_produced_amount(state=output_stream_state)

        initial_storage_level_at_end_time = (
            post_or_validated_state_data.current_storage_level
        )
        temporary_production_plan = (
            self.state_data_container.get_temporary_production_plan()
        )
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
                # continuous_input_stream_time_share = (
                #     input_stream.get_time_frame_overlap_share(
                #         numerator_date_range=storage_date_range,
                #         denominator_date_range=input_stream_date_range,
                #     )
                # )
                # continuous_input_mass_share_input_commodity = (
                #     input_mass * continuous_input_stream_time_share
                # )
                continuous_input_mass_share_input_commodity = (
                    input_stream.get_mass_share_in_time_period(
                        stream_state=input_stream_state,
                        numerator_date_range=storage_date_range,
                    )
                )
                continuous_input_mass_share_output_commodity = (
                    self.convert_input_to_output_mass(
                        input_mass=continuous_input_mass_share_input_commodity,
                    )
                )

            else:
                continuous_input_mass_share_output_commodity = 0

            if isinstance(output_stream, ContinuousStream):
                # continuous_output_stream_time_share = (
                #     output_stream.get_time_frame_overlap_share(
                #         numerator_date_range=storage_date_range,
                #         denominator_date_range=output_stream_state_date_range,
                #     )
                # )
                # continuous_output_mass_share = (
                #     output_mass * continuous_output_stream_time_share
                # )

                continuous_output_mass_share = (
                    output_stream.get_mass_share_in_time_period(
                        stream_state=output_stream_state,
                        numerator_date_range=storage_date_range,
                    )
                )

            else:
                continuous_output_mass_share = 0

            if back_calculation is True:
                net_add = -(
                    continuous_input_mass_share_output_commodity
                    - continuous_output_mass_share
                )
            else:
                net_add = (
                    continuous_input_mass_share_output_commodity
                    - continuous_output_mass_share
                )
            new_storage_level_at_start = (
                net_add + self.state_data_container.get_storage_level()
            )

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
            self.time_data.set_storage_last_update_time(
                updated_storage_datetime=start_time
            )
            self.state_data_container.update_storage_level(
                new_storage_level=new_storage_level_at_start
            )

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

                self.state_data_container.update_storage_level(
                    new_storage_level=new_storage_level_at_start_with_batch
                )

        self.state_data_container.update_temporary_production_plan(
            updated_temporary_production_plan=temporary_production_plan
        )

    # def determine_total_input_mass_at_last_input_batch_mass(self,negative_storage_level:float)->float:
    #     input_stream=self.stream_handler.get_stream(stream_name=self.input_stream_name)
    #     if isinstance(input_stream,BatchStream):
    #         max_input_batch_mass=input_stream.static_data.maximum_batch_mass_value
    #         if max_input_batch_mass is None:
    #             raise Exception("Maximum output stream mass has not been set for stream: "+str(max_input_batch_mass.name))
    #         state_data=self.state_data_container.get_validated_pre_or_post_production_state()

    #         output_stream=self.stream_handler.get_stream(stream_name=self.output_stream_name)
    #         required_output_stream_mass=output_stream.get_produced_amount(state=state_data.current_output_stream_state)
    #         required_output_mass=self.minimum_storage_level_at_start_time_of_production_branch-negative_storage_level
    #         number_of_required_input_batches=required_output_mass/max_input_batch_mass
    #         rounded_number_of_required_input_batches=math.ceil(number_of_required_input_batches)
    #         total_input_mass=rounded_number_of_required_input_batches*max_input_batch_mass
    #         new_storage_level=total_input_mass+state_data.current_storage_level
    #         return new_storage_level
    #     else:
    #         raise Exception("Can not determine last storage level based on ")

    # def create_storage_entries_without_inputstream_and_consuming_output(
    #     self,
    # ):
    #     # Determine all relevant time ranges for the storage entries

    #     pre_production_state_data = (
    #         self.state_data_container.get_pre_production_state_data()
    #     )

    #     output_stream_state = pre_production_state_data.current_output_stream_state
    #     exclude_output_times_before_input_end_time=False
    #     exclude_output_times_before_input_start_time=False
    #     list_of_storage_date_ranges = self.create_a_list_of_datetime_ranges_from_list_of_stream_states(
    #         list_of_input_stream_states=[],
    #         list_of_output_stream_states=[output_stream_state],
    #         exclude_output_times_before_input_end_time=exclude_output_times_before_input_end_time,
    #         exclude_output_times_before_input_start_time=exclude_output_times_before_input_start_time,
    #     )
    #     batch_dict = self.create_batch_dictionary(
    #         list_of_storage_date_ranges=list_of_storage_date_ranges,
    #         list_of_input_stream_states=[],
    #         list_of_output_stream_states=[output_stream_state],
    #     )

    #     output_stream = self.stream_handler.get_stream(
    #         stream_name=output_stream_state.name
    #     )

    #     # Determine Storage level
    #     output_mass = output_stream.get_produced_amount(state=output_stream_state)

    #     storage_level_at_end_time = pre_production_state_data.current_storage_level
    #     temporary_production_plan = (
    #         pre_production_state_data.temporary_production_plan
    #     )

    #     output_stream_state_date_range = datetimerange.DateTimeRange(
    #         start_datetime=output_stream_state.start_time,
    #         end_datetime=output_stream_state.end_time,
    #     )
    #     for storage_date_range in list_of_storage_date_ranges:
    #         start_time = storage_date_range.start_datetime
    #         end_time = storage_date_range.end_datetime
    #         duration = storage_date_range.timedelta

    #         if isinstance(output_stream, ContinuousStream):
    #             continuous_output_stream_time_share = (
    #                 output_stream.get_time_frame_overlap_share(
    #                     numerator_date_range=storage_date_range,
    #                     denominator_date_range=output_stream_state_date_range,
    #                 )
    #             )
    #             continuous_output_mass_share = (
    #                 output_mass * continuous_output_stream_time_share
    #             )
    #         else:
    #             continuous_output_mass_share = 0

    #         new_storage_level = (
    #             - continuous_output_mass_share                + storage_level_at_end_time
    #         )

    #         storage_entry = StorageProductionPlanEntry(
    #             process_step_name=self.process_step_name,
    #             start_time=start_time,
    #             end_time=end_time,
    #             duration=duration,
    #             storage_level_at_end=storage_level_at_end_time,
    #             storage_level_at_start=new_storage_level,
    #             commodity=self.commodity,
    #         )
    #         temporary_production_plan.add_storage_entry(
    #             process_step_name=self.process_step_name,
    #             storage_entry=storage_entry,
    #         )
    #         self.time_data.set_storage_last_update_time(
    #             updated_storage_datetime=start_time
    #         )
    #         if start_time in batch_dict:
    #             net_batch_mass_add = batch_dict[start_time]
    #             storage_level_after_continuous_entry = new_storage_level
    #             new_storage_level = (
    #                 +net_batch_mass_add + storage_level_after_continuous_entry
    #             )
    #             infinite_storage_entry = StorageProductionPlanEntry(
    #                 process_step_name=self.process_step_name,
    #                 start_time=start_time,
    #                 end_time=start_time,
    #                 duration=datetime.timedelta(hours=0),
    #                 storage_level_at_end=storage_level_after_continuous_entry,
    #                 storage_level_at_start=new_storage_level,
    #                 commodity=self.commodity,
    #             )
    #             temporary_production_plan.add_storage_entry(
    #                 process_step_name=self.process_step_name,
    #                 storage_entry=infinite_storage_entry,
    #             )
    #         storage_level_at_end_time = new_storage_level
    #     self.state_data_container.update_temporary_production_plan(
    #         updated_temporary_production_plan=temporary_production_plan
    #     )

    #     self.state_data_container.update_storage_level(
    #         new_storage_level=storage_level_at_end_time
    #     )
