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
    state_connector: StateConnector
    process_step_data: ProcessStepData

    def calculate_next_event_time_backward(self) -> datetime.datetime:
        raise NotImplementedError


class ProcessStateSwitchDelay(ProcessStateSwitch):
    def __init__(
        self,
        process_step_data: ProcessStepData,
        state_connector: StateConnector,
        delay: datetime.timedelta,
    ) -> None:
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
    def __init__(
        self,
        process_step_data: ProcessStepData,
        state_connector: StateConnector,
    ) -> None:
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
        """This method calculates the time until the next storage event occurs
        for each storage of the process step
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
    def __init__(
        self,
        process_step_data: ProcessStepData,
        state_connector: StateConnector,
    ) -> None:
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
        """This method calculates the time until the next storage event occurs
        for each storage of the process step
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
    def __init__(
        self,
        process_step_data: ProcessStepData,
        state_connector: StateConnector,
    ) -> None:
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
        """This method calculates the time until the next storage event occurs
        for each storage of the process step
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
    def __init__(
        self,
        process_step_data: ProcessStepData,
        state_connector: StateConnector,
    ) -> None:
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
        """This method calculates the time until the next storage event occurs
        for each storage of the process step
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
