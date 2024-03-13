import datetime
import uuid
from abc import ABC
from dataclasses import dataclass, field
from typing import Optional

from ethos_penalps.data_classes import (
    Commodity,
    OutputBranchIdentifier,
    ProductionOrder,
    TemporalBranchIdentifier,
)
from ethos_penalps.simulation_data.simulation_data_branch import (
    CompleteOutputBranchData,
    IncompleteOutputBranchData,
    OutputBranchData,
)
from ethos_penalps.stream import (
    BatchStreamProductionPlanEntry,
    BatchStreamState,
    ContinuousStreamProductionPlanEntry,
    ContinuousStreamState,
)


@dataclass
class NodeOperation(ABC):
    next_node_name: str | None
    starting_node_name: str


def get_new_uuid() -> str:
    return str(uuid.uuid4())


@dataclass
class UpstreamNewProductionOrder(NodeOperation):
    """This order is passed in upstream direction and
    requests a new output stream from the target node.

    :param NodeOperation: _description_
    :type NodeOperation: _type_
    """

    stream_state: ContinuousStreamState | BatchStreamState
    production_order: ProductionOrder
    starting_node_output_branch_data: IncompleteOutputBranchData
    operation_type: str = "Upstream new production order"

    def __post_init__(self):
        if not isinstance(
            self.starting_node_output_branch_data, IncompleteOutputBranchData
        ):
            raise Exception("Wrong data type")


@dataclass
class UpstreamAdaptionOrder(NodeOperation):
    """This order is passed in upstream direction
    as a response to a previous input stream adaption request which is
    passed downstream. The start node of this operation has accepted
    the previously proposed adaption.

    :param NodeOperation: _description_
    :type NodeOperation: _type_
    """

    stream_state: ContinuousStreamState | BatchStreamState
    production_order: ProductionOrder
    starting_node_output_branch_data: IncompleteOutputBranchData
    target_node_output_branch_data: IncompleteOutputBranchData
    operation_type: str = "Upstream adaption order"

    def __post_init__(self):
        if not isinstance(
            self.starting_node_output_branch_data, IncompleteOutputBranchData
        ):
            raise Exception("Wrong data type")
        if not isinstance(
            self.target_node_output_branch_data, IncompleteOutputBranchData
        ):
            raise Exception("Wrong data type")


@dataclass
class DownstreamAdaptionOrder(NodeOperation):
    """The order is passed downstream and requests an adaption of the previously
    requests input stream of the target node. The adaption is either a shift to
    an earlier delivery or a reduced delivered mass. The adaption request will always
    be accepted.

    :param NodeOperation: _description_
    :type NodeOperation: _type_
    """

    stream_state: ContinuousStreamState | BatchStreamState
    production_order: ProductionOrder
    starting_node_output_branch_data: IncompleteOutputBranchData
    target_node_output_branch_data: IncompleteOutputBranchData
    operation_type: str = "Downstream adaption operation"


@dataclass
class DownstreamValidationOrder(NodeOperation):
    """This order is passed downstream and validates that the previously
    requested input stream can be delivered as requested.

    :param NodeOperation: _description_
    :type NodeOperation: _type_
    """

    starting_node_output_branch_data: CompleteOutputBranchData
    target_node_output_branch_identifier: OutputBranchIdentifier
    target_node_temporal_identifier: TemporalBranchIdentifier
    production_order: ProductionOrder
    operation_type: str = "Downstream validation operation"


@dataclass
class TerminateProduction(NodeOperation):
    operation_type: str = "Terminate production"
