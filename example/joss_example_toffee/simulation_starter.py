import datetime
import cProfile
import cloudpickle
from typeguard import install_import_hook

install_import_hook("ethos_penalps")


from ethos_penalps.data_classes import LoadType
from ethos_penalps.enterprise import Enterprise, NetworkLevel
from ethos_penalps.time_data import TimeData
from ethos_penalps.data_classes import Commodity
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.general_functions import ResultPathGenerator

from toffee_preparation_chain_1 import fill_toffee_preparation_chain_1
from toffee_preparation_chain_2 import fill_toffee_preparation_chain_2
from cutting_and_packaging_chain import fill_cutting_and_packaging_chain

# from process_chain_2_1 import fill_process_chain_2_1

simulation_start_time = datetime.datetime.now()
import logging

logger = PeNALPSLogger.get_human_readable_logger()
logger = PeNALPSLogger.get_logger_to_create_table()
logger.setLevel(logging.DEBUG)

time_data = TimeData(
    global_end_date=datetime.datetime(year=2023, month=1, day=1),
    global_start_date=datetime.datetime(year=2022, month=1, day=1),
)

enterprise = Enterprise(location="", time_data=time_data)


toffee_packaging_level = enterprise.create_network_level()
toffee_production_level = enterprise.create_network_level()
electricity_load = LoadType("Electricity")
natural_gas_load = LoadType("Natural Gas")

toffee_input_commodity = Commodity(name="Raw Toffee Ingredients")
cooled_toffee = Commodity(name="Cooled Toffee")
cut_toffee_commodity = Commodity(name="Cut Toffee")
packaged_toffee_commodity = Commodity(name="Packaged Toffee")
order_generator = NOrderGenerator(
    commodity=packaged_toffee_commodity,
    mass_per_order=0.5,
    production_deadline=time_data.global_end_date,
    number_of_orders=4,
    # number_of_orders=1923,
    # number_of_orders=3,
)
product_order_collection = order_generator.create_n_order_collection()
# End Points for Hot Rolling

packaged_toffee_sink = toffee_packaging_level.create_main_sink(
    order_collection=product_order_collection,
    name="Packaged Toffee Sink",
    commodity=packaged_toffee_commodity,
)
cooled_toffee_storage = toffee_packaging_level.create_process_chain_storage_as_source(
    commodity=cooled_toffee,
    name="Cooled Toffee Storage",
)

toffee_production_level.add_process_chain_storage_as_sink(
    process_chain_storage=cooled_toffee_storage
)
toffee_raw_material_source = toffee_production_level.create_main_source(
    name="Toffee Raw Materials", commodity=toffee_input_commodity
)


toffee_packaging_chain = toffee_packaging_level.create_process_chain(
    process_chain_name="Cutting and Packaging"
)
toffee_packaging_chain = fill_cutting_and_packaging_chain(
    process_chain=toffee_packaging_chain,
    sink=packaged_toffee_sink,
    source=cooled_toffee_storage,
    cooled_toffee=cooled_toffee,
    cut_toffee_commodity=cut_toffee_commodity,
    packaged_toffee_commodity=packaged_toffee_commodity,
    electricity_load=electricity_load,
)

# Add Chain to Toffee Production
toffee_production_chain_2 = toffee_production_level.create_process_chain(
    process_chain_name="Toffee Production Chain 2",
)
toffee_production_chain_1 = toffee_production_level.create_process_chain(
    process_chain_name="Toffee Production Chain 1",
)

toffee_production_chain_1 = fill_toffee_preparation_chain_1(
    process_chain=toffee_production_chain_1,
    cooled_toffee_sink=cooled_toffee_storage,
    raw_toffee_source=toffee_raw_material_source,
    electricity_load=electricity_load,
    natural_gas_load=natural_gas_load,
)
toffee_production_chain_2 = fill_toffee_preparation_chain_2(
    process_chain=toffee_production_chain_2,
    cooled_toffee_sink=cooled_toffee_storage,
    raw_toffee_source=toffee_raw_material_source,
    electricity_load=electricity_load,
    natural_gas_load=natural_gas_load,
)


# def pickle_dump_production_plan(
#     file_to_pickle,
#     file_name: str = "production_plan",
#     subdirectory_name: str = "production_plan",
#     add_time_stamp_to_filename: bool = True,
# ):
#     result_path_generator = ResultPathGenerator()
#     result_path = result_path_generator.create_path_to_file_relative_to_main_file(
#         file_name=file_name,
#         subdirectory_name=subdirectory_name,
#         add_time_stamp_to_filename=add_time_stamp_to_filename,
#         file_extension=".pckl",
#     )
#     with open(result_path, "wb") as file:
#         cloudpickle.dump(file_to_pickle, file, protocol=None)


# def pickle_load_production_plan(self, path_to_pickle_file: str):
#     with open(path_to_pickle_file, "rb") as input_file:
#         self.production_plan = cloudpickle.load(input_file)
# first_sink.initialize_sink()
enterprise.start_simulation()
simulation_end_time = datetime.datetime.now()
enterprise.production_plan.save_all_simulation_results_to_sqlite()
# pickle_dump_production_plan(enterprise)
enterprise.production_plan
enterprise.create_post_simulation_report(
    # gantt_chart_end_date=time_data.global_end_date - datetime.timedelta(hours=24),
    # gantt_chart_start_date=time_data.global_end_date - datetime.timedelta(hours=48),
    gantt_chart_end_date=time_data.global_end_date,
    gantt_chart_start_date=time_data.global_end_date - datetime.timedelta(hours=24),
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
