import datetime
import numbers
import warnings
from dataclasses import dataclass, field, fields
from typing import Optional

import pandas
import pint
from dataclasses_json import DataClassJsonMixin, config, dataclass_json

from ethos_penalps.utilities.exceptions_and_warnings import UnexpectedBehaviorWarning
from ethos_penalps.utilities.general_functions import get_new_uuid
from ethos_penalps.utilities.units import Units


@dataclass(
    frozen=True,
    eq=True,
)
class Commodity(DataClassJsonMixin):
    """This object describes a commodity used in an Enterprise. It can be transported in streams
    or converted into other commodities in process steps.
    """

    name: str

    def __str__(self) -> str:
        return "Commodity: " + self.name

    def __repr__(self) -> str:
        return "Commodity: " + self.name


@dataclass(frozen=True, eq=True, slots=True)
class LoadType(DataClassJsonMixin):
    """Represents an energy carrier like electricity or natural
    gas that should be considered during the simulation.
    """

    name: str
    """Name of energy load type
    """
    uuid: str = field(default_factory=get_new_uuid)
    """Unique identifier to distinguish load types.
    """


@dataclass(frozen=True, eq=True)
class ProcessStateData(DataClassJsonMixin):
    """Intermediate simulation data that represents
    a discrete state of the process step during the
    discrete event simulation.
    """

    process_state_name: str
    start_time: datetime.datetime
    end_time: datetime.datetime


@dataclass
class EmptyMetaDataInformation:
    """Represents a simulation results like a list of LoadProfileEntry
    or a list BatchStreamProductionPlanEntry that did not create a
    single entry during the simulation. This data is used to prevent
    analysis on this non existent data.
    """

    name: str
    object_type: str


@dataclass()
class ProductEnergyData(DataClassJsonMixin):
    """Summarizes the specific energy demand that is
    required for an end product. It considers previous
    energy demand and conversion factors from previous
    steps."""

    product_commodity: Commodity
    specific_energy_demand: float
    load_type: LoadType
    mass_unit: str = str(Units.energy_unit)
    energy_unit: str = str(Units.energy_unit)


@dataclass(frozen=True, eq=True, unsafe_hash=True)
class StreamLoadEnergyData(DataClassJsonMixin):
    """Summarizes the energy data that is required
    to converts a stream state to a LoadProfileEntry.
    """

    stream_name: str
    specific_energy_demand: float
    load_type: LoadType
    mass_unit: str = str(Units.mass_unit)
    energy_unit: str = str(Units.energy_unit)


@dataclass(slots=True, frozen=True)
class LoadProfileEntry(DataClassJsonMixin):
    """Represents the energy demand of
    stream or process step in the given time
    period.
    """

    load_type: LoadType
    start_time: datetime.datetime
    end_time: datetime.datetime
    energy_quantity: float
    energy_unit: str
    average_power_consumption: float
    power_unit: str

    def _adjust_power_unit(
        self, new_power_value: float, new_power_unit: str
    ) -> "LoadProfileEntry":
        """Converts the power quantity to a
        new value and unit.

        Args:
            new_power_value (float): New power value.
            new_power_unit (str): New power unit string.

        Returns:
            LoadProfileEntry: Converted load profile entry.
        """
        load_profile_entry = LoadProfileEntry(
            load_type=self.load_type,
            start_time=self.start_time,
            end_time=self.end_time,
            energy_quantity=self.energy_quantity,
            energy_unit=self.energy_unit,
            power_unit=new_power_unit,
            average_power_consumption=new_power_value,
        )
        return load_profile_entry


class LoopCounter:
    """Counts the iterations within a ProcessChain
    during the simulation.
    """

    loop_number: float | str = "Loop has not started"


@dataclass(kw_only=True, frozen=True, slots=True)
class ProcessStepProductionPlanEntry(DataClassJsonMixin):
    """Summarizes the activity of a process step in
    a discrete time period.
    """

    process_step_name: str
    process_state_name: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    duration: str
    process_state_type: str


@dataclass(frozen=True, slots=True)
class StorageProductionPlanEntry(DataClassJsonMixin):
    """Represents the storage level in a discrete
    time period.
    """

    process_step_name: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    duration: str
    storage_level_at_start: float
    storage_level_at_end: float
    commodity: Commodity


@dataclass(frozen=True, eq=True, slots=True)
class StateConnector:
    """Represents the connection between
    two states of the petri net in a ProcessStep.
    """

    start_state_name: str
    end_state_name: str


@dataclass
class ProcessStepDataFrameMetaInformation:
    """Provides the simulation results of a
    ProcessStep and additional meta information
    about this data and the.
    """

    data_frame: pandas.DataFrame
    process_step_name: str
    list_of_process_state_names: list[str]
    first_start_time: datetime.datetime
    last_end_time: datetime.datetime


