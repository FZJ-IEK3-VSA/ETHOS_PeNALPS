import datetime
import itertools
from collections.abc import Iterable
from dataclasses import dataclass

from ethos_penalps.data_classes import LoadProfileEntry, LoadType
from ethos_penalps.utilities.units import Units


class BaseLoadProfileGeneratorClass:
    def create_load_profile_entry_list(
        self,
        total_start_time: datetime.datetime,
        total_end_time: datetime.datetime,
        time_step: datetime.timedelta,
    ) -> list[LoadProfileEntry]:
        list_of_energy_values = list(range(int(0), int(10)))
        load_type = LoadType("Electricity")
        energy_unit = "MJ"
        power_unit = "MW"
        energy_cycle = itertools.cycle(list_of_energy_values)

        power_values = [
            Units.convert_energy_to_power(
                energy_value=e,
                energy_unit=energy_unit,
                time_step=time_step,
                target_power_unit=power_unit,
            )
            for e in list_of_energy_values
        ]
        power_cycle = itertools.cycle(power_values)

        number_of_time_steps = (total_end_time - total_start_time) / time_step
        current_start_time = total_end_time - time_step
        current_end_time = total_end_time
        list_of_load_profile_entries = []

        for _ in range(int(number_of_time_steps)):
            load_profile_entry = LoadProfileEntry(
                load_type=load_type,
                start_time=current_start_time,
                end_time=current_end_time,
                energy_unit=energy_unit,
                energy_quantity=next(energy_cycle),
                average_power_consumption=next(power_cycle),
                power_unit=power_unit,
            )
            list_of_load_profile_entries.append(load_profile_entry)
            current_start_time = current_start_time - time_step
            current_end_time = current_end_time - time_step

        return list_of_load_profile_entries
