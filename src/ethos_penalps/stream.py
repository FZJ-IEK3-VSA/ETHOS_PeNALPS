import datetime
import json
import logging
import numbers
import os
from abc import ABC
from dataclasses import dataclass, field
from typing import Union

import datetimerange
import pandas as pd
from dataclasses_json import DataClassJsonMixin, config, dataclass_json

from ethos_penalps.data_classes import (
    Commodity,
    LoadType,
    ProcessChainIdentifier,
    ProcessStepProductionPlanEntry,
    StreamLoadEnergyData,
)
from ethos_penalps.utilities.exceptions_and_warnings import UnexpectedDataType
from ethos_penalps.utilities.general_functions import (
    check_if_date_1_is_before_date_2,
    check_if_date_1_is_before_or_at_date_2,
)
from ethos_penalps.utilities.json_coding_functions import (
    json_datetime_deserialization_function,
    json_datetime_range_deserialization_function,
    json_datetime_range_serialization_function,
    json_datetime_serialization_function,
    json_pint_unit_deserialization_function,
    json_pint_unit_serialization_function,
    json_timedelta_deserialization_function,
    json_timedelta_serialization_function,
)
from ethos_penalps.utilities.units import Units


@dataclass(kw_only=True, frozen=True)
class BaseStreamState(DataClassJsonMixin):
    """A StreamState represents a discrete activity of the stream."""

    name: str
    """Name and Identifier of a StreamState.
    """
    start_time: datetime.datetime = field(
        metadata=config(
            encoder=json_datetime_serialization_function,
            decoder=json_datetime_deserialization_function,
        )
    )
    """Start time of the discrete activity.
    """
    end_time: datetime.datetime = field(
        metadata=config(
            encoder=json_datetime_serialization_function,
            decoder=json_datetime_deserialization_function,
        )
    )
    """End time of the discrete activity.
    """
    date_time_range: datetimerange.DateTimeRange = field(
        metadata=config(
            encoder=json_datetime_range_serialization_function,
            decoder=json_datetime_range_deserialization_function,
        )
    )
    """DateTimeRange of the discrete activity.
    """


# @dataclass(kw_only=True)
# class BaseStream:
#     state: BatchStreamState
@dataclass(kw_only=True)
class StreamStaticData(DataClassJsonMixin):
    """Base class of the static data of a stream
    that does not change during the simulation.
    """

    start_process_step_name: str
    end_process_step_name: str
    commodity: Commodity
    mass_unit: str = Units.mass_unit.__str__()
    name_to_display: str | None = None


@dataclass
class StreamEnergyData(DataClassJsonMixin):
    """Contains the data that is required to determine
    a LoadProfileEntry from a ProcessStateEntry for each LoadType.
    """

    stream_name: str
    load_dict: dict[str, LoadType] = field(default_factory=dict)
    """This dictionary contains all LoadTypes that are consumed by the stream.
    The key is the unique id of the LoadType.
    """
    dict_stream_load_energy_data: dict[str, StreamLoadEnergyData] = field(
        default_factory=dict
    )
    """Dictionary that has LoadType uuid as a key and the StreamLoadEnergyData
    to calculate the LoadProfileEntry for the respective LoadType.
    """

    def add_stream_load_energy_data(
        self, stream_load_energy_data: StreamLoadEnergyData
    ):
        """Adds the StreamLoadEnergyData for a specific LoadType.

        Args:
            stream_load_energy_data (StreamLoadEnergyData): StreamLoadEnergyData for a specific LoadType.
        """
        self.load_dict[stream_load_energy_data.load_type.uuid] = (
            stream_load_energy_data.load_type
        )
        self.dict_stream_load_energy_data[stream_load_energy_data.load_type.uuid] = (
            stream_load_energy_data
        )


@dataclass(kw_only=True)
class BatchStreamStaticData(StreamStaticData):
    """Contains the data of the BatchStream that does not change
    during the simulation.
    """

    delay: datetime.timedelta = field(
        metadata=config(
            encoder=json_timedelta_serialization_function,
            decoder=json_timedelta_deserialization_function,
            mm_field=datetime.timedelta,
        )
    )
    """Determines the time between start time and end time
    of the stream. Must be greater than zero.
    """
    minimum_batch_mass_value: numbers.Number = field(
        default=0, metadata=config(mm_field=numbers.Number)
    )
    """Determines the minimum batch mass that must be transferred
    by the batch stream.
    """
    maximum_batch_mass_value: numbers.Number = field(
        default=float("inf"),
        metadata=config(mm_field=numbers.Number),
    )
    """Defies the stream type. Must not be changed.
    """
    stream_type: str = "BatchStream"


