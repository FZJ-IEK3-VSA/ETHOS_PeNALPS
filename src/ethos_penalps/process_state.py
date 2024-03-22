import datetime
import numbers
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ethos_penalps.data_classes import (
    Commodity,
    ProcessStateData,
    ProcessStepProductionPlanEntry,
    StateConnector,
    ProcessStateEnergyData,
)
from ethos_penalps.load_profile_calculator import (
    LoadType,
    ProcessStateEnergyLoadData,
    ProcessStateEnergyLoadDataBasedOnStreamMass,
)
from ethos_penalps.process_state_switch import (
    ProcessStateSwitch,
    ProcessStateSwitchAfterInputAndOutputStream,
    ProcessStateSwitchAtInputStreamProvided,
    ProcessStateSwitchAtNextDiscreteEvent,
    ProcessStateSwitchAtOutputStreamProvided,
    ProcessStateSwitchDelay,
)
from ethos_penalps.process_step_data import ProcessStepData
from ethos_penalps.simulation_data.container_simulation_data import (
    PreProductionStateData,
    ValidatedPostProductionStateData,
)
from ethos_penalps.storage import Storage
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamProductionPlanEntry,
    BatchStreamState,
    ContinuousStream,
    ContinuousStreamProductionPlanEntry,
    ContinuousStreamState,
    ProcessStepProductionPlanEntryWithInputStreamState,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.exceptions_and_warnings import UnexpectedDataType
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger


logger = PeNALPSLogger.get_logger_without_handler()


class ProcessState(ABC):
    """This class represents a state in the Petri net ofa process step. It models
    a type of activity of the ProcessStep"""

    def __init__(
        self,
        process_state_name: str,
        process_step_name: str,
        process_step_data: ProcessStepData,
    ):
        self.process_state_name: str = process_state_name
        self.next_process_state_end_time: datetime.datetime
        self.start_time: datetime.datetime
        self.end_time: datetime.datetime
        self.process_step_name: str = process_step_name
        self.process_step_data: ProcessStepData = process_step_data
        self.process_state_energy_data: ProcessStateEnergyData = ProcessStateEnergyData(
            process_step_name=self.process_step_name,
            process_state_name=self.process_state_name,
        )

    def _create_process_step_production_plan_entry(
        self, process_state_state: ProcessStateData
    ) -> ProcessStepProductionPlanEntry:
        """Creates ProcessStepProductionPlanEntry

        Args:
            process_state_state (ProcessStateData): _description_

        Returns:
            ProcessStepProductionPlanEntry: _description_
        """
        entry = ProcessStepProductionPlanEntry(
            process_step_name=self.process_step_name,
            process_state_name=self.process_state_name,
            start_time=process_state_state.start_time,
            end_time=process_state_state.end_time,
            duration=str(process_state_state.end_time - process_state_state.start_time),
            process_state_type=str(type(self)),
        )
        logger.debug(
            "The following ProcessStepProductionPlanEntry has been created: %s",
            str(entry),
        )
        return entry

    def create_process_state_energy_data_based_on_stream_mass(
        self,
        specific_energy_demand: float,
        load_type: LoadType,
        stream: BatchStream | ContinuousStream,
    ):
        if isinstance(stream, (BatchStream, ContinuousStream)):
            new_energy_data = ProcessStateEnergyLoadDataBasedOnStreamMass(
                process_step_name=self.process_step_name,
                process_state_name=self.process_state_name,
                specific_energy_demand=specific_energy_demand,
                load_type=load_type,
                stream_name=stream.name,
            )
            self.add_process_state_energy_data(
                process_state_energy_data=new_energy_data
            )
        else:
            raise Exception(
                "Expected a stream of type BatchStream or ContinuousStream but got: "
                + str(stream)
            )

    def add_process_state_energy_data(
        self, process_state_energy_data: ProcessStateEnergyLoadData
    ):
        self.process_state_energy_data.add_process_state_energy_load_data(
            process_state_energy_load_data=process_state_energy_data
        )


