import cProfile
import datetime

import cloudpickle
from typeguard import install_import_hook


install_import_hook("ethos_penalps")
from cutting_and_heating_chain import fill_cutting_and_heating_chain
from forming_quenching_and_triming_chain import (
    fill_forming_quenching_and_trimming_chain,
)


from ethos_penalps.data_classes import Commodity
from ethos_penalps.enterprise import Enterprise, NetworkLevel
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.capacity_calculator import CapacityCalculator, CapacityAdjuster

# from process_chain_2_1 import fill_process_chain_2_1

simulation_start_time = datetime.datetime.now()
# logger = ELPSILogger.get_human_readable_logger()
# logger = ELPSILogger.get_logger_to_create_table()


time_data = TimeData(
    global_end_date=datetime.datetime(year=2023, month=1, day=1),
    global_start_date=datetime.datetime(year=2022, month=1, day=1),
)

enterprise = Enterprise(location="", time_data=time_data)


forming_and_trimming_level = enterprise.create_network_level()
cutting_and_heating_level = enterprise.create_network_level()


steel_strip = Commodity(name="Steel Strip")
cold_blank = Commodity(name="Cold Blank")
hot_blank = Commodity(name="Hot Blank")
formed_and_quenched_part = Commodity(name="Formed and quenched part")
trimmed_part = Commodity(name="Trimmed part")
order_generator = NOrderGenerator(
    commodity=trimmed_part,
    mass_per_order=300,
    production_deadline=time_data.global_end_date,
    number_of_orders=5,
    # number_of_orders=1923,
    # number_of_orders=3,
)
trimmed_part_collection = order_generator.create_n_order_collection()
# End Points for Hot Rolling
trimmed_part_sink = forming_and_trimming_level.create_main_sink(
    name="Trimmed Part Sink",
    commodity=trimmed_part,
    order_collection=trimmed_part_collection,
)

hot_part_storage = forming_and_trimming_level.create_process_chain_storage_as_source(
    name="Hot Part Sink",
    commodity=trimmed_part,
)

cutting_and_heating_level.add_process_chain_storage_as_sink(
    process_chain_storage=hot_part_storage
)

steel_strip_source = cutting_and_heating_level.create_main_source(
    name="Steel Strip Source",
    commodity=steel_strip,
)


forming_and_trimming_chain = forming_and_trimming_level.create_process_chain(
    process_chain_name="Forming and Trimming Chain"
)
fill_forming_quenching_and_trimming_chain(
    process_chain=forming_and_trimming_chain,
    sink=trimmed_part_sink,
    source=hot_part_storage,
    steel_strip=steel_strip,
    cold_blank=cold_blank,
    hot_blank=hot_blank,
    formed_and_quenched_part=formed_and_quenched_part,
    trimmed_part=trimmed_part,
)

# Add Chain to Hot Rolling
cutting_and_heating_chain = cutting_and_heating_level.create_process_chain(
    process_chain_name="Cutting and Heating Chain",
)

cutting_and_heating_chain = fill_cutting_and_heating_chain(
    process_chain=cutting_and_heating_chain,
    sink=hot_part_storage,
    source=steel_strip_source,
    steel_strip=steel_strip,
    cold_blank=cold_blank,
    hot_blank=hot_blank,
    formed_and_quenched_part=formed_and_quenched_part,
    trimmed_part=trimmed_part,
)


# hot_rolling = hot_rolling_chain_1.process_node_dict["Hot Mill"]
# capacity_calculator = CapacityCalculator(process_step=hot_rolling)
# hot_rolling_capacity = capacity_calculator.determine_capacity_of_process_step()

# continuous_casting = continuous_casting_chain_1.process_node_dict["Continuous Caster 1"]

# capacity_adjuster = CapacityAdjuster(process_step=continuous_casting)
# capacity_adjuster.adjust_process_step_capacity(target_rate=65.85365853658537 / 2)


# eaf = electric_arc_furnace_process_chain_1.process_node_dict["EAF 1"]
# capacity_calculator = CapacityCalculator(process_step=eaf)
# capacity_calculator.determine_capacity_of_process_step()
# json_dump = trimmed_part_sink.stream_handler.json_dump_streams()

enterprise.start_simulation()
simulation_end_time = datetime.datetime.now()

enterprise.create_post_simulation_report(
    gantt_chart_end_date=time_data.global_end_date,
    gantt_chart_start_date=time_data.global_end_date - datetime.timedelta(hours=36),
    x_axis_time_delta=datetime.timedelta(hours=24),
    # start_date=time_data.global_start_date,
    start_date=time_data.global_end_date - datetime.timedelta(days=365),
    end_date=time_data.global_end_date,
)

simulation_end_time_with_post_processing = datetime.datetime.now()
simulation_duration_without_postprocessing = simulation_end_time - simulation_start_time
simulation_duration_with_postprocessing = (
    simulation_end_time_with_post_processing - simulation_start_time
)

print("Duration without postprocessing", simulation_duration_without_postprocessing)
print("Duration with postprocessing", simulation_duration_with_postprocessing)

print("Done")
