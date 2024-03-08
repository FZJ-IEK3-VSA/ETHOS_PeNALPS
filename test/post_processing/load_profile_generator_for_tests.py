import datetime
import itertools
import os
import pathlib
from collections.abc import Iterable
from dataclasses import dataclass

import pint
import pytest
from ethos_penalps.data_classes import LoadProfileEntry, LoadType
from ethos_penalps.post_processing.tikz_visualizations.carpet_plot_load_profile_generator import (
    CarpetPlotLoadProfileGenerator,
    CarpetPlotMatrix,
)
from ethos_penalps.utilities.general_functions import (
    ResultPathGenerator,
    convert_date_time_to_string,
)
from ethos_penalps.utilities.units import Units


@dataclass
class EnergyData:
    list_of_energy_values: Iterable[float]
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


class BaseLoadProfileGeneratorClass:

    def create_energy_data(self, time_step: datetime.timedelta) -> EnergyData:
        list_of_energy_values = list(range(int(0), int(10)))
        load_type = LoadType("Electricity")
        energy_data = EnergyData(
            list_of_energy_values=list_of_energy_values,
            load_type=load_type,
            energy_unit="MJ",
            time_step=time_step,
        )
        return energy_data

    def create_load_profile_entry_list(
        self,
        total_start_time: datetime.datetime,
        total_end_time: datetime.datetime,
        time_step: datetime.timedelta,
    ) -> list[LoadProfileEntry]:
        energy_data = self.create_energy_data(time_step=time_step)
        power_data = energy_data.convert_to_power_data(target_power_unit="MW")

        number_of_time_steps = (total_end_time - total_start_time) / time_step
        current_start_time = total_end_time - time_step
        current_end_time = total_end_time
        list_of_load_profile_entries = []

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
