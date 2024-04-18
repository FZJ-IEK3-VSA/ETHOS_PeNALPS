import datetime
from abc import ABC, abstractmethod

from ethos_penalps.data_classes import StateConnector
from ethos_penalps.petri_net.process_state import (
    ProcessState,
    ProcessStateSwitchHandler,
)
from ethos_penalps.petri_net.process_state_switch import (
    ProcessStateSwitch,
    ProcessStateSwitchAtInputStreamProvided,
    ProcessStateSwitchAtNextDiscreteEvent,
    ProcessStateSwitchAtOutputStreamProvided,
    ProcessStateSwitchDelay,
)
from ethos_penalps.process_step_data import ProcessStepData
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class ProcessStateSwitchSelector(ABC):
    """A process state selector determines which process state switch
    is triggered from the current process state.
    """

    def __init__(self, process_step_data: ProcessStepData) -> None:
        """

        Args:
            process_step_data (ProcessStepData): Contains all data
                that define the simulation state of the process step and all
                methods to alter the state.
        """
        self.target_state_name: str
        self.process_step_data: ProcessStepData = process_step_data

    @abstractmethod
    def select_state_switch(self) -> ProcessStateSwitch:
        """Determines which process sate switch is returned. The switch direction
        is from end state to start state. A process state switch
        is also required if only a single state switch is available.

        Returns:
            ProcessStateSwitch: The selected ProcessStateSwitch.
        """
        raise NotImplementedError


class SingleChoiceSelector(ProcessStateSwitchSelector):
    """This process state switch is used when there is only a
    single process state switch for the process state.
    """

    def __init__(
        self,
        process_step_data: ProcessStepData,
        process_state_switch: ProcessStateSwitch,
    ) -> None:
        """

        Args:
            process_step_data (ProcessStepData): Contains all data
                that define the simulation state of the process step and all
                methods to alter the state.
            process_state_switch (ProcessStateSwitch): Can be any ProcessStateSwitch.
        """
        super().__init__(process_step_data)
        self.process_state_switch: ProcessStateSwitch = process_state_switch
        self.target_state_name: str = (
            self.process_state_switch.state_connector.end_state_name
        )

    def select_state_switch(
        self,
    ) -> ProcessStateSwitch:
        """Returns the only ProcessStatesSwitch

        Returns:
            ProcessStateSwitch: _description_
        """
        return self.process_state_switch


class MultiTargetSelector(ABC):
    pass


class BatchStateSwitchSelector(ProcessStateSwitchSelector, MultiTargetSelector):
    def __init__(
        self,
        process_step_data: ProcessStepData,
        further_input_is_required_switch: ProcessStateSwitch,
        input_is_satisfied_switch: ProcessStateSwitch,
    ) -> None:
        ProcessStateSwitchSelector.__init__(self, process_step_data=process_step_data)
        MultiTargetSelector.__init__(self)
        if (
            further_input_is_required_switch.state_connector.end_state_name
            != input_is_satisfied_switch.state_connector.end_state_name
        ):
            raise Exception("Both target switches dont lead to the same state")
        self.target_state_name: str = (
            further_input_is_required_switch.state_connector.end_state_name
        )
        self.process_step_data: ProcessStepData = process_step_data
        self.further_input_is_required_switch: ProcessStateSwitch = (
            further_input_is_required_switch
        )
        self.input_is_satisfied_switch: ProcessStateSwitch = input_is_satisfied_switch
        self.target_state_name: str = (
            further_input_is_required_switch.state_connector.end_state_name
        )

    def select_state_switch(
        self,
    ) -> ProcessStateSwitch:
        missing_mass = (
            self.process_step_data.main_mass_balance.determine_missing_mass_for_output_stream()
        )
        error_limit = 0
        # if missing_mass > error_limit:
        #     output_state_switch = self.further_input_is_required_switch
        #     logger.debug(
        #         "Further input streams are required to satisfy the output stream"
        #     )
        # elif missing_mass < error_limit and missing_mass > -error_limit:
        #     output_state_switch = self.input_is_satisfied_switch
        #     logger.debug("The following stream satisfies the output stream")
        # else:
        #     raise Exception("Unexpected missing mass: " + str(missing_mass))
        if missing_mass > 0:
            output_state_switch = self.further_input_is_required_switch
            logger.debug(
                "Further input streams are required to satisfy the output stream"
            )
        elif missing_mass == 0:
            output_state_switch = self.input_is_satisfied_switch
            logger.debug("The following stream satisfies the output stream")
        else:
            raise Exception("Unexpected missing mass: " + str(missing_mass))
        return output_state_switch