@dataclass
class StorageDataFrameMetaInformation:
    """Provides the simulation results of
    a stream and additional meta information
    about this data and the.
    """

    data_frame: pandas.DataFrame
    process_step_name: str
    commodity: Commodity
    first_start_time: datetime.datetime
    last_end_time: datetime.datetime
    mass_unit: str


@dataclass
class CurrentProcessNode:
    """Tracks the current active node
    during the simulation."""

    node_name: str = "Node not set yet"


@dataclass(frozen=True, eq=True, slots=True)
class OutputBranchIdentifier:
    """Is used to identify and distinguish output branches.
    An output branch represents a request for an output stream
    that is fulfilled by a ProcessStep.
    """

    branch_number: float
    global_unique_identifier: Optional[str] = field(default_factory=get_new_uuid)


@dataclass(frozen=True, eq=True, slots=True)
class TemporalBranchIdentifier:
    """Identifies an instance of the same input stream state
    that is required to fulfill an output stream.
    """

    branch_number: float
    global_unique_identifier: Optional[str] = field(default_factory=get_new_uuid)


@dataclass(frozen=True, eq=True, slots=True)
class StreamBranchIdentifier:
    """Is used to identify one of multiple
    input stream that is required to fulfill an output stream.
    Multiple input streams are still in development."""

    stream_name: str
    global_unique_identifier: Optional[str] = field(default_factory=get_new_uuid)


@dataclass(frozen=True, eq=True, slots=True)
class OutputInputBranchConnector:
    """Stores the connection between an input and output
    branch.
    """

    input_branch_identifier: TemporalBranchIdentifier
    output_branch_identifier: OutputBranchIdentifier


@dataclass(frozen=True, eq=True, slots=True)
class StaticTimePeriod:
    """Constitutes a discrete time period."""

    start_time: datetime.datetime
    end_time: datetime.datetime
    uuid: OutputBranchIdentifier

    def get_duration(self) -> datetime.timedelta:
        return self.end_time - self.start_time


@dataclass(frozen=True, slots=True, eq=True)
class ProcessChainIdentifier:
    """Is used to identify and distinguish
    multiple process chains.
    """

    chain_number: int
    chain_name: str
    unique_identifier: str = get_new_uuid()


@dataclass
class ProductionOrder:
    """Represents an Order for a product
    that should be produced during the simulation."""

    production_target: float
    production_deadline: datetime.datetime
    order_number: float
    commodity: Commodity
    global_unique_identifier: str = field(default_factory=get_new_uuid)
    produced_mass: float = 0


class OrderCollection:
    """Combines multiple order that should be passed
    to a sink.
    """

    def __init__(
        self,
        target_mass: float,
        commodity: Commodity,
        order_data_frame: pandas.DataFrame | None = None,
    ) -> None:
        """

        Args:
            target_mass (float): Total mass of all orders
            commodity (Commodity): Commodity of all orders.
                All orders must have the same commodity
            order_data_frame (pandas.DataFrame | None, optional):
                The data frame is created from a list of ProductionOrder
                Defaults to None.
        """
        self.target_mass: float = target_mass
        self.commodity: Commodity = commodity
        if order_data_frame is None:
            list_of_order_field_names = []
            for current_field in fields(ProductionOrder):
                list_of_order_field_names.append(current_field.name)

            self.order_data_frame: pandas.DataFrame = pandas.DataFrame(
                columns=list_of_order_field_names
            )
        else:
            self.order_data_frame: pandas.DataFrame = order_data_frame
        self.deadline_column_name: str = "production_deadline"
        self.production_target_column_name: str = "production_target"
        self.order_number_column_name: str = "order_number"

    def sort_orders_by_deadline(self, ascending: bool = True):
        """Sorts the orders in the data frame by their deadline.

        Args:
            ascending (bool, optional): Determines the order direction. Defaults to True.
        """
        self.order_data_frame.sort_values(
            self.deadline_column_name, inplace=True, ascending=ascending
        )
        self.order_data_frame.reset_index(inplace=True, drop=True)

    def append_order_collection(self, order_collection: "OrderCollection"):
        """Appends another Order collection to the current collection.

        Args:
            order_collection (OrderCollection): New collection that should
                be appended.
        """
        if self.commodity != order_collection.commodity:
            warnings.warn("Tried to append order collection with different commodity.")
        self.order_data_frame = pandas.concat(
            [self.order_data_frame, order_collection.order_data_frame]
        )
        new_sum = self.target_mass + order_collection.target_mass
        self.target_mass = new_sum


