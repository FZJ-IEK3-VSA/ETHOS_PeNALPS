import datetime
import json
import numbers

import datetimerange
import jsonpickle
import pandas
import pint

from ethos_penalps.data_classes import ProcessStateData, ProcessStepProductionPlanEntry
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamProductionPlanEntry,
    BatchStreamState,
    ContinuousStream,
    ContinuousStreamProductionPlanEntry,
    ContinuousStreamState,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.general_functions import (
    check_if_date_1_is_before_date_2,
    check_if_date_1_is_before_or_at_date_2,
)
from ethos_penalps.utilities.units import Units


class StreamPostProcessor:
    def __init__(
        self,
        stream: ContinuousStream | BatchStream,
        list_of_stream_states: list[
            ContinuousStreamProductionPlanEntry | BatchStreamProductionPlanEntry
        ],
    ) -> None:
        self.stream: ContinuousStream | BatchStream = stream
        self.list_of_stream_states: list[
            ContinuousStreamProductionPlanEntry | BatchStreamProductionPlanEntry
        ] = list_of_stream_states

    def determine_total_mass_in_time(
        self, earliest_start_date: datetime.datetime, latest_end_date: datetime.datetime
    ) -> numbers.Number:
        stream_data_frame = pandas.DataFrame(data=self.list_of_stream_states)
        full_data_frame = stream_data_frame.loc[
            (stream_data_frame["end_time"] >= earliest_start_date)
            & (stream_data_frame["start_time"] <= latest_end_date)
        ]
        start_partial = stream_data_frame.loc[
            (stream_data_frame["end_time"] <= earliest_start_date)
            & (stream_data_frame["start_time"] >= earliest_start_date)
        ]
        end_partial = stream_data_frame.loc[
            (stream_data_frame["end_time"] <= earliest_start_date)
            & (stream_data_frame["start_time"] >= earliest_start_date)
        ]

        if isinstance(self.stream, ContinuousStream):
            total_mass_column = full_data_frame["total_mass"].sum()
        elif isinstance(self.stream, BatchStream):
            total_mass_column = full_data_frame["batch_mass_value"].sum()

        return total_mass_column

    def determine_actual_throughput(
        self, earliest_start_date: datetime.datetime, latest_end_date: datetime.datetime
    ) -> pint.Quantity:
        stream_data_frame = pandas.DataFrame(data=self.list_of_stream_states)
        if isinstance(self.stream, ContinuousStream):
            total_stream_mass = stream_data_frame["total_mass"].sum()
        elif isinstance(self.stream, BatchStream):
            total_stream_mass = stream_data_frame["batch_mass_value"].sum()
        time_range_number = (
            earliest_start_date - latest_end_date
        ) / datetime.timedelta(hours=1)
        mass_stream_unit = Units.get_unit(unit_string="metric_ton/h")
        capacity = (total_stream_mass / time_range_number) * mass_stream_unit
        return capacity

    def fill_from_date_to_start(
        self,
        list_of_stream_entries: list[ProcessStepProductionPlanEntry],
        start_date: datetime.datetime,
    ) -> list[ProcessStepProductionPlanEntry]:
        first_entry = list_of_stream_entries[0]

        if check_if_date_1_is_before_date_2(
            date_1=start_date, date_2=first_entry.start_time
        ):
            if isinstance(self.stream, ContinuousStream):
                stream_state = ContinuousStreamState(
                    total_mass=0,
                    current_operation_rate=0,
                    start_time=start_date,
                    end_date=first_entry.start_time,
                    date_time_range=datetimerange.DateTimeRange(
                        start_datetime=start_date, end_datetime=first_entry.start_time
                    ),
                )
                production_plan_entry = self.stream.create_production_plan_entry(
                    state=stream_state
                )
            elif isinstance(self.stream, BatchStream):
                stream_state = BatchStreamState(
                    batch_mass_value=0,
                    start_time=start_date,
                    end_date=first_entry.start_time,
                    date_time_range=datetimerange.DateTimeRange(
                        start_datetime=start_date, end_datetime=first_entry.start_time
                    ),
                )
                production_plan_entry = self.stream.create_production_plan_entry(
                    state=stream_state
                )
            list_of_stream_entries.insert(0, production_plan_entry)

        return list_of_stream_entries

    def get_earliest_stream_time(self) -> datetime.datetime:
        return self.list_of_stream_states[0].start_time

    def get_latest_stream_time(self) -> datetime.datetime:
        return self.list_of_stream_states[-1].end_time

    def fill_to_end_date(
        self,
        list_of_stream_entries: list[
            ContinuousStreamProductionPlanEntry | BatchStreamProductionPlanEntry
        ],
        end_date: datetime.datetime,
    ) -> list[ProcessStepProductionPlanEntry]:
        last_entry = list_of_stream_entries[-1]

        if check_if_date_1_is_before_date_2(
            date_1=last_entry.end_time, date_2=end_date
        ):
            if isinstance(self.stream, ContinuousStream):
                stream_state = ContinuousStreamState(
                    total_mass=0,
                    current_operation_rate=0,
                    start_time=last_entry.end_time,
                    end_date=end_date,
                    date_time_range=datetimerange.DateTimeRange(
                        start_datetime=last_entry.end_time, end_datetime=end_date
                    ),
                )
                production_plan_entry = self.stream.create_production_plan_entry(
                    state=stream_state
                )
            elif isinstance(self.stream, BatchStream):
                stream_state = BatchStreamState(
                    batch_mass_value=0,
                    start_time=last_entry.end_time,
                    end_date=end_date,
                    date_time_range=datetimerange.DateTimeRange(
                        start_datetime=last_entry.end_time, end_datetime=end_date
                    ),
                )
                production_plan_entry = self.stream.create_production_plan_entry(
                    state=stream_state
                )

            list_of_stream_entries.append(production_plan_entry)
        return list_of_stream_entries


