import datetime
import numbers
import warnings
import uuid
from dataclasses import dataclass, field, fields
from typing import Optional

import pandas
import pint
from dataclasses_json import DataClassJsonMixin, config, dataclass_json

from ethos_penalps.utilities.general_functions import get_new_uuid
from ethos_penalps.utilities.units import Units
from ethos_penalps.utilities.exceptions_and_warnings import UnexpectedBehaviorWarning


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
    name: str
    uuid: str = field(default_factory=get_new_uuid)


@dataclass(frozen=True, eq=True)
class ProcessStateData(DataClassJsonMixin):
    process_state_name: str
    start_time: datetime.datetime
    end_time: datetime.datetime


@dataclass
class EmptyMetaDataInformation:
    name: str
    object_type: str


@dataclass()
class ProductEnergyData(DataClassJsonMixin):
    product_commodity: Commodity
    specific_energy_demand: float
    load_type: LoadType
    mass_unit: str = str(Units.energy_unit)
    energy_unit: str = str(Units.energy_unit)


@dataclass(frozen=True, eq=True, unsafe_hash=True)
class StreamLoadEnergyData(DataClassJsonMixin):
    stream_name: str
    specific_energy_demand: float
    load_type: LoadType
    mass_unit: str = str(Units.mass_unit)
    energy_unit: str = str(Units.energy_unit)


@dataclass(slots=True, frozen=True)
class LoadProfileEntry(DataClassJsonMixin):
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
    loop_number: float | str = "Loop has not started"


@dataclass(kw_only=True, frozen=True, slots=True)
class ProcessStepProductionPlanEntry(DataClassJsonMixin):
    process_step_name: str
    process_state_name: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    duration: str
    process_state_type: str


@dataclass(frozen=True, slots=True)
class StorageProductionPlanEntry(DataClassJsonMixin):
    process_step_name: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    duration: str
    storage_level_at_start: float
    storage_level_at_end: float
    commodity: Commodity


@dataclass(frozen=True, eq=True, slots=True)
class StateConnector:
    start_state_name: str
    end_state_name: str


@dataclass
class ProcessStepDataFrameMetaInformation:
    data_frame: pandas.DataFrame
    process_step_name: str
    list_of_process_state_names: list[str]
    first_start_time: datetime.datetime
    last_end_time: datetime.datetime


@dataclass
class StorageDataFrameMetaInformation:
    data_frame: pandas.DataFrame
    process_step_name: str
    commodity: Commodity
    first_start_time: datetime.datetime
    last_end_time: datetime.datetime
    mass_unit: str


@dataclass
class CurrentProcessNode:
    node_name: str = "Node not set yet"


@dataclass(frozen=True, eq=True, slots=True)
class OutputBranchIdentifier:
    branch_number: float
    global_unique_identifier: Optional[str] = field(default_factory=get_new_uuid)


@dataclass(frozen=True, eq=True, slots=True)
class TemporalBranchIdentifier:
    branch_number: float
    global_unique_identifier: Optional[str] = field(default_factory=get_new_uuid)


@dataclass(frozen=True, eq=True, slots=True)
class StreamBranchIdentifier:
    stream_name: str
    global_unique_identifier: Optional[str] = field(default_factory=get_new_uuid)


@dataclass(frozen=True, eq=True, slots=True)
class OutputInputBranchConnector:
    input_branch_identifier: TemporalBranchIdentifier
    output_branch_identifier: OutputBranchIdentifier


@dataclass(frozen=True, eq=True, slots=True)
class StaticTimePeriod:
    start_time: datetime.datetime
    end_time: datetime.datetime
    uuid: OutputBranchIdentifier

    def get_duration(self) -> datetime.timedelta:
        return self.end_time - self.start_time


@dataclass(frozen=True, slots=True, eq=True)
class ProcessChainIdentifier:
    chain_number: int
    chain_name: str
    unique_identifier: str = get_new_uuid()


@dataclass
class ProductionOrder:
    production_target: float
    production_deadline: datetime.datetime
    order_number: float
    commodity: Commodity
    global_unique_identifier: str = field(default_factory=get_new_uuid)
    produced_mass: float = 0


class OrderCollection:
    def __init__(
        self,
        target_mass: float,
        commodity: Commodity,
        order_data_frame: pandas.DataFrame | None = None,
    ) -> None:
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
        self.order_data_frame.sort_values(
            self.deadline_column_name, inplace=True, ascending=ascending
        )
        self.order_data_frame.reset_index(inplace=True, drop=True)

    def append_order_collection(self, order_collection: "OrderCollection"):
        if self.commodity != order_collection.commodity:
            warnings.warn("Tried to append order collection with different commodity.")
        self.order_data_frame = pandas.concat(
            [self.order_data_frame, order_collection.order_data_frame]
        )
        new_sum = self.target_mass + order_collection.target_mass
        self.target_mass = new_sum


@dataclass(kw_only=True)
class ProcessStateEnergyLoadData(DataClassJsonMixin):
    process_state_name: str
    process_step_name: str
    specific_energy_demand: float
    load_type: LoadType
    mass_unit: str = str(Units.mass_unit)
    energy_unit: str = str(Units.energy_unit)


@dataclass(kw_only=True)
class ProcessStateEnergyLoadDataBasedOnStreamMass(ProcessStateEnergyLoadData):
    stream_name: str


@dataclass
class ProductionOrderMetadata(DataClassJsonMixin):
    data_frame: pandas.DataFrame
    list_of_aggregated_production_order: list[list[numbers.Number]]
    list_of_unique_deadlines: list[datetime.datetime]
    commodity: Commodity
    total_order_mass: numbers.Number
    earliest_deadline: datetime.datetime
    latest_deadline: datetime.datetime


@dataclass
class ProcessStateEnergyData:
    process_step_name: str
    process_state_name: str
    dict_of_loads: dict[str, LoadType] = field(default_factory=dict)
    dict_of_load_energy_data: dict[str, ProcessStateEnergyLoadData] = field(
        default_factory=dict
    )

    def add_process_state_energy_load_data(
        self, process_state_energy_load_data: ProcessStateEnergyLoadData
    ):
        self.dict_of_loads[process_state_energy_load_data.load_type.uuid] = (
            process_state_energy_load_data.load_type
        )
        self.dict_of_load_energy_data[process_state_energy_load_data.load_type.uuid] = (
            process_state_energy_load_data
        )

    def get_dict_of_loads(self) -> dict[str, LoadType]:
        return self.dict_of_loads


@dataclass
class EmptyLoadProfileMetadata:
    name: str
    object_type: str


@dataclass
class LoadProfileMetaData(DataClassJsonMixin):
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