@dataclass(kw_only=True)
class ProcessStateEnergyLoadData(DataClassJsonMixin):
    """Combines the energy data that is required to create
    a LoadProfileEntry from a process State entry"""

    process_state_name: str
    process_step_name: str
    specific_energy_demand: float
    load_type: LoadType
    mass_unit: str = str(Units.mass_unit)
    energy_unit: str = str(Units.energy_unit)


@dataclass(kw_only=True)
class ProcessStateEnergyLoadDataBasedOnStreamMass(ProcessStateEnergyLoadData):
    """Appends the stream name that provides the mass that is the basis
    to create a lod profile from the process state.
    """

    stream_name: str


@dataclass
class ProductionOrderMetadata(DataClassJsonMixin):
    """Provides the orders of a sink and additional
    meta information about it.
    """

    data_frame: pandas.DataFrame
    list_of_aggregated_production_order: list[list[numbers.Number]]
    list_of_unique_deadlines: list[datetime.datetime]
    commodity: Commodity
    total_order_mass: numbers.Number
    earliest_deadline: datetime.datetime
    latest_deadline: datetime.datetime


@dataclass
class ProcessStateEnergyData:
    """Combines the ProcessStateEnergyLoadData for each
    LoadType of a process step.
    """

    process_step_name: str
    process_state_name: str
    dict_of_loads: dict[str, LoadType] = field(default_factory=dict)
    dict_of_load_energy_data: dict[str, ProcessStateEnergyLoadData] = field(
        default_factory=dict
    )

    def add_process_state_energy_load_data(
        self, process_state_energy_load_data: ProcessStateEnergyLoadData
    ):
        """Adds the ProcessStateEnergyLoadData for a specific LoadType.

        Args:
            process_state_energy_load_data (ProcessStateEnergyLoadData): Provides
                the information that is required to determine the energy demand
                of a process sate for a specific LoadType.
        """
        self.dict_of_loads[process_state_energy_load_data.load_type.uuid] = (
            process_state_energy_load_data.load_type
        )
        self.dict_of_load_energy_data[process_state_energy_load_data.load_type.uuid] = (
            process_state_energy_load_data
        )

    def get_dict_of_loads(self) -> dict[str, LoadType]:
        """Returns a dictionary that contains all LoadTypes
        that are consumed by a ProcessState-.
        Returns:
            dict[str, LoadType]: Dictionary that contains all LoadTypes
        that are consumed by a ProcessState.
        """
        return self.dict_of_loads


@dataclass
class EmptyLoadProfileMetadata:
    """Represents that no load profiles for a LoadType
    of an Object have been created during a simulation run.
    """

    name: str
    object_type: str


@dataclass
class ListOfLoadProfileEntryMetaData:
    """Provides a list of LoadProfileEntry and
    some summarized information about this list.
    """

    name: str
    object_type: str
    list_of_load_profiles: list[LoadProfileEntry]
    load_type: LoadType
    power_unit: str
    energy_unit: str


@dataclass
class LoadProfileMetaData(DataClassJsonMixin):
    """Provides a list of LoadProfileEntry, a data frame
    from this list and meta data about this list.
    """

    name: str
    object_type: str
    list_of_load_profiles: list[LoadProfileEntry]
    data_frame: pandas.DataFrame
    first_start_time: datetime.datetime
    last_end_time: datetime.datetime
    load_type: LoadType
    power_unit: str
    energy_unit: str
    maximum_energy: float
    maximum_power: float
    total_energy: float


@dataclass(kw_only=True)
class LoadProfileMetaDataResampled:
    """Contains the list of resampled load profile entries,
    a data frame from that list and additional meta information
    about it.
    """

    name: str
    object_type: str
    list_of_load_profiles: list[LoadProfileEntry]
    data_frame: pandas.DataFrame
    power_unit: str
    energy_unit: str
    total_energy: float
    maximum_power: float
    load_type: LoadType
    time_step: datetime.timedelta
    resample_frequency: str


@dataclass(kw_only=True)
class CarpetPlotMatrixEmpty:
    """Indicates that no Load Profile entries
    were available for the object with object_name.
    """

    object_name: str


@dataclass(kw_only=True)
class CarpetPlotMatrix(CarpetPlotMatrixEmpty):
    """A dataclass that contains all information that is necessary to create
    a load profile carpet plot.
    """

    data_frame: pandas.DataFrame
    start_date_time_series: datetime.datetime
    end_date_time_series: datetime.datetime
    x_axis_time_period_timedelta: datetime.timedelta
    power_unit: str
    energy_unit: str
    total_energy_demand: float
    load_type: LoadType
    resample_frequency: str = "1min"
