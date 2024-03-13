import copy
import dataclasses
import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ethos_penalps.data_classes import (
    OutputBranchIdentifier,
    ProcessStateData,
    StreamBranchIdentifier,
    TemporalBranchIdentifier,
)
from ethos_penalps.production_plan import OutputBranchProductionPlan
from ethos_penalps.stream import BatchStreamState, ContinuousStreamState
from ethos_penalps.utilities.exceptions_and_warnings import (
    IllogicalFunctionCall,
    UnexpectedDataType,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

# Branch data


# Simulation Data


@dataclass(kw_only=True)
class SimulationData(ABC):
    @abstractmethod
    def create_self_copy(self):
        raise NotImplementedError


@dataclass(kw_only=True)
class UninitializedCurrentStateData(SimulationData):
    def create_self_copy(self):
        return UninitializedCurrentStateData()


@dataclass(kw_only=True)
class CurrentProductionStateData(SimulationData):
    current_process_state_name: str
    current_output_stream_state: ContinuousStreamState | BatchStreamState
    current_storage_level: float
    process_state_data_dictionary: dict[str, ProcessStateData] = field(
        default_factory=dict
    )

    def create_self_copy(self):
        copy_of_process_state_data_dictionary = (
            self._create_copy_of_process_state_data_dictionary()
        )
        new_data_class = CurrentProductionStateData(
            current_process_state_name=self.current_process_state_name,
            current_output_stream_state=self.current_output_stream_state,
            current_storage_level=self.current_storage_level,
            process_state_data_dictionary=copy_of_process_state_data_dictionary,
        )
        return new_data_class

    def _create_copy_of_process_state_data_dictionary(self):
        copy_of_process_state_data_dictionary = dict(self.process_state_data_dictionary)
        return copy_of_process_state_data_dictionary


@dataclass(kw_only=True)
class PreProductionStateData(CurrentProductionStateData):
    def create_self_copy(self):
        copy_of_process_state_data_dictionary = (
            self._create_copy_of_process_state_data_dictionary()
        )

        self_copy = PreProductionStateData(
            current_process_state_name=self.current_process_state_name,
            current_output_stream_state=self.current_output_stream_state,
            current_storage_level=self.current_storage_level,
            process_state_data_dictionary=copy_of_process_state_data_dictionary,
        )
        return self_copy


@dataclass(kw_only=True)
class AdaptedProductionStateData(PreProductionStateData):
    # def __init__(
    #     self,
    #     preproduction_state_data: PreProductionStateData,
    #     adapted_output_stream_state: ContinuousStreamState | BatchStreamState,
    # ):
    #     super.()
    #     self.adapted_output_stream_state: ContinuousStreamState | BatchStreamState = (
    #         adapted_output_stream_state
    #     )

    def create_self_copy(self):
        copy_of_process_state_data_dictionary = (
            self._create_copy_of_process_state_data_dictionary()
        )
        self_copy = AdaptedProductionStateData(
            current_process_state_name=self.current_process_state_name,
            current_output_stream_state=self.current_output_stream_state,
            current_storage_level=self.current_storage_level,
            process_state_data_dictionary=copy_of_process_state_data_dictionary,
            adapted_output_stream_state=self.adapted_output_stream_state,
        )
        return self_copy


@dataclass(kw_only=True)
class ValidatedPostProductionStateData(PreProductionStateData):
    validated_input_stream_list: list[ContinuousStreamState | BatchStreamState] = field(
        default_factory=list
    )

    def create_self_copy(self):
        copy_of_process_state_data_dictionary = (
            self._create_copy_of_process_state_data_dictionary()
        )
        copy_of_validated_input_stream_list = (
            self._create_copy_of_validated_input_stream_list()
        )
        self_copy = ValidatedPostProductionStateData(
            current_process_state_name=self.current_process_state_name,
            current_output_stream_state=self.current_output_stream_state,
            current_storage_level=self.current_storage_level,
            process_state_data_dictionary=copy_of_process_state_data_dictionary,
            validated_input_stream_list=copy_of_validated_input_stream_list,
        )
        return self_copy

    def _create_copy_of_validated_input_stream_list(self):
        copy_of_validated_input_stream_list = list(self.validated_input_stream_list)
        return copy_of_validated_input_stream_list


@dataclass(kw_only=True)
class PostProductionStateData(ValidatedPostProductionStateData):
    current_input_stream_state: ContinuousStreamState | BatchStreamState

    def create_self_copy(self):
        copy_of_process_state_data_dictionary = (
            self._create_copy_of_process_state_data_dictionary()
        )
        copy_of_validated_input_stream_list = (
            self._create_copy_of_validated_input_stream_list()
        )
        self_copy = PostProductionStateData(
            current_process_state_name=self.current_process_state_name,
            current_output_stream_state=self.current_output_stream_state,
            current_storage_level=self.current_storage_level,
            process_state_data_dictionary=copy_of_process_state_data_dictionary,
            validated_input_stream_list=copy_of_validated_input_stream_list,
            current_input_stream_state=self.current_input_stream_state,
        )
        return self_copy
