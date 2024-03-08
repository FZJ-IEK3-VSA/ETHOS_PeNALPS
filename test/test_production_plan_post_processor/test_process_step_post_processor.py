import datetime

from test.test_production_plan_post_processor.cutting_and_heating_chain import (
    fill_cutting_and_heating_chain,
)
from test.test_production_plan_post_processor.forming_quenching_and_triming_chain import (
    fill_forming_quenching_and_trimming_chain,
)

from ethos_penalps.capacity_calculator import CapacityAdjuster, CapacityCalculator
from ethos_penalps.data_classes import Commodity
from ethos_penalps.enterprise import Enterprise, NetworkLevel
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.post_processing.production_plan_post_processor import (
    ProcessStepPostProcessor,
    StreamPostProcessor,
)

# from process_chain_2_1 import fill_process_chain_2_1


def test_production_plan_post_processor():
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
    stream_handler = enterprise._get_combined_stream_handler()
    process_step_dict = enterprise.get_all_process_steps()
    for (
        process_step_name,
        list_of_process_step_states,
    ) in enterprise.production_plan.process_step_states_dict.items():
        process_step = process_step_dict[process_step_name]
        input_stream_name = process_step.get_output_stream_name()
        output_stream_name = process_step.get_input_stream_name()

        input_stream = stream_handler.get_stream(stream_name=input_stream_name)
        output_stream = stream_handler.get_stream(stream_name=output_stream_name)
        list_of_input_stream_states = enterprise.production_plan.stream_state_dict[
            input_stream_name
        ]
        list_of_output_stream_states = enterprise.production_plan.stream_state_dict[
            output_stream_name
        ]
        input_stream_post_processor = StreamPostProcessor(
            stream=input_stream, list_of_stream_states=list_of_input_stream_states
        )
        output_stream_post_processor = StreamPostProcessor(
            stream=output_stream, list_of_stream_states=list_of_output_stream_states
        )

        process_step_post_processor = ProcessStepPostProcessor(
            list_of_process_step_entries=list_of_process_step_states,
            input_stream_post_processor=input_stream_post_processor,
            output_stream_post_processor=output_stream_post_processor,
            process_step=process_step,
        )
        earliest_process_step_time = (
            process_step_post_processor.get_earliest_start_date()
        )
        latest_process_step_time = process_step_post_processor.get_latest_end_date()
        throughput = process_step_post_processor.determine_mass_throughput(
            earliest_start_date=earliest_process_step_time,
            latest_end_date=latest_process_step_time,
        )

        print(process_step.name)
        print(throughput)
