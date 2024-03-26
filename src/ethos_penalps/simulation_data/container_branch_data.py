from dataclasses import dataclass, field

from ethos_penalps.data_classes import (
    OutputBranchIdentifier,
    ProcessStateData,
    StreamBranchIdentifier,
    TemporalBranchIdentifier,
)
from ethos_penalps.production_plan import OutputBranchProductionPlan
from ethos_penalps.simulation_data.simulation_data_branch import (
    CompleteOutputBranchData,
    CompleteStreamBranchData,
    CompleteTemporalBranchData,
    IncompleteOutputBranchData,
    IncompleteStreamBranchData,
    OutputBranchData,
    StreamBranchData,
    TemporalBranchData,
    UninitializedOutputBranchData,
)
from ethos_penalps.stream import BatchStreamState, ContinuousStreamState
from ethos_penalps.utilities.exceptions_and_warnings import (
    IllogicalFunctionCall,
    IllogicalSimulationState,
    UnexpectedDataType,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger


class BranchDataContainer:
    """This class is used to store the internal simulation data of a
    process step during the simulation.
    """

    def __init__(self) -> None:
        self.current_branch_data: (
            IncompleteOutputBranchData | OutputBranchData | CompleteOutputBranchData
        ) = UninitializedOutputBranchData()
        self.list_of_complete_branch_data: list[CompleteOutputBranchData] = []

    def get_current_output_branch_identifier(self) -> OutputBranchIdentifier:
        """Returns OutputBranchIdentifier of the current branch.


        Returns:
            OutputBranchIdentifier: Identifier of the current output branch.
        """
        if isinstance(
            self.current_branch_data,
            (IncompleteOutputBranchData, OutputBranchData, CompleteOutputBranchData),
        ):
            current_output_branch_identifier = self.current_branch_data.identifier
            return current_output_branch_identifier

        raise UnexpectedDataType(
            current_data_type=self.current_branch_data,
            expected_data_type=(
                IncompleteOutputBranchData,
                OutputBranchData,
                CompleteOutputBranchData,
            ),
        )

    def get_current_temporal_branch_identifier(self) -> TemporalBranchIdentifier:
        """Returns the temporal branch identifier of the current simulation
        data. This identifier is used to distinguish multiple input stream states.

        Returns:
            TemporalBranchIdentifier: Identifies the data that was created to create
                a request for a specific input stream state.
        """
        previous_output_branch_data = self.current_branch_data
        if type(previous_output_branch_data) is IncompleteOutputBranchData:
            current_stream_branch = previous_output_branch_data.current_stream_branch
            if type(current_stream_branch) is IncompleteStreamBranchData:
                temporal_branch_identifier = (
                    current_stream_branch.current_incomplete_input_branch.identifier
                )
            else:
                raise IllogicalFunctionCall
        else:
            raise IllogicalFunctionCall
        return temporal_branch_identifier

    def update_temporary_production_plan(
        self, updated_temporary_production_plan: OutputBranchProductionPlan
    ):
        """Updates the temporary production plan. It stores all the simulation results
        of a process step that are created to provide an output stream. When all
        required input stream states are validated the data is transferred to the production
        plan.

        Args:
            updated_temporary_production_plan (OutputBranchProductionPlan): Is an updated
                temporary production plan that contains additional information.
        """
        self.current_branch_data.production_branch_production_plan = (
            updated_temporary_production_plan
        )

    def get_temporary_production_plan(self) -> OutputBranchProductionPlan:
        """Returns temporary production plan that contains the simulation results
            before the input streams are validated.

        Returns:
            OutputBranchProductionPlan: Stores the
                the intermediate production results before the input streams are validated
                and the output branch is completed.
        """
        return self.current_branch_data.production_branch_production_plan

    def get_incomplete_branch_data(self) -> IncompleteOutputBranchData:
        """Returns incomplete output branch data. It contains the simulation
        data of the request and indicates that not all input streams have been
        validated before.

        Returns:
            IncompleteOutputBranchData: contains the simulation
                data of the request and indicates that not all input streams have been
                validated before.
        """
        if type(self.current_branch_data) is not IncompleteOutputBranchData:
            raise UnexpectedDataType(
                current_data_type=self.current_branch_data,
                expected_data_type=IncompleteOutputBranchData,
            )
        return self.current_branch_data

    def get_complete_branch_data(self) -> CompleteOutputBranchData:
        """Returns the complete branch data that signals that
        all input stream states have been validated.

        Returns:
            CompleteOutputBranchData: Complete branch data that signals that
                all input stream states have been validated.
        """
        if type(self.current_branch_data) is not CompleteOutputBranchData:
            raise UnexpectedDataType(
                current_data_type=self.current_branch_data,
                expected_data_type=CompleteOutputBranchData,
            )
        return self.current_branch_data

    def get_output_branch_data(self) -> OutputBranchData:
        """Returns the output branch data that identifies
        a specific output stream request.

        Returns:
            OutputBranchData: Output branch data that identifies
        a specific output stream request.
        """
        if not isinstance(self.current_branch_data, OutputBranchData):
            raise UnexpectedDataType(
                current_data_type=self.current_branch_data,
                expected_data_type=OutputBranchData,
            )

        return self.current_branch_data

    def create_new_output_branch_data(
        self, parent_branch_data: IncompleteOutputBranchData
    ):
        """Creates a new output branch data for a new stream request.

        Args:
            parent_branch_data (IncompleteOutputBranchData): The identifier
                of the output stream state that initialized the
                request for this stream.
        """
        # Store old branch data
        if type(self.current_branch_data) is CompleteOutputBranchData:
            self.list_of_complete_branch_data.append(self.current_branch_data)
            last_output_branch_data = self.list_of_complete_branch_data[-1]
            output_branch_number = last_output_branch_data.identifier.branch_number
            new_output_branch_identifier = OutputBranchIdentifier(
                branch_number=output_branch_number + 1
            )

            new_output_branch_data = OutputBranchData(
                identifier=new_output_branch_identifier,
                parent_output_identifier=parent_branch_data.parent_output_identifier,
                parent_input_identifier=parent_branch_data.parent_input_identifier,
                production_branch_production_plan=OutputBranchProductionPlan(),
            )
            self.current_branch_data = new_output_branch_data
        elif type(self.current_branch_data) is UninitializedOutputBranchData:
            new_output_branch_identifier = OutputBranchIdentifier(branch_number=0)
            new_output_branch_data = OutputBranchData(
                identifier=new_output_branch_identifier,
                parent_output_identifier=parent_branch_data.parent_output_identifier,
                parent_input_identifier=parent_branch_data.parent_input_identifier,
                production_branch_production_plan=OutputBranchProductionPlan(),
            )
            self.current_branch_data = new_output_branch_data
        elif type(self.current_branch_data) is IncompleteOutputBranchData:
            raise IllogicalSimulationState(
                "A previous input branch has not been validated before "
            )
        elif type(self.current_branch_data) is CompleteOutputBranchData:
            raise IllogicalSimulationState(
                "the current output branch is already prepared"
            )
        else:
            raise IllogicalSimulationState

    def prepare_new_stream_branch(self, stream_name: str):
        """It converts an OutputBranchData to an IncompleteOutputBranchData"""
        previous_branch_data = self.current_branch_data
        if type(previous_branch_data) is OutputBranchData:
            stream_branch_data = StreamBranchData(
                identifier=StreamBranchIdentifier(stream_name=stream_name)
            )

            new_current_branch_data = IncompleteOutputBranchData(
                identifier=previous_branch_data.identifier,
                parent_output_identifier=previous_branch_data.parent_output_identifier,
                parent_input_identifier=previous_branch_data.parent_input_identifier,
                current_stream_branch=stream_branch_data,
                production_branch_production_plan=previous_branch_data.production_branch_production_plan,
            )
            self.current_branch_data = new_current_branch_data
        elif type(previous_branch_data) is IncompleteOutputBranchData:
            raise IllogicalFunctionCall(
                """Preparation for a new temporal branch has been called before
                the previous temporal branch has been validated"""
            )
        elif type(previous_branch_data) is CompleteOutputBranchData:
            raise IllogicalFunctionCall(
                """Preparation for a new temporal branch has been called even
                though the output branch is already complete """
            )
        elif type(previous_branch_data) is UninitializedOutputBranchData:
            raise IllogicalFunctionCall(
                """Preparation for a new temporal branch has been called before the simulation
                data is initialized"""
            )
        else:
            raise IllogicalSimulationState

    def prepare_new_temporal_branch(self):
        """Prepares the simulation data for a new temporal branch.
        It converts IncompleteOutputBranchData to an IncompleteStreamBranchData."""
        previous_output_branch_data = self.current_branch_data
        if type(previous_output_branch_data) is IncompleteOutputBranchData:
            stream_branch_data = previous_output_branch_data.current_stream_branch
            identifier = TemporalBranchIdentifier(
                branch_number=len(stream_branch_data.list_of_complete_input_branches)
            )
            temporal_branch_data = TemporalBranchData(identifier=identifier)
            incomplete_stream_branch_data = IncompleteStreamBranchData(
                identifier=stream_branch_data.identifier,
                list_of_complete_input_branches=stream_branch_data.list_of_complete_input_branches,
                current_incomplete_input_branch=temporal_branch_data,
            )
            new_current_branch_data = previous_output_branch_data.create_copy()
            new_current_branch_data.current_stream_branch = (
                incomplete_stream_branch_data
            )
            self.current_branch_data = new_current_branch_data
        elif type(previous_output_branch_data) is OutputBranchData:
            raise IllogicalFunctionCall(
                """Preparation for a new temporal branch has been called before
                the previous temporal branch has been validated"""
            )
        elif type(previous_output_branch_data) is CompleteOutputBranchData:
            raise IllogicalFunctionCall(
                """Preparation for a new temporal branch has been called even
                though the output branch is already complete """
            )
        elif type(previous_output_branch_data) is UninitializedOutputBranchData:
            raise IllogicalFunctionCall(
                """Preparation for a new temporal branch has been called before the simulation
                data is initialized"""
            )
        else:
            raise IllogicalSimulationState

    def complete_temporal_branch(self):
        """Converts an IncompleteOutputBranchData into an
        StreamBranchData.

        """
        previous_output_branch_data = self.current_branch_data
        if type(previous_output_branch_data) is IncompleteOutputBranchData:
            stream_branch_data = previous_output_branch_data.current_stream_branch
            if type(stream_branch_data) is IncompleteStreamBranchData:
                complete_temporal_branch_data = CompleteTemporalBranchData(
                    identifier=stream_branch_data.current_incomplete_input_branch.identifier
                )
                stream_branch_data = StreamBranchData(
                    identifier=stream_branch_data.identifier,
                    list_of_complete_input_branches=list(
                        stream_branch_data.list_of_complete_input_branches
                    ),
                )
                stream_branch_data.list_of_complete_input_branches.append(
                    complete_temporal_branch_data
                )
                new_branch_data = previous_output_branch_data.create_copy()
                new_branch_data.current_stream_branch = stream_branch_data
                self.current_branch_data = new_branch_data
            else:
                raise IllogicalSimulationState
        else:
            raise IllogicalSimulationState

    def complete_stream_branch(self):
        """Converts the simulation data from IncompleteOutputBranchData to
        OutputBranchData.

        """
        previous_output_branch_data = self.current_branch_data
        if type(previous_output_branch_data) is IncompleteOutputBranchData:
            stream_branch_data = previous_output_branch_data.current_stream_branch
            if type(stream_branch_data) is StreamBranchData:
                stream_branch_data = CompleteStreamBranchData(
                    stream_branch_data=stream_branch_data,
                )
                new_output_branch_data = OutputBranchData(
                    identifier=previous_output_branch_data.identifier,
                    parent_output_identifier=previous_output_branch_data.parent_output_identifier,
                    parent_input_identifier=previous_output_branch_data.parent_input_identifier,
                    dict_of_complete_stream_branch=dict(
                        previous_output_branch_data.dict_of_complete_stream_branch
                    ),
                    production_branch_production_plan=previous_output_branch_data.production_branch_production_plan.create_self_copy(),
                )
                new_output_branch_data.dict_of_complete_stream_branch[
                    stream_branch_data.identifier.stream_name
                ] = stream_branch_data
                self.current_branch_data = new_output_branch_data
            else:
                raise IllogicalSimulationState
        else:
            raise IllogicalSimulationState

    def complete_output_branch(self):
        """Converts the OutputBranchData into the CompleteOutputBranchData."""
        previous_output_branch_data = self.current_branch_data
        if type(previous_output_branch_data) is OutputBranchData:
            start_time = (
                previous_output_branch_data.production_branch_production_plan.determine_start_time()
            )
            end_time = (
                previous_output_branch_data.production_branch_production_plan.determine_start_time()
            )
            complete_output_branch_data = CompleteOutputBranchData(
                start_time=start_time,
                end_time=end_time,
                output_branch_data=previous_output_branch_data,
            )
            self.current_branch_data = complete_output_branch_data
        else:
            raise IllogicalSimulationState
