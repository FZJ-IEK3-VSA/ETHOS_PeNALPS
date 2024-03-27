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
from ethos_penalps.petri_net.process_state_switch import (
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
    """This class represents a state in the Petri net of a process step. It models
    a type of activity of the ProcessStep"""

    def __init__(
        self,
        process_state_name: str,
        process_step_name: str,
        process_step_data: ProcessStepData,
    ):
        """

        Args:
            process_state_name (str): The name of the process state
                must be unique within the process step.
            process_step_name (str): Name of the process step
                to which this state belongs to.
            process_step_data (ProcessStepData): Contains all data
                that define the simulation state of the process step and all
                methods to alter the state.
        """
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
        """Adds additional information simulation process
        state to the final ProcessStepProductionPlanEntry.

        Args:
            process_state_state (ProcessStateData): Internal simulation state
                that should be converted to a final simulation result.

        Returns:
            ProcessStepProductionPlanEntry: Final simulation result entry.
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
        """Adds the energy data that is required to convert a process state
        in combination with a respective input stream state into a load profile

        Args:
            specific_energy_demand (float): The mass specific energy demand
                that is consumed by the process state. The mass is defined
                the input stream state that precedes the process state.
            load_type (LoadType): The energy carrier that is consumed by the
                process state.
            stream (BatchStream | ContinuousStream): The stream that provides
                the mass that is treated during the process state.

        """
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
        """Adds the ProcessStateEnergyLoadData to the collection of energy data.

        Args:
            process_state_energy_data (ProcessStateEnergyLoadData): Contains
            the information that is required to convert a ProcessStateState
            into a LoadProfileEntry.
        """
        self.process_state_energy_data.add_process_state_energy_load_data(
            process_state_energy_load_data=process_state_energy_data
        )


class OutputStreamProvidingState(ProcessState, ABC):
    """This state models the activity during which a process step
    provides an output stream.
    """

    def __init__(
        self,
        process_state_name: str,
        process_step_name: str,
        process_step_data: ProcessStepData,
        maximum_stream_mass: float | None = None,
    ):
        """
        Args:
            process_state_name (str): The name of the process state
                must be unique within the process step.
            process_step_name (str): Name of the process step
                to which this state belongs to.
            process_step_data (ProcessStepData): Contains all data
                that define the simulation state of the process step and all
                methods to alter the state.
            maximum_stream_mass (float | None, optional): Determines
                the maximum mass can be transported within a single
                output stream state. Defaults to None.
        """
        super().__init__(process_state_name, process_step_name, process_step_data)
        self.maximum_stream_mass = maximum_stream_mass

    def determine_if_stream_mass_can_be_provided(
        self, output_stream_state: ContinuousStreamState | BatchStreamState
    ) -> ContinuousStreamState | BatchStreamState:
        """Check if the required output_mass can be provided under the constraint of
        the maximum stream mass of this process state. Returns an adapted stream state
        if it exceeds the maximum mass.

        Args:
            output_stream_state (ContinuousStreamState | BatchStreamState): The requested
                output stream state that should be checked for the maximum mass constraints.


        Returns:
            ContinuousStreamState | BatchStreamState: The checked and possibly adapted
                stream state.
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

    @abstractmethod
    def check_if_storage_can_supply_output_directly(self) -> bool:
        """Checks if the output stream request can be supplied directly
        from the internal storage without creating an input stream
        request.

        Returns:
            bool: Returns True if the mass can be provided directly.
        """
        raise NotImplementedError


class InputStreamProvidingState(ProcessState, ABC):
    """Models the state at which the process step receives an input stream.
    Contains the method that determines the required input stream state from
    the output stream state.
    """

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
        """Creates another input stream request if the previous input stream state
        did not provide sufficient mass to provide the output stream state.


        Returns:
            ContinuousStreamState | BatchStreamState: The new input stream state that
                is requested from the upstream node.
        """
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
        """Creates the storage entries from the input stream states, output stream
        state and the storage level.
        """
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


        Returns:
            ContinuousStreamState | BatchStreamState: The input stream state that is tries
                to provide the mass for the output stream.
        """
        raise NotImplementedError

    def determine_if_stream_branch_if_fulfilled(self) -> bool:
        """Checks if all streams have been requested and validated.

        Returns:
            bool: Returns True if all required input streams have been
                requested and validated.
        """
        # Must be called after storage is updated
        production_branch_if_fulfilled = (
            self.process_step_data.main_mass_balance.check_if_production_branch_is_fulfilled()
        )
        return production_branch_if_fulfilled

    def determine_if_production_branch_is_fulfilled(self) -> bool:
        """Checks if all stream instances have been requested to provide
        the output stream as requested.

        Returns:
            bool: Returns true if all required input streams states have been
                requested and validated.
        """
        return True


class FullBatchInputStreamProvidingState(InputStreamProvidingState):
    """This state models a process step that always request a fixed input stream
    mass independent from the requested output mass. THis state must be paired with a
    OutputStreamFromStorageState.


    """

    def create_storage_entries(self):
        """Creates the storage entries from the input stream states, output stream
        state and the storage level.
        """
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
        """Creates another input stream request if the previous input stream state
        did not provide sufficient mass to provide the output stream state.


        Returns:
            ContinuousStreamState | BatchStreamState: The new input stream state that
                is requested from the upstream node.
        """
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
        """Creates the initial conversion of an output to an input stream

        The following steps must be conducted the function

        1. Determine end time of the input stream
            1.1. Add the stream end time to time_data class with time_data.set_next_stream_end_time()
        2. Create stream state based on the output stream state and determined end time
        3. Add stream to process step data
        4. Return determined input stream state


        Returns:
            ContinuousStreamState | BatchStreamState: The input stream state that is tries
                to provide the mass for the output stream.
        """
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

    def determine_if_stream_branch_if_fulfilled(self) -> bool:
        """Checks if all streams have been requested and validated.

        Returns:
            bool: Returns True if all required input streams have been
                requested and validated.
        """
        # Must be called after storage is updated
        production_branch_if_fulfilled = (
            self.process_step_data.main_mass_balance.check_if_production_branch_is_fulfilled_with_over_production()
        )
        return production_branch_if_fulfilled


class InputAndOutputStreamProvidingState(
    InputStreamProvidingState, OutputStreamProvidingState, ABC
):
    """This is the abstract class for states with combined input and
    output states. These states model the parallel operation of input
    and output streams.
    """

    @abstractmethod
    def create_storage_entries(self):
        raise NotImplementedError

    @abstractmethod
    def check_if_storage_can_supply_output_directly(self) -> bool:
        raise NotImplementedError


class IntermediateState(ProcessState, ABC):
    """Is the base class for intermediate states between input, output,
    idle state or another intermediate state. These can be used
    to model more details of a production phase.

    """

    def __str__(self) -> str:
        return (
            "Intermediate process state: "
            + str(self.process_state_name)
            + " of process step : "
            + str(self.process_step_name)
        )


class IntermediateStateBasedOnEnergy(IntermediateState):
    """This state models a phase of continuous energy demand between the input, output,
    idle state or another intermediate state.

    """

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
    """This state models the parallel activity of an input and output stream state."""

    def __init__(
        self,
        process_state_name: str,
        process_step_name: str,
        process_step_data: ProcessStepData,
        maximum_stream_mass: float | None = None,
    ):
        """_summary_

        Args:
            process_state_name (str): The name of the process state
                must be unique within the process step.
            process_step_name (str): Name of the process step
                to which this state belongs to.
            process_step_data (ProcessStepData): Contains all data
                that define the simulation state of the process step and all
                methods to alter the state.
            maximum_stream_mass (float | None, optional): Determines
                the maximum mass can be transported within a single
                output stream state. Defaults to None.
        """
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
        """Creates the initial conversion of an output to an input stream

        The following steps must be conducted the function

        1. Determine end time of the input stream
            1.1. Add the stream end time to time_data class with time_data.set_next_stream_end_time()
        2. Create stream state based on the output stream state and determined end time
        3. Add stream to process step data
        4. Return determined input stream state


        Returns:
            ContinuousStreamState | BatchStreamState: The input stream state that is tries
                to provide the mass for the output stream.
        """
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
        """Creates another input stream request if the previous input stream state
        did not provide sufficient mass to provide the output stream state.


        Returns:
            ContinuousStreamState | BatchStreamState: The new input stream state that
                is requested from the upstream node.
        """
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
        """Creates the storage entries from the input stream states, output stream
        state and the storage level.
        """
        self.process_step_data.main_mass_balance.storage.create_all_storage_production_plan_entry(
            exclude_output_times_before_input_end_time=False,
            exclude_output_times_before_input_start_time=True,
            back_calculation=True,
        )

    def check_if_storage_can_supply_output_directly(self) -> bool:
        """Checks if the output stream request can be supplied directly
        from the internal storage without creating an input stream
        request.

        Returns:
            bool: Returns True if the mass can be provided directly.
        """
        return False


class ContinuousOutputStreamProvidingState(OutputStreamProvidingState):
    """This state models the activity during which a process step
    provides a continuous output stream.
    """

    def __init__(
        self,
        process_state_name: str,
        process_step_name: str,
        process_step_data: ProcessStepData,
        maximum_stream_mass: float | None = None,
    ):
        """_summary_

        Args:
            process_state_name (str): The name of the process state
                must be unique within the process step.
            process_step_name (str): Name of the process step
                to which this state belongs to.
            process_step_data (ProcessStepData): Contains all data
                that define the simulation state of the process step and all
                methods to alter the state.
            maximum_stream_mass (float | None, optional): Determines
                the maximum mass can be transported within a single
                output stream state.. Defaults to None.
        """
        super().__init__(process_state_name, process_step_name, process_step_data)
        self.maximum_stream_mass = maximum_stream_mass

    def check_if_storage_can_supply_output_directly(self) -> bool:
        return False


class OutputStreamFromStorageState(OutputStreamProvidingState):
    """Tries to provides the requested output stream directly from
    the internal storage if sufficient mass is available.
    """

    def __init__(
        self,
        process_state_name: str,
        process_step_name: str,
        process_step_data: ProcessStepData,
        maximum_stream_mass: float | None = None,
    ):
        """
        Args:
            process_state_name (str): The name of the process state
                must be unique within the process step.
            process_step_name (str): Name of the process step
                to which this state belongs to.
            process_step_data (ProcessStepData): Contains all data
                that define the simulation state of the process step and all
                methods to alter the state.
            maximum_stream_mass (float | None, optional): Determines
                the maximum mass can be transported within a single
                output stream state.. Defaults to None.
        """
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
    """Models the state at which the process step receives an output stream.
    Contains the method that determines the required input stream state from
    the output stream state.
    """

    def __init__(
        self,
        process_state_name: str,
        process_step_name: str,
        process_step_data: ProcessStepData,
        maximum_stream_mass: float | None = None,
    ):
        """

        Args:
            process_state_name (str): The name of the process state
                must be unique within the process step.
            process_step_name (str): Name of the process step
                to which this state belongs to.
            process_step_data (ProcessStepData): Contains all data
                that define the simulation state of the process step and all
                methods to alter the state.
            maximum_stream_mass (float | None, optional): Determines
                the maximum mass can be transported within a single
                output stream state.. Defaults to None.
        """
        super().__init__(process_state_name, process_step_name, process_step_data)
        self.maximum_stream_mass = maximum_stream_mass

    def check_if_storage_can_supply_output_directly(self) -> bool:
        """Checks if the output stream request can be supplied directly
        from the internal storage without creating an input stream
        request.

        Returns:
            bool: Returns True if the mass can be provided directly.
        """
        return False


class ContinuousInputStreamRequestingStateWithStorage(InputStreamProvidingState):
    """Models the state at which the process step receives a continuous input stream.
    Contains the method that determines the required input stream state from
    the output stream state.
    """

    def determine_required_input_stream_state(self) -> ContinuousStreamState:
        """Determines the required input stream state from the output stream state.

        Returns:
            ContinuousStreamState: New input stream state that is requested from the upstream node.
        """
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
        """Creates the storage entries from the input stream states, output stream
        state and the storage level.
        """
        self.process_step_data.main_mass_balance.storage.create_all_storage_production_plan_entry(
            exclude_output_times_before_input_end_time=False,
            exclude_output_times_before_input_start_time=True,
            back_calculation=True,
        )


class BatchInputStreamRequestingStateWithStorage(InputStreamProvidingState):
    def determine_required_input_stream_state(
        self,
    ) -> BatchStreamState:
        """Determines the required input stream state from the output stream state.

        Returns:
            BatchStreamState: New input stream state that is requested from the upstream node.
        """
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
        """Creates the storage entries from the input stream states, output stream
        state and the storage level.
        """
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
        """Adds additional information simulation process
        state to the final ProcessStepProductionPlanEntry.

        Args:
            process_state_state (ProcessStateData): Internal simulation state
                that should be converted to a final simulation result.

        Returns:
            ProcessStepProductionPlanEntry: Final simulation result entry.
        """
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
    """Models the idle phase of a ProcessStep. The ProcessStep always
    switches back to idle when its not fulfilling any requests.
    """

    def __init__(
        self,
        process_state_name: str,
        process_step_name: str,
        process_step_data: ProcessStepData,
    ):
        """

        Args:
            process_state_name (str): The name of the process state
                must be unique within the process step.
            process_step_name (str): Name of the process step
                to which this state belongs to.
            process_step_data (ProcessStepData): Contains all data
                that define the simulation state of the process step and all
                methods to alter the state.
        """
        super().__init__(process_state_name, process_step_name, process_step_data)

    def __str__(self) -> str:
        return (
            "Idle process state: "
            + str(self.process_state_name)
            + " of process step : "
            + str(self.process_step_name)
        )


class ProcessStateSwitchHandler:
    """Contains all ProcessStateSwitches of the Petri net. A ProcessStateSwitch
    defines the switch condition between states.
    """

    def __init__(self, process_step_data: ProcessStepData):
        """

        Args:
            process_step_data (ProcessStepData): Contains all data
                that define the simulation state of the process step and all
                methods to alter the state.
        """
        self.process_step_data: ProcessStepData = process_step_data
        self.process_state_switch_dictionary: dict[
            StateConnector, ProcessStateSwitch
        ] = {}

    def add_process_state_switch(self, process_state_switch: ProcessStateSwitch):
        """Adds a ProcessStateSwitch instance that defines the switch condition between two states.
        Only a single ProcessStateSwitch is allowed to connect two states.


        Args:
            process_state_switch (ProcessStateSwitch): Defines the switch
                condition between two states.

        """
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
        """This Process state switch connects the arbitrary state to the Idle State
        as end state. This switch is triggered when the process step receives
        a new output stream request.


        Args:
            start_process_state (ProcessState): Name of the process state
                before the idle state in temporal order.
            end_process_state (ProcessState): Name of the idle state of the process
                step.

        Returns:
            ProcessStateSwitchAtNextDiscreteEvent: Returns the ProcessStateSwitch
                so it can integrated into a suitable selector.
        """
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
        """Creates an StateSwitch that triggers the switch to the input state.
        The end state must always be at the input state.

        Args:
            start_process_state (ProcessState): Name of the previous state in temporal
                order.
            end_process_state (ProcessState): Name of the input stream state.

        Returns:
            ProcessStateSwitchAtInputStreamProvided: Returns the ProcessStateSwitch
                so it can integrated into a suitable selector.
        """
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
        """Creates an StateSwitch that triggers the switch to the output state.
        The end state must always be at the output state.

        Args:
            start_process_state (ProcessState): Name of the previous state in temporal
                order.
            end_process_state (ProcessState): Name of the output stream state.

        Returns:
            ProcessStateSwitchAtOutputStreamProvided:  Returns the ProcessStateSwitch
                so it can integrated into a suitable selector.
        """
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
        """Creates a process state switch that triggers  the state switch
        from the start process to the end process after a fixed delay.

        Args:
            start_process_state (ProcessState): Name of the previous state in temporal
                order.
            end_process_state (ProcessState): Name of the target state in temporal
                order.
            delay (datetime.timedelta): Determines the duration from start to end time of the
                end process state.

        Returns:
            ProcessStateSwitchDelay: Returns the ProcessStateSwitch
                so it can integrated into a suitable selector.
        """
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
        """Creates a process state switch that triggers the switch to a
        combined input and output state of the ProcessStep.

        Args:
            start_process_state (ProcessState): Name of the previous state in temporal
                order.
            end_process_state (ProcessState): State name of the combined input and output
                state.

        Returns:
            ProcessStateSwitchAfterInputAndOutputStream: Returns the ProcessStateSwitch
                so it can integrated into a suitable selector.
        """
        return ProcessStateSwitchAfterInputAndOutputStream(
            process_step_data=self.process_step_data,
            state_connector=StateConnector(
                start_state_name=start_process_state.process_state_name,
                end_state_name=end_process_state.process_state_name,
            ),
        )