@dataclass(frozen=True, slots=True)
class BatchStreamState(BaseStreamState):
    """A StreamState represents a discrete activity of the BatchStream."""

    batch_mass_value: numbers.Number = field(metadata=config(mm_field=numbers.Number))


@dataclass(frozen=True, slots=True)
class BatchStreamProductionPlanEntry(DataClassJsonMixin):
    """Simulation Result for a discrete time span of the BatchStream."""

    name: str
    commodity: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    duration: datetime.timedelta = field(metadata=config(mm_field=datetime.timedelta))
    delay: datetime.timedelta = field(metadata=config(mm_field=datetime.timedelta))
    batch_mass_value: numbers.Number = field(metadata=config(mm_field=numbers.Number))
    batch_mass_unit: str
    minimum_batch_mass_value: numbers.Number = field(
        metadata=config(mm_field=numbers.Number)
    )
    maximum_batch_mass_value: numbers.Number = field(
        metadata=config(mm_field=numbers.Number)
    )
    stream_type: str
    name_to_display: str | None


@dataclass
class BatchStream(DataClassJsonMixin):
    """Batch streams represent streams which transfer mass in a discrete manner.
    All mass is removed from the start node at the start time and all mass is added
    to the target node at the end time. Attention should be paid to the compatibility
    of the input and output states of ProcessStates of the connected Process Steps.
    These must be compatible to BatchStreams.
    """

    static_data: BatchStreamStaticData

    stream_type = "BatchStream"

    def __post_init__(self):
        self.name = (
            self.static_data.start_process_step_name
            + "_"
            + self.static_data.end_process_step_name
            + "_"
            + self.static_data.commodity.name
        )
        self.stream_energy_data: StreamEnergyData = StreamEnergyData(
            stream_name=self.name
        )

    def create_stream_energy_data(
        self,
        specific_energy_demand: numbers.Number,
        load_type: LoadType,
        mass_unit: str = Units.mass_unit.__str__(),
        energy_unit: str = Units.energy_unit.__str__(),
    ):
        """Creates the data that is required to determine the energy demand of a
        Stream for a specific LoadType.

        Args:
            specific_energy_demand (numbers.Number): Value for the mass specific energy
                demand.
            load_type (LoadType): LoadType representing the energy type that is consumed
                by the Stream.
            mass_unit (str, optional): Mass unit in the denominator of the specific
                energy demand. Defaults to Units.mass_unit.__str__().
            energy_unit (str, optional): Energy unit in the numerator
                of the specific energy demand. Defaults to Units.energy_unit.__str__().
        """
        stream_load_energy_data = StreamLoadEnergyData(
            stream_name=self.name,
            specific_energy_demand=specific_energy_demand,
            load_type=load_type,
            mass_unit=mass_unit,
            energy_unit=energy_unit,
        )
        self.stream_energy_data.add_stream_load_energy_data(
            stream_load_energy_data=stream_load_energy_data
        )

    def create_production_plan_entry(
        self, state: BatchStreamState
    ) -> BatchStreamProductionPlanEntry:
        """Creates the ResultProductionPlanEntry

        Args:
            state (BatchStreamState): Discrete Simulation State
                of the stream with reduced information.

        Returns:
            BatchStreamProductionPlanEntry: SimulationResults
        """
        new_production_plan_entry = BatchStreamProductionPlanEntry(
            name=self.name,
            commodity=self.static_data.commodity.name,
            start_time=state.start_time,
            end_time=state.end_time,
            duration=state.end_time - state.start_time,
            delay=self.static_data.delay,
            batch_mass_value=state.batch_mass_value,
            batch_mass_unit=self.static_data.mass_unit,
            minimum_batch_mass_value=self.static_data.minimum_batch_mass_value,
            maximum_batch_mass_value=self.static_data.maximum_batch_mass_value,
            stream_type="BatchStream",
            name_to_display=self.static_data.name_to_display,
        )
        return new_production_plan_entry

    def get_produced_amount(self, state: BatchStreamState) -> numbers.Number:
        """Returns the produced mass of the BatchStreamState.

        Args:
            state (BatchStreamState): BatchStreamState to be analyzed.

        Returns:
            numbers.Number: Mass of the BatchStreamState.
        """
        if not isinstance(state, BatchStreamState):
            raise UnexpectedDataType(
                current_data_type=state, expected_data_type=BatchStreamState
            )
        produced_amount = state.batch_mass_value
        return produced_amount

    def get_time_frame_overlap_share(
        self,
        stream_state: BatchStreamState,
        is_input_stream: bool,
        target_date_range: datetimerange.DateTimeRange,
    ) -> float:
        """Determines the time overlap of the target_date_range and
        the stream state. Returns a value between 0 and 1.

        Args:
            stream_state (BatchStreamState): Stream state that is analyzed
                for the temporal overlap.
            is_input_stream (bool): If set to true the mass transfer is analyzed
                for the start node.
            target_date_range (datetimerange.DateTimeRange): Date range that
                is analyzed for their mass transfer.

        Returns:
            (float) : Share of the temporal overlap target date range and the
             stream state.
        """
        if is_input_stream is True:
            if stream_state.end_time in target_date_range:
                if stream_state.end_time == target_date_range.end_datetime:
                    overlap_share = 0
                else:
                    overlap_share = 1

            else:
                overlap_share = 0
        elif is_input_stream is False:
            if stream_state.start_time in target_date_range:
                # In order to prevent double allocation to two date ranges, it is allocated to the start time shift
                if stream_state.start_time == target_date_range.end_datetime:
                    overlap_share = 0
                else:
                    overlap_share = 1
            else:
                overlap_share = 0

        return overlap_share

    def get_mass_share_in_time_period(
        self,
        stream_state: BatchStreamState,
        is_input_stream: bool,
        target_date_range: datetimerange.DateTimeRange,
    ) -> numbers.Number:
        """Returns the mass that is transferred by the stream state
        within the target_date_range. The mass is transferred in a discrete
        manner at the start date and end date. At the start date the complete
        mass is removed from the start node and at the end date the complete
        mass is added to the target node.

        Args:
            stream_state (BatchStreamState): The stream state that should
                be analyzed for its mass.
            is_input_stream (bool): Determines if the mass transfer behavior
                should be analyzed at the start or target node.
            target_date_range (datetimerange.DateTimeRange): The analysis date range
                is analyzed for the transferred mass.

        Returns:
            numbers.Number: The total transferred mass within the target_date_range.
        """
        if is_input_stream is True:
            mass_transfer_time = stream_state.end_time
        else:
            mass_transfer_time = stream_state.start_time
        if (
            mass_transfer_time in target_date_range
            and target_date_range.timedelta == datetime.timedelta(hours=0)
        ):
            overlap_share = 1
        else:
            overlap_share = 0

        mass_share = overlap_share * stream_state.batch_mass_value
        return mass_share

    def create_batch_state(
        self, end_time: datetime.datetime, batch_mass_value: numbers.Number
    ) -> BatchStreamState:
        """Creates a new batch state based on the end time and batch mass value.

        Args:
            end_time (datetime.datetime): End time of the new batch stream
                state.
            batch_mass_value (numbers.Number): Mass that is transferred during
                the period of the state.

        Returns:
            BatchStreamState: New stream state with the provided end_time and
                transfer mass.
        """
        start_time = end_time - self.static_data.delay
        batch_stream_state = BatchStreamState(
            name=self.name,
            start_time=start_time,
            end_time=end_time,
            batch_mass_value=batch_mass_value,
            date_time_range=datetimerange.DateTimeRange(
                start_datetime=start_time, end_datetime=end_time
            ),
        )
        return batch_stream_state

    def consider_maximum_batch_mass(
        self, target_batch_mass: numbers.Number
    ) -> numbers.Number:
        """Check if the desired maximum batch mass can be returned.
        Returns desired mass if its within boundaries. If desired mass
        is bigger than maximum, the maximum value is returned.

        Args:
            target_batch_mass (numbers.Number): Mass that should be checked
                for feasibility against the static data.

        Returns:
            numbers.Number: Equal the target_batch_mass if it is smaller
                than the static batch mass. Equals the maximum batch mass
                if the target batch mass is greater than the maximum batch
                mass.
        """
        maximum_batch_mass = self.static_data.maximum_batch_mass_value
        if maximum_batch_mass == float("inf"):
            possible_batch_mass = target_batch_mass
        else:
            if target_batch_mass <= maximum_batch_mass:
                possible_batch_mass = target_batch_mass
            elif target_batch_mass > maximum_batch_mass:
                possible_batch_mass = maximum_batch_mass

        return possible_batch_mass

    def get_upstream_node_name(self) -> str:
        """Returns the name of the stream start node.

        Returns:
            str: Name of the stream start node.
        """
        return self.static_data.start_process_step_name

    def get_downstream_node_name(self) -> str:
        """Returns the name of the stream target node.

        Returns:
            str: Name of the stream target node.
        """
        return self.static_data.end_process_step_name

    def get_produced_mass_between_end_and_start_date(
        self,
        target_start_date: datetime.datetime,
        target_end_date: datetime.datetime,
        state: BatchStreamState,
    ) -> numbers.Number:
        """Returns the mass of stream state that was produced
        between start date and end date provided as arguments.

        Args:
            target_start_date (datetime.datetime): Start date of the
                analysis time range.
            target_end_date (datetime.datetime): End date of the
                analysis time range.
            state (BatchStreamState): State that should be analyzed
                for the mass between the provided start and end date.


        Returns:
            numbers.Number: Total mass of the stream state.
        """
        state_start_date = state.start_time
        state_end_date = state.end_time
        state_time_difference = state_end_date - state_start_date
        target_time_difference = target_end_date - target_start_date
        produced_mass = self.get_produced_amount(state=state)
        if check_if_date_1_is_before_date_2(
            date_1=target_start_date, date_2=state_start_date
        ):
            raise Exception(
                "Tried to separate state in a time before the state has started"
            )
        if check_if_date_1_is_before_date_2(
            date_1=state_end_date, date_2=target_end_date
        ):
            raise Exception(
                "Tried to separate state in a time frame after the state has ended"
            )
        mass_between_target_start_and_end_time = produced_mass * (
            target_time_difference / state_time_difference
        )
        return mass_between_target_start_and_end_time

    def json_dumps_state(
        self, stream_state: BatchStreamState, path_to_save_folder: str = ""
    ):
        """Dumps the stream state to a json file.

        Args:
            stream_state (BatchStreamState): Stream state that should be dumped.
            path_to_save_folder (str, optional): Path to the json file. Defaults to "".
        """
        file_name = stream_state.name + ".json"
        output_path = os.path.join(path_to_save_folder, file_name)
        json_string = stream_state.to_json()
        # batch_stream_dict.pop("date_time_range", None)

        with open(output_path, "w", encoding="utf8") as output_file:
            output_file.write(json_string)
        # with open(output_path, "w", encoding="utf8") as output_file:
        #     json.dump(batch_stream_dict, output_file, ensure_ascii=False)

    def json_load_state(self, path_to_file: str = ""):
        """Loads the stream state from a json file.

        Args:
            path_to_file (str, optional): path to the json file
                that contains the stream state information. Defaults to "".

        Returns:
            _type_: Stream state from the json file.
        """
        with open(path_to_file, "r", encoding="utf8") as input_file:
            json_string = input_file.read()
        # with open(path_to_file, "w", encoding="utf8") as input_file:
        #     batch_stream_dict: dict = json.load(
        #         batch_stream_dict, input_file, ensure_ascii=False
        #     )
        # date_time_range = datetimerange.DateTimeRange(
        #     start_datetime=batch_stream_dict["start_time"],
        #     end_datetime=batch_stream_dict["end_time"],
        # )
        # batch_stream_dict["date_time_range"] = date_time_range
        batch_stream_state = BatchStreamState.from_json(json_string)
        return batch_stream_state


