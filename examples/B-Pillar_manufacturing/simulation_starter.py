import datetime
import logging

from cutting_and_heating_chain import fill_cutting_and_heating_chain
from forming_quenching_and_trimming_chain import (
    fill_forming_quenching_and_trimming_chain,
)

from ethos_penalps.data_classes import Commodity
from ethos_penalps.enterprise import Enterprise
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

# Create logger to receiver information about the simulation progress
logger = PeNALPSLogger.get_human_readable_logger(logging.INFO)

# Set simulation time data
time_data = TimeData(
    global_end_date=datetime.datetime(year=2023, month=1, day=1),
    global_start_date=datetime.datetime(year=2022, month=1, day=1),
)
# Initialize enterprise
enterprise = Enterprise(location="Example Location", time_data=time_data)

# Create network level
forming_and_trimming_level = enterprise.create_network_level()
cutting_and_heating_level = enterprise.create_network_level()

# Determine all relevant commodities
steel_strip = Commodity(name="Steel Strip")
cold_blank = Commodity(name="Cold Blank")
hot_blank = Commodity(name="Hot Blank")
formed_and_quenched_part = Commodity(name="Formed and quenched part")
trimmed_part = Commodity(name="Trimmed part")

# Create all order for the simulation
order_generator = NOrderGenerator(
    commodity=trimmed_part,
    mass_per_order=0.006,
    production_deadline=time_data.global_end_date,
    number_of_orders=43,
)
trimmed_part_collection = order_generator.create_n_order_collection()

# Create all sources, sinks and network level storages
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

# Create first process chain
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

# Create second process chain
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

# Start the Simulation
enterprise.start_simulation()

# Create report of the simulation results
enterprise.create_post_simulation_report(
    gantt_chart_end_date=time_data.global_end_date,
    gantt_chart_start_date=time_data.global_end_date - datetime.timedelta(minutes=30),
    x_axis_time_delta=datetime.timedelta(hours=1),
    start_date=time_data.global_end_date - datetime.timedelta(days=365),
    end_date=time_data.global_end_date,
    resample_frequency="1s",
)
