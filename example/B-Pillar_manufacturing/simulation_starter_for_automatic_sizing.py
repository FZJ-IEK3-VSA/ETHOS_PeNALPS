import cProfile
import datetime

import cloudpickle
from typeguard import install_import_hook


install_import_hook("ethos_elpsi")
from cutting_and_heating_chain import fill_cutting_and_heating_chain
from forming_quenching_and_triming_chain import (
    fill_forming_quenching_and_trimming_chain,
)
import scipy.optimize


from ethos_penalps.data_classes import Commodity
from ethos_penalps.enterprise import Enterprise, NetworkLevel
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.capacity_calculator import CapacityCalculator, CapacityAdjuster
from ethos_penalps.post_processing.production_plan_post_processor import (
    ProductionPlanPostProcessor,
)
from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.utilities.units import Units
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.stream import ContinuousStream, BatchStream
from ethos_penalps.automatic_sizer.automatic_setter import ProcessStepSetter


def run_simulation(x):
    b_pillar_mass = 0.006
    coil_cutter_batch_input = b_pillar_mass

    open_heart_furnace_throughput = x[0]
    coil_cutter_to_open_heart_furnace_batch_size = b_pillar_mass
    quenching_input = b_pillar_mass
    forming_and_quenching_throughput = b_pillar_mass
    trimming_throughput = b_pillar_mass

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
        mass_per_order=0.006,
        production_deadline=time_data.global_end_date,
        # number_of_orders=86,
        number_of_orders=43,
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
    combined_stream_handler = enterprise.get_combined_stream_handler()
    process_step_dict = enterprise.get_all_process_steps()
    # Coil Cutter
    coil_cutter = process_step_dict["Coil Cutter"]
    process_step_setter = ProcessStepSetter(
        process_step=coil_cutter, stream_handler=combined_stream_handler
    )
    process_step_setter.set_batch_input_stream_value(batch_mass=coil_cutter_batch_input)
    # Open Heart Furnace
    open_hearth_furnace = process_step_dict["Open Hearth Furnace"]
    process_step_setter = ProcessStepSetter(
        process_step=open_hearth_furnace, stream_handler=combined_stream_handler
    )
    process_step_setter.set_continuous_output_stream_max_rate(
        maximum_operation_rate=open_heart_furnace_throughput
    )
    process_step_setter.set_batch_input_stream_value(
        batch_mass=coil_cutter_to_open_heart_furnace_batch_size
    )

    # Forming and Quenching
    forming_and_quenching_machine = process_step_dict["Forming Quenching"]
    process_step_setter = ProcessStepSetter(
        process_step=forming_and_quenching_machine,
        stream_handler=combined_stream_handler,
    )
    process_step_setter.set_batch_output_stream_value(
        batch_mass=forming_and_quenching_throughput
    )
    process_step_setter.set_batch_input_stream_value(batch_mass=quenching_input)

    # Trimming
    trimming_machine = forming_and_trimming_chain.get_process_node(
        process_node_name="Trimming"
    )
    process_step_setter = ProcessStepSetter(
        process_step=trimming_machine, stream_handler=combined_stream_handler
    )
    process_step_setter.set_batch_output_stream_value(batch_mass=trimming_throughput)

    # first_sink.initialize_sink()
    enterprise.start_simulation(number_of_iterations_in_chain=None)

    production_plan_post_processor = ProductionPlanPostProcessor(
        process_node_dict=enterprise.get_all_process_steps(),
        production_plan=enterprise.production_plan,
        stream_handler=combined_stream_handler,
        time_data=enterprise.time_data,
    )
    earliest_process_state_date = (
        production_plan_post_processor.determine_earliest_process_state()
    )
    latest_end_time = production_plan_post_processor.determine_latest_end_time()

    process_step_post_processor_dict = (
        production_plan_post_processor.create_all_process_step_processors()
    )
    trimming_idle_time = (
        production_plan_post_processor.determine_idle_time_for_process_step(
            post_production_post_processor_dict=process_step_post_processor_dict,
            process_step_name="Trimming",
            start_date=earliest_process_state_date,
            end_date=latest_end_time,
        )
    )
    forming_and_quenching_idle_time = (
        production_plan_post_processor.determine_idle_time_for_process_step(
            post_production_post_processor_dict=process_step_post_processor_dict,
            process_step_name="Forming Quenching",
            start_date=earliest_process_state_date,
            end_date=latest_end_time,
        )
    )
    open_heart_furnace_idle_time = (
        production_plan_post_processor.determine_idle_time_for_process_step(
            post_production_post_processor_dict=process_step_post_processor_dict,
            process_step_name="Open Hearth Furnace",
            start_date=earliest_process_state_date,
            end_date=latest_end_time,
        )
    )
    coil_cutter_idle_time = (
        production_plan_post_processor.determine_idle_time_for_process_step(
            post_production_post_processor_dict=process_step_post_processor_dict,
            process_step_name="Coil Cutter",
            start_date=earliest_process_state_date,
            end_date=latest_end_time,
        )
    )
    sum_diff = (
        trimming_idle_time
        + forming_and_quenching_idle_time
        + open_heart_furnace_idle_time
        # + coil_cutter_idle_time
    )
    # Trimmer
    current_throughput_trimming_throughput = (
        production_plan_post_processor.determine_throughput_for_process_step(
            post_production_post_processor_dict=process_step_post_processor_dict,
            process_step_name="Trimming",
        )
    )
    print(
        "current_throughput_trimming_throughput", current_throughput_trimming_throughput
    )
    # # throughput and quenching
    # forming_and_quenching_throughput = (
    #     production_plan_post_processor.determine_throughput_for_process_step(
    #         post_production_post_processor_dict=process_step_post_processor_dict,
    #         process_step_name="Forming Quenching",
    #     )
    # )
    # print("forming_and_quenching_throughput", forming_and_quenching_throughput)

    # # Open Heart furnace
    # open_hearth_furnace_throughput = (
    #     production_plan_post_processor.determine_throughput_for_process_step(
    #         post_production_post_processor_dict=process_step_post_processor_dict,
    #         process_step_name="Open Hearth Furnace",
    #     )
    # )
    # print("open_hearth_furnace_throughput", open_hearth_furnace_throughput)
    # # Diff

    # coil_cutter_throughput = (
    #     production_plan_post_processor.determine_throughput_for_process_step(
    #         post_production_post_processor_dict=process_step_post_processor_dict,
    #         process_step_name="Coil Cutter",
    #     )
    # )
    # print("coil_cutter_throughput", coil_cutter_throughput)
    # sum_diff = abs(
    #     forming_and_quenching_throughput - open_hearth_furnace_throughput
    # ) + abs(coil_cutter_throughput - forming_and_quenching_throughput)
    print("sum_diff", sum_diff)
    sum_diff_magnitude = sum_diff.magnitude

    enterprise.create_post_simulation_report(
        # gantt_chart_end_date=time_data.global_end_date - datetime.timedelta(hours=24),
        # gantt_chart_start_date=time_data.global_end_date - datetime.timedelta(hours=48),
        gantt_chart_end_date=time_data.global_end_date,
        gantt_chart_start_date=time_data.global_end_date
        - datetime.timedelta(minutes=30),
        x_axis_time_delta=datetime.timedelta(hours=24),
        # start_date=time_data.global_start_date,
        start_date=time_data.global_end_date - datetime.timedelta(days=365),
        end_date=time_data.global_end_date,
    )
    return sum_diff_magnitude