@dataclass(frozen=True, slots=True)
class ContinuousStreamState(BaseStreamState):
    total_mass: numbers.Number = field(metadata=config(mm_field=numbers.Number))
    current_operation_rate: numbers.Number = field(
        metadata=config(mm_field=numbers.Number)
    )


@dataclass(kw_only=True)
class ContinuousStreamStaticData(StreamStaticData):
    minimum_operation_rate: numbers.Number = field(
        default=0,
        metadata=config(mm_field=numbers.Number),
    )
    """This rate defines the minimum rate at which
    mass can be transferred by this stream.
    """
    maximum_operation_rate: numbers.Number = field(
        default=float("inf"),
        metadata=config(mm_field=numbers.Number),
    )
    """This rate defines the maximum rate at which
    mass can be transferred by this stream.
    """
    time_unit: datetime.timedelta = field(
        default=datetime.timedelta(hours=1),
        metadata=config(
            encoder=json_timedelta_serialization_function,
            decoder=json_timedelta_deserialization_function,
            mm_field=datetime.timedelta,
        ),
    )
    """Determines the denominator unit of the
    operation rate.
    """
    stream_type: str = "ContinuousStream"
    """Defines the object type. Must no be changed.
    """


@dataclass(frozen=True, slots=True)
class ContinuousStreamProductionPlanEntry(DataClassJsonMixin):
    """Represents a single discrete simulation result for a stream."""

    name: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    duration: datetime.timedelta
    commodity: str
    current_operation_rate_value: numbers.Number
    current_operation_rate_unit: str
    mass_unit: str
    minimum_operation_rate: numbers.Number
    maximum_operation_rate: numbers.Number
    total_mass: numbers.Number
    stream_type: str
    name_to_display: str