class OutputStreamProvidingState(ProcessState, ABC):
    """During the activity of this state  a

    Args:
        ProcessState (_type_): _description_
        ABC (_type_): _description_
    """

    def __init__(
        self,
        process_state_name: str,
        process_step_name: str,
        process_step_data: ProcessStepData,
        maximum_stream_mass: float | None = None,
    ):
        super().__init__(process_state_name, process_step_name, process_step_data)
        self.maximum_stream_mass = maximum_stream_mass

    def determine_if_stream_mass_can_be_provided(
        self, output_stream_state: ContinuousStreamState | BatchStreamState
    ) -> ContinuousStreamState | BatchStreamState:
        """Check if the required output_mass can be provided under the constraint of
        the maximum stream mass of this process state. Returns an adapted state
        if it exceeds the maximum mass.

        :param output_stream_state: _description_
        :type output_stream_state: ContinuousStreamState | BatchStreamState
        :raises Exception: _description_
        :raises Exception: _description_
        :return: _description_
        :rtype: ContinuousStreamState | BatchStreamState
        """
        if self.maximum_stream_mass is None:
            feasible_output_stream_state = output_stream_state
        elif isinstance(self.maximum_stream_mass, numbers.Number):
            output_stream = self.process_step_data.stream_handler.get_stream(
                stream_name=output_stream_state.name
            )

            produced_mass = output_stream.get_produced_amount(state=output_stream_state)
            if produced_mass <= self.maximum_stream_mass:
                feasible_output_stream_state = output_stream_state
            elif produced_mass > self.maximum_stream_mass:
                feasible_mass = self.maximum_stream_mass
                if isinstance(output_stream, BatchStream):
                    feasible_output_stream_state = output_stream.create_batch_state(
                        end_time=output_stream_state.end_time,
                        batch_mass_value=feasible_mass,
                    )
                elif isinstance(output_stream_state, ContinuousStream):
                    # start_time = output_stream.determine_start_time(
                    #     end_time=output_stream_state.end_time,
                    #     total_transported_mass=self.maximum_stream_mass,
                    #     operation_rate=output_stream_state.current_operation_rate,
                    # )
                    feasible_output_stream_state = (
                        output_stream.create_stream_state_for_commodity_amount(
                            commodity_amount=self.maximum_stream_mass,
                            end_time=output_stream_state.end_time,
                        )
                    )

                else:
                    raise Exception("Unexpected stream datatype: " + str(output_stream))

        else:
            raise Exception(
                "Unexpected data type in self.maximum_stream_mass: "
                + str(self.maximum_stream_mass)
            )
        return feasible_output_stream_state

    def determine_if_storage_level_is_within_limits(self):
        pass

    @abstractmethod
    def check_if_storage_can_supply_output_directly(self) -> bool:
        raise NotImplementedError


class InputStreamProvidingState(ProcessState, ABC):
    # def __init__(
    #     self,
    #     process_state_name: str,
    #     process_step_name: str,
    #     process_step_data: ProcessStepData,
    # ):
    #     super().__init__(process_state_name, process_step_name, process_step_data)

    def __str__(self) -> str:
        return "InputStreamProvidingState with name: " + self.process_state_name

    def fulfill_order(self) -> ContinuousStreamState | BatchStreamState:
        self.process_step_data.state_data_container.get_validated_production_state_data()

        next_stream_end_time_from_previous_streams = (
            self.process_step_data.main_mass_balance.determine_next_stream_end_time_from_previous_input_streams()
        )
        last_process_state_switch_time = (
            self.process_step_data.time_data.get_last_process_state_switch_time()
        )
        next_stream_end_time = min(
            next_stream_end_time_from_previous_streams, last_process_state_switch_time
        )
        self.process_step_data.time_data.set_next_stream_end_time(
            next_stream_end_time=next_stream_end_time
        )
        input_stream = self.process_step_data.stream_handler.get_stream(
            stream_name=self.process_step_data.main_mass_balance.main_input_stream_name
        )
        if isinstance(input_stream, ContinuousStream):
            required_input_stream_state = (
                self.process_step_data.main_mass_balance.set_continuous_input_stream_according_to_output_stream_with_storage()
            )
        elif isinstance(input_stream, BatchStream):
            required_input_stream_state = (
                self.process_step_data.main_mass_balance.set_batch_input_stream_according_to_output_stream_with_storage()
            )
        self.process_step_data.state_data_container.add_input_stream_to_validated_data(
            new_input_stream_state=required_input_stream_state
        )

        return required_input_stream_state

    @abstractmethod
    def create_storage_entries(self):
        raise NotImplementedError

    @abstractmethod
    def determine_required_input_stream_state(
        self,
    ) -> ContinuousStreamState | BatchStreamState:
        """Creates the initial conversion of an output to an input stream

        The following steps must be conducted the function

        1. Determine end time of the input stream
            1.1. Add the stream end time to time_data class with time_data.set_next_stream_end_time()
        2. Create stream state based on the output stream state and determined end time
        3. Add stream to process step data
        4. Return determined input stream state
        """

        raise NotImplementedError

    def determine_if_stream_branch_if_fulfilled(self) -> bool:
        # Must be called after storage is updated
        production_branch_if_fulfilled = (
            self.process_step_data.main_mass_balance.check_if_production_branch_is_fulfilled()
        )
        return production_branch_if_fulfilled

    def determine_if_production_branch_is_fulfilled(self) -> bool:
        return True