class ProvideOutputFromStorageSwitchSelector(
    ProcessStateSwitchSelector, MultiTargetSelector
):
    def __init__(
        self,
        process_step_data: ProcessStepData,
        output_is_supplied_from_storage_switch: ProcessStateSwitch,
        input_stream_is_required_switch: ProcessStateSwitch,
    ) -> None:
        ProcessStateSwitchSelector.__init__(self, process_step_data=process_step_data)
        MultiTargetSelector.__init__(self)

        if (
            output_is_supplied_from_storage_switch.state_connector.end_state_name
            != input_stream_is_required_switch.state_connector.end_state_name
        ):
            raise Exception("Both target switches dont lead to the same state")
        self.target_state_name: str = (
            output_is_supplied_from_storage_switch.state_connector.end_state_name
        )
        self.process_step_data: ProcessStepData = process_step_data
        self.output_is_supplied_from_storage_switch: ProcessStateSwitch = (
            output_is_supplied_from_storage_switch
        )
        self.input_stream_is_required_switch: ProcessStateSwitch = (
            input_stream_is_required_switch
        )

    def select_state_switch(
        self,
    ) -> ProcessStateSwitch:
        can_be_supplied_directly = (
            self.process_step_data.main_mass_balance.check_if_output_stream_can_be_supplied_directly_from_storage()
        )

        if can_be_supplied_directly is True:
            output_state_switch = self.output_is_supplied_from_storage_switch
            logger.debug(
                "Further input streams are required to satisfy the output stream"
            )
        elif can_be_supplied_directly is False:
            output_state_switch = self.input_stream_is_required_switch
            logger.debug("The following stream satisfies the output stream")

        return output_state_switch


class ProcessStateSwitchSelectorHandler:
    """The process state switch selector adds an object which decides which process state switch
    has to be applied for the next process state switch
    """

    def __init__(
        self,
        process_step_data: ProcessStepData,
    ) -> None:
        self.process_state_switch_selector_dict: dict[
            str, ProcessStateSwitchSelector
        ] = {}
        self.process_step_data: ProcessStepData = process_step_data
        self.process_state_switch_handler = ProcessStateSwitchHandler(
            process_step_data=process_step_data
        )

    def get_switch_selector_to_previous_state(
        self, current_process_state_name: str
    ) -> ProcessStateSwitchSelector:
        """Returns a process state switch selector with all process state switches
        that have the current state as a target. Only a single ProcessStateSwitch
        is allowed per state.

        :param current_process_state_name: _description_
        :type current_process_state_name: str
        :return: _description_
        :rtype: ProcessStateSwitchSelector
        """

        process_state_switch_selector = self.process_state_switch_selector_dict[
            current_process_state_name
        ]
        return process_state_switch_selector

    def add_process_state_switch_selector(
        self, process_state_switch_selector: ProcessStateSwitchSelector
    ):
        """Adds a process state switch selector to the process_state_switch_selector_dict.
        Only a single ProcessStateSwitchSelector is allowed per state. It has to handle
        all possible path decisions to the current state.

        :param process_state_switch_selector: _description_
        :type process_state_switch_selector: ProcessStateSwitchSelector
        :raises Exception: _description_
        """
        if (
            process_state_switch_selector.target_state_name
            in self.process_state_switch_selector_dict
        ):
            raise Exception(
                "There is already a selector available for process state: "
                + str(process_state_switch_selector.target_state_name)
            )
        self.process_state_switch_selector_dict[
            process_state_switch_selector.target_state_name
        ] = process_state_switch_selector

    def create_single_choice_selector(
        self, process_state_switch: ProcessStateSwitch
    ) -> SingleChoiceSelector:
        single_choice_selector = SingleChoiceSelector(
            process_step_data=self.process_step_data,
            process_state_switch=process_state_switch,
        )
        self.add_process_state_switch_selector(
            process_state_switch_selector=single_choice_selector
        )
        return single_choice_selector

    def create_batch_state_switch_selector(
        self,
        further_input_is_required_switch: ProcessStateSwitch,
        input_is_satisfied_switch: ProcessStateSwitch,
    ) -> BatchStateSwitchSelector:
        batch_state_switch_selector = BatchStateSwitchSelector(
            process_step_data=self.process_step_data,
            further_input_is_required_switch=further_input_is_required_switch,
            input_is_satisfied_switch=input_is_satisfied_switch,
        )
        self.add_process_state_switch_selector(
            process_state_switch_selector=batch_state_switch_selector
        )
        return batch_state_switch_selector

    def create_storage_provision_state_switch(
        self,
        output_is_supplied_from_storage_switch: ProcessStateSwitch,
        input_stream_is_required_switch: ProcessStateSwitch,
    ):
        storage_switch_selector = ProvideOutputFromStorageSwitchSelector(
            process_step_data=self.process_step_data,
            output_is_supplied_from_storage_switch=output_is_supplied_from_storage_switch,
            input_stream_is_required_switch=input_stream_is_required_switch,
        )
        self.add_process_state_switch_selector(
            process_state_switch_selector=storage_switch_selector
        )
        return storage_switch_selector
