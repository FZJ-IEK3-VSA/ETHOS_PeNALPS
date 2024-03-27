import datetime
from dataclasses import dataclass

from ethos_penalps.data_classes import TemporalBranchIdentifier
from ethos_penalps.mass_balance import MassBalance
from ethos_penalps.process_state import (
    BatchInputStreamRequestingStateWithStorage,
    BatchInputStreamRequestingStateWithStorageEnergyBasedOnStream,
    FullBatchInputStreamProvidingState,
    InputAndOutputStreamProvidingState,
    InputStreamProvidingState,
    IntermediateStateBasedOnEnergy,
    OutputStreamProvidingState,
    ProcessStateParallelContinuousInputWithStorage,
)
from ethos_penalps.process_state_handler import ProcessStateHandler
from ethos_penalps.production_plan import OutputBranchProductionPlan, ProductionPlan
from ethos_penalps.simulation_data.container_simulation_data import (
    OutputBranchData,
    PostProductionStateData,
    PreProductionStateData,
    ValidatedPostProductionStateData,
)
from ethos_penalps.stream import BatchStreamState, ContinuousStreamState
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


@dataclass
class OutputStreamAdaptionDecider:
    """Tracks if the an output stream required adaption."""

    def __init__(
        self, original_stream_state: ContinuousStreamState | BatchStreamState
    ) -> None:
        """

        Args:
            original_stream_state (ContinuousStreamState | BatchStreamState): The original
                requested output_stream_state that is checked if adaption is required.
        """
        self.original_stream_state: ContinuousStreamState | BatchStreamState = (
            original_stream_state
        )
        self.adapted_stream_state: ContinuousStreamState | BatchStreamState = (
            original_stream_state
        )
        self.adaption_is_necessary: bool = False

    def add_adapted_state(
        self, adapted_state: ContinuousStreamState | BatchStreamState
    ):
        """This method is called if an adaptation was necessary.

        Args:
            adapted_state (ContinuousStreamState | BatchStreamState): The adapted
                output stream state.
        """
        self.adapted_stream_state = adapted_state
        self.adaption_is_necessary: bool = True