class FullBatchInputStreamProvidingState(InputStreamProvidingState):
    def create_storage_entries(self):
        state_data = (
            self.process_step_data.state_data_container.get_validated_pre_or_post_production_state()
        )
        if isinstance(state_data, ValidatedPostProductionStateData):
            self.process_step_data.main_mass_balance.storage.create_all_storage_production_plan_entry(
                exclude_output_times_before_input_end_time=True,
                exclude_output_times_before_input_start_time=False,
                back_calculation=False,
            )

        elif type(state_data) is PreProductionStateData:
            self.process_step_data.main_mass_balance.storage.create_storage_entries_without_inputstream_and_consuming_output()

    def fulfill_order(self) -> ContinuousStreamState | BatchStreamState:
        self.process_step_data.state_data_container.get_validated_production_state_data()

        next_stream_end_time_from_previous_streams = (
            self.process_step_data.main_mass_balance.determine_next_stream_end_time_from_previous_input_streams()
        )
        last_process_state_switch_time = (
            self.process_step_data.time_data.get_last_process_state_switch_time()
        )
        next_stream_end_time = min(
            next_stream_end_time_from_previous_streams, last_process_state_switch_time
        )
        self.process_step_data.time_data.set_next_stream_end_time(
            next_stream_end_time=next_stream_end_time
        )
        input_stream = self.process_step_data.stream_handler.get_stream(
            stream_name=self.process_step_data.main_mass_balance.main_input_stream_name
        )
        if isinstance(input_stream, ContinuousStream):
            raise Exception(
                "Stream of wrong type is connected to the process step: "
                + self.process_step_name
            )
        if isinstance(input_stream, BatchStream):
            input_stream: BatchStream = (
                self.process_step_data.stream_handler.get_stream(
                    stream_name=self.process_step_data.main_mass_balance.main_input_stream_name
                )
            )
            next_stream_end_time = (
                self.process_step_data.time_data.get_next_stream_end_time()
            )
            batch_max_value = input_stream.static_data.maximum_batch_mass_value
            if batch_max_value is None:
                raise Exception(
                    "No batch max value has been set for stream:"
                    + input_stream.name
                    + " which is required in process step: "
                    + self.process_step_name
                )
            required_input_stream_state = input_stream.create_batch_state(
                end_time=next_stream_end_time,
                batch_mass_value=input_stream.static_data.maximum_batch_mass_value,
            )
        self.process_step_data.state_data_container.add_input_stream_to_validated_data(
            new_input_stream_state=required_input_stream_state
        )

        return required_input_stream_state

    def determine_required_input_stream_state(
        self,
    ) -> ContinuousStreamState | BatchStreamState:
        input_stream = self.process_step_data.stream_handler.get_stream(
            stream_name=self.process_step_data.main_mass_balance.main_input_stream_name
        )

        if isinstance(input_stream, ContinuousStream):
            raise Exception(
                "Stream of wrong type is connected to the process step: "
                + self.process_step_name
            )

        if isinstance(input_stream, BatchStream):
            next_stream_end_time = (
                self.process_step_data.main_mass_balance.determine_required_batch_end_time_to_fulfill_storage()
            )
            self.process_step_data.time_data.set_next_stream_end_time(
                next_stream_end_time=next_stream_end_time
            )
            input_stream: BatchStream = (
                self.process_step_data.stream_handler.get_stream(
                    stream_name=self.process_step_data.main_mass_balance.main_input_stream_name
                )
            )
            next_stream_end_time = (
                self.process_step_data.time_data.get_next_stream_end_time()
            )
            batch_max_value = input_stream.static_data.maximum_batch_mass_value
            if batch_max_value is None:
                raise Exception(
                    "No batch max value has been set for stream:"
                    + input_stream.name
                    + " which is required in process step: "
                    + self.process_step_name
                )
            required_input_stream_state = input_stream.create_batch_state(
                end_time=next_stream_end_time,
                batch_mass_value=input_stream.static_data.maximum_batch_mass_value,
            )

        else:
            raise Exception("Case not implemented yet")

        self.process_step_data.state_data_container.add_first_input_stream_state(
            first_input_stream_state=required_input_stream_state
        )

        return required_input_stream_state

    def determine_if_storage_level_is_within_limits(self):
        pass
        # TODO add check for flexible storage range

    def determine_if_stream_branch_if_fulfilled(self) -> bool:
        # Must be called after storage is updated
        production_branch_if_fulfilled = (
            self.process_step_data.main_mass_balance.check_if_production_branch_is_fulfilled_with_over_production()
        )
        return production_branch_if_fulfilled


