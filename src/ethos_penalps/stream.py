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
from dataclasses_json import config, dataclass_json, DataClassJsonMixin

from ethos_penalps.utilities.units import Units
from ethos_penalps.data_classes import (
    Commodity,
    LoadType,
    ProcessStepProductionPlanEntry,
    StreamLoadEnergyData,
    ProcessChainIdentifier,
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
    json_timedelta_deserialization_function,
    json_timedelta_serialization_function,
    json_pint_unit_deserialization_function,
    json_pint_unit_serialization_function,
)


@dataclass(kw_only=True, frozen=True)
class BaseStreamState(DataClassJsonMixin):
    name: str
    start_time: datetime.datetime = field(
        metadata=config(
            encoder=json_datetime_serialization_function,
            decoder=json_datetime_deserialization_function,
        )
    )
    end_time: datetime.datetime = field(
        metadata=config(
            encoder=json_datetime_serialization_function,
            decoder=json_datetime_deserialization_function,
        )
    )
    date_time_range: datetimerange.DateTimeRange = field(
        metadata=config(
            encoder=json_datetime_range_serialization_function,
            decoder=json_datetime_range_deserialization_function,
        )
    )


# @dataclass(kw_only=True)
# class BaseStream:
#     state: BatchStreamState
@dataclass(kw_only=True)
class StreamStaticData(DataClassJsonMixin):
    start_process_step_name: str
    end_process_step_name: str
    commodity: Commodity
    mass_unit: str = Units.mass_unit.__str__()
    name_to_display: str | None = None


@dataclass
class StreamEnergyData(DataClassJsonMixin):
    stream_name: str
    load_dict: dict[str, LoadType] = field(default_factory=dict)
    dict_stream_load_energy_data: dict[str, StreamLoadEnergyData] = field(
        default_factory=dict
    )

    def add_stream_load_energy_data(
        self, stream_load_energy_data: StreamLoadEnergyData
    ):
        self.load_dict[
            stream_load_energy_data.load_type.uuid
        ] = stream_load_energy_data.load_type
        self.dict_stream_load_energy_data[
            stream_load_energy_data.load_type.uuid
        ] = stream_load_energy_data


@dataclass(kw_only=True)
class BatchStreamStaticData(StreamStaticData):
    delay: datetime.timedelta = field(
        metadata=config(
            encoder=json_timedelta_serialization_function,
            decoder=json_timedelta_deserialization_function,
            mm_field=datetime.timedelta,
        )
    )
    minimum_batch_mass_value: numbers.Number = field(
        default=0, metadata=config(mm_field=numbers.Number)
    )
    maximum_batch_mass_value: numbers.Number = field(
        default=float("inf"),
        metadata=config(mm_field=numbers.Number),
    )
    stream_type: str = "BatchStream"


@dataclass(frozen=True, slots=True)
class BatchStreamState(BaseStreamState):
    batch_mass_value: numbers.Number = field(metadata=config(mm_field=numbers.Number))


@dataclass(frozen=True, slots=True)
class BatchStreamProductionPlanEntry(DataClassJsonMixin):
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
    """Batch streams represent streams which are instantaneously loaded and unloaded.
    The mass reaches the destination in a discrete event opposed to continuous delivery in a continuous stream
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
    ) -> datetimerange.DateTimeRange:
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

        :param target_batch_mass: _description_
        :type target_batch_mass: float
        :raises Exception: _description_
        :return: _description_
        :rtype: float
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
        return self.static_data.start_process_step_name

    def get_downstream_node_name(self) -> str:
        return self.static_data.end_process_step_name

    def get_produced_mass_between_end_and_start_date(
        self,
        target_start_date: datetime.datetime,
        target_end_date: datetime.datetime,
        state: BatchStreamState,
    ) -> numbers.Number:
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
        file_name = stream_state.name + ".json"
        output_path = os.path.join(path_to_save_folder, file_name)
        json_string = stream_state.to_json()
        # batch_stream_dict.pop("date_time_range", None)

        with open(output_path, "w", encoding="utf8") as output_file:
            output_file.write(json_string)
        # with open(output_path, "w", encoding="utf8") as output_file:
        #     json.dump(batch_stream_dict, output_file, ensure_ascii=False)

    def json_load_state(self, path_to_file: str = ""):
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
    maximum_operation_rate: numbers.Number = field(
        default=float("inf"),
        metadata=config(mm_field=numbers.Number),
    )
    time_unit: datetime.timedelta = field(
        default=datetime.timedelta(hours=1),
        metadata=config(
            encoder=json_timedelta_serialization_function,
            decoder=json_timedelta_deserialization_function,
            mm_field=datetime.timedelta,
        ),
    )
    stream_type: str = "ContinuousStream"


@dataclass(frozen=True, slots=True)
class ContinuousStreamProductionPlanEntry(DataClassJsonMixin):
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
    """Continuous streams provide mass in continuously while they are active."""

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
        if not isinstance(state, ContinuousStreamState):
            raise UnexpectedDataType(
                current_data_type=state, expected_data_type=ContinuousStreamState
            )
            # raise Exception("Wrong input data type for stream state: " + str(state))

        return state.total_mass

    def check_if_operation_rate_is_within_boundaries(
        self, operation_rate_to_check: numbers.Number
    ) -> bool:
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
        return self.static_data.start_process_step_name

    def get_downstream_node_name(self) -> str:
        return self.static_data.end_process_step_name

    def get_produced_mass_between_end_and_start_date(
        self,
        target_start_date: datetime.datetime,
        target_end_date: datetime.datetime,
        state: ContinuousStreamState,
    ) -> numbers.Number:
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
        file_name = stream_state.name + ".json"
        output_path = os.path.join(path_to_save_folder, file_name)
        json_string = stream_state.to_json()
        # batch_stream_dict.pop("date_time_range", None)

        with open(output_path, "w", encoding="utf8") as output_file:
            output_file.write(json_string)

    def json_load_state(self, path_to_file: str = ""):
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
    stream_start_time: datetime.datetime
    stream_end_time: datetime.datetime
    total_stream_mass: numbers.Number


@dataclass
class StreamDataFrameMetaInformation(DataClassJsonMixin):
    data_frame: pd.DataFrame
    stream_name: str
    first_start_time: datetime.datetime
    last_end_time: datetime.datetime
    stream_type: str
    mass_unit: str
    commodity: Commodity
    name_to_display: str
