import datetime
import numbers
from abc import ABC
from copy import deepcopy
from dataclasses import dataclass

import datetimerange
import scipy.optimize

from ethos_penalps.order_generator import OrderGenerator
from ethos_penalps.process_chain import ProcessChain
from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.stream import BatchStream, ContinuousStream
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.data_classes import ProcessChainIdentifier
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.load_profile_calculator import LoadProfileHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.order_generator import OrderCollection, NOrderGenerator


@dataclass
class CapacityClassifier(ABC):
    process_step_name: str
    first_start_time: datetime.datetime
    last_end_time: datetime.datetime
    total_length: datetime.timedelta
    hourly_capacity: float


@dataclass
class BatchCapacityClassifier(CapacityClassifier):
    output_batch_mass: float

    def pretty_print(self):
        print(
            self.process_step_name
            + ": the hourly capacity is: "
            + str(self.hourly_capacity),
            # "\n",
            # "The batch output batch mass is: "
            # + str(self.output_batch_mass)
            # + " and the batch to batch time is: "
            # + str(self.total_length),
        )


@dataclass
class ContinuousCapacityClassifier(CapacityClassifier):
    output_stream_length: datetime.timedelta
    total_output_mass: numbers.Number
    output_to_total_length_ratio: numbers.Number
    stream_rate: numbers.Number

    def pretty_print(self):
        print(
            self.process_step_name
            + ": the hourly capacity is: "
            + str(self.hourly_capacity),
            # "\n",
            # "The total output mass in one hour is: "
            # + str(self.total_output_mass)
            # + " and the output stream to total length factor is: "
            # + str(self.output_to_total_length_ratio),
        )

    def determine_required_stream_rate_to_reach_process_step_capacity(
        self,
    ):
        pass


class CapacityCalculatorProcessChain:
    def __init__(
        self,
        process_step: ProcessStep,
    ) -> None:
        self.process_step: ProcessStep = deepcopy(process_step)
        self.process_step_input_stream: ContinuousStream | BatchStream = self.process_step.process_state_handler.process_step_data.stream_handler.get_stream(
            stream_name=self.process_step.process_state_handler.process_step_data.main_mass_balance.main_input_stream_name
        )
        self.process_step_output_stream: ContinuousStream | BatchStream = self.process_step.process_state_handler.process_step_data.stream_handler.get_stream(
            stream_name=self.process_step.process_state_handler.process_step_data.main_mass_balance.main_output_stream_name
        )
        self.__post_innit__()

    def __post_innit__(self):
        self.process_chain = self._create_process_chain()
        self.sink = self._create_sink()
        self.source = self._create_source()

    def _create_process_chain(self) -> ProcessChain:
        process_chain = ProcessChain(
            process_chain_identifier=ProcessChainIdentifier(
                chain_name="Capacity Calculator Chain", chain_number=0
            ),
            production_plan=self.process_step.production_plan,
            load_profile_handler=self.process_step.production_plan.load_profile_handler,
        )
        process_chain.add_process_node(process_node_to_add=self.process_step)
        return process_chain

    def _create_sink(self) -> Sink:
        sink = Sink(
            name=self.process_step_output_stream.static_data.end_process_step_name,
            commodity=self.process_step_output_stream.static_data.commodity,
            stream_handler=self.process_step.process_state_handler.process_step_data.stream_handler,
            production_plan=self.process_step.production_plan,
            time_data=self.process_step.time_data,
        )
        self.process_chain.add_sink(sink=sink)

        sink.add_input_stream(
            input_stream=self.process_step_output_stream,
            process_chain_identifier=self.process_chain.process_chain_identifier,
        )
        return sink

    def _create_source(self) -> Source:
        source = Source(
            name=self.process_step_input_stream.static_data.start_process_step_name,
            commodity=self.process_step_input_stream.static_data.commodity,
            stream_handler=self.process_step.process_state_handler.process_step_data.stream_handler,
            time_data=self.process_step.process_state_handler.process_step_data.time_data,
            production_plan=self.process_step.production_plan,
        )
        source.add_output_stream(
            output_stream=self.process_step_input_stream,
            process_chain_identifier=self.process_chain.process_chain_identifier,
        )
        self.process_chain.add_source(source=source)
        source.set_current_output_stream(
            process_chain_identifier=self.process_chain.process_chain_identifier
        )
        return source

    def add_single_order(self):
        if isinstance(self.process_step_output_stream, ContinuousStream):
            maximum_output_operation_rate = (
                self.process_step_output_stream.static_data.maximum_operation_rate
            )
            target_mass = maximum_output_operation_rate * 1
        elif isinstance(self.process_step_output_stream, BatchStream):
            maximum_batch_mass = (
                self.process_step_output_stream.static_data.maximum_batch_mass_value
            )
            target_mass = maximum_batch_mass * 1

        order_generator = NOrderGenerator(
            commodity=self.process_step_output_stream.static_data.commodity,
            production_deadline=self.process_step.time_data.global_end_date,
            number_of_orders=1,
            mass_per_order=target_mass,
        )
        order_collection = order_generator.create_n_order_collection()
        self.sink.order_distributor.update_order_collection(
            new_order_collection=order_collection
        )
        self.process_chain.sink.order_distributor.split_production_order_dict()
        self.process_chain.sink.order_distributor.set_current_splitted_order_by_chain_identifier(
            process_chain_identifier=self.process_chain.process_chain_identifier
        )
        self.process_step.production_plan.initialize_process_step_production_plan_entry(
            process_step_name=self.process_step.name
        )
        self.process_step.production_plan.initialize_stream_production_plan_entry(
            stream_name=self.process_step_output_stream.name
        )
        self.process_step.production_plan.initialize_stream_production_plan_entry(
            stream_name=self.process_step_input_stream.name
        )