class InputAndOutputStreamProvidingState(
    InputStreamProvidingState, OutputStreamProvidingState, ABC
):
    @abstractmethod
    def create_storage_entries(self):
        raise NotImplementedError

    @abstractmethod
    def check_if_storage_can_supply_output_directly(self) -> bool:
        raise NotImplementedError


class IntermediateState(ProcessState, ABC):
    def __str__(self) -> str:
        return (
            "Intermediate process state: "
            + str(self.process_state_name)
            + " of process step : "
            + str(self.process_step_name)
        )


class IntermediateStateBasedOnEnergy(IntermediateState):
    def _create_process_step_production_plan_entry(
        self,
        process_state_state: ProcessStateData,
        input_stream_state: (
            BatchStreamProductionPlanEntry | ContinuousStreamProductionPlanEntry
        ),
    ) -> ProcessStepProductionPlanEntry:
        if isinstance(input_stream_state, BatchStreamProductionPlanEntry):
            total_stream_mass = input_stream_state.batch_mass_value
        elif isinstance(input_stream_state, ContinuousStreamProductionPlanEntry):
            total_stream_mass = input_stream_state.total_mass
        entry = ProcessStepProductionPlanEntryWithInputStreamState(
            process_step_name=self.process_step_name,
            process_state_name=self.process_state_name,
            start_time=process_state_state.start_time,
            end_time=process_state_state.end_time,
            duration=str(process_state_state.end_time - process_state_state.start_time),
            process_state_type=str(type(self)),
            stream_start_time=input_stream_state.start_time,
            stream_end_time=input_stream_state.end_time,
            total_stream_mass=total_stream_mass,
        )
        logger.debug(entry)
        return entry