@dataclass
class ContinuousStream(DataClassJsonMixin):
    """Continuous streams connect process nodes in a continuous manner.
    The mass between the nodes is transferred at a continuous rate between the start and
    end time of a ContinuousStreamState."""

    static_data: ContinuousStreamStaticData
    stream_type = "ContinuousStream"

    def __post_init__(
        self,
    ):
        self.name: str = (
            self.static_data.start_process_step_name
            + "_"
            + self.static_data.end_process_step_name
            + "_"
            + self.static_data.commodity.name
        )
        self.stream_energy_data: StreamEnergyData = StreamEnergyData(
            stream_name=self.name
        )

    def create_stream_energy_data(
        self,
        specific_energy_demand: numbers.Number,
        load_type: LoadType,
        mass_unit: str = Units.mass_unit.__str__(),
        energy_unit: str = Units.energy_unit.__str__(),
    ):
        """Creates the data that is required to determine the energy demand of a
        Stream for a specific LoadType.

        Args:
            specific_energy_demand (numbers.Number): Value for the mass specific energy
                demand.
            load_type (LoadType): LoadType representing the energy type that is consumed
                by the Stream.
            mass_unit (str, optional): Mass unit in the denominator of the specific
                energy demand. Defaults to Units.mass_unit.__str__().
            energy_unit (str, optional): Energy unit in the numerator
                of the specific energy demand. Defaults to Units.energy_unit.__str__().
        """
        stream_load_energy_data = StreamLoadEnergyData(
            stream_name=self.name,
            specific_energy_demand=specific_energy_demand,
            load_type=load_type,
            mass_unit=mass_unit,
            energy_unit=energy_unit,
        )
        self.stream_energy_data.add_stream_load_energy_data(
            stream_load_energy_data=stream_load_energy_data
        )

    def create_stream_state_for_commodity_amount(
        self,
        commodity_amount: numbers.Number,
        end_time: datetime.datetime,
        operation_rate: numbers.Number = float("inf"),
    ) -> ContinuousStreamState:
        """Creates a stream state based on the end time, commodity mass
        and operation rate.


        Args:
            commodity_amount (numbers.Number): Total commodity amount of the output
                stream state.
            end_time (datetime.datetime): End time of the stream state.
            operation_rate (numbers.Number, optional): Operation rate of the
                stream state. Defaults to float("inf").

        Returns:
            ContinuousStreamState: New stream state that is based on the arguments of the method.
        """
        # When maximum operation rate is set to none, set to maximum rate
        if operation_rate == float("inf"):
            operation_rate = self.static_data.maximum_operation_rate

        if operation_rate is None:
            # If maximum rate ist still none make the stream instant
            raise Exception(
                "No maximum operation rate has been set for stream: ",
                self.static_data.name_to_display,
            )

        operation_rate_is_within_boundaries = (
            self.check_if_operation_rate_is_within_boundaries(
                operation_rate_to_check=operation_rate
            )
        )
        if operation_rate_is_within_boundaries is False:
            raise Exception("Operation is not within boundaries")

        start_time = end_time - datetime.timedelta(
            hours=commodity_amount / operation_rate
        )

        continuous_stream_state = ContinuousStreamState(
            name=self.name,
            end_time=end_time,
            start_time=start_time,
            total_mass=commodity_amount,
            current_operation_rate=operation_rate,
            date_time_range=datetimerange.DateTimeRange(
                start_datetime=start_time, end_datetime=end_time
            ),
        )
        return continuous_stream_state

    def get_time_frame_overlap_share(
        self,
        numerator_date_range: datetimerange.DateTimeRange,
        denominator_date_range: datetimerange.DateTimeRange,
    ) -> numbers.Number:
        """Determines the time share of two date ranges.

        Args:
            numerator_date_range (datetimerange.DateTimeRange): Time share in the numerator.
            denominator_date_range (datetimerange.DateTimeRange): Time share in the denominator.

        Returns:
            numbers.Number: Time share of the numerator in the denominator. Can be between 0 and 1.
        """
        # if denominator_date_range.get_timedelta_second() == 0:
        #     overlap_share = 0
        # else:
        if denominator_date_range.is_intersection(numerator_date_range):
            intersection = denominator_date_range.intersection(x=numerator_date_range)
            overlap_share = (
                intersection.get_timedelta_second()
                / denominator_date_range.get_timedelta_second()
            )

        else:
            overlap_share = 0
        return overlap_share

    def get_mass_share_in_time_period(
        self,
        numerator_date_range: datetimerange.DateTimeRange,
        stream_state: ContinuousStreamState,
    ) -> numbers.Number:
        """Returns the mass of the stream that was produced during the
        numerator date range.

        Args:
            numerator_date_range (datetimerange.DateTimeRange): The date range that
                for which the produced mass should be determined.
            stream_state (ContinuousStreamState): Stream state that contains should be checked
                for the mass in the numerator date range.

        Returns:
            numbers.Number: Mass produced in the numerator date range.
        """
        denominator_date_range = stream_state.date_time_range
        if denominator_date_range.is_intersection(numerator_date_range):
            intersection = denominator_date_range.intersection(x=numerator_date_range)
            overlap_share = (
                intersection.get_timedelta_second()
                / denominator_date_range.get_timedelta_second()
            )

        else:
            overlap_share = 0
        mass_share = overlap_share * stream_state.total_mass
        return mass_share

    def create_production_plan_entry(
        self, state: ContinuousStreamState
    ) -> ContinuousStreamProductionPlanEntry:
        """Creates a stream simulation result from a simulation result.
        The simulation results contains additional information that was not
        required during the simulation.

        Args:
            state (ContinuousStreamState): Internal simulation result
                that should be converted into a final simulation result.

        Returns:
            ContinuousStreamProductionPlanEntry: Final simulation result entry.
        """
        production_plan_entry = ContinuousStreamProductionPlanEntry(
            name=self.name,
            start_time=state.start_time,
            end_time=state.end_time,
            duration=state.end_time - state.start_time,
            commodity=self.static_data.commodity.name,
            current_operation_rate_value=state.current_operation_rate,
            mass_unit=self.static_data.mass_unit,
            current_operation_rate_unit=str(self.static_data.mass_unit)
            + "\\"
            + str(self.static_data.time_unit),
            minimum_operation_rate=self.static_data.minimum_operation_rate,
            maximum_operation_rate=self.static_data.maximum_operation_rate,
            total_mass=state.current_operation_rate
            * ((state.end_time - state.start_time) / self.static_data.time_unit),
            stream_type="ContinuousStream",
            name_to_display=self.static_data.name_to_display,
        )

        return production_plan_entry

    def get_produced_amount(self, state: ContinuousStreamState) -> numbers.Number:
        """Returns the total mass of the stream state.

        Args:
            state (ContinuousStreamState): Stream state that contains the total
                mass of interest.

        Returns:
            numbers.Number: Total mass of the input stream state.
        """
        if not isinstance(state, ContinuousStreamState):
            raise UnexpectedDataType(
                current_data_type=state, expected_data_type=ContinuousStreamState
            )
            # raise Exception("Wrong input data type for stream state: " + str(state))

        return state.total_mass

    def check_if_operation_rate_is_within_boundaries(
        self, operation_rate_to_check: numbers.Number
    ) -> bool:
        """Checks if operation rate is within the limits of the
        static data of a stream.

        Args:
            operation_rate_to_check (numbers.Number): Operation rate
                that should be checked.

        Returns:
            bool: Is true if the operation that is provided is within the
                limits of the static stream data.
        """
        if self.static_data.maximum_operation_rate == float("inf"):
            operation_rate_is_within_boundaries = True
        elif isinstance(self.static_data.maximum_operation_rate, numbers.Number):
            if operation_rate_to_check > self.static_data.maximum_operation_rate:
                operation_rate_to_check = self.static_data.maximum_operation_rate
                operation_rate_is_within_boundaries = False
            elif (
                operation_rate_to_check <= self.static_data.maximum_operation_rate
                and operation_rate_to_check >= 0
            ):
                operation_rate_is_within_boundaries = True
            elif operation_rate_to_check < 0:
                raise Exception(
                    "Input stream operation rate has been set to "
                    + str(operation_rate_to_check)
                )
            else:
                raise Exception(
                    "Unexpected data in comparison of maximum and current operation rate"
                )
        else:
            raise Exception(
                "Unexpected datatype for maximum operation rate: "
                + str(self.static_data.maximum_operation_rate)
                + " of type: "
                + str(type(self.static_data.maximum_operation_rate))
            )

        return operation_rate_is_within_boundaries

    def determine_start_time(
        self,
        end_time: datetime.datetime,
        operation_rate: numbers.Number,
        total_transported_mass: numbers.Number,
    ) -> datetime.datetime:
        """Determine the start time of the stream state
        based on the end_time, operation rate and the total
        mass that is produced during the state.

        Args:
            end_time (datetime.datetime): End time of the state.
            operation_rate (numbers.Number): Rate at which mass is transferred
                during stream state.
            total_transported_mass (numbers.Number): Total produced
                mass of the stream state.

        Returns:
            datetime.datetime: Start time that was defined based on the arguments.
        """
        start_time = end_time - datetime.timedelta(
            hours=total_transported_mass / operation_rate
        )
        logging.debug(
            "The end time is: %s , start_time:%s operation rate: %s and the total transported mass: %s ",
            end_time,
            start_time,
            operation_rate,
            total_transported_mass,
        )
        return start_time

    def determine_stream_state_mass(
        self,
        end_time: datetime.datetime,
        start_time: datetime.datetime,
        current_operation_rate: numbers.Number | None,
    ) -> numbers.Number:
        """Returns the total mass that is produced at the current operation rate
        during the period defined.

        Args:
            end_time (datetime.datetime): End time of the period to be analyzed.
            start_time (datetime.datetime): Start time of the period to be analyzed.
            current_operation_rate (numbers.Number | None): Rate at which mass is transferred.

        Returns:
            numbers.Number: Total mass that is produced during the period.
        """
        time_difference_date_time: datetime.timedelta = end_time - start_time
        time_difference_float: numbers.Number = (
            time_difference_date_time / self.static_data.time_unit
        )
        produced_amount: numbers.Number = time_difference_float * current_operation_rate
        return produced_amount

    def create_continuous_stream_state(
        self,
        end_time: datetime.datetime,
        start_time: datetime.datetime,
        current_operation_rate: numbers.Number | None,
    ) -> ContinuousStreamState:
        """Creates a continuous stream state for the time period and operation
        rate that is provided by the input arguments.

        Args:
            end_time (datetime.datetime): End time of the stream state.
            start_time (datetime.datetime): Start time of the stream state.
            current_operation_rate (numbers.Number | None): Operation rate
                of the stream state.

        Returns:
            ContinuousStreamState: New stream state.
        """
        produced_amount = self.determine_stream_state_mass(
            end_time=end_time,
            start_time=start_time,
            current_operation_rate=current_operation_rate,
        )
        return ContinuousStreamState(
            name=self.name,
            start_time=start_time,
            end_time=end_time,
            total_mass=produced_amount,
            current_operation_rate=current_operation_rate,
            date_time_range=datetimerange.DateTimeRange(
                start_datetime=start_time, end_datetime=end_time
            ),
        )

    def get_upstream_node_name(self) -> str:
        """Returns the name of the start node of the stream.

        Returns:
            str: Name of the start node of the stream.
        """
        return self.static_data.start_process_step_name

    def get_downstream_node_name(self) -> str:
        """Returns the name of the target node of the stream.

        Returns:
            str: Name of the target node of the stream
        """
        return self.static_data.end_process_step_name

    def get_produced_mass_between_end_and_start_date(
        self,
        target_start_date: datetime.datetime,
        target_end_date: datetime.datetime,
        state: ContinuousStreamState,
    ) -> numbers.Number:
        """Returns the mass that was produced by the stream state
        in the given period.

        Args:
            target_start_date (datetime.datetime): Start date of the
                period that should be analyzed for transported mass.
            target_end_date (datetime.datetime): End date of the
                period that should be analyzed for transported mass.
            state (ContinuousStreamState): State that should be checked
                for the produced mass.

        Raises:
            Exception: Returns an exception if the analysis start date occurs
                before the start of the stream state.
            Exception: Returns an exception if the analysis end date occurs
                after the end of the stream state.

        Returns:
            numbers.Number: Value of the produced mass.
        """
        state_start_date = state.start_time
        state_end_date = state.end_time
        state_time_difference = state_end_date - state_start_date
        target_time_difference = target_end_date - target_start_date
        produced_mass = self.get_produced_amount(state=state)
        if check_if_date_1_is_before_date_2(
            date_1=target_start_date, date_2=state_start_date
        ):
            raise Exception(
                "Tried to separate state in a time before the state has started"
            )
        if check_if_date_1_is_before_date_2(
            date_1=state_end_date, date_2=target_end_date
        ):
            raise Exception(
                "Tried to separate state in a time frame after the state has ended"
            )
        mass_between_target_start_and_end_time = produced_mass * (
            target_time_difference / state_time_difference
        )
        return mass_between_target_start_and_end_time

    def json_dumps_state(
        self, stream_state: ContinuousStreamState, path_to_save_folder: str = ""
    ):
        """Dumps a streams tate to a json file.

        Args:
            stream_state (ContinuousStreamState): Continuous stream state
                that should be dumped.
            path_to_save_folder (str, optional): Path to json file. Defaults to "".
        """
        file_name = stream_state.name + ".json"
        output_path = os.path.join(path_to_save_folder, file_name)
        json_string = stream_state.to_json()
        # batch_stream_dict.pop("date_time_range", None)

        with open(output_path, "w", encoding="utf8") as output_file:
            output_file.write(json_string)

    def json_load_state(self, path_to_file: str = "") -> "ContinuousStreamState":
        """Loads a stream simulation state.

        Args:
            path_to_file (str, optional): Path to the json file. Defaults to "".

        Returns:
            ContinuousStreamState: stream state that was read from the json file.
        """
        with open(path_to_file, "r", encoding="utf8") as input_file:
            json_string = input_file.read()
        # date_time_range = datetimerange.DateTimeRange(
        #     start_datetime=stream_dict["start_time"],
        #     end_datetime=stream_dict["end_time"],
        # )
        # stream_dict["date_time_range"] = date_time_range
        stream_state = ContinuousStreamState.from_json(json_string)
        return stream_state


@dataclass(kw_only=True, frozen=True)
class ProcessStepProductionPlanEntryWithInputStreamState(
    ProcessStepProductionPlanEntry
):
    """
    Discrete simulation state that couples an input stream
    to the respective simulation process state.
    """

    stream_start_time: datetime.datetime
    stream_end_time: datetime.datetime
    total_stream_mass: numbers.Number


@dataclass
class StreamDataFrameMetaInformation(DataClassJsonMixin):
    """Contains a list of LoadProfileEntries, a DataFrame that is
    created from this list and additional meta data about both.
    """

    data_frame: pd.DataFrame
    stream_name: str
    first_start_time: datetime.datetime
    last_end_time: datetime.datetime
    stream_type: str
    mass_unit: str
    commodity: Commodity
    name_to_display: str
