import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ethos_penalps.data_classes import (
    OutputBranchIdentifier,
    OutputInputBranchConnector,
    ProcessStateData,
    TemporalBranchIdentifier,
)
from ethos_penalps.production_plan import OutputBranchProductionPlan
from ethos_penalps.simulation_data.container_branch_data import BranchDataContainer
from ethos_penalps.simulation_data.container_process_state_network_data import (
    ProcessStateNetworkContainer,
)
from ethos_penalps.simulation_data.simulation_data_branch import (
    CompleteOutputBranchData,
    CompleteStreamBranchData,
    CompleteTemporalBranchData,
    IncompleteOutputBranchData,
    OutputBranchData,
    StreamBranchData,
    TemporalBranchData,
    UninitializedOutputBranchData,
)
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


class ProductionProcessStateContainer(
    BranchDataContainer, ProcessStateNetworkContainer
):
    def __init__(self) -> None:
        BranchDataContainer.__init__(self)
        ProcessStateNetworkContainer.__init__(self)

    def add_process_state_state(self, process_state_state: ProcessStateData):
        if type(self.state_data) in (
            PreProductionStateData,
            PostProductionStateData,
            ValidatedPostProductionStateData,
        ):
            self.state_data.process_state_data_dictionary[
                process_state_state.process_state_name
            ] = process_state_state

    def restore_process_state_data(
        self,
        state_data_to_update: (
            ValidatedPostProductionStateData
            | PostProductionStateData
            | PreProductionStateData
        ),
    ):
        self.state_data = state_data_to_update

    def restore_branch_data(self, branch_data_at_start: OutputBranchData):
        self.current_branch_data = branch_data_at_start

    def check_if_validated_input_stream_list_is_shorter_than_1(self) -> bool:
        if type(self.state_data) is PreProductionStateData:
            validated_input_stream_list_is_longer_than_1 = True
        elif type(self.state_data) in (
            PostProductionStateData,
            ValidatedPostProductionStateData,
        ):
            if len(self.state_data.validated_input_stream_list) > 1:
                validated_input_stream_list_is_longer_than_1 = False
            else:
                validated_input_stream_list_is_longer_than_1 = True
        else:
            raise UnexpectedDataType(
                current_data_type=self.state_data,
                expected_data_type=(
                    PreProductionStateData,
                    PostProductionStateData,
                    ValidatedPostProductionStateData,
                ),
            )

        return validated_input_stream_list_is_longer_than_1

    def get_post_production_state_data(self) -> PostProductionStateData:
        if type(self.state_data) is not PostProductionStateData:
            raise UnexpectedDataType(
                current_data_type=self.state_data,
                expected_data_type=PostProductionStateData,
            )
        return self.state_data

    def get_pre_production_state_data(self) -> PreProductionStateData:
        if type(self.state_data) is not PreProductionStateData:
            raise UnexpectedDataType(
                current_data_type=self.state_data,
                expected_data_type=PreProductionStateData,
            )
        return self.state_data

    def get_pre_or_post_production_state_data(
        self,
    ) -> PreProductionStateData | PostProductionStateData:
        if type(self.state_data) not in (
            PostProductionStateData,
            PreProductionStateData,
        ):
            raise UnexpectedDataType(
                current_data_type=self.state_data,
                expected_data_type=(PostProductionStateData, PreProductionStateData),
            )
        return self.state_data

    def get_validated_production_state_data(
        self,
    ) -> ValidatedPostProductionStateData:
        if not type(self.state_data) is ValidatedPostProductionStateData:
            raise UnexpectedDataType(
                current_data_type=self.state_data,
                expected_data_type=ValidatedPostProductionStateData,
            )
        return self.state_data

    def get_validated_or_post_production_state_data(
        self,
    ) -> ValidatedPostProductionStateData | PostProductionStateData:
        if not type(self.state_data) in (
            ValidatedPostProductionStateData,
            PostProductionStateData,
        ):
            raise UnexpectedDataType(
                current_data_type=self.state_data,
                expected_data_type=(
                    ValidatedPostProductionStateData,
                    PostProductionStateData,
                ),
            )
        return self.state_data

    def get_validated_pre_or_post_production_state(
        self,
    ) -> (
        PreProductionStateData
        | PostProductionStateData
        | ValidatedPostProductionStateData
    ):
        if not type(self.state_data) in (
            PostProductionStateData,
            PreProductionStateData,
            ValidatedPostProductionStateData,
        ):
            raise UnexpectedDataType(
                current_data_type=self.state_data,
                expected_data_type=(PostProductionStateData, PreProductionStateData),
            )
        return self.state_data

    def initialize_production_data(
        self,
    ):
        current_process_state_name = (
            self.initialization_data_collector.current_process_state_name
        )
        output_stream_state = (
            self.initialization_data_collector.current_output_stream_state
        )
        current_storage_level = self.initialization_data_collector.current_storage_level
        if type(self.state_data) is UninitializedCurrentStateData:
            self.state_data = PreProductionStateData(
                current_process_state_name=current_process_state_name,
                current_output_stream_state=output_stream_state,
                current_storage_level=current_storage_level,
            )
        elif type(self.state_data) in (PreProductionStateData, PostProductionStateData):
            raise IllogicalFunctionCall("Process state data is already initialized")
        else:
            raise UnexpectedDataType(
                current_data_type=self.state_data,
                expected_data_type=(PostProductionStateData, PreProductionStateData),
            )

    def prepare_for_new_output_branch(
        self,
        new_output_stream_state: ContinuousStreamState | BatchStreamState,
        parent_branch_data: IncompleteOutputBranchData,
    ):
        previous_production_state_data = self.state_data
        if type(previous_production_state_data) is ValidatedPostProductionStateData:
            self.list_of_complete_branch_data.append(self.current_branch_data)
            self.state_data = PreProductionStateData(
                current_process_state_name=previous_production_state_data.current_process_state_name,
                current_output_stream_state=new_output_stream_state,
                current_storage_level=previous_production_state_data.current_storage_level,
            )

        elif type(previous_production_state_data) is PreProductionStateData:
            self.state_data = PreProductionStateData(
                current_process_state_name=previous_production_state_data.current_process_state_name,
                current_output_stream_state=new_output_stream_state,
                current_storage_level=previous_production_state_data.current_storage_level,
            )
            self.list_of_complete_branch_data.append(self.current_branch_data)
        elif type(previous_production_state_data) is UninitializedCurrentStateData:
            raise IllogicalFunctionCall(
                "Preparation for new production branch begins before initialization"
            )
        else:
            raise UnexpectedDataType(
                current_data_type=previous_production_state_data,
                expected_data_type=(
                    ValidatedPostProductionStateData,
                    PreProductionStateData,
                ),
            )
        self.create_new_output_branch_data(parent_branch_data=parent_branch_data)

    def validate_input_stream(self):
        previous_production_state_data = self.state_data
        if type(previous_production_state_data) is PostProductionStateData:
            new_validated_stream_list = list(
                previous_production_state_data.validated_input_stream_list
            )
            new_validated_stream_list.append(
                previous_production_state_data.current_input_stream_state
            )
            if type(new_validated_stream_list) != list:
                raise Exception("Unexpected datatype")
            self.state_data = ValidatedPostProductionStateData(
                current_process_state_name=previous_production_state_data.current_process_state_name,
                current_output_stream_state=previous_production_state_data.current_output_stream_state,
                current_storage_level=previous_production_state_data.current_storage_level,
                validated_input_stream_list=new_validated_stream_list,
                process_state_data_dictionary=dict(
                    previous_production_state_data.process_state_data_dictionary
                ),
            )
            self.complete_temporal_branch()

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
                expected_data_type=PostProductionStateData,
            )

    def clear_up_after_input_branch(self):
        if not type(self.state_data) in (
            PostProductionStateData,
            PreProductionStateData,
            ValidatedPostProductionStateData,
        ):
            raise UnexpectedDataType(
                current_data_type=self.state_data,
                expected_data_type=(PostProductionStateData, PreProductionStateData),
            )

        self.state_data.process_state_data_dictionary = {}