class ProcessStateParallelContinuousInputWithStorage(
    InputAndOutputStreamProvidingState
):
    def __init__(
        self,
        process_state_name: str,
        process_step_name: str,
        process_step_data: ProcessStepData,
        maximum_stream_mass: float | None = None,
    ):
        super().__init__(process_state_name, process_step_name, process_step_data)
        self.maximum_stream_mass = maximum_stream_mass

    def __str__(self) -> str:
        return (
            "Production process state: "
            + str(self.process_state_name)
            + " of process step : "
            + str(self.process_step_name)
        )

    def determine_required_input_stream_state(
        self,
    ) -> BatchStreamState | ContinuousStreamState:
        state_data = (
            self.process_step_data.state_data_container.get_pre_production_state_data()
        )
        output_stream_state = state_data.current_output_stream_state
        output_stream = self.process_step_data.stream_handler.get_stream(
            stream_name=output_stream_state.name
        )
        input_stream = self.process_step_data.stream_handler.get_stream(
            stream_name=self.process_step_data.main_mass_balance.main_input_stream_name
        )
        full_output_mass = output_stream.get_produced_amount(state=output_stream_state)
        last_process_state_switch_time = (
            self.process_step_data.time_data.get_last_process_state_switch_time()
        )

        if isinstance(output_stream, ContinuousStream) and isinstance(
            input_stream, ContinuousStream
        ):
            self.process_step_data.time_data.set_next_stream_end_time(
                next_stream_end_time=last_process_state_switch_time
            )
            input_stream_state = (
                self.process_step_data.main_mass_balance.set_continuous_operation_rate_for_parallel_input_and_output_stream_with_storage()
            )

        elif isinstance(input_stream, BatchStream) and isinstance(
            output_stream, ContinuousStream
        ):
            next_stream_end_time = (
                self.process_step_data.main_mass_balance.determine_required_batch_end_time_to_fulfill_storage()
            )
            self.process_step_data.time_data.set_next_stream_end_time(
                next_stream_end_time=next_stream_end_time
            )
            input_stream_state = (
                self.process_step_data.main_mass_balance.set_batch_stream_for_parallel_input_and_output_with_storage()
            )
        elif isinstance(input_stream, ContinuousStream) and isinstance(
            output_stream, BatchStream
        ):
            self.process_step_data.time_data.set_next_stream_end_time(
                next_stream_end_time=last_process_state_switch_time
            )
            input_stream_state = (
                self.process_step_data.main_mass_balance.set_continuous_input_stream_according_to_output_stream_with_storage()
            )
        else:
            raise Exception("Case not implemented yet")

        self.process_step_data.state_data_container.add_first_input_stream_state(
            first_input_stream_state=input_stream_state
        )

        return input_stream_state

    def fulfill_order(self) -> BatchStreamState:
        state_data = (
            self.process_step_data.state_data_container.get_validated_production_state_data()
        )
        output_stream_state = state_data.current_output_stream_state
        output_stream = self.process_step_data.stream_handler.get_stream(
            stream_name=output_stream_state.name
        )
        input_stream = self.process_step_data.stream_handler.get_stream(
            stream_name=self.process_step_data.main_mass_balance.main_input_stream_name
        )
        full_output_mass = output_stream.get_produced_amount(state=output_stream_state)
        last_process_state_switch_time = (
            self.process_step_data.time_data.get_last_process_state_switch_time()
        )

        if isinstance(output_stream, ContinuousStream) and isinstance(
            input_stream, ContinuousStream
        ):
            self.process_step_data.time_data.set_next_stream_end_time(
                next_stream_end_time=last_process_state_switch_time
            )
            input_stream_state = (
                self.process_step_data.main_mass_balance.set_continuous_operation_rate_for_parallel_input_and_output_stream_with_storage()
            )

        elif isinstance(input_stream, BatchStream) and isinstance(
            output_stream, ContinuousStream
        ):
            next_stream_end_time = (
                self.process_step_data.main_mass_balance.determine_required_batch_end_time_to_fulfill_storage()
            )
            self.process_step_data.time_data.set_next_stream_end_time(
                next_stream_end_time=next_stream_end_time
            )
            input_stream_state = (
                self.process_step_data.main_mass_balance.set_batch_stream_for_parallel_input_and_output_with_storage()
            )
        else:
            raise Exception("Case not implemented yet")

        self.process_step_data.state_data_container.add_input_stream_to_validated_data(
            new_input_stream_state=input_stream_state
        )

        return input_stream_state

    def create_storage_entries(self):
        self.process_step_data.main_mass_balance.storage.create_all_storage_production_plan_entry(
            exclude_output_times_before_input_end_time=False,
            exclude_output_times_before_input_start_time=True,
            back_calculation=True,
        )

    def check_if_storage_can_supply_output_directly(self) -> bool:
        return False


class ContinuousOutputStreamProvidingState(OutputStreamProvidingState):
    def __init__(
        self,
        process_state_name: str,
        process_step_name: str,
        process_step_data: ProcessStepData,
        maximum_stream_mass: float | None = None,
    ):
        super().__init__(process_state_name, process_step_name, process_step_data)
        self.maximum_stream_mass = maximum_stream_mass

    def check_if_storage_can_supply_output_directly(self) -> bool:
        return False


