import datetime
from abc import ABC, abstractmethod

from ethos_penalps.data_classes import (
    Commodity,
    OutputBranchIdentifier,
    ProcessChainIdentifier,
    StaticTimePeriod,
    TemporalBranchIdentifier,
)
from ethos_penalps.load_profile_calculator import LoadProfileHandler
from ethos_penalps.mass_balance import MassBalance
from ethos_penalps.node_operations import (
    DownstreamAdaptionOrder,
    DownstreamValidationOrder,
    NodeOperation,
    ProductionOrder,
    TerminateProduction,
    UpstreamAdaptionOrder,
    UpstreamNewProductionOrder,
)
from ethos_penalps.process_node_communicator import (
    EmptyProductionBranch,
    ProcessNodeCommunicator,
)
from ethos_penalps.process_state_handler import ProcessStateHandler
from ethos_penalps.process_step_data import ProcessStepData
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.simulation_data.simulation_data_branch import (
    CompleteOutputBranchData,
    IncompleteOutputBranchData,
    OutputBranchData,
)
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamState,
    ContinuousStream,
    ContinuousStreamState,
)
from ethos_penalps.stream_handler import StreamHandler

from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.exceptions_and_warnings import Misconfiguration
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger


class ProcessNode(ABC):
    def __init__(
        self,
        stream_handler: StreamHandler,
        name: str,
    ) -> None:
        super().__init__()
        self.stream_handler: StreamHandler = stream_handler
        self.name: str = name

    @abstractmethod
    def process_input_order(self, input_node_operation: NodeOperation) -> NodeOperation:
        raise NotImplementedError

    @abstractmethod
    def get_input_stream_name(
        self,
    ) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def get_output_stream_name(
        self,
    ) -> str:
        raise NotImplementedError
