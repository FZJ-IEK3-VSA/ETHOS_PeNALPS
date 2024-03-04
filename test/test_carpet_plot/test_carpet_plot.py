import datetime
import itertools
import os
import pathlib

from ethos_penalps.data_classes import LoadProfileEntry, LoadType
from ethos_penalps.post_processing.load_profile_post_processor import (
    CarpetPlotMatrix,
    LoadProfilePostProcessor,
)

load_profile_post_processor = LoadProfilePostProcessor()
list_of_load_profile_entries = []
total_start_time = datetime.datetime(year=2022, month=1, day=1)
total_end_time = datetime.datetime(year=2022, month=7, day=3)
energy_unit: str = "MJ"
discrete_time_step = datetime.timedelta(minutes=5)
number_of_time_steps = (total_end_time - total_start_time) / discrete_time_step
iter_n = 0
current_start_time = total_end_time - discrete_time_step
current_end_time = total_end_time
load_type = LoadType("Electricity")
energy_quantity = 5
average_power_consumption = 10
power_unit = "MW"

energy_quantity_iterator = itertools.cycle(range(int(0), int(10)))
power_quantity_iterator = itertools.cycle(range(int(0), int(10)))
for time_step in range(int(number_of_time_steps)):
    current_energy_quantity = next(energy_quantity_iterator)
    current_energy_power = next(power_quantity_iterator)
    load_profile_entry = LoadProfileEntry(
        load_type=load_type,
        start_time=current_start_time,
        end_time=current_end_time,
        energy_unit=energy_unit,
        energy_quantity=current_energy_quantity,
        average_power_consumption=current_energy_power,
        power_unit=power_unit,
    )
    list_of_load_profile_entries.append(load_profile_entry)
    current_start_time = current_start_time - discrete_time_step
    current_end_time = current_end_time - discrete_time_step


load_profile_matrix = (
    load_profile_post_processor.convert_lpg_load_profile_to_data_frame_matrix(
        list_of_load_profile_entries=list_of_load_profile_entries,
        start_date_time_series=total_start_time,
        end_date_time_series=total_end_time,
        x_axis_time_period_timedelta=datetime.timedelta(days=1),
        resample_frequency="5min",
    )
)
figure = load_profile_post_processor.plot_load_profile_carpet_from_data_frame_matrix(
    carpet_plot_load_profile_matrix=load_profile_matrix, load_type_name=load_type.name
)
parent_directory = pathlib.Path(__file__).parent.absolute()
path_to_figure = os.path.join(parent_directory, "carpet_plot_figure.png")

figure.savefig(fname=path_to_figure, bbox_inches="tight")
# load_profile_post_processor.convert_lpg_load_profile_to_data_frame_matrix()