class OutputStreamFromStorageState(OutputStreamProvidingState):
    def __init__(
        self,
        process_state_name: str,
        process_step_name: str,
        process_step_data: ProcessStepData,
        maximum_stream_mass: float | None = None,
    ):
        super().__init__(process_state_name, process_step_name, process_step_data)
        self.maximum_stream_mass = maximum_stream_mass

    def check_if_storage_can_supply_output_directly(self) -> bool:
        direct_mass_supply_is_possible = (
            self.process_step_data.main_mass_balance.check_if_output_stream_can_be_supplied_directly_from_storage()
        )
        return direct_mass_supply_is_possible

    # def create_output_stream_from_storage(self):
    #     self.process_step_data.main_mass_balance.storage.create_storage_entries_without_inputstream_and_consuming_output(
    #         exclude_output_times_before_input_end_time=False,
    #         exclude_output_times_before_input_start_time=False,
    #     )


class BatchOutputStreamProvidingState(OutputStreamProvidingState):
    def __init__(
        self,
        process_state_name: str,
        process_step_name: str,
        process_step_data: ProcessStepData,
        maximum_stream_mass: float | None = None,
    ):
        super().__init__(process_state_name, process_step_name, process_step_data)
        self.maximum_stream_mass = maximum_stream_mass

    def check_if_storage_can_supply_output_directly(self) -> bool:
        return False


class ContinuousInputStreamRequestingStateWithStorage(InputStreamProvidingState):
    def determine_required_input_stream_state(self) -> ContinuousStreamState:
        # Determine end time of the input stream
        next_stream_end_time = (
            self.process_step_data.time_data.get_next_process_state_switch_time()
        )
        self.process_step_data.time_data.set_next_stream_end_time(
            next_stream_end_time=next_stream_end_time
        )

        input_stream = self.process_step_data.stream_handler.get_stream(
            stream_name=self.process_step_data.main_mass_balance.main_input_stream_name
        )
        # Check if correct stream is connected to the state
        if isinstance(input_stream, ContinuousStream):
            # Create stream state based on the output stream state and determined end time
            input_stream_state = (
                self.process_step_data.main_mass_balance.set_continuous_input_stream_according_to_output_stream_with_storage()
            )
        else:
            raise Exception(
                "Wrong stream is connected to this state: " + self.process_state_name
            )
        # Add stream to process step data
        self.process_step_data.state_data_container.add_first_input_stream_state(
            first_input_stream_state=input_stream_state
        )

        return input_stream_state

    def create_storage_entries(self):
        self.process_step_data.main_mass_balance.storage.create_all_storage_production_plan_entry(
            exclude_output_times_before_input_end_time=False,
            exclude_output_times_before_input_start_time=True,
            back_calculation=True,
        )


class BatchInputStreamRequestingStateWithStorage(InputStreamProvidingState):
    def determine_required_input_stream_state(
        self,
    ) -> BatchStreamState:
        # Determine end time of the input stream
        next_stream_end_time = (
            self.process_step_data.time_data.get_next_process_state_switch_time()
        )
        self.process_step_data.time_data.set_next_stream_end_time(
            next_stream_end_time=next_stream_end_time
        )
        # Check if correct stream is connected to the state
        input_stream = self.process_step_data.stream_handler.get_stream(
            stream_name=self.process_step_data.main_mass_balance.main_input_stream_name
        )
        if isinstance(input_stream, BatchStream):
            # Create stream state based on the output stream state and determined end time
            input_stream_state = (
                self.process_step_data.main_mass_balance.set_batch_input_stream_according_to_output_stream_with_storage()
            )
        else:
            raise Exception(
                "Wrong stream is connected to this state: " + self.process_state_name
            )
        # Add stream to process step data
        self.process_step_data.state_data_container.add_first_input_stream_state(
            first_input_stream_state=input_stream_state
        )

        return input_stream_state

    def create_storage_entries(self):
        self.process_step_data.main_mass_balance.storage.create_all_storage_production_plan_entry(
            exclude_output_times_before_input_end_time=True,
            exclude_output_times_before_input_start_time=False,
            back_calculation=True,
        )


