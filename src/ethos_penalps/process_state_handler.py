import datetime

from ethos_penalps.data_classes import (
    OutputBranchIdentifier,
    ProcessStateData,
    ProcessStepProductionPlanEntry,
)
from ethos_penalps.process_state import (
    BatchInputStreamRequestingStateWithStorage,
    BatchInputStreamRequestingStateWithStorageEnergyBasedOnStream,
    BatchOutputStreamProvidingState,
    ContinuousInputStreamRequestingStateWithStorage,
    ContinuousOutputStreamProvidingState,
    FullBatchInputStreamProvidingState,
    InputAndOutputStreamProvidingState,
    InputStreamProvidingState,
    IntermediateState,
    IntermediateStateBasedOnEnergy,
    OutputStreamFromStorageState,
    OutputStreamProvidingState,
    ProcessState,
    ProcessStateIdle,
    ProcessStateParallelContinuousInputWithStorage,
)
from ethos_penalps.process_state_switch import ProcessStateSwitch
from ethos_penalps.process_state_switch_selector import (
    MultiTargetSelector,
    ProcessStateSwitchSelectorHandler,
)
from ethos_penalps.process_step_data import ProcessStepData
from ethos_penalps.simulation_data.container_branch_data import (
    IncompleteOutputBranchData,
    OutputBranchData,
)
from ethos_penalps.simulation_data.container_simulation_data import (
    CurrentProductionStateData,
    PreProductionStateData,
    UninitializedCurrentStateData,
    ValidatedPostProductionStateData,
)
from ethos_penalps.stream import BatchStreamState, ContinuousStreamState
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class ProcessStateHandler:
    """
    The ProcessStateHandler contains all objects necessary to switch the process states of a process step.
    Its core functionality is to switch between Idle, InputRequestingProcessStates, OutputProvidingProcessStates.
    In order to switch from the current process state the process_state_switch_selector_handler is required.
    It determines which process_state_switch is conducted. This allows multi path routes in a network of process states.
    The process state switch determines the next process state and the switch time of the process state.
    The process_state_dictionary must contain an idle, input requesting and output providing process state.
    """

    def __init__(self, process_step_data: ProcessStepData) -> None:
        self.process_state_dictionary: dict[str, ProcessState] = {}
        self.process_state_switch_selector_handler = ProcessStateSwitchSelectorHandler(
            process_step_data=process_step_data
        )
        self.process_step_data: ProcessStepData = process_step_data
        self.output_stream_providing_state_name: str
        self.input_stream_providing_state_name: str
        self.idle_process_state_name: str

    def switch_to_output_stream_providing_state(
        self, activation_date: datetime.datetime
    ) -> OutputStreamProvidingState:
        logger.debug("Start switch to output request state")
        self.process_step_data.time_data.set_next_process_state_switch_time(
            next_discrete_event_time=activation_date
        )
        state_data = (
            self.process_step_data.state_data_container.get_validated_pre_or_post_production_state()
        )
        current_process_state = self.get_process_state(
            state_data.current_process_state_name
        )
        if isinstance(current_process_state, OutputStreamProvidingState):
            raise Exception("production process state is already implemented")
        archive_state_list = []

        while not isinstance(current_process_state, OutputStreamProvidingState):
            current_process_state = self.switch_to_previous_state()
            if current_process_state in archive_state_list:
                raise Exception("Found a closed loop in state switches")
            else:
                archive_state_list.append(current_process_state)

        return current_process_state

    def switch_to_input_stream_requesting_state(
        self, force_first_switch: bool = False
    ) -> InputStreamProvidingState:
        logger.debug("Start switch to input request state")

        state_data = (
            self.process_step_data.state_data_container.get_validated_pre_or_post_production_state()
        )
        current_process_state = self.get_process_state(
            state_data.current_process_state_name
        )

        if force_first_switch is True:
            current_process_state = self.switch_to_previous_state()

        archive_state_list = []

        while not isinstance(current_process_state, InputStreamProvidingState):
            current_process_state = self.switch_to_previous_state()
            if current_process_state in archive_state_list:
                raise Exception("Found a closed loop in state switches")
            else:
                archive_state_list.append(current_process_state)

        return current_process_state

    def switch_to_idle_state(
        self,
    ) -> ProcessStateIdle:
        logger.debug("Start switch to idle state")

        state_data = (
            self.process_step_data.state_data_container.get_validated_pre_or_post_production_state()
        )
        current_process_state = self.get_process_state(
            state_data.current_process_state_name
        )
        archive_state_list = []

        while not isinstance(current_process_state, ProcessStateIdle):
            current_process_state = self.switch_to_previous_state()
            if current_process_state in archive_state_list:
                raise Exception("Found a closed loop in state switches")
            else:
                archive_state_list.append(current_process_state)
        idle_process_state = current_process_state
        self.process_step_data.time_data.set_next_event_time_as_last_idle_time()
        return idle_process_state

    def check_if_multiple_target_states_are_possible(self):
        state_data = (
            self.process_step_data.state_data_container.get_validated_pre_or_post_production_state()
        )

        switch_selector = self.process_state_switch_selector_handler.get_switch_selector_to_previous_state(
            current_process_state_name=state_data.current_process_state_name
        )
        if isinstance(switch_selector, MultiTargetSelector):
            is_multi_target = True
        else:
            is_multi_target = False

        return is_multi_target

    def get_earliest_output_stream_production_time(
        self,
    ) -> datetime.datetime:
        logger.debug("determine earliest output stream providing date")
        earliest_process_state_switch_date = (
            self.process_step_data.time_data.get_last_idle_date()
        )
        production_state = self.switch_to_output_stream_providing_state(
            activation_date=earliest_process_state_switch_date
        )

        earliest_output_date_time = (
            self.process_step_data.time_data.get_last_process_state_switch_time()
        )
        return earliest_output_date_time

    def switch_to_previous_state(self) -> ProcessState:
        """
        1.Determines which process state switch should be applied from the current state.
        2. Determines the next switch time.
        3. Sets end time off current state and stores state to process_entry_dict
        4. Sets start time for next process state

        :raises Exception: _description_
        :return: _description_
        :rtype: ProcessState
        """
        state_data = (
            self.process_step_data.state_data_container.get_validated_pre_or_post_production_state()
        )
        current_process_state = self.get_process_state(
            state_data.current_process_state_name
        )
        logger.debug(
            "State Switch starts at state: %s", current_process_state.process_state_name
        )

        current_process_state_switch_selector = self.process_state_switch_selector_handler.get_switch_selector_to_previous_state(
            current_process_state_name=state_data.current_process_state_name
        )

        current_process_state_switch: ProcessStateSwitch = (
            current_process_state_switch_selector.select_state_switch()
        )

        next_backward_event_time = (
            current_process_state_switch.calculate_next_event_time_backward()
        )
        self.process_step_data.time_data.set_next_process_state_switch_time(
            next_discrete_event_time=next_backward_event_time
        )
        end_state_name_of_switch = (
            current_process_state_switch.state_connector.end_state_name
        )
        start_state_name_of_switch = (
            current_process_state_switch.state_connector.start_state_name
        )
        if end_state_name_of_switch is not current_process_state.process_state_name:
            raise Exception(
                "Current process state is not end state of process state switch"
            )

        self.deactivate_state(
            state_name_to_deactivate=end_state_name_of_switch,
            time_to_deactivate=next_backward_event_time,
        )
        new_active_state = self.activate_state(
            state_name_to_activate=start_state_name_of_switch,
            time_to_activate=next_backward_event_time,
        )
        logger.debug(
            "State after switch is: %s",
            new_active_state.process_state_name,
        )
        return new_active_state

    def activate_state(
        self, state_name_to_activate: str, time_to_activate: datetime.datetime
    ) -> ProcessState:
        logger.debug(
            "State: %s of process step: %s is activated at: %s",
            state_name_to_activate,
            self.process_step_data.process_step_name,
            time_to_activate,
        )

        self.process_step_data.state_data_container.update_current_process_state(
            new_process_state_name=state_name_to_activate
        )
        state_to_activate = self.get_process_state(
            process_state_name=state_name_to_activate
        )
        self.process_step_data.time_data.set_last_process_state_switch_time()
        return state_to_activate

    def deactivate_state(
        self, state_name_to_deactivate: str, time_to_deactivate: datetime.datetime
    ):
        """Deactivates the current state at time_to_deactivate provided. It is assumed that
        the state to be deactivated has already an end_time. Time to deactivate is then set
        and the state is stored to process state list.

        :param state_name_to_deactivate: _description_
        :type state_name_to_deactivate: str
        :param time_to_deactivate: _description_
        :type time_to_deactivate: datetime.datetime
        :raises Exception: _description_
        """
        logger.debug(
            "State: %s of process step: %s is deactivated at: %s",
            state_name_to_deactivate,
            self.process_step_data.process_step_name,
            time_to_deactivate,
        )

        state_data = (
            self.process_step_data.state_data_container.get_validated_pre_or_post_production_state()
        )
        current_process_state = self.get_process_state(
            process_state_name=state_data.current_process_state_name
        )
        last_process_state_switch_time = (
            self.process_step_data.time_data.get_last_process_state_switch_time()
        )
        process_state_state = ProcessStateData(
            process_state_name=current_process_state.process_state_name,
            start_time=time_to_deactivate,
            end_time=last_process_state_switch_time,
        )
        self.process_step_data.state_data_container.add_process_state_state(
            process_state_state=process_state_state
        )
        self.process_step_data.time_data.set_last_process_state_switch_time()

        # self.store_current_state_to_process_state_list()

    def restore_process_step_data(
        self,
        time_data_at_start: TimeData,
        simulation_state_data_at_start: CurrentProductionStateData,
        branch_data_at_start: OutputBranchData,
    ):
        """Restores the state of the process step data from another process step data.

        :param time_data_at_start: _description_
        :type time_data_at_start: TimeData
        :param simulation_state_data_at_start: _description_
        :type simulation_state_data_at_start: CurrentProductionStateData
        """

        self.process_step_data.restore_time_data(new_time_data=time_data_at_start)
        self.process_step_data.state_data_container.restore_process_state_data(
            state_data_to_update=simulation_state_data_at_start
        )
        self.process_step_data.state_data_container.restore_branch_data(
            branch_data_at_start=branch_data_at_start
        )

    def prepare_for_new_production_branch(
        self,
        new_output_stream_state: ContinuousStreamState | BatchStreamState,
        incomplete_output_branch_data: IncompleteOutputBranchData,
    ):
        """Resets some values for a new Production Branch

        :param new_output_stream_state: _description_
        :type new_output_stream_state: ContinuousStreamState | BatchStreamState
        :raises Exception: _description_
        """
        logger.debug("Start preparation for new production branch")
        state_data = self.process_step_data.state_data_container.state_data

        if isinstance(state_data, ValidatedPostProductionStateData):
            self.process_step_data.state_data_container.prepare_for_new_output_branch(
                parent_branch_data=incomplete_output_branch_data,
                new_output_stream_state=new_output_stream_state,
            )

        elif isinstance(state_data, UninitializedCurrentStateData):
            self.process_step_data.state_data_container.initialization_data_collector.add_current_output_stream_state(
                current_output_stream_state=new_output_stream_state
            )
            self.process_step_data.state_data_container.initialization_data_collector.add_current_process_state_name(
                current_process_state_name=self.idle_process_state_name
            )
            self.process_step_data.state_data_container.initialize_production_data()
            self.activate_state(
                state_name_to_activate=self.process_step_data.state_data_container.initialization_data_collector.current_process_state_name,
                time_to_activate=self.process_step_data.time_data.global_end_date,
            )
            self.process_step_data.state_data_container.prepare_for_new_output_branch(
                parent_branch_data=incomplete_output_branch_data,
                new_output_stream_state=new_output_stream_state,
            )
        elif type(state_data) is PreProductionStateData:
            self.process_step_data.state_data_container.prepare_for_new_output_branch(
                new_output_stream_state=new_output_stream_state,
                parent_branch_data=incomplete_output_branch_data,
            )
        else:
            raise Exception("Unexpected datatype")

    def check_if_input_and_output_stream_occur_in_same_state(self) -> bool:
        output_stream_providing_state = self.get_process_state(
            process_state_name=self.output_stream_providing_state_name
        )
        if isinstance(
            output_stream_providing_state, InputAndOutputStreamProvidingState
        ):
            occurs_in_same_state = True

        else:
            occurs_in_same_state = False

        return occurs_in_same_state

    def get_output_stream_providing_state_name(self) -> str:
        return self.output_stream_providing_state_name

    def get_process_state(self, process_state_name: str) -> ProcessState:
        process_state = self.process_state_dictionary[process_state_name]
        return process_state

    def add_process_state(
        self, process_state: ProcessState, add_as_current_state: bool = False
    ):
        logger.debug("Process state: %s has been added:", process_state)
        if process_state.process_state_name in self.process_state_dictionary:
            raise Exception(
                "Process state: "
                + process_state.process_state_name
                + " is already in process state dictionary"
            )
        self.process_state_dictionary[process_state.process_state_name] = process_state

        if isinstance(process_state, OutputStreamProvidingState):
            self.output_stream_providing_state_name = process_state.process_state_name
            logger.debug(
                "Process state has been added as output stream providing process state"
            )
        if isinstance(process_state, ProcessStateIdle):
            self.idle_process_state_name = process_state.process_state_name
            logger.debug("Process state has been added as idle process state")
        if isinstance(process_state, InputStreamProvidingState):
            self.input_stream_providing_state_name = process_state.process_state_name
            logger.debug(
                "Process state has been added as input stream providing process state"
            )
        if add_as_current_state:
            self.process_step_data.state_data_container.initialization_data_collector.add_current_process_state_name(
                current_process_state_name=process_state.process_state_name
            )

    def store_current_state_to_process_state_list(
        self,
    ) -> ProcessStepProductionPlanEntry:
        logger.debug("Store current process state to production plan")
        state_data = (
            self.process_step_data.state_data_container.get_validated_pre_or_post_production_state()
        )
        process_state = self.get_process_state(
            process_state_name=state_data.current_process_state_name
        )

        production_plan_entry = (
            process_state._create_process_step_production_plan_entry()
        )

        # self.list_of_production_plan_entries.append(production_plan_entry)
        temporary_production_plan = (
            self.process_step_data.state_data_container.get_temporary_production_plan()
        )
        temporary_production_plan.add_process_state_entry(
            production_plan_entry=production_plan_entry
        )
        temporary_production_plan.check_process_state_consistency()
        self.process_step_data.state_data_container.update_temporary_production_plan(
            updated_temporary_production_plan=temporary_production_plan
        )
        return production_plan_entry

    # def get_and_remove_list_of_process_step_production_plan_entries(
    #     self,
    # ) -> list[ProcessStepProductionPlanEntry]:
    #     list_of_production_plan_entries = self.list_of_production_plan_entries
    #     self.list_of_production_plan_entries = []
    #     return list_of_production_plan_entries

    def create_state_for_parallel_input_and_output_stream_with_storage(
        self, process_state_name: str, add_as_current_state: bool = False
    ) -> ProcessStateParallelContinuousInputWithStorage:
        process_state_production = ProcessStateParallelContinuousInputWithStorage(
            process_state_name=process_state_name,
            process_step_name=self.process_step_data.process_step_name,
            process_step_data=self.process_step_data,
        )
        self.add_process_state(
            process_state=process_state_production,
            add_as_current_state=add_as_current_state,
        )

        return process_state_production

    def create_continuous_output_stream_providing_state(
        self, process_state_name: str
    ) -> ContinuousOutputStreamProvidingState:
        continuous_output_stream_providing_state = ContinuousOutputStreamProvidingState(
            process_state_name=process_state_name,
            process_step_name=self.process_step_data.process_step_name,
            process_step_data=self.process_step_data,
        )
        self.add_process_state(
            process_state=continuous_output_stream_providing_state,
            add_as_current_state=False,
        )
        return continuous_output_stream_providing_state

    def create_batch_output_stream_providing_state(
        self, process_state_name: str
    ) -> BatchOutputStreamProvidingState:
        continuous_output_stream_providing_state = BatchOutputStreamProvidingState(
            process_state_name=process_state_name,
            process_step_name=self.process_step_data.process_step_name,
            process_step_data=self.process_step_data,
        )
        self.add_process_state(
            process_state=continuous_output_stream_providing_state,
            add_as_current_state=False,
        )
        return continuous_output_stream_providing_state

    def create_continuous_input_stream_requesting_state(
        self, process_state_name: str
    ) -> ContinuousInputStreamRequestingStateWithStorage:
        continuous_input_stream_requesting_state = (
            ContinuousInputStreamRequestingStateWithStorage(
                process_state_name=process_state_name,
                process_step_name=self.process_step_data.process_step_name,
                process_step_data=self.process_step_data,
            )
        )
        self.add_process_state(
            process_state=continuous_input_stream_requesting_state,
            add_as_current_state=False,
        )
        return continuous_input_stream_requesting_state

    def create_output_stream_providing_state_from_storage(
        self, process_state_name: str, maximum_stream_mass: float | None = None
    ) -> OutputStreamFromStorageState:
        output_state_from_storage = OutputStreamFromStorageState(
            process_state_name=process_state_name,
            process_step_name=self.process_step_data.process_step_name,
            process_step_data=self.process_step_data,
            maximum_stream_mass=maximum_stream_mass,
        )
        self.add_process_state(
            process_state=output_state_from_storage,
            add_as_current_state=False,
        )
        return output_state_from_storage

    def create_batch_input_stream_requesting_state(
        self, process_state_name: str
    ) -> BatchInputStreamRequestingStateWithStorage:
        batch_input_stream_requesting_state = (
            BatchInputStreamRequestingStateWithStorage(
                process_state_name=process_state_name,
                process_step_name=self.process_step_data.process_step_name,
                process_step_data=self.process_step_data,
            )
        )
        self.add_process_state(
            process_state=batch_input_stream_requesting_state,
            add_as_current_state=False,
        )
        return batch_input_stream_requesting_state

    def create_full_batch_input_stream_requesting_state(
        self,
        process_state_name: str,
    ) -> FullBatchInputStreamProvidingState:
        batch_input_stream_requesting_state = FullBatchInputStreamProvidingState(
            process_state_name=process_state_name,
            process_step_name=self.process_step_data.process_step_name,
            process_step_data=self.process_step_data,
        )
        self.add_process_state(
            process_state=batch_input_stream_requesting_state,
            add_as_current_state=False,
        )
        return batch_input_stream_requesting_state

    def create_batch_input_stream_requesting_state_energy_based_on_stream_mass(
        self, process_state_name: str
    ) -> BatchInputStreamRequestingStateWithStorageEnergyBasedOnStream:
        batch_input_stream_requesting_state = (
            BatchInputStreamRequestingStateWithStorageEnergyBasedOnStream(
                process_state_name=process_state_name,
                process_step_name=self.process_step_data.process_step_name,
                process_step_data=self.process_step_data,
            )
        )
        self.add_process_state(
            process_state=batch_input_stream_requesting_state,
            add_as_current_state=False,
        )
        return batch_input_stream_requesting_state

    def create_idle_process_state(
        self, process_state_name: str, add_as_current_state: bool = True
    ) -> ProcessStateIdle:
        process_state_idle = ProcessStateIdle(
            process_state_name=process_state_name,
            process_step_name=self.process_step_data.process_step_name,
            process_step_data=self.process_step_data,
        )

        self.add_process_state(
            process_state=process_state_idle,
            add_as_current_state=add_as_current_state,
        )
        return process_state_idle

    def create_intermediate_process_state(
        self, process_state_name: str
    ) -> IntermediateState:
        intermediate_state = IntermediateState(
            process_state_name=process_state_name,
            process_step_name=self.process_step_data.process_step_name,
            process_step_data=self.process_step_data,
        )
        self.add_process_state(
            process_state=intermediate_state, add_as_current_state=False
        )
        return intermediate_state

    def create_intermediate_process_state_energy_based_on_stream_mass(
        self, process_state_name: str
    ):
        intermediate_state = IntermediateStateBasedOnEnergy(
            process_state_name=process_state_name,
            process_step_name=self.process_step_data.process_step_name,
            process_step_data=self.process_step_data,
        )
        self.add_process_state(
            process_state=intermediate_state, add_as_current_state=False
        )
        return intermediate_state

    def get_output_stream_providing_state(self) -> OutputStreamProvidingState:
        output_stream_providing_state = self.get_process_state(
            process_state_name=self.output_stream_providing_state_name
        )
        return output_stream_providing_state

    def get_input_stream_providing_state(self) -> InputStreamProvidingState:
        input_stream_providing_state = self.get_process_state(
            process_state_name=self.input_stream_providing_state_name
        )
        return input_stream_providing_state

    def get_idle_state(self) -> ProcessStateIdle:
        idle_state = self.get_process_state(
            process_state_name=self.idle_process_state_name
        )
        return idle_state
