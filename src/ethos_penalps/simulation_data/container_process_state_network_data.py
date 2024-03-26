import warnings
import numbers
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ethos_penalps.data_classes import TemporalBranchIdentifier
from ethos_penalps.production_plan import OutputBranchProductionPlan
from ethos_penalps.simulation_data.simulation_data_complete import (
    AdaptedProductionStateData,
    CurrentProductionStateData,
    PostProductionStateData,
    PreProductionStateData,
    SimulationData,
    UninitializedCurrentStateData,
    ValidatedPostProductionStateData,
)
from ethos_penalps.stream import BatchStreamState, ContinuousStreamState
from ethos_penalps.utilities.exceptions_and_warnings import (
    IllogicalFunctionCall,
    IllogicalSimulationState,
    UnexpectedDataType,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class InitializationDataCollector:
    """Collects the data that is required to initialize the simulation
    data of a ProcessStep.
    """

    def __init__(self) -> None:
        self.current_process_state_name: str
        self.current_output_stream_state: ContinuousStreamState | BatchStreamState
        self.current_storage_level: numbers.Number

    def add_current_process_state_name(self, current_process_state_name: str):
        """Adds a new process state as current process state.

        Args:
            current_process_state_name (str): The new process state name.
        """
        self.current_process_state_name = current_process_state_name

    def add_current_output_stream_state(
        self, current_output_stream_state: ContinuousStreamState | BatchStreamState
    ):
        """Adds a new output stream state to the simulation data.

        Args:
            current_output_stream_state (ContinuousStreamState | BatchStreamState): The new output
                stream state of the simulation data.
        """
        self.current_output_stream_state = current_output_stream_state

    def add_current_storage_level(self, current_storage_level: numbers.Number):
        """Add the first storage level.

        Args:
            current_storage_level (numbers.Number): The first storage level in the simulation
                data.
        """
        self.current_storage_level = current_storage_level


class ProcessStateNetworkContainer:
    """_summary_"""

    def __init__(self) -> None:
        self.state_data: CurrentProductionStateData = UninitializedCurrentStateData()
        self.initialization_data_collector = InitializationDataCollector()

    def update_storage_level(self, new_storage_level: numbers.Number):
        """Updates the storage level in the simulation data.

        Args:
            new_storage_level (numbers.Number): New storage level.

        """
        if new_storage_level < -1:
            warnings.warn(
                "Storage level went below zero at level: "
                + str(new_storage_level)
                + "Results are faulty"
            )
        if type(self.state_data) is PostProductionStateData:
            previous_state_data = self.state_data
            self.state_data = PostProductionStateData(
                current_input_stream_state=previous_state_data.current_input_stream_state,
                current_process_state_name=previous_state_data.current_process_state_name,
                current_storage_level=new_storage_level,
                current_output_stream_state=previous_state_data.current_output_stream_state,
                process_state_data_dictionary=dict(
                    previous_state_data.process_state_data_dictionary
                ),
            )
            logger.debug(
                "Storage level is updated to %s", self.state_data.current_storage_level
            )
        elif type(self.state_data) is PreProductionStateData:
            previous_state_data = self.state_data
            self.state_data = PreProductionStateData(
                current_output_stream_state=previous_state_data.current_output_stream_state,
                current_process_state_name=previous_state_data.current_process_state_name,
                current_storage_level=new_storage_level,
                process_state_data_dictionary=dict(
                    previous_state_data.process_state_data_dictionary
                ),
            )
            logger.debug(
                "Storage level is updated to %s", self.state_data.current_storage_level
            )
        elif type(self.state_data) is ValidatedPostProductionStateData:
            previous_state_data = self.state_data
            self.state_data = ValidatedPostProductionStateData(
                current_output_stream_state=previous_state_data.current_output_stream_state,
                current_process_state_name=previous_state_data.current_process_state_name,
                current_storage_level=new_storage_level,
                validated_input_stream_list=previous_state_data.validated_input_stream_list,
                process_state_data_dictionary=dict(
                    previous_state_data.process_state_data_dictionary
                ),
            )

            logger.debug(
                "Storage level is updated to %s", self.state_data.current_storage_level
            )
        else:
            raise UnexpectedDataType(
                current_data_type=self.state_data,
                expected_data_type=(
                    PreProductionStateData,
                    PostProductionStateData,
                    ValidatedPostProductionStateData,
                ),
            )

    def get_storage_level(self) -> numbers.Number:
        """Returns the current storage level.

        Returns:
            numbers.Number: Current storage level
        """
        return self.state_data.current_storage_level

    def update_existing_output_stream_state(
        self, new_output_stream_state: ContinuousStreamState | BatchStreamState
    ):
        """Updates the existing output stream state.

        Args:
            new_output_stream_state (ContinuousStreamState | BatchStreamState): The new
                output stream state.
        """
        previous_production_state_data = self.state_data
        if type(previous_production_state_data) is PreProductionStateData:
            self.state_data = PreProductionStateData(
                current_process_state_name=previous_production_state_data.current_process_state_name,
                current_output_stream_state=new_output_stream_state,
                current_storage_level=previous_production_state_data.current_storage_level,
                process_state_data_dictionary=dict(
                    previous_production_state_data.process_state_data_dictionary
                ),
            )

        elif type(previous_production_state_data) is PostProductionStateData:
            raise Exception(
                "Output stream should not ab adapted after post production state has been created "
            )

        elif type(previous_production_state_data) is UninitializedCurrentStateData:
            raise Exception(
                "Preparation for new production branch begins before initialization"
            )
        else:
            raise UnexpectedDataType(
                current_data_type=previous_production_state_data,
                expected_data_type=PreProductionStateData,
            )

    def add_input_stream_to_validated_data(
        self, new_input_stream_state: ContinuousStreamState | BatchStreamState
    ):
        """Adds a new input stream state as the current unvalidated stream.

        Args:
            new_input_stream_state (ContinuousStreamState | BatchStreamState): New
                input stream that waits for validation.

        """
        previous_production_state_data = self.state_data
        if type(previous_production_state_data) is ValidatedPostProductionStateData:
            self.state_data = PostProductionStateData(
                current_process_state_name=previous_production_state_data.current_process_state_name,
                current_output_stream_state=previous_production_state_data.current_output_stream_state,
                current_input_stream_state=new_input_stream_state,
                validated_input_stream_list=list(
                    previous_production_state_data.validated_input_stream_list
                ),
                current_storage_level=previous_production_state_data.current_storage_level,
                process_state_data_dictionary=dict(
                    previous_production_state_data.process_state_data_dictionary
                ),
            )
            if 1 == 2:
                pass
        elif type(previous_production_state_data) is PreProductionStateData:
            raise Exception(
                "Output stream should not ab adapted after post production state has been created "
            )

        elif type(previous_production_state_data) is UninitializedCurrentStateData:
            raise Exception(
                "Preparation for new production branch begins before initialization"
            )
        else:
            raise UnexpectedDataType(
                current_data_type=previous_production_state_data,
                expected_data_type=ValidatedPostProductionStateData,
            )

    def update_current_process_state(self, new_process_state_name: str):
        """Updates the current process state.

        Args:
            new_process_state_name (str): The new state in the petri net.

        """
        if type(self.state_data) is PostProductionStateData:
            previous_state_data = self.state_data
            self.state_data = PostProductionStateData(
                current_input_stream_state=previous_state_data.current_input_stream_state,
                current_process_state_name=new_process_state_name,
                current_storage_level=previous_state_data.current_storage_level,
                current_output_stream_state=previous_state_data.current_output_stream_state,
                process_state_data_dictionary=dict(
                    previous_state_data.process_state_data_dictionary
                ),
            )
        elif type(self.state_data) is PreProductionStateData:
            previous_state_data = self.state_data
            self.state_data = PreProductionStateData(
                current_output_stream_state=previous_state_data.current_output_stream_state,
                current_process_state_name=new_process_state_name,
                current_storage_level=previous_state_data.current_storage_level,
                process_state_data_dictionary=dict(
                    previous_state_data.process_state_data_dictionary
                ),
            )
        elif type(self.state_data) is ValidatedPostProductionStateData:
            previous_state_data = self.state_data
            self.state_data = ValidatedPostProductionStateData(
                current_output_stream_state=previous_state_data.current_output_stream_state,
                current_process_state_name=new_process_state_name,
                current_storage_level=previous_state_data.current_storage_level,
                validated_input_stream_list=previous_state_data.validated_input_stream_list,
                process_state_data_dictionary=dict(
                    previous_state_data.process_state_data_dictionary
                ),
            )
        elif type(self.state_data) is UninitializedCurrentStateData:
            raise Exception("State data should have been initialized")
        else:
            raise UnexpectedDataType(
                current_data_type=self.state_data,
                expected_data_type=(PostProductionStateData, PreProductionStateData),
            )

    def add_first_input_stream_state(
        self, first_input_stream_state: ContinuousStreamState | BatchStreamState
    ):
        """Adds the first input stream state that was requested to provide mass
        for the output stream state.

        Args:
            first_input_stream_state (ContinuousStreamState | BatchStreamState): First input
                stream state.

        """
        previous_production_state_data = self.state_data
        if type(previous_production_state_data) is PreProductionStateData:
            self.state_data = PostProductionStateData(
                current_process_state_name=previous_production_state_data.current_process_state_name,
                current_output_stream_state=previous_production_state_data.current_output_stream_state,
                current_storage_level=previous_production_state_data.current_storage_level,
                current_input_stream_state=first_input_stream_state,
                process_state_data_dictionary=dict(
                    previous_production_state_data.process_state_data_dictionary
                ),
            )
        elif type(previous_production_state_data) is PostProductionStateData:
            raise Exception(
                "Output stream should not ab adapted after post production state has been created "
            )

        elif type(previous_production_state_data) is UninitializedCurrentStateData:
            raise Exception(
                "Preparation for new production branch begins before initialization"
            )
        else:
            raise UnexpectedDataType(
                current_data_type=previous_production_state_data,
                expected_data_type=PreProductionStateData,
            )

    def adapt_existing_input_stream_state(
        self, new_input_stream_state: BatchStreamState | ContinuousStreamState
    ):
        """Adapts an existing input stream state.

        Args:
            new_input_stream_state (BatchStreamState | ContinuousStreamState): Adapted
                input stream state.
        """
        previous_production_state_data = self.state_data
        if type(previous_production_state_data) is PostProductionStateData:
            self.state_data = PostProductionStateData(
                current_process_state_name=previous_production_state_data.current_process_state_name,
                current_output_stream_state=previous_production_state_data.current_output_stream_state,
                current_input_stream_state=new_input_stream_state,
                current_storage_level=previous_production_state_data.current_storage_level,
                process_state_data_dictionary=dict(
                    previous_production_state_data.process_state_data_dictionary
                ),
                validated_input_stream_list=list(
                    previous_production_state_data.validated_input_stream_list
                ),
            )
        elif type(previous_production_state_data) is PreProductionStateData:
            raise Exception(
                "Preparation for new production branch has been called before previous production branch is fulfilled"
            )
        elif type(previous_production_state_data) is UninitializedCurrentStateData:
            raise Exception(
                "Preparation for new production branch begins before initialization"
            )
        else:
            raise UnexpectedDataType(
                current_data_type=previous_production_state_data,
                expected_data_type=PostProductionStateData,
            )