if __name__ == "__main__":
    # import logging

    # logger = PeNALPSLogger.get_logger_to_create_table(logging_level=logging.DEBUG)

    # logger = PeNALPSLogger.get_human_readable_logger(logging_level=logging.INFO)
    # def equality_constraint_1(x):
    #     return x[2] - x[3]

    # def equality_constraint_2(x):
    #     return x[3] - x[4]

    # constraint_1 = scipy.optimize.NonlinearConstraint(
    #     fun=equality_constraint_1, lb=0, ub=0
    # )
    # constraint_2 = scipy.optimize.NonlinearConstraint(
    #     fun=equality_constraint_2, lb=0, ub=0
    # )
    from multiprocessing import Pool

    # n_workers = 8
    # with Pool(n_workers) as p:
    #     processed_chunks_1 = p.map(self.calc_building_features, chunks)
    # results = scipy.optimize.differential_evolution(
    #     func=run_simulation,
    #     x0=[344.11717332, 177.86530134, 0.55078313],
    #     bounds=[(100, 500), (100, 500), (0.1, 2)],
    #     # constraints=[constraint_1, constraint_2],
    #     workers=4,
    #     disp=True,
    #     updating="deferred",
    # )
    # import logging

    # logger = PeNALPSLogger.get_human_readable_logger(logging_level=logging.INFO)

    results = run_simulation(
        x=[244.16363707, 208.32257974, 1.27725414, 1.27725414, 1.27725414]
    )
    # results = run_simulation(x=[225.1301106, 69.69739767, 86.66533953, 86.66533953])
    print(results)
