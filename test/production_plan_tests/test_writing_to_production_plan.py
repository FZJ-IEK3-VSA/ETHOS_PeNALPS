import datetime
import pathlib

from test.production_plan_tests.cutting_and_heating_chain import (
    fill_cutting_and_heating_chain,
)
from test.production_plan_tests.forming_quenching_and_trimming_chain import (
    fill_forming_quenching_and_trimming_chain,
)

from ethos_penalps.capacity_calculator import CapacityAdjuster, CapacityCalculator
from ethos_penalps.data_classes import Commodity
from ethos_penalps.enterprise import Enterprise, NetworkLevel
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

# from process_chain_2_1 import fill_process_chain_2_1


def test_write_production_plan():
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
    )

    trimmed_part_collection = order_generator.create_n_order_collection()
    # End Points for Hot Rolling
    trimmed_part_sink = forming_and_trimming_level.create_main_sink(
        name="Trimmed Part Sink",
        commodity=trimmed_part,
        order_collection=trimmed_part_collection,
    )

    hot_part_storage = (
        forming_and_trimming_level.create_process_chain_storage_as_source(
            name="Hot Part Sink",
            commodity=trimmed_part,
        )
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

    enterprise.start_simulation()
    # current_directory_directory = pathlib.Path(__file__).parent.absolute()

    list_of_output_file_paths = (
        enterprise.production_plan.save_all_simulation_results_to_sqlite()
    )
    pathlib.Path(list_of_output_file_paths[0]).unlink()
    pathlib.Path(list_of_output_file_paths[1]).unlink()


if __name__ == "__main__":
    test_write_production_plan()
