import datetime
import logging

from ethos_penalps.data_classes import Commodity, LoadType
from ethos_penalps.enterprise import Enterprise
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.stream import BatchStreamStaticData, ContinuousStreamStaticData
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from blending_process_chain import (
    fill_blending_process_chain,
)
from cooking_process_chain import (
    fill_cooking_process_chain,
)

logger = PeNALPSLogger.get_human_readable_logger(logging.INFO)

# Determine all relevant commodities
raw_commodity = Commodity(name="Raw Goods")
uncooked_commodity = Commodity(name="Uncooked Goods")
cooked_commodity = Commodity(name="Cooked Goods")
# Enterprise structure

# Set simulation time data
start_date = datetime.datetime(2022, 1, 2, hour=22, minute=30)
end_date = datetime.datetime(2022, 1, 3)
time_data = TimeData(
    global_start_date=start_date,
    global_end_date=end_date,
)

# Create all order for the simulation
order_generator = NOrderGenerator(
    commodity=cooked_commodity,
    mass_per_order=0.00065,
    production_deadline=end_date,
    number_of_orders=4,
)

order_collection = order_generator.create_n_order_collection()

# Initialize enterprise
enterprise = Enterprise(time_data=time_data, name="Cooking Example")

cooking_network_level = enterprise.create_network_level()
blending_network_level = enterprise.create_network_level()


blending_chain_1 = blending_network_level.create_process_chain("Blending Chain 1")
blending_chain_2 = blending_network_level.create_process_chain("Blending Chain 2")

cooking_chain_1 = cooking_network_level.create_process_chain("Cooking Chain 1")
cooking_chain_2 = cooking_network_level.create_process_chain("Cooking Chain 2")

cooked_goods_sink = cooking_network_level.create_main_sink(
    name="Cooked Goods Sink",
    commodity=cooked_commodity,
    order_collection=order_collection,
)

uncooked_goods_storage = cooking_network_level.create_process_chain_storage_as_source(
    name="Uncooked Goods", commodity=uncooked_commodity
)
raw_goods_source = blending_network_level.create_main_source(
    "Raw Goods", commodity=raw_commodity
)
blending_network_level.add_process_chain_storage_as_sink(
    process_chain_storage=uncooked_goods_storage
)


blending_chain_1.add_sink(sink=uncooked_goods_storage)
blending_chain_2.add_sink(sink=uncooked_goods_storage)
blending_chain_1.add_source(source=raw_goods_source)
blending_chain_2.add_source(source=raw_goods_source)
cooking_chain_1.add_sink(sink=cooked_goods_sink)
cooking_chain_1.add_source(source=uncooked_goods_storage)
cooking_chain_2.add_sink(sink=cooked_goods_sink)
cooking_chain_2.add_source(source=uncooked_goods_storage)


fill_cooking_process_chain(
    process_chain=cooking_chain_1,
    uncooked_commodity=uncooked_commodity,
    cooked_commodity=cooked_commodity,
    cooked_goods_sink=cooked_goods_sink,
    uncooked_goods_storage=uncooked_goods_storage,
    process_step_name="Cooker 1",
)
fill_cooking_process_chain(
    process_chain=cooking_chain_2,
    uncooked_commodity=uncooked_commodity,
    cooked_commodity=cooked_commodity,
    cooked_goods_sink=cooked_goods_sink,
    uncooked_goods_storage=uncooked_goods_storage,
    process_step_name="Cooker 2",
)

fill_blending_process_chain(
    process_chain=blending_chain_1,
    raw_commodity=raw_commodity,
    cooked_commodity=cooked_commodity,
    raw_goods_source=raw_goods_source,
    uncooked_storage=uncooked_goods_storage,
    process_step_name="Blender 1",
)
fill_blending_process_chain(
    process_chain=blending_chain_2,
    raw_commodity=raw_commodity,
    cooked_commodity=cooked_commodity,
    raw_goods_source=raw_goods_source,
    uncooked_storage=uncooked_goods_storage,
    process_step_name="Blender 2",
)


# Start the simulation
enterprise.start_simulation(number_of_iterations_in_chain=200)

# Create report of the simulation results
enterprise.create_post_simulation_report(
    start_date=start_date,
    end_date=end_date,
    x_axis_time_delta=datetime.timedelta(hours=1),
    resample_frequency="5min",
    gantt_chart_end_date=end_date,
    gantt_chart_start_date=start_date,
)