class ProcessStateNetworkNavigator:
    """
    The ProcessStateNetworkNavigator is the interface to the Petri net of the
    ProcessStep Agent. Depending on the received communication a different path
    path in the Petri net is triggered. The navigator can also just check the state
    of the simulation data to request adaptations.
    """

    def __init__(
        self,
        production_plan: ProductionPlan,
        process_state_handler: ProcessStateHandler,
    ) -> None:
        """

        Args:
            production_plan (ProductionPlan): Stores the simulation data
                of the petri net and the input stream.
            process_state_handler (ProcessStateHandler): Stores all instances
                the streams that are connected to this process step.
        """
        self.process_state_handler: ProcessStateHandler = process_state_handler
        # This copy can be used to restore the state of the process state handler

        self.production_plan: ProductionPlan = production_plan
        self.time_data_at_start: TimeData
        self.simulation_state_data_at_start: (
            PreProductionStateData
            | PostProductionStateData
            | ValidatedPostProductionStateData
        )
        self.branch_data_at_start: OutputBranchData

    def determine_if_output_stream_requires_adaption(
        self,
    ) -> OutputStreamAdaptionDecider:
        """Determines if the output stream can be provided as requested.
        Currently tests if this process step is busy and shifts the production to the first time available.
        Also tests for a maximum mass provided in a single stream. Cuts the stream to maximum mass if
        more mass is requested.

        Returns:
            OutputStreamAdaptionDecider: Contains the output stream state and a bool flag
                that tracks if it has been adapted.
        """
        logger.debug("Determine if output stream requires adaption has been called")

        output_stream_adaption_decider = (
            self.shift_output_stream_to_first_manageable_date_if_necessary()
        )

        output_stream_providing_state = (
            self.process_state_handler.get_output_stream_providing_state()
        )
        mass_adapted_stream_state = (
            output_stream_providing_state.determine_if_stream_mass_can_be_provided(
                output_stream_state=output_stream_adaption_decider.adapted_stream_state
            )
        )

        self.reset_temporal_branch()

        if (
            mass_adapted_stream_state
            != output_stream_adaption_decider.adapted_stream_state
        ):
            output_stream_adaption_decider.add_adapted_state(
                adapted_state=mass_adapted_stream_state
            )
        self.process_state_handler.process_step_data.state_data_container.update_existing_output_stream_state(
            new_output_stream_state=output_stream_adaption_decider.adapted_stream_state
        )

        # It is necessary to adjust the initial state if the stream required adaption
        # due to the required reset at several points

        logger.debug(
            "Output stream adaption is necessary: %s",
            output_stream_adaption_decider.adaption_is_necessary,
        )

        self.store_current_simulation_data()

        return output_stream_adaption_decider

    def store_current_simulation_data(self):
        """Stores the current simulation data so it can be restored at a later point of the simulation."""
        self.time_data_at_start = (
            self.process_state_handler.process_step_data.time_data.create_self_copy()
        )
        self.simulation_state_data_at_start = (
            self.process_state_handler.process_step_data.state_data_container.state_data.create_self_copy()
        )
        self.branch_data_at_start = (
            self.process_state_handler.process_step_data.state_data_container.current_branch_data.create_copy()
        )

    def shift_output_stream_to_first_manageable_date_if_necessary(
        self,
    ) -> OutputStreamAdaptionDecider:
        """Checks if the output stream must be shifted because the process step is not available yet.
        If a shift is necessary the state is shifted to the earliest available date


        Returns:
            OutputStreamAdaptionDecider: Contains the output stream state and a bool flag
                that tracks if it has been adapted.
        """

        earliest_output_stream_end_time = (
            self.process_state_handler.get_earliest_output_stream_production_time()
        )
        state_data = (
            self.process_state_handler.process_step_data.state_data_container.get_pre_production_state_data()
        )
        required_output_stream_end_time = (
            state_data.current_output_stream_state.end_time
        )

        logger.debug(
            "Temporal branch is available for production at: %s and the requested stream must be finished at: %s",
            earliest_output_stream_end_time,
            required_output_stream_end_time,
        )
        output_stream_adaption_decider = OutputStreamAdaptionDecider(
            original_stream_state=state_data.current_output_stream_state
        )
        if earliest_output_stream_end_time < required_output_stream_end_time:
            logger.debug(
                "The process step is still occupied when the requested stream must be finished"
            )

            old_state = state_data.current_output_stream_state
            logger.debug(
                "Old stream starts at: %s and finishes at: %s, temporal branch is available at: %s",
                old_state.start_time,
                old_state.end_time,
                earliest_output_stream_end_time,
            )
            # Assumption stream end time is after idle time thus resulting in a positive difference
            required_time_shift = old_state.end_time - earliest_output_stream_end_time
            if required_time_shift < datetime.timedelta(minutes=0):
                raise Exception("Required time shift is negative")

            # The difference is subtracted to shift the stream to an earlier date
            new_end_time = old_state.end_time - required_time_shift
            new_start_time = old_state.start_time - required_time_shift
            output_stream = (
                self.process_state_handler.process_step_data.stream_handler.get_stream(
                    stream_name=old_state.name
                )
            )
            if isinstance(old_state, ContinuousStreamState):
                old_state: ContinuousStreamState
                new_stream_state = (
                    output_stream.create_stream_state_for_commodity_amount(
                        commodity_amount=old_state.total_mass, end_time=new_end_time
                    )
                )

            elif isinstance(old_state, BatchStreamState):
                old_state: BatchStreamState
                new_stream_state = output_stream.create_batch_state(
                    end_time=new_end_time, batch_mass_value=old_state.batch_mass_value
                )

            else:
                raise Exception("Unexpected stream state")
            self.process_state_handler.process_step_data.state_data_container.update_existing_output_stream_state(
                new_output_stream_state=new_stream_state
            )
            logger.debug(
                "New stream starts at : %s, ends at: %s, time shift: %s",
                new_start_time,
                new_end_time,
                required_time_shift,
            )
            output_stream_adaption_decider.add_adapted_state(
                adapted_state=new_stream_state
            )
        elif earliest_output_stream_end_time >= required_output_stream_end_time:
            logger.debug("Production can be conducted on time")

        return output_stream_adaption_decider

    def determine_start_time_for_shift_to_production_state(
        self, stream_end_time: datetime.datetime
    ) -> datetime.datetime:
        """Determines the time when process state shift must be initiated to shift into the process state providing state
        in time. This is necessary to shift over pre output stream providing states

        Args:
            stream_end_time (datetime.datetime): The end_time of the output stream.


        Returns:
            datetime.datetime: Initiation date for process state shift from idle to output stream providing state
        """

        earliest_output_stream_end_time = (
            self.process_state_handler.get_earliest_output_stream_production_time()
        )

        time_difference_until_start = earliest_output_stream_end_time - stream_end_time
        if time_difference_until_start < datetime.timedelta(minutes=0):
            raise Exception(
                "Time difference is negative which implies a shift to production state while the process state is still idle "
            )
        start_time = (
            self.process_state_handler.process_step_data.time_data.get_last_idle_date()
            - time_difference_until_start
        )

        self.reset_temporal_branch()
        logger.debug(
            "The earliest output stream end time is: %s the required start time is at: %s",
            earliest_output_stream_end_time,
            start_time,
        )
        return start_time

    def determine_input_stream_from_output_stream(
        self,
    ) -> ContinuousStreamState | BatchStreamState:
        """Determines the required input stream from the output stream.

        Returns:
            ContinuousStreamState | BatchStreamState: The new input stream
                that is requested to provide mass for the output stream state.
        """
        state_data = (
            self.process_state_handler.process_step_data.state_data_container.get_pre_production_state_data()
        )
        logger.debug(
            "Conversion of the following output stream to an input stream starts: %s",
            state_data.current_output_stream_state,
        )

        stream_end_time = state_data.current_output_stream_state.end_time
        process_state_shift_start_time = (
            self.determine_start_time_for_shift_to_production_state(
                stream_end_time=stream_end_time
            )
        )
        logger.debug(
            "Switch to output stream providing state at: %s",
            process_state_shift_start_time,
        )

        output_stream_providing_state = (
            self.process_state_handler.switch_to_output_stream_providing_state(
                activation_date=process_state_shift_start_time
            )
        )
        if not isinstance(output_stream_providing_state, OutputStreamProvidingState):
            raise Exception(
                "Expected an OutputStreamProvidingState but is "
                + str(output_stream_providing_state)
            )

        streams_are_in_same_state = (
            self.process_state_handler.check_if_input_and_output_stream_occur_in_same_state()
        )
        if streams_are_in_same_state:
            logger.debug("Input and output stream are requested in the same state")
            input_stream_requesting_state = output_stream_providing_state
            if not isinstance(input_stream_requesting_state, InputStreamProvidingState):
                raise Exception(
                    "Expected an OutputStreamProvidingState but is "
                    + str(output_stream_providing_state)
                )

        else:
            logger.debug(
                "Input stream is requested in a separate state from the output stream state"
            )
            input_stream_requesting_state = (
                self.process_state_handler.switch_to_input_stream_requesting_state()
            )
        logger.debug("Start to determine the temporal branch requirement decider")
        input_stream_state = (
            input_stream_requesting_state.determine_required_input_stream_state()
        )

        state_data = (
            self.process_state_handler.process_step_data.state_data_container.get_post_production_state_data()
        )
        logger.debug(
            "A new input stream state has been determined: %s",
            state_data.current_input_stream_state,
        )

        logger.debug(
            "Output stream state was: %s",
            state_data.current_output_stream_state,
        )
        input_duration = (
            state_data.current_input_stream_state.end_time
            - state_data.current_input_stream_state.start_time
        )
        if input_duration == datetime.timedelta(minutes=0):
            raise Exception("Infinitesimal stream is requested")

        return input_stream_state

    def combine_input_and_output_stream(
        self,
        new_input_stream_state: ContinuousStreamState | BatchStreamState,
    ) -> ContinuousStreamState | BatchStreamState:
        """Is called if an adapation for in input stream is requested.
        It updates the requested input stream state and the duration of the
        input state.

        Args:
            new_input_stream_state (ContinuousStreamState | BatchStreamState): The
                adapted input stream state from the upstream node.

        Returns:
            ContinuousStreamState | BatchStreamState: The adapted input stream state.
                It is the same state that was provided as an argument.
        """

        logger.debug("Start to combine input and output stream")

        self.reset_temporal_branch()
        state_data = (
            self.process_state_handler.process_step_data.state_data_container.get_validated_pre_or_post_production_state()
        )
        current_process_state = self.process_state_handler.get_process_state(
            process_state_name=state_data.current_process_state_name
        )
        if type(state_data) is PreProductionStateData:
            logger.debug(
                "This is a first temporal branch to the production branch of this process step"
            )

            # Determine when a shift to an output_stream_providing state is necessary
            stream_end_time = state_data.current_output_stream_state.end_time
            process_state_shift_start_time = (
                self.determine_start_time_for_shift_to_production_state(
                    stream_end_time=stream_end_time
                )
            )
            output_stream_providing_state = (
                self.process_state_handler.switch_to_output_stream_providing_state(
                    activation_date=process_state_shift_start_time
                )
            )

            streams_are_in_same_state = (
                self.process_state_handler.check_if_input_and_output_stream_occur_in_same_state()
            )
            if streams_are_in_same_state:
                input_stream_requesting_state: InputAndOutputStreamProvidingState = (
                    output_stream_providing_state
                )
                if not isinstance(
                    input_stream_requesting_state, InputAndOutputStreamProvidingState
                ):
                    raise Exception(
                        "Expected an OutputStreamProvidingState but is "
                        + str(output_stream_providing_state)
                    )

            else:
                input_stream_requesting_state: InputStreamProvidingState = (
                    self.process_state_handler.switch_to_input_stream_requesting_state()
                )
            self.process_state_handler.process_step_data.state_data_container.add_first_input_stream_state(
                first_input_stream_state=new_input_stream_state
            )

        elif isinstance(
            state_data,
            (PostProductionStateData, ValidatedPostProductionStateData),
        ):
            logger.debug("A temporal branch already exists to this process step")

            input_stream_requesting_state = (
                self.process_state_handler.get_process_state(
                    process_state_name=state_data.current_process_state_name
                )
            )

            input_stream_requesting_state = (
                self.process_state_handler.switch_to_input_stream_requesting_state(
                    force_first_switch=False
                )
            )
            if isinstance(state_data, PostProductionStateData):
                self.process_state_handler.process_step_data.state_data_container.adapt_existing_input_stream_state(
                    new_input_stream_state=new_input_stream_state
                )
            elif isinstance(state_data, ValidatedPostProductionStateData):
                self.process_state_handler.process_step_data.state_data_container.add_input_stream_to_validated_data(
                    new_input_stream_state=new_input_stream_state
                )
            else:
                raise Exception("Unexpected datatype")

            if not isinstance(input_stream_requesting_state, InputStreamProvidingState):
                raise Exception(
                    "Unexpected state here:" + str(input_stream_requesting_state)
                )
        else:
            raise Exception("Unexpected process state: " + str(current_process_state))

        input_duration = (
            new_input_stream_state.end_time - new_input_stream_state.start_time
        )
        if input_duration == datetime.timedelta(minutes=0):
            raise Exception("Infinitesimal stream is requested")
        return new_input_stream_state

    def fulfill_temporal_branch(self) -> ContinuousStreamState | BatchStreamState:
        """This method is called to created an additional request for an input stream state.
        Before this method is called it must be checked that an additional stream is required.

        Returns:
            ContinuousStreamState | BatchStreamState: The new input stream state that is requested
                from the upstream node.
        """
        logger.debug("Start to fulfill production branch")
        state_data = (
            self.process_state_handler.process_step_data.state_data_container.get_validated_production_state_data()
        )
        current_process_state = self.process_state_handler.get_process_state(
            process_state_name=state_data.current_process_state_name
        )

        if isinstance(
            current_process_state,
            (
                BatchInputStreamRequestingStateWithStorage,
                ProcessStateParallelContinuousInputWithStorage,
                FullBatchInputStreamProvidingState,
            ),
        ):
            logger.debug("Switch to input request state")
            multi_target_switch_is_available = (
                self.process_state_handler.check_if_multiple_target_states_are_possible()
            )
            if multi_target_switch_is_available is True:
                current_process_state = (
                    self.process_state_handler.switch_to_input_stream_requesting_state(
                        force_first_switch=True
                    )
                )
            logger.debug("Create temporal branch requirement decider")
            input_stream_state = current_process_state.fulfill_order()

        else:
            raise Exception("Not implemented scenario")

        logger.debug(
            "The new input stream state is: %s",
            input_stream_state,
        )
        input_duration = input_stream_state.end_time - input_stream_state.start_time
        if input_duration == datetime.timedelta(minutes=0):
            raise Exception("Infinitesimal stream is requested")
        return input_stream_state

    def store_input_stream_state_to_temporary_production_plan(self):
        """Stores the input stream state to the production plan.
        Should be called before the branch is validated
        """
        logger.debug("Store streams to production plan")
        state_data = (
            self.process_state_handler.process_step_data.state_data_container.get_post_production_state_data()
        )
        input_stream_state = state_data.current_input_stream_state
        stream = self.process_state_handler.process_step_data.stream_handler.get_stream(
            stream_name=input_stream_state.name
        )

        stream_production_plan_entry = stream.create_production_plan_entry(
            state=input_stream_state
        )

        temporary_production_plan = (
            self.process_state_handler.process_step_data.state_data_container.get_temporary_production_plan()
        )
        temporary_production_plan.add_stream_state_entry(
            stream_state_entry=stream_production_plan_entry
        )

    def reset_temporal_branch(self):
        """Restores the process step data to previously stored state."""
        self.process_state_handler.restore_process_step_data(
            time_data_at_start=self.time_data_at_start,
            simulation_state_data_at_start=self.simulation_state_data_at_start,
            branch_data_at_start=self.branch_data_at_start,
        )

        logger.debug("Temporal branch has been reset")

    def provide_output_stream_from_storage(self):
        """Creates an output stream state from the mass in the
        internal storage.
        """
        state_data = (
            self.process_state_handler.process_step_data.state_data_container.get_pre_production_state_data()
        )
        logger.debug(
            "Provision of output stream directly from storage starts: %s",
            state_data.current_output_stream_state,
        )

        stream_end_time = state_data.current_output_stream_state.end_time
        process_state_shift_start_time = (
            self.determine_start_time_for_shift_to_production_state(
                stream_end_time=stream_end_time
            )
        )
        logger.debug(
            "Switch to output stream providing state at: %s",
            process_state_shift_start_time,
        )

        self.process_state_handler.switch_to_output_stream_providing_state(
            activation_date=process_state_shift_start_time
        )

        self.process_state_handler.switch_to_idle_state()

    def validate_temporal_branch_without_input_stream(self):
        """Creates the storage entries and process state entries
        without the request for an input stream state."""
        logger.debug("Start to validate temporal branch without input stream")
        input_stream_state = (
            self.process_state_handler.get_input_stream_providing_state()
        )
        input_stream_state.create_storage_entries()
        self.create_process_state_entries()

    def validate_temporal_branch(self):
        """Moves the input stream state to the list of validated
        input stream state. Creates the process state and storage
        entries.
        """
        logger.debug("Validation of temporal branch starts")
        self.store_input_stream_state_to_temporary_production_plan()
        self.process_state_handler.process_step_data.validate_input_stream()
        input_stream_state = (
            self.process_state_handler.get_input_stream_providing_state()
        )
        input_stream_state.create_storage_entries()
        self.create_process_state_entries()
        self.process_state_handler.process_step_data.state_data_container.clear_up_after_input_branch()

        logger.debug("Temporal branch is validated")

    def create_process_state_entries(self):
        """Creates the process state entries from the provision
        of the previous output stream state.
        """
        logger.debug("Start to create process state entries")
        state_data = (
            self.process_state_handler.process_step_data.state_data_container.get_validated_pre_or_post_production_state()
        )
        temporary_production_plan = (
            self.process_state_handler.process_step_data.state_data_container.get_temporary_production_plan()
        )
        process_state_entry_list = []
        process_step_name = (
            self.process_state_handler.process_step_data.process_step_name
        )
        for process_state_state in state_data.process_state_data_dictionary.values():
            process_state = self.process_state_handler.get_process_state(
                process_state_name=process_state_state.process_state_name
            )
            if isinstance(
                process_state,
                (
                    IntermediateStateBasedOnEnergy,
                    BatchInputStreamRequestingStateWithStorageEnergyBasedOnStream,
                ),
            ):
                input_stream_name = (
                    self.process_state_handler.process_step_data.main_mass_balance.main_input_stream_name
                )
                input_stream_production_plan_entry = (
                    temporary_production_plan.stream_state_dict[input_stream_name][-1]
                )
                process_state_entry = (
                    process_state._create_process_step_production_plan_entry(
                        process_state_state=process_state_state,
                        input_stream_state=input_stream_production_plan_entry,
                    )
                )

            else:
                process_state_entry = (
                    process_state._create_process_step_production_plan_entry(
                        process_state_state=process_state_state
                    )
                )
            process_state_entry_list.append(process_state_entry)
        if process_step_name in temporary_production_plan.process_step_states_dict:
            temporary_production_plan.process_step_states_dict[
                process_step_name
            ].extend(process_state_entry_list)
        else:
            temporary_production_plan.process_step_states_dict[process_step_name] = (
                process_state_entry_list
            )

        self.process_state_handler.process_step_data.state_data_container.update_temporary_production_plan(
            updated_temporary_production_plan=temporary_production_plan
        )