class CapacityCalculator:
    def __init__(self, process_step: ProcessStep) -> None:
        self.process_step: ProcessStep = deepcopy(process_step)
        self.capacity_calculator_process_chain: CapacityCalculatorProcessChain = (
            CapacityCalculatorProcessChain(process_step=self.process_step)
        )

    def determine_throughput_of_process_step(
        self, print_output: bool = True
    ) -> CapacityClassifier:
        self.capacity_calculator_process_chain.add_single_order()
        self.capacity_calculator_process_chain.process_chain.create_process_chain_production_plan()
        process_step_capacity_classifier = self.create_capacity_classifier()
        return process_step_capacity_classifier

    def create_capacity_classifier(self) -> CapacityClassifier:
        list_of_start_times = []
        list_of_end_times = []

        for (
            process_step_name
        ) in (
            self.capacity_calculator_process_chain.process_chain.production_plan.process_step_states_dict
        ):
            list_of_process_state_entries = self.capacity_calculator_process_chain.process_chain.production_plan.process_step_states_dict[
                process_step_name
            ]
            if list_of_process_state_entries:
                list_of_start_times.append(list_of_process_state_entries[-1].start_time)
                list_of_end_times.append(list_of_process_state_entries[0].end_time)
        for (
            stream_name
        ) in (
            self.capacity_calculator_process_chain.process_chain.production_plan.stream_state_dict
        ):
            list_of_stream_entries = self.capacity_calculator_process_chain.process_chain.production_plan.stream_state_dict[
                stream_name
            ]
            if list_of_stream_entries:
                # print("stream_name: ", stream_name,"\n", list_of_stream_entries)
                list_of_start_times.append(list_of_stream_entries[-1].start_time)
                list_of_end_times.append(list_of_stream_entries[0].end_time)
        first_start_time = min(list_of_start_times)
        last_end_time = max(list_of_end_times)
        time_period_of_production = last_end_time - first_start_time
        time_normalization_fraction = time_period_of_production / datetime.timedelta(
            hours=1
        )
        if isinstance(
            self.capacity_calculator_process_chain.process_step_output_stream,
            ContinuousStream,
        ):
            maximum_output_operation_rate = (
                self.capacity_calculator_process_chain.process_step_output_stream.static_data.maximum_operation_rate
            )
            target_mass = maximum_output_operation_rate * 1
        elif isinstance(
            self.capacity_calculator_process_chain.process_step_output_stream,
            BatchStream,
        ):
            maximum_batch_mass = (
                self.capacity_calculator_process_chain.process_step_output_stream.static_data.maximum_batch_mass_value
            )
            target_mass = maximum_batch_mass
        hour_normalized_mass = target_mass / time_normalization_fraction
        list_of_output_stream_entries = self.capacity_calculator_process_chain.process_chain.production_plan.stream_state_dict[
            self.capacity_calculator_process_chain.process_step_output_stream.name
        ]

        if len(list_of_output_stream_entries) > 1:
            print(
                """Something went wrong. There should not
                be more than one output stream entry in the production plan"""
            )

        if isinstance(
            self.capacity_calculator_process_chain.process_step_output_stream,
            ContinuousStream,
        ):
            output_stream_state = list_of_output_stream_entries[0]
            output_stream_mass = output_stream_state.total_mass
            output_to_total_length_ratio = (
                output_stream_state.duration / time_period_of_production
            )
            process_step_capacity_classifier = ContinuousCapacityClassifier(
                process_step_name=process_step_name,
                output_stream_length=output_stream_state.duration,
                total_length=time_period_of_production,
                total_output_mass=output_stream_mass,
                first_start_time=first_start_time,
                last_end_time=last_end_time,
                hourly_capacity=hour_normalized_mass,
                output_to_total_length_ratio=output_to_total_length_ratio,
                stream_rate=self.capacity_calculator_process_chain.process_step_output_stream.static_data.maximum_operation_rate,
            )
        elif isinstance(
            self.capacity_calculator_process_chain.process_step_output_stream,
            BatchStream,
        ):
            output_stream_state = list_of_output_stream_entries[0]
            process_step_capacity_classifier = BatchCapacityClassifier(
                process_step_name=process_step_name,
                total_length=time_period_of_production,
                first_start_time=first_start_time,
                last_end_time=last_end_time,
                output_batch_mass=output_stream_state.batch_mass_value,
                hourly_capacity=hour_normalized_mass,
            )
            process_step_capacity_classifier.pretty_print()
        return process_step_capacity_classifier