class ProcessStepPostProcessor:
    def __init__(
        self,
        list_of_process_step_entries: list[ProcessStepProductionPlanEntry],
        process_step: ProcessStep,
        input_stream_post_processor: StreamPostProcessor,
        output_stream_post_processor: StreamPostProcessor,
    ) -> None:
        self.list_of_process_step_entries: list[
            ProcessStepProductionPlanEntry
        ] = list_of_process_step_entries[::-1]
        self.process_step: ProcessStep = process_step
        self.input_stream_post_processor: StreamPostProcessor = (
            input_stream_post_processor
        )
        self.output_stream_post_processor: StreamPostProcessor = (
            output_stream_post_processor
        )

    def fill_from_date_to_start(
        self,
        list_of_process_step_entries: list[ProcessStepProductionPlanEntry],
        start_date: datetime.datetime,
    ) -> list[ProcessStepProductionPlanEntry]:
        first_entry = list_of_process_step_entries[0]

        if check_if_date_1_is_before_date_2(
            date_1=start_date, date_2=first_entry.start_time
        ):
            idle_state = self.process_step.process_state_handler.get_idle_state()
            new_first_process_step_entry = (
                idle_state.create_process_step_production_plan_entry(
                    process_state_state=ProcessStateData(
                        process_state_name=idle_state.process_state_name,
                        start_time=start_date,
                        end_time=first_entry.start_time,
                    )
                )
            )
            list_of_process_step_entries.insert(0, new_first_process_step_entry)

        return list_of_process_step_entries

    def fill_to_end_date(
        self,
        list_of_process_step_entries: list[ProcessStepProductionPlanEntry],
        end_date: datetime.datetime,
    ) -> list[ProcessStepProductionPlanEntry]:
        last_entry = list_of_process_step_entries[-1]

        if check_if_date_1_is_before_date_2(
            date_1=last_entry.end_time, date_2=end_date
        ):
            idle_state = self.process_step.process_state_handler.get_idle_state()
            new_last_process_step_entry = (
                idle_state.create_process_step_production_plan_entry(
                    process_state_state=ProcessStateData(
                        process_state_name=idle_state.process_state_name,
                        start_time=last_entry.end_time,
                        end_time=end_date,
                    )
                )
            )
            list_of_process_step_entries.append(new_last_process_step_entry)
        return list_of_process_step_entries

    def check_if_list_of_load_profile_entries_has_gaps(
        self, list_of_process_step_states_entries: list[ProcessStepProductionPlanEntry]
    ):
        row_number = 0
        previous_entry = None

        for process_step_entry in list_of_process_step_states_entries:
            if not isinstance(process_step_entry, ProcessStepProductionPlanEntry):
                raise Exception("Unexpected  input in input list")
            if previous_entry is not None:
                if previous_entry.end_time != process_step_entry.start_time:
                    print("Previous Entry:\n", previous_entry)
                    print("Current Entry:\n", process_step_entry)

                    raise Exception(
                        "There is a gap between last and current entry. Last entry "
                        + str(previous_entry)
                        + " current entry: "
                        + str(process_step_entry)
                        + " at row: "
                        + str(row_number)
                    )

            previous_entry = process_step_entry
            row_number = row_number + 1

    def get_earliest_start_date(self) -> datetime.datetime:
        return self.list_of_process_step_entries[0].start_time

    def get_latest_end_date(self) -> datetime.datetime:
        return self.list_of_process_step_entries[-1].end_time

    def determine_mass_throughput(
        self,
        earliest_start_date: datetime.datetime | None = None,
        latest_end_date: datetime.datetime | None = None,
    ) -> pint.Quantity:
        if earliest_start_date is None:
            earliest_start_date = self.get_earliest_start_date()
        if latest_end_date is None:
            latest_end_date = self.get_latest_end_date()
        total_mass_in_time = (
            self.output_stream_post_processor.determine_total_mass_in_time(
                earliest_start_date=earliest_start_date, latest_end_date=latest_end_date
            )
        ) * Units.get_unit("metric_ton")
        total_hours = (
            (latest_end_date - earliest_start_date)
            / datetime.timedelta(hours=1)
            * Units.get_unit("h")
        )
        mass_stream = total_mass_in_time / total_hours
        return mass_stream

    def determine_idle_time(self) -> pint.Quantity:
        idle_state = self.process_step.process_state_handler.get_idle_state()
        total_idle_time = datetime.timedelta(minutes=0)
        for process_state_entry in self.list_of_process_step_entries:
            if process_state_entry.process_state_name == idle_state.process_state_name:
                duration = process_state_entry.end_time - process_state_entry.start_time
                total_idle_time = total_idle_time + duration
        output_idle_times = total_idle_time.total_seconds() * Units.get_unit("seconds")
        return output_idle_times


