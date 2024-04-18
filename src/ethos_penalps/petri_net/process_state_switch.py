import datetime
from abc import ABC, abstractclassmethod

from ethos_penalps.data_classes import StateConnector
from ethos_penalps.process_step_data import ProcessStepData
from ethos_penalps.simulation_data.container_simulation_data import (
    PostProductionStateData,
    PreProductionStateData,
    ValidatedPostProductionStateData,
)
from ethos_penalps.stream import BatchStreamState, ContinuousStreamState
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class ProcessStateSwitch(ABC):
    """A ProcessState switch models the transition within a
    Petri it net. It defines which states are connected by an arc
    and when a transition occurs.
    """

    state_connector: StateConnector
    process_step_data: ProcessStepData

    def calculate_next_event_time_backward(self) -> datetime.datetime:
        """Determines the switch time to the next state.

        Returns:
            datetime.datetime: Time when a switch occurs from the
                end state to the start state.
        """
        raise NotImplementedError


class ProcessStateSwitchDelay(ProcessStateSwitch):
    """This delay is used to model a state switch after a static delay. This
    is mainly used to model the length of an intermediate state.
    """

    def __init__(
        self,
        process_step_data: ProcessStepData,
        state_connector: StateConnector,
        delay: datetime.timedelta,
    ) -> None:
        """_summary_

        Args:
            process_step_data (ProcessStepData): Contains all data
                that define the simulation state of the process step and all
                methods to alter the state.
            state_connector (StateConnector): Summarizes the connection of two process states.
            delay (datetime.timedelta): The static delay after the process state switch occurs.
        """
        if not isinstance(state_connector.start_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )
        if not isinstance(state_connector.end_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )

        self.process_step_data: ProcessStepData = process_step_data
        self.state_connector: StateConnector = state_connector
        self.delay: datetime.timedelta = delay

    def __str__(self):
        return "ProcessStateSwitchDelay " + str(self.state_connector)

    def calculate_next_event_time_backward(self) -> datetime.datetime:
        """This method calculates the time until the next storage event occurs
        for each storage of the process step
        """

        next_event_time = (
            self.process_step_data.time_data.last_process_state_switch_time - self.delay
        )
        logger.debug(
            "Next event time is at: %s and last process state switch time is at: %s",
            next_event_time,
            self.process_step_data.time_data.last_process_state_switch_time,
        )
        return next_event_time


class ProcessStateSwitchAtOutputStreamProvided(ProcessStateSwitch):
    """This process state switch triggers at the start time of the output stream state.
    The output state must be defined at the end state of this switch."""

    def __init__(
        self,
        process_step_data: ProcessStepData,
        state_connector: StateConnector,
    ) -> None:
        """
        Args:
            process_step_data (ProcessStepData): Contains all data
                that define the simulation state of the process step and all
                methods to alter the state.
            state_connector (StateConnector): Connects two states. The end state of
                this switch should be an output stream providing state.
        """
        if not isinstance(state_connector.start_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )
        if not isinstance(state_connector.end_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )

        self.process_step_data: ProcessStepData = process_step_data
        self.state_connector: StateConnector = state_connector

    def __str__(self):
        return "ProcessStateSwitchAtTimeProvided " + str(self.state_connector)

    def calculate_next_event_time_backward(
        self,
    ) -> datetime.datetime:
        """This method calculates the process state switch time. It triggers the switch
        at the start time of the output stream state.

        Returns:
            datetime.datetime: The new switch time at the start time of the
                output stream state.
        """
        if not isinstance(self.state_connector.start_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )
        if not isinstance(self.state_connector.end_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )
        logger.debug("ProcessStateSwitchAtOutputStreamProvided")

        state_data = (
            self.process_step_data.state_data_container.get_validated_pre_or_post_production_state()
        )
        next_event_time = state_data.current_output_stream_state.start_time
        logger.debug(
            "Next event time is at: %s and last process state switch time is at: %s at process step: %s with the current process state: %s",
            next_event_time,
            self.process_step_data.time_data.last_process_state_switch_time,
            self.process_step_data.process_step_name,
            state_data.current_output_stream_state,
        )

        return next_event_time


class ProcessStateSwitchAtInputStreamProvided(ProcessStateSwitch):
    """This switch triggers at the the start time of the input stream state.
    It must be connected to an input stream providing state as target state.
    """

    def __init__(
        self,
        process_step_data: ProcessStepData,
        state_connector: StateConnector,
    ) -> None:
        """
        Args:
            process_step_data (ProcessStepData): Contains all data
                that define the simulation state of the process step and all
                methods to alter the state.
            state_connector (StateConnector): Connects two states. The end state of
                this switch should be an input stream providing state.
        """
        if not isinstance(state_connector.start_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )
        if not isinstance(state_connector.end_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )

        self.process_step_data: ProcessStepData = process_step_data
        self.state_connector: StateConnector = state_connector

    def __str__(self):
        return "ProcessStateSwitchAtTimeProvided " + str(self.state_connector)

    def calculate_next_event_time_backward(
        self,
    ) -> datetime.datetime:
        """This method calculates the next process state switch time. It switches at the
        start time of the input stream state.

        Returns:
            datetime.datetime: The process state switch time at the start time
                of the input stream state.
        """
        if not isinstance(self.state_connector.start_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )
        if not isinstance(self.state_connector.end_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )
        state_data = (
            self.process_step_data.state_data_container.get_validated_or_post_production_state_data()
        )
        if isinstance(state_data, ValidatedPostProductionStateData):
            next_event_time = state_data.validated_input_stream_list[-1].start_time
        elif isinstance(state_data, PostProductionStateData):
            next_event_time = state_data.current_input_stream_state.start_time
        else:
            raise Exception("Unexpected datatype")

        logger.debug(
            "Next event time is at: %s and last process state switch time is at: %s at process step: %s with the current process state: %s",
            next_event_time,
            self.process_step_data.time_data.last_process_state_switch_time,
            self.process_step_data.process_step_name,
            state_data.current_process_state_name,
        )

        return next_event_time


