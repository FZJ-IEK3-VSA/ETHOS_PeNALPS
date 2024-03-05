import datetime
import itertools
import os
import pathlib
from dataclasses import dataclass

import pint
from ethos_penalps.data_classes import (
    ListLoadProfileMetaDataEmpty,
    ListOfLoadProfileMetaData,
    CarpetPlotMatrix,
    LoadProfileEntry,
    LoadType,
)
from ethos_penalps.post_processing.load_profile_entry_post_processor import (
    ListOfLoadProfileEntryAnalyzer,
    LoadProfileEntryPostProcessor,
)
from ethos_penalps.post_processing.load_profile_post_processor import (
    CarpetPlotMatrix,
    LoadProfileEntryPostProcessor,
    LoadProfilePostProcessor,
)
from ethos_penalps.utilities.units import Units


@dataclass
class EnergyData:
    list_of_energy_values: list[float]
    energy_unit: str
    time_step: datetime.timedelta
    load_type: LoadType

    def __post_init__(self):
        self.energy_value_cycle_operator: itertools.cycle = itertools.cycle(
            self.list_of_energy_values
        )

    def reset_cycle(self):
        self.energy_value_cycle_operator: itertools.cycle = itertools.cycle(
            self.list_of_energy_values
        )

    def convert_to_power_data(self, target_power_unit: str) -> "PowerData":
        list_of_power_values = []
        for energy_value in self.list_of_energy_values:
            power_value = Units.convert_energy_to_power(
                energy_value=energy_value,
                energy_unit=self.energy_unit,
                time_step=self.time_step,
                target_power_unit=target_power_unit,
            )
            list_of_power_values.append(power_value)
        power_data = PowerData(
            list_of_power_values=list_of_power_values,
            power_unit=target_power_unit,
            time_step=self.time_step,
            load_type=self.load_type,
        )
        return power_data


@dataclass
class PowerData:
    list_of_power_values: list[float]
    power_unit: str
    time_step: datetime.timedelta
    load_type: LoadType

    def __post_init__(self):
        self.power_value_cycle_operator: itertools.cycle = itertools.cycle(
            self.list_of_power_values
        )

    def reset_cycle(self):
        self.power_value_cycle_operator: itertools.cycle = itertools.cycle(
            self.list_of_power_values
        )

    def convert_to_energy_data(self, target_energy_unit: str) -> "EnergyData":
        list_of_energy_values = []
        for power_value in self.list_of_power_values:
            energy_value = Units.convert_power_to_energy(
                power_value=power_value,
                power_unit=self.power_unit,
                time_step=self.time_step,
                target_energy_unit=target_energy_unit,
            )
            list_of_energy_values.append(energy_value)
        energy_data = EnergyData(
            list_of_energy_values=list_of_energy_values,
            energy_unit=target_energy_unit,
            time_step=self.time_step,
            load_type=self.load_type,
        )
        return energy_data


def create_sample_list_of_load_profile_entry_data(
    energy_data: EnergyData,
    power_data: PowerData,
    total_start_time: datetime.datetime,
    total_end_time: datetime.datetime,
):
    current_start_time = total_end_time - energy_data.time_step
    current_end_time = total_end_time
    list_of_load_profile_entries = []
    number_of_time_steps = (total_end_time - total_start_time) / energy_data.time_step
    for time_step in range(int(number_of_time_steps)):
        current_energy_quantity = next(energy_data.energy_value_cycle_operator)
        current_energy_power = next(power_data.power_value_cycle_operator)
        load_profile_entry = LoadProfileEntry(
            load_type=energy_data.load_type,
            start_time=current_start_time,
            end_time=current_end_time,
            energy_unit=energy_data.energy_unit,
            energy_quantity=current_energy_quantity,
            average_power_consumption=current_energy_power,
            power_unit=power_data.power_unit,
        )
        list_of_load_profile_entries.append(load_profile_entry)
        current_start_time = current_start_time - energy_data.time_step
        current_end_time = current_end_time - energy_data.time_step

    return list_of_load_profile_entries


def test_resampling(
    x_axis_time_period_timedelta: datetime.timedelta,
    energy_data: EnergyData,
    power_data: PowerData,
    total_start_time: datetime.datetime,
    total_end_time: datetime.datetime,
    resample_frequency: str,
):

    list_of_load_profile_entries = create_sample_list_of_load_profile_entry_data(
        energy_data=energy_data,
        power_data=power_data,
        total_start_time=total_start_time,
        total_end_time=total_end_time,
    )
    load_profile_post_processor = LoadProfilePostProcessor()

    load_profile_entry_process_process = ListOfLoadProfileEntryAnalyzer()
    load_profile_entry_process_process.check_if_power_and_energy_match()
    list_of_load_profile_meta_data = (
        load_profile_entry_process_process.create_list_of_load_profile_meta_data(
            list_of_load_profiles=list_of_load_profile_entries, object_name="Test Name"
        )
    )
    load_profile_matrix = (
        load_profile_post_processor.convert_lpg_load_profile_to_data_frame_matrix(
            list_of_load_profile_entries=list_of_load_profile_entries,
            start_date_time_series=total_start_time,
            end_date_time_series=total_end_time,
            x_axis_time_period_timedelta=x_axis_time_period_timedelta,
            resample_frequency=resample_frequency,
            object_name="Test row",
        )
    )
    assert type(load_profile_matrix) is CarpetPlotMatrix
    assert type(list_of_load_profile_meta_data) is ListOfLoadProfileMetaData
    assert (
        list_of_load_profile_meta_data.total_energy
        == load_profile_matrix.total_energy_demand
    )
    return load_profile_matrix.total_energy_demand


if __name__ == "__main__":
    total_start_time = datetime.datetime(year=2022, month=2, day=2)
    total_end_time = datetime.datetime(year=2022, month=2, day=5)
    x_axis_time_period_timedelta = datetime.timedelta(hours=1)
    list_of_energy_values = list(range(int(0), int(10)))
    load_type = LoadType("Electricity")
    energy_data = EnergyData(
        list_of_energy_values=list_of_energy_values,
        load_type=load_type,
        energy_unit="MJ",
        time_step=datetime.timedelta(hours=1),
    )
    power_data = energy_data.convert_to_power_data(target_power_unit="MW")

    list_of_load_profile_entries_1 = create_sample_list_of_load_profile_entry_data(
        energy_data=energy_data,
        power_data=power_data,
        total_start_time=total_start_time,
        total_end_time=total_end_time,
    )
    energy_data.reset_cycle()
    power_data.reset_cycle()
    list_of_load_profile_entries_2 = create_sample_list_of_load_profile_entry_data(
        energy_data=energy_data,
        power_data=power_data,
        total_start_time=total_start_time,
        total_end_time=total_end_time,
    )
    assert list_of_load_profile_entries_1 == list_of_load_profile_entries_2
    energy_data.reset_cycle()
    power_data.reset_cycle()
    total_energy_demand_1 = test_resampling(
        x_axis_time_period_timedelta=x_axis_time_period_timedelta,
        energy_data=energy_data,
        power_data=power_data,
        total_start_time=total_start_time,
        total_end_time=total_end_time,
        resample_frequency="1min",
    )
    energy_data.reset_cycle()
    power_data.reset_cycle()
    total_energy_demand_2 = test_resampling(
        x_axis_time_period_timedelta=x_axis_time_period_timedelta,
        energy_data=energy_data,
        power_data=power_data,
        total_start_time=total_start_time,
        total_end_time=total_end_time,
        resample_frequency="1min",
    )
    assert total_energy_demand_1 == total_energy_demand_2