class ProductionPlanPostProcessor:
    def __init__(
        self,
        production_plan: ProductionPlan,
        process_node_dict: dict[str, ProcessNode],
        stream_handler: StreamHandler,
        time_data: TimeData,
    ) -> None:
        self.production_plan: ProductionPlan = production_plan
        self.process_node_dict: dict[str, ProcessNode] = process_node_dict
        self.time_data: TimeData = time_data
        self.stream_handler: StreamHandler = stream_handler

    def create_all_process_step_processors(self) -> dict[str, ProcessStepPostProcessor]:
        dict_of_process_step_processors = {}
        for process_step_name in self.production_plan.process_step_states_dict:
            dict_of_process_step_processors[
                process_step_name
            ] = self.create_process_step_processor(process_step_name=process_step_name)

        return dict_of_process_step_processors

    def determine_throughput_for_process_step(
        self,
        post_production_post_processor_dict: dict[str, ProcessStepPostProcessor],
        process_step_name: str,
    ) -> pint.Quantity:
        post_load_profile_processor_process_step = post_production_post_processor_dict[
            process_step_name
        ]
        current_throughput = (
            post_load_profile_processor_process_step.determine_mass_throughput()
        )
        return current_throughput

    def determine_idle_time_for_process_step(
        self,
        post_production_post_processor_dict: dict[str, ProcessStepPostProcessor],
        process_step_name: str,
        start_date: datetime.datetime | None = None,
        end_date: datetime.datetime | None = None,
    ) -> pint.Quantity:
        post_load_profile_processor_process_step = post_production_post_processor_dict[
            process_step_name
        ]
        if start_date is not None:
            list_of_process_step_entries = post_load_profile_processor_process_step.fill_from_date_to_start(
                list_of_process_step_entries=post_load_profile_processor_process_step.list_of_process_step_entries,
                start_date=start_date,
            )
            post_load_profile_processor_process_step.list_of_process_step_entries = (
                list_of_process_step_entries
            )
        if end_date is not None:
            list_of_process_step_entries = post_load_profile_processor_process_step.fill_to_end_date(
                end_date=end_date,
                list_of_process_step_entries=post_load_profile_processor_process_step.list_of_process_step_entries,
            )
            post_load_profile_processor_process_step.list_of_process_step_entries = (
                list_of_process_step_entries
            )
        idle_time = post_load_profile_processor_process_step.determine_idle_time()
        return idle_time

    def determine_throughput_difference_for_process_step(
        self,
        post_production_post_processor_dict: dict[str, ProcessStepPostProcessor],
        process_step_name: str,
        target_throughput: pint.Quantity,
    ) -> pint.Quantity:
        post_load_profile_processor_process_step = post_production_post_processor_dict[
            process_step_name
        ]
        current_throughput = (
            post_load_profile_processor_process_step.determine_mass_throughput()
        )
        target_difference_quantity = current_throughput - target_throughput
        print(target_difference_quantity)
        return target_difference_quantity

    def create_process_step_processor(
        self, process_step_name: str
    ) -> ProcessStepPostProcessor:
        process_step = self.process_node_dict[process_step_name]
        input_stream_name = process_step.get_output_stream_name()
        output_stream_name = process_step.get_input_stream_name()

        input_stream_post_processor = self.create_stream_post_processor(
            stream_name=input_stream_name
        )
        output_stream_post_processor = self.create_stream_post_processor(
            stream_name=output_stream_name
        )
        list_of_process_step_states = self.production_plan.process_step_states_dict[
            process_step_name
        ]

        process_step_post_processor = ProcessStepPostProcessor(
            list_of_process_step_entries=list_of_process_step_states,
            input_stream_post_processor=input_stream_post_processor,
            output_stream_post_processor=output_stream_post_processor,
            process_step=process_step,
        )
        return process_step_post_processor

    def create_stream_post_processor(self, stream_name: str) -> StreamPostProcessor:
        stream = self.stream_handler.get_stream(stream_name=stream_name)
        list_of_stream_states = self.production_plan.stream_state_dict[stream_name]
        stream_post_processor = StreamPostProcessor(
            stream=stream, list_of_stream_states=list_of_stream_states
        )
        return stream_post_processor

    def determine_earliest_process_state(self) -> datetime.datetime:
        dict_of_process_step_processors = self.create_all_process_step_processors()
        list_of_start_dates = []
        for process_step_processor in dict_of_process_step_processors.values():
            start_date = process_step_processor.get_earliest_start_date()
            list_of_start_dates.append(start_date)
        earliest_start_date = min(list_of_start_dates)
        return earliest_start_date

    def determine_latest_end_time(self) -> datetime.datetime:
        dict_of_process_step_processors = self.create_all_process_step_processors()
        list_of_end_dates = []
        for process_step_processor in dict_of_process_step_processors.values():
            end_date = process_step_processor.get_earliest_start_date()
            list_of_end_dates.append(end_date)
        latest_start_date = max(list_of_end_dates)
        return latest_start_date
