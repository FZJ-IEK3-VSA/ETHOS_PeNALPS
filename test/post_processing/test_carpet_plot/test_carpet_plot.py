import datetime
import itertools
import os
import pathlib
from dataclasses import dataclass

import pint
from ethos_penalps.data_classes import LoadProfileEntry, LoadType
from ethos_penalps.post_processing.carpet_plot_load_profile_generator import (
    CarpetPlotMatrix,
    CarpetPlotLoadProfileGenerator,
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


def create_hour_plot(
    x_axis_time_period_timedelta: datetime.timedelta,
    output_file_name: str,
    energy_data: EnergyData,
    power_data: PowerData,
    total_start_time: datetime.datetime,
    total_end_time: datetime.datetime,
    resample_frequency: str,
):
    load_profile_post_processor = CarpetPlotLoadProfileGenerator()
    list_of_load_profile_entries = []

    number_of_time_steps = (total_end_time - total_start_time) / energy_data.time_step
    current_start_time = total_end_time - energy_data.time_step
    current_end_time = total_end_time

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
    figure = (
        load_profile_post_processor.plot_load_profile_carpet_from_data_frame_matrix(
            carpet_plot_load_profile_matrix=load_profile_matrix,
        )
    )
    parent_directory = pathlib.Path(__file__).parent.absolute()
    path_to_figure = os.path.join(parent_directory, output_file_name)

    figure.savefig(fname=path_to_figure, bbox_inches="tight")


def test_create_1_hour_plots():
    total_start_time = datetime.datetime(year=2022, month=2, day=2)
    total_end_time = datetime.datetime(year=2022, month=2, day=5)
    list_of_energy_values = list(range(int(0), int(10)))
    load_type = LoadType("Electricity")
    energy_data = EnergyData(
        list_of_energy_values=list_of_energy_values,
        load_type=load_type,
        energy_unit="MJ",
        time_step=datetime.timedelta(hours=1),
    )
    power_data = energy_data.convert_to_power_data(target_power_unit="MW")
    energy_data.reset_cycle()
    power_data.reset_cycle()
    create_hour_plot(
        total_start_time=total_start_time,
        total_end_time=total_end_time,
        x_axis_time_period_timedelta=datetime.timedelta(hours=1),
        output_file_name="carpet_plot_figure_x_axis_1_hour_1min_resample.png",
        energy_data=energy_data,
        power_data=power_data,
        resample_frequency="1min",
    )
    energy_data.reset_cycle()
    power_data.reset_cycle()
    create_hour_plot(
        total_start_time=total_start_time,
        total_end_time=total_end_time,
        x_axis_time_period_timedelta=datetime.timedelta(hours=1),
        output_file_name="carpet_plot_figure_x_axis_1_hour_30s_resample.png",
        energy_data=energy_data,
        power_data=power_data,
        resample_frequency="30s",
    )
    energy_data.reset_cycle()
    power_data.reset_cycle()
    create_hour_plot(
        total_start_time=total_start_time,
        total_end_time=total_end_time,
        x_axis_time_period_timedelta=datetime.timedelta(hours=1),
        output_file_name="carpet_plot_figure_x_axis_1_hour_1s_resample.png",
        energy_data=energy_data,
        power_data=power_data,
        resample_frequency="1s",
    )


def test_create_1_day_plots():
    total_start_time = datetime.datetime(year=2022, month=1, day=1)
    total_end_time = datetime.datetime(year=2022, month=12, day=31)
    x_axis_time_period_timedelta = datetime.timedelta(days=1)
    list_of_energy_values = list(range(int(0), int(10)))
    load_type = LoadType("Electricity")
    energy_data = EnergyData(
        list_of_energy_values=list_of_energy_values,
        load_type=load_type,
        energy_unit="MJ",
        time_step=datetime.timedelta(hours=1),
    )
    power_data = energy_data.convert_to_power_data(target_power_unit="MW")
    energy_data.reset_cycle()
    power_data.reset_cycle()
    create_hour_plot(
        total_start_time=total_start_time,
        total_end_time=total_end_time,
        x_axis_time_period_timedelta=x_axis_time_period_timedelta,
        output_file_name="carpet_plot_figure_x_axis_1_day_1hour_resample.png",
        energy_data=energy_data,
        power_data=power_data,
        resample_frequency="1h",
    )
    energy_data.reset_cycle()
    power_data.reset_cycle()
    create_hour_plot(
        total_start_time=total_start_time,
        total_end_time=total_end_time,
        x_axis_time_period_timedelta=x_axis_time_period_timedelta,
        output_file_name="carpet_plot_figure_x_axis_1_day_5min_resample.png",
        energy_data=energy_data,
        power_data=power_data,
        resample_frequency="5min",
    )
    energy_data.reset_cycle()
    power_data.reset_cycle()
    create_hour_plot(
        total_start_time=total_start_time,
        total_end_time=total_end_time,
        x_axis_time_period_timedelta=x_axis_time_period_timedelta,
        output_file_name="carpet_plot_figure_x_axis_1_day_1min_resample.png",
        energy_data=energy_data,
        power_data=power_data,
        resample_frequency="1min",
    )


def test_create_1_week_plots():
    total_start_time = datetime.datetime(year=2022, month=1, day=1)
    total_end_time = datetime.datetime(year=2022, month=12, day=31)
    x_axis_time_period_timedelta = datetime.timedelta(weeks=1)
    list_of_energy_values = list(range(int(0), int(10)))
    load_type = LoadType("Electricity")
    energy_data = EnergyData(
        list_of_energy_values=list_of_energy_values,
        load_type=load_type,
        energy_unit="MJ",
        time_step=datetime.timedelta(hours=1),
    )
    power_data = energy_data.convert_to_power_data(target_power_unit="MW")
    energy_data.reset_cycle()
    power_data.reset_cycle()
    create_hour_plot(
        total_start_time=total_start_time,
        total_end_time=total_end_time,
        x_axis_time_period_timedelta=x_axis_time_period_timedelta,
        output_file_name="carpet_plot_figure_x_axis_1_week_1hour_resample.png",
        energy_data=energy_data,
        power_data=power_data,
        resample_frequency="1h",
    )
    energy_data.reset_cycle()
    power_data.reset_cycle()
    create_hour_plot(
        total_start_time=total_start_time,
        total_end_time=total_end_time,
        x_axis_time_period_timedelta=x_axis_time_period_timedelta,
        output_file_name="carpet_plot_figure_x_axis_1_week_30min_resample.png",
        energy_data=energy_data,
        power_data=power_data,
        resample_frequency="30 min",
    )
    energy_data.reset_cycle()
    power_data.reset_cycle()
    create_hour_plot(
        total_start_time=total_start_time,
        total_end_time=total_end_time,
        x_axis_time_period_timedelta=x_axis_time_period_timedelta,
        output_file_name="carpet_plot_figure_x_axis_1_week_5min_resample.png",
        energy_data=energy_data,
        power_data=power_data,
        resample_frequency="5min",
    )