class ProcessStateSwitchAfterInputAndOutputStream(ProcessStateSwitch):
    """This process sate switch triggers at the start time of either the input stream state
    or the output stream state. If they do not start at the same time, the earlier start date
    is chosen.
    """

    def __init__(
        self,
        process_step_data: ProcessStepData,
        state_connector: StateConnector,
    ) -> None:
        """
        Args:
            process_step_data (ProcessStepData): Contains all data
                that define the simulation state of the process step and all
                methods to alter the state.
            state_connector (StateConnector): Connects two states. The end state of
                this switch should be a combined output and input stream providing state.

        """
        if not isinstance(state_connector.start_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )
        if not isinstance(state_connector.end_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )

        self.process_step_data: ProcessStepData = process_step_data
        self.state_connector: StateConnector = state_connector

    def __str__(self):
        return "ProcessStateSwitchAtTimeProvided " + str(self.state_connector)

    def calculate_next_event_time_backward(
        self,
    ) -> datetime.datetime:
        """This method calculates the next process state switch time. It switches at the
        start time of the input stream state or output stream state. If they do not
        start at the same time, the earlier start date is chosen.

        Returns:
            datetime.datetime: The new process state switch time. It is the start time
                of the input stream state or the output stream state. If they do not
                start at the same time, the earlier start date is chosen.
        """
        if not isinstance(self.state_connector.start_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )
        if not isinstance(self.state_connector.end_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )
        state_data = (
            self.process_step_data.state_data_container.get_validated_or_post_production_state_data()
        )
        if isinstance(state_data, PostProductionStateData):
            next_event_time = min(
                state_data.current_input_stream_state.start_time,
                state_data.current_output_stream_state.start_time,
            )
        elif isinstance(state_data, ValidatedPostProductionStateData):
            start_time_list = []
            for validated_stream in state_data.validated_input_stream_list:
                start_time_list.append(validated_stream.start_time)
            start_time_list.append(state_data.current_output_stream_state.start_time)
            next_event_time = min(start_time_list)
        else:
            raise Exception("Unexpected cased in state data")
        logger.debug(
            "Next event time is at: %s and last process state switch time is at: %s at process step: %s with the current process state: %s",
            next_event_time,
            self.process_step_data.time_data.last_process_state_switch_time,
            self.process_step_data.process_step_name,
            state_data.current_process_state_name,
        )

        return next_event_time


class ProcessStateSwitchAtNextDiscreteEvent(ProcessStateSwitch):
    """This process state switch triggers the switch from the idle state
    so that material request can be fulfilled just in time. The target state
    of this switch should be the idle state.
    """

    def __init__(
        self,
        process_step_data: ProcessStepData,
        state_connector: StateConnector,
    ) -> None:
        """
        Args:
            process_step_data (ProcessStepData): Contains all data
                that define the simulation state of the process step and all
                methods to alter the state.
            state_connector (StateConnector): Connects two states. The end state of
                this switch should be an idle state.
        """
        if not isinstance(state_connector.start_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )
        if not isinstance(state_connector.end_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )

        self.process_step_data: ProcessStepData = process_step_data
        self.state_connector: StateConnector = state_connector

    def __str__(self):
        return "ProcessStateSwitchAtTimeProvided " + str(self.state_connector)

    def calculate_next_event_time_backward(
        self,
    ) -> datetime.datetime:
        """This method determines the switch time from the idle state.

        Returns:
            datetime.datetime: The time when the switch from the idle state must
                occur so that the output stream sate can be delivered just in time.
        """
        if not isinstance(self.state_connector.start_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )
        if not isinstance(self.state_connector.end_state_name, str):
            raise Exception(
                "A name of typ string should be supplied for process state identification"
            )
        next_event_time = (
            self.process_step_data.time_data.get_next_process_state_switch_time()
        )
        state_data = (
            self.process_step_data.state_data_container.get_pre_or_post_production_state_data()
        )
        logger.debug(
            "Next event time is at: %s and last process state switch time is at: %s at process step: %s with the current process state: %s",
            next_event_time,
            self.process_step_data.time_data.last_process_state_switch_time,
            self.process_step_data.process_step_name,
            state_data.current_process_state_name,
        )

        return next_event_time
