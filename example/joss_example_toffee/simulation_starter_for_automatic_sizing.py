import datetime
import cProfile
import cloudpickle
from typeguard import install_import_hook
import pint

install_import_hook("ethos_penalps")


from ethos_penalps.data_classes import LoadType
from ethos_penalps.enterprise import Enterprise, NetworkLevel
from ethos_penalps.time_data import TimeData
from ethos_penalps.data_classes import Commodity
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.post_processing.production_plan_post_processor import (
    ProductionPlanPostProcessor,
)
from ethos_penalps.automatic_sizer.automatic_setter import ProcessStepSetter
from ethos_penalps.utilities.units import Units
from toffee_preparation_chain_1 import fill_toffee_preparation_chain_1
from toffee_preparation_chain_2 import fill_toffee_preparation_chain_2
from cutting_and_packaging_chain import fill_cutting_and_packaging_chain

# from process_chain_2_1 import fill_process_chain_2_1


def run_simulation(x):
    packaging_and_cutting_stream = x[0]
    toffee_machine_output_and_input = x[1]
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
        mass_per_order=0.39 * 2 * 24 * 1,
        production_deadline=time_data.global_end_date,
        number_of_orders=1,
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
    combined_stream_handler = enterprise.get_combined_stream_handler()
    process_step_dict = enterprise.get_all_process_steps()
    # Packaging Machine

    ## Cold mill process state switches
    packaging_machine = process_step_dict["Packaging Machine"]
    process_step_setter = ProcessStepSetter(
        process_step=packaging_machine, stream_handler=combined_stream_handler
    )
    process_step_setter.set_continuous_output_stream_max_rate(
        maximum_operation_rate=packaging_and_cutting_stream
    )
    # Cutting Machine
    cutting_machine = process_step_dict["Cutting Machine"]
    process_step_setter_packaging = ProcessStepSetter(
        process_step=cutting_machine, stream_handler=combined_stream_handler
    )
    process_step_setter_packaging.set_continuous_output_stream_max_rate(
        maximum_operation_rate=packaging_and_cutting_stream
    )
    process_step_setter_packaging.set_batch_input_stream_value(
        batch_mass=toffee_machine_output_and_input
    )
    # Toffee Machine
    # Machine 1
    toffee_machine_1 = process_step_dict["Toffee Machine 1"]
    process_step_setter_toffee_machine_1 = ProcessStepSetter(
        process_step=toffee_machine_1, stream_handler=combined_stream_handler
    )
    process_step_setter_toffee_machine_1.set_batch_output_stream_value(
        batch_mass=toffee_machine_output_and_input
    )
    process_step_setter_toffee_machine_1.set_batch_input_stream_value(
        batch_mass=toffee_machine_output_and_input
    )
    # Machine 2
    toffee_machine_2 = process_step_dict["Toffee Machine 2"]
    process_step_setter_toffee_machine_2 = ProcessStepSetter(
        process_step=toffee_machine_2, stream_handler=combined_stream_handler
    )
    process_step_setter_toffee_machine_2.set_batch_output_stream_value(
        batch_mass=toffee_machine_output_and_input
    )
    process_step_setter_toffee_machine_2.set_batch_input_stream_value(
        batch_mass=toffee_machine_output_and_input
    )

    enterprise.start_simulation()
    production_plan_post_processor = ProductionPlanPostProcessor(
        process_node_dict=enterprise.get_all_process_steps(),
        production_plan=enterprise.production_plan,
        stream_handler=combined_stream_handler,
        time_data=enterprise.time_data,
    )
    process_step_post_processor_dict = (
        production_plan_post_processor.create_all_process_step_processors()
    )

    # Packaging_machine
    packaging_machine_throughput_difference = (
        production_plan_post_processor.determine_throughput_difference_for_process_step(
            post_production_post_processor_dict=process_step_post_processor_dict,
            process_step_name="Packaging Machine",
            target_throughput=390 * 2 * Units.get_unit(unit_string="kg/h"),
        )
    )
    # Continuous Caster
    cutting_machine_throughput_difference = (
        production_plan_post_processor.determine_throughput_difference_for_process_step(
            post_production_post_processor_dict=process_step_post_processor_dict,
            process_step_name="Cutting Machine",
            target_throughput=390 * 2 * Units.get_unit(unit_string="kg/h"),
        )
    )
    # Toffee machines
    # 1
    toffee_machine_1_throughput_difference = (
        production_plan_post_processor.determine_throughput_difference_for_process_step(
            post_production_post_processor_dict=process_step_post_processor_dict,
            process_step_name="Toffee Machine 1",
            target_throughput=390 * Units.get_unit(unit_string="kg/h"),
        )
    )

    # 2
    toffee_machine_2_throughput_difference = (
        production_plan_post_processor.determine_throughput_difference_for_process_step(
            post_production_post_processor_dict=process_step_post_processor_dict,
            process_step_name="Toffee Machine 2",
            target_throughput=390 * Units.get_unit(unit_string="kg/h"),
        )
    )

    print(
        "packaging_machine_throughput_difference",
    )
    print(packaging_machine_throughput_difference)
    print("cutting_machine_throughput_difference")
    print(cutting_machine_throughput_difference)
    print("toffee_machine_1_throughput_difference")
    print(toffee_machine_1_throughput_difference)
    print("toffee_machine_2_throughput_difference")
    print(toffee_machine_2_throughput_difference)
    sum_diff_quantity = (
        abs(packaging_machine_throughput_difference)
        + abs(cutting_machine_throughput_difference)
        + abs(toffee_machine_1_throughput_difference)
        + abs(toffee_machine_2_throughput_difference)
    )
    sum_diff_magnitude = sum_diff_quantity.magnitude

    enterprise.create_post_simulation_report(
        # gantt_chart_end_date=time_data.global_end_date - datetime.timedelta(hours=24),
        # gantt_chart_start_date=time_data.global_end_date - datetime.timedelta(hours=48),
        gantt_chart_end_date=time_data.global_end_date,
        gantt_chart_start_date=time_data.global_end_date - datetime.timedelta(hours=28),
        x_axis_time_delta=datetime.timedelta(hours=24),
        # start_date=time_data.global_start_date,
        start_date=time_data.global_end_date - datetime.timedelta(days=365),
        end_date=time_data.global_end_date,
    )
    return sum_diff_magnitude