class BatchInputStreamRequestingStateWithStorageEnergyBasedOnStream(
    BatchInputStreamRequestingStateWithStorage
):
    def _create_process_step_production_plan_entry(
        self,
        process_state_state: ProcessStateData,
        input_stream_state: ContinuousStreamState | BatchStreamState,
    ) -> ProcessStepProductionPlanEntry:
        self.process_state_energy_data_dict

        entry = ProcessStepProductionPlanEntryWithInputStreamState(
            process_step_name=self.process_step_name,
            process_state_name=self.process_state_name,
            start_time=process_state_state.start_time,
            end_time=process_state_state.end_time,
            duration=str(process_state_state.end_time - process_state_state.start_time),
            process_state_type=str(type(self)),
            input_stream_state=input_stream_state,
        )

        logger.debug(entry)
        return entry


class ProcessStateIdle(ProcessState):
    def __init__(
        self,
        process_state_name: str,
        process_step_name: str,
        process_step_data: ProcessStepData,
    ):
        super().__init__(process_state_name, process_step_name, process_step_data)

    def __str__(self) -> str:
        return (
            "Idle process state: "
            + str(self.process_state_name)
            + " of process step : "
            + str(self.process_step_name)
        )


class ProcessStateSwitchHandler:
    def __init__(self, process_step_data: ProcessStepData):
        self.process_step_data: ProcessStepData = process_step_data
        self.process_state_switch_dictionary: dict[
            StateConnector, ProcessStateSwitch
        ] = {}

    def add_process_state_switch(self, process_state_switch: ProcessStateSwitch):
        if process_state_switch.state_connector in self.process_state_switch_dictionary:
            raise Exception(
                "Process state connector :"
                + str(process_state_switch.state_connector)
                + " is already in process state switch dictionary of :"
                + str(self.process_step_data.process_step_name)
            )
        self.process_state_switch_dictionary[process_state_switch.state_connector] = (
            process_state_switch
        )

    def create_process_state_switch_at_next_discrete_event(
        self, start_process_state: ProcessState, end_process_state: ProcessState
    ) -> ProcessStateSwitchAtNextDiscreteEvent:
        process_state_switch = ProcessStateSwitchAtNextDiscreteEvent(
            state_connector=StateConnector(
                start_state_name=start_process_state.process_state_name,
                end_state_name=end_process_state.process_state_name,
            ),
            process_step_data=self.process_step_data,
        )
        self.add_process_state_switch(process_state_switch=process_state_switch)
        return process_state_switch

    def create_process_state_switch_at_input_stream(
        self, start_process_state: ProcessState, end_process_state: ProcessState
    ) -> ProcessStateSwitchAtInputStreamProvided:
        process_state_switch = ProcessStateSwitchAtInputStreamProvided(
            state_connector=StateConnector(
                start_state_name=start_process_state.process_state_name,
                end_state_name=end_process_state.process_state_name,
            ),
            process_step_data=self.process_step_data,
        )
        self.add_process_state_switch(process_state_switch=process_state_switch)
        return process_state_switch

    def create_process_state_switch_at_output_stream(
        self, start_process_state: ProcessState, end_process_state: ProcessState
    ) -> ProcessStateSwitchAtOutputStreamProvided:
        process_state_switch = ProcessStateSwitchAtOutputStreamProvided(
            state_connector=StateConnector(
                start_state_name=start_process_state.process_state_name,
                end_state_name=end_process_state.process_state_name,
            ),
            process_step_data=self.process_step_data,
        )
        self.add_process_state_switch(process_state_switch=process_state_switch)
        return process_state_switch

    def create_process_state_switch_delay(
        self,
        start_process_state: ProcessState,
        end_process_state: ProcessState,
        delay: datetime.timedelta,
    ) -> ProcessStateSwitchDelay:
        state_connector = StateConnector(
            start_state_name=start_process_state.process_state_name,
            end_state_name=end_process_state.process_state_name,
        )
        process_state_switch_delay = ProcessStateSwitchDelay(
            process_step_data=self.process_step_data,
            state_connector=state_connector,
            delay=delay,
        )

        self.add_process_state_switch(process_state_switch=process_state_switch_delay)
        return process_state_switch_delay

    def create_process_state_switch_after_output_and_input_stream(
        self, start_process_state: ProcessState, end_process_state: ProcessState
    ) -> ProcessStateSwitchAfterInputAndOutputStream:
        return ProcessStateSwitchAfterInputAndOutputStream(
            process_step_data=self.process_step_data,
            state_connector=StateConnector(
                start_state_name=start_process_state.process_state_name,
                end_state_name=end_process_state.process_state_name,
            ),
        )
