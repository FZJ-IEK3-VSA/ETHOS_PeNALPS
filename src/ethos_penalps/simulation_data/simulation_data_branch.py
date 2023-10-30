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


# Input Branch data classes
@dataclass(kw_only=True)
class TemporalBranchData:
    identifier: TemporalBranchIdentifier


@dataclass(kw_only=True)
class CompleteTemporalBranchData(TemporalBranchData):
    pass


# Input Stream Branch data classes


@dataclass(kw_only=True)
class StreamBranchData:
    identifier: StreamBranchIdentifier
    list_of_complete_input_branches: list[CompleteTemporalBranchData] = field(
        default_factory=list
    )

    def complete_input_branch_data(
        self, incomplete_input_branch_data: TemporalBranchData
    ):
        self.list_of_complete_input_branches.append(
            CompleteTemporalBranchData(
                identifier=incomplete_input_branch_data.identifier
            )
        )

    def get_incomplete_input_branch_data(self):
        raise IllogicalFunctionCall("")

    def create_copy(self):
        return StreamBranchData(
            identifier=self.identifier,
            list_of_complete_input_branches=list(self.list_of_complete_input_branches),
        )


@dataclass(kw_only=True)
class IncompleteStreamBranchData(StreamBranchData):
    current_incomplete_input_branch: TemporalBranchData

    def create_complete_input_branch_data(self) -> CompleteTemporalBranchData:
        return CompleteTemporalBranchData(
            identifier=self.current_incomplete_input_branch
        )

    def get_incomplete_input_branch_data(self) -> TemporalBranchData:
        return self.current_incomplete_input_branch

    def create_copy(self):
        return IncompleteStreamBranchData(
            identifier=self.identifier,
            list_of_complete_input_branches=list(self.list_of_complete_input_branches),
            current_incomplete_input_branch=self.current_incomplete_input_branch,
        )


class CompleteStreamBranchData(StreamBranchData):
    def __init__(self, stream_branch_data: StreamBranchData) -> None:
        super().__init__(
            identifier=stream_branch_data.identifier,
            list_of_complete_input_branches=list(
                stream_branch_data.list_of_complete_input_branches
            ),
        )
        self.identifier: StreamBranchIdentifier = stream_branch_data.identifier

    def get_incomplete_input_branch_data(self):
        raise IllogicalFunctionCall("")

    def create_copy(self):
        return CompleteStreamBranchData(
            stream_branch_data=StreamBranchData(
                identifier=self.identifier,
                list_of_complete_input_branches=list(
                    self.list_of_complete_input_branches
                ),
            )
        )


# Output Branch Data
@dataclass(kw_only=True)
class UninitializedOutputBranchData:
    pass


@dataclass(kw_only=True)
class OutputBranchData:
    identifier: OutputBranchIdentifier
    parent_output_identifier: OutputBranchIdentifier
    parent_input_identifier: TemporalBranchIdentifier
    dict_of_complete_stream_branch: dict[str, StreamBranchData] = field(
        default_factory=dict
    )
    production_branch_production_plan: OutputBranchProductionPlan

    # list_of_complete_input_branches: list[CompleteInputBranchData] = field(
    #     default_factory=list
    # )
    def create_copy(self):
        return OutputBranchData(
            identifier=self.identifier,
            parent_output_identifier=self.parent_output_identifier,
            parent_input_identifier=self.parent_input_identifier,
            dict_of_complete_stream_branch=dict(self.dict_of_complete_stream_branch),
            production_branch_production_plan=self.production_branch_production_plan.create_self_copy(),
        )


@dataclass(kw_only=True)
class IncompleteOutputBranchData(OutputBranchData):
    # TODO check old references
    current_stream_branch: StreamBranchData

    # current_input_branch: InputBranchData
    def create_copy(self):
        return IncompleteOutputBranchData(
            identifier=self.identifier,
            current_stream_branch=self.current_stream_branch.create_copy(),
            parent_input_identifier=self.parent_input_identifier,
            parent_output_identifier=self.parent_output_identifier,
            dict_of_complete_stream_branch=dict(self.dict_of_complete_stream_branch),
            production_branch_production_plan=self.production_branch_production_plan.create_self_copy(),
        )


class CompleteOutputBranchData(OutputBranchData):
    def __init__(
        self,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        output_branch_data: OutputBranchData,
    ):
        super().__init__(
            identifier=output_branch_data.identifier,
            parent_output_identifier=output_branch_data.parent_output_identifier,
            parent_input_identifier=output_branch_data.parent_input_identifier,
            dict_of_complete_stream_branch=dict(
                output_branch_data.dict_of_complete_stream_branch
            ),
            production_branch_production_plan=output_branch_data.production_branch_production_plan,
        )
        self.start_time: datetime.datetime = start_time
        self.end_time: datetime.datetime = end_time

    def create_copy(self):
        return CompleteOutputBranchData(
            start_time=self.start_time,
            end_time=self.end_time,
            output_branch_data=OutputBranchData(
                identifier=self.identifier,
                parent_input_identifier=self.parent_input_identifier,
                parent_output_identifier=self.parent_output_identifier,
                dict_of_complete_stream_branch=dict(
                    self.dict_of_complete_stream_branch
                ),
                production_branch_production_plan=self.production_branch_production_plan.create_self_copy(),
            ),
        )
