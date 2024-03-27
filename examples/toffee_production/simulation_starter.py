import datetime
import logging

from cutting_and_packaging_chain import fill_cutting_and_packaging_chain
from ethos_penalps.data_classes import Commodity, LoadType
from ethos_penalps.organizational_agents.enterprise import Enterprise
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from toffee_preparation_chain_1 import fill_toffee_preparation_chain_1
from toffee_preparation_chain_2 import fill_toffee_preparation_chain_2


def start_simulation():
    # Create logger to receiver information about the simulation progress [optional]
    logger = PeNALPSLogger.get_human_readable_logger(logging.INFO)

    # Set simulation time data
    time_data = TimeData(
        global_end_date=datetime.datetime(year=2023, month=1, day=1),
        global_start_date=datetime.datetime(year=2022, month=12, day=30),
    )

    # Initialize enterprise
    enterprise = Enterprise(location="Example Location", time_data=time_data)

    # Create network level
    toffee_packaging_level = enterprise.create_network_level()
    toffee_production_level = enterprise.create_network_level()

    # Determine all relevant commodities
    toffee_input_commodity = Commodity(name="Raw Toffee Ingredients")
    cooled_toffee = Commodity(name="Cooled Toffee")
    cut_toffee_commodity = Commodity(name="Cut Toffee")
    packaged_toffee_commodity = Commodity(name="Packaged Toffee")

    # Create all considered load types
    electricity_load = LoadType("Electricity")
    natural_gas_load = LoadType("Natural Gas")

    # Create all order for the simulation
    order_generator = NOrderGenerator(
        commodity=packaged_toffee_commodity,
        mass_per_order=0.39 * 2 * 24 * 1,
        production_deadline=time_data.global_end_date,
        number_of_orders=1,
    )
    product_order_collection = order_generator.create_n_order_collection()

    # Create all sources, sinks and network level storages
    packaged_toffee_sink = toffee_packaging_level.create_main_sink(
        order_collection=product_order_collection,
        name="Packaged Toffee Sink",
        commodity=packaged_toffee_commodity,
    )
    cooled_toffee_storage = (
        toffee_packaging_level.create_process_chain_storage_as_source(
            commodity=cooled_toffee,
            name="Cooled Toffee Storage",
        )
    )

    toffee_production_level.add_process_chain_storage_as_sink(
        process_chain_storage=cooled_toffee_storage
    )
    toffee_raw_material_source = toffee_production_level.create_main_source(
        name="Toffee Raw Materials", commodity=toffee_input_commodity
    )

    # Create first process chain
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

    # Create first process chain of network level 1
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

    # Create second process chain of network level 1
    toffee_production_chain_2 = toffee_production_level.create_process_chain(
        process_chain_name="Toffee Production Chain 2",
    )
    toffee_production_chain_2 = fill_toffee_preparation_chain_2(
        process_chain=toffee_production_chain_2,
        cooled_toffee_sink=cooled_toffee_storage,
        raw_toffee_source=toffee_raw_material_source,
        electricity_load=electricity_load,
        natural_gas_load=natural_gas_load,
    )

    # Start the simulation
    enterprise.start_simulation()

    # Create report of the simulation results
    enterprise.create_post_simulation_report(
        gantt_chart_end_date=time_data.global_end_date,
        # gantt_chart_start_date=time_data.global_end_date - datetime.timedelta(hours=28),
        gantt_chart_start_date=time_data.global_end_date
        - datetime.timedelta(minutes=20),
        x_axis_time_delta=datetime.timedelta(days=1),
        start_date=time_data.global_start_date,
        end_date=time_data.global_end_date,
        resample_frequency="1min",
    )


if __name__ == "__main__":
    start_simulation()
