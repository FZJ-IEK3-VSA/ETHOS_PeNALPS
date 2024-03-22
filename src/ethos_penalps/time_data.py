import datetime

from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class TimeData:
    """Each instance of process step data contains an own instance of the this class.
    It contains the temporal information of the discrete event simulation
    of the current process step. Global start and end date is the same
    for each process step in the Enterprise.
    """

    def __init__(
        self,
        global_start_date: datetime.datetime = datetime.datetime(2021, 1, 1),
        global_end_date: datetime.datetime = datetime.datetime(2022, 1, 1),
    ) -> None:
        """
        Args:
            global_start_date (datetime.datetime, optional): _description_. Defaults to datetime.datetime(2021, 1, 1).
            global_end_date (datetime.datetime, optional): _description_. Defaults to datetime.datetime(2022, 1, 1).
        """
        self.global_start_date: datetime.datetime = global_start_date
        self.global_end_date: datetime.datetime = global_end_date
        self.last_idle_time: datetime.datetime = global_end_date
        self.last_process_state_switch_time: datetime.datetime = global_end_date
        self.next_process_state_switch_time: datetime.datetime = global_end_date
        self.next_stream_end_time: datetime.datetime
        self.storage_last_update_time: datetime.datetime = global_end_date

    def set_current_process_time(self, current_process_time: datetime.datetime):
        """Sets the current process time of a process step.

        Args:
            current_process_time (datetime.datetime): Determines the current
                process time in the discrete event simulation.
        """
        if not isinstance(current_process_time, datetime.datetime):
            raise Exception(
                "Instead of datetime.datetime datatype, the datatype: "
                + str(type(current_process_time))
                + " was received"
            )
        self.current_process_time = current_process_time

    def get_last_idle_date(self) -> datetime.datetime:
        """Returns the last idle time of the process step.

        Returns:
            datetime.datetime: Last idle date of the process step.
        """
        return self.last_idle_time

    def get_next_process_state_switch_time(self) -> datetime.datetime:
        """Returns the next process state switch time.

        Returns:
            datetime.datetime: Next process state switch time.
        """
        return self.next_process_state_switch_time

    def set_next_event_time_as_last_idle_time(self):
        logger.debug(
            "Current process time has been set to: %s from: %s",
            self.last_idle_time,
            self.next_process_state_switch_time,
        )
        if self.next_process_state_switch_time > self.last_idle_time:
            raise Exception("Next discrete event time is after last idle time")
        self.last_idle_time = self.next_process_state_switch_time

    def set_next_process_state_switch_time(
        self, next_discrete_event_time: datetime.datetime
    ):
        if not isinstance(next_discrete_event_time, datetime.datetime):
            raise Exception(
                "Instead of datetime.datetime datatype, the datatype: "
                + str(next_discrete_event_time)
                + " was received",
                next_discrete_event_time,
            )
        if next_discrete_event_time > self.last_idle_time:
            raise Exception("Next discrete event time is after last idle time")
        self.next_process_state_switch_time = next_discrete_event_time
        logger.debug("Next event time is set to: %s", next_discrete_event_time)

    def set_last_process_state_switch_time(
        self,
    ):
        new_last_process_state_switch_time = self.get_next_process_state_switch_time()

        if new_last_process_state_switch_time > self.last_process_state_switch_time:
            raise Exception("New last process_state_switch_time is before old time")
        self.last_process_state_switch_time = new_last_process_state_switch_time

    def get_last_process_state_switch_time(self) -> datetime.datetime:
        """Returns the last process_state_switch time.

        Returns:
            datetime.datetime: returns the last process state switch time
        """
        return self.last_process_state_switch_time

    def set_next_stream_end_time(self, next_stream_end_time: datetime.datetime):
        """Sets the next stream end time.

        Args:
            next_stream_end_time (datetime.datetime): Next stream end time.
        """
        self.next_stream_end_time = next_stream_end_time

    def get_next_stream_end_time(self) -> datetime.datetime:
        """Returns the next stream end time.

        Returns:
            datetime.datetime: Next stream end time.
        """
        return self.next_stream_end_time

    def get_storage_last_update_time(self) -> datetime.datetime:
        """Returns the last storage update time.

        Returns:
            datetime.datetime: Last storage update time.
        """
        return self.storage_last_update_time

    def set_storage_last_update_time(self, updated_storage_datetime: datetime.datetime):
        """Sets the last update time of the storage.

        Args:
            updated_storage_datetime (datetime.datetime): Updated storage time.
        """
        self.storage_last_update_time = updated_storage_datetime

    def create_self_copy(self) -> "TimeData":
        """Returns a self copy that can be used to store the current simulation state.

        Returns:
            TimeData: Copy of the current time data state.
        """
        self_copy = TimeData(
            global_start_date=self.global_start_date,
            global_end_date=self.global_end_date,
        )
        self_copy.last_idle_time = self.last_idle_time
        self_copy.last_process_state_switch_time = self.last_process_state_switch_time
        self_copy.next_process_state_switch_time = self.next_process_state_switch_time

        self_copy.storage_last_update_time = self.storage_last_update_time

        if hasattr(self, "next_stream_end_time"):
            self_copy.next_stream_end_time = self.next_stream_end_time

        return self_copy