class CapacityAdjuster:
    def __init__(self, process_step: ProcessStep) -> None:
        self.process_step: ProcessStep = process_step
        self.capacity_calculator: CapacityCalculator = CapacityCalculator(
            process_step=process_step
        )

    def adjust_process_step_capacity(self, target_rate: numbers.Number):
        output_stream = (
            self.capacity_calculator.capacity_calculator_process_chain.process_step_output_stream
        )
        if isinstance(output_stream, ContinuousStream):
            initial_stream_operation_rate = (
                self.capacity_calculator.capacity_calculator_process_chain.process_step_output_stream.static_data.maximum_operation_rate
            )
            print("initial_stream_operation_rate", initial_stream_operation_rate)
        capacity_classifier = (
            self.capacity_calculator.determine_throughput_of_process_step()
        )
        capacity_classifier.pretty_print()
        current_stream_capacity = float(initial_stream_operation_rate)
        # scipy.optimize.minimize()
        target_capacity_ratio = target_rate / capacity_classifier.hourly_capacity
        new_stream_capacity = target_capacity_ratio * current_stream_capacity
        print("target_capacity_ratio", target_capacity_ratio)
        print("new_stream_capacity", new_stream_capacity)
        new_capacity_calculator = CapacityCalculator(process_step=self.process_step)
        new_capacity_calculator.capacity_calculator_process_chain.process_step_output_stream.static_data.maximum_operation_rate = (
            new_stream_capacity
        )
        capacity_classifier = (
            new_capacity_calculator.determine_throughput_of_process_step()
        )
        capacity_classifier.pretty_print()
