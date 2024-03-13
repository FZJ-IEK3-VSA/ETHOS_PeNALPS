import datetime
import logging

from typeguard import install_import_hook

install_import_hook("ethos_penalps")
from ethos_penalps.data_classes import Commodity, LoadType
from ethos_penalps.enterprise import Enterprise
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.stream import BatchStreamStaticData, ContinuousStreamStaticData
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_human_readable_logger(logging.INFO)

# Enterprise structure

# Set simulation time data
start_date = datetime.datetime(2022, 1, 2, hour=22)
end_date = datetime.datetime(2022, 1, 3)
time_data = TimeData(
    global_start_date=start_date,
    global_end_date=end_date,
)


# Determine all relevant commodities
output_commodity = Commodity(name="Cooked Goods")
input_commodity = Commodity(name="Raw Goods")

# Create all order for the simulation
order_generator = NOrderGenerator(
    commodity=output_commodity,
    mass_per_order=0.00065,
    production_deadline=end_date,
    number_of_orders=4,
    time_span_between_order=datetime.timedelta(minutes=5),
)

order_collection = order_generator.create_n_order_collection()

# Initialize enterprise
enterprise = Enterprise(time_data=time_data, name="Cooking Example")

# Create network level
network_level = enterprise.create_network_level()
# Create first process chain

process_chain_1 = network_level.create_process_chain(
    process_chain_name="Cooker Chain 1"
)
process_chain_2 = network_level.create_process_chain(
    process_chain_name="Cooker Chain 2"
)


# Create all sources, sinks and network level storages
sink = network_level.create_main_sink(
    name="Cooked Goods Storage",
    commodity=output_commodity,
    order_collection=order_collection,
)
source = network_level.create_main_source(
    name="Raw Material Storage",
    commodity=input_commodity,
)


# Add sources and sinks to process chain
process_chain_1.add_sink(sink=sink)
process_chain_1.add_source(source=source)
process_chain_2.add_sink(sink=sink)
process_chain_2.add_source(source=source)

# Create Process nodes
process_step_1 = process_chain_1.create_process_step(name="Cooker 1")
process_step_2 = process_chain_2.create_process_step(name="Cooker 2")

# Streams
raw_materials_to_cooking_stream_1 = process_chain_1.stream_handler.create_batch_stream(
    batch_stream_static_data=BatchStreamStaticData(
        start_process_step_name=source.name,
        end_process_step_name=process_step_1.name,
        delay=datetime.timedelta(minutes=1),
        commodity=input_commodity,
        maximum_batch_mass_value=0.00065,
    )
)
cooking_to_sink_stream_1 = process_chain_1.stream_handler.create_batch_stream(
    batch_stream_static_data=BatchStreamStaticData(
        start_process_step_name=process_step_1.name,
        end_process_step_name=sink.name,
        delay=datetime.timedelta(minutes=1),
        commodity=output_commodity,
        maximum_batch_mass_value=0.00065,
    )
)

raw_materials_to_cooking_stream_2 = process_chain_2.stream_handler.create_batch_stream(
    batch_stream_static_data=BatchStreamStaticData(
        start_process_step_name=source.name,
        end_process_step_name=process_step_2.name,
        delay=datetime.timedelta(minutes=1),
        commodity=input_commodity,
        maximum_batch_mass_value=0.00065,
    )
)
cooking_to_sink_stream_2 = process_chain_2.stream_handler.create_batch_stream(
    batch_stream_static_data=BatchStreamStaticData(
        start_process_step_name=process_step_2.name,
        end_process_step_name=sink.name,
        delay=datetime.timedelta(minutes=1),
        commodity=output_commodity,
        maximum_batch_mass_value=0.00065,
    )
)

# Add streams to sinks and sources
source.add_output_stream(
    output_stream=raw_materials_to_cooking_stream_1,
    process_chain_identifier=process_chain_1.process_chain_identifier,
)
sink.add_input_stream(
    input_stream=cooking_to_sink_stream_1,
    process_chain_identifier=process_chain_1.process_chain_identifier,
)
source.add_output_stream(
    output_stream=raw_materials_to_cooking_stream_2,
    process_chain_identifier=process_chain_2.process_chain_identifier,
)
sink.add_input_stream(
    input_stream=cooking_to_sink_stream_2,
    process_chain_identifier=process_chain_2.process_chain_identifier,
)

""" Create petri net for process step
Each process state must have at least the following:
- Either
    - one combined production state
    your_combined_state=process_step.process_state_handler.create_continuous_production_process_state_with_storage(
    process_state_name="your process state name"
    )
    or
        - an input stream requesting state
        your_input_stream_requesting_state=process_step.process_state_handler.create_continuous_input_stream_requesting_state(process_state_name="your input stream providing state")
        - and input stream requesting state
        your_output_stream_providing_state=process_step.create_continuous_output_stream_providing_state(process_state_name="your output stream providing state")
    also an idle state is required
    your_idle_state=process_step..process_state_handler.create_idle_process_state(
        process_state_name="Your idle state"
    )
"""

# Cooker 1
idle_state_1 = process_step_1.process_state_handler.create_idle_process_state(
    process_state_name="Idle"
)
fill_raw_materials_state_1 = (
    process_step_1.process_state_handler.create_batch_input_stream_requesting_state(
        process_state_name="Fill raw materials"
    )
)

cooking_state_1 = process_step_1.process_state_handler.create_intermediate_process_state_energy_based_on_stream_mass(
    process_state_name="Cooking"
)

discharge_goods_state_1 = (
    process_step_1.process_state_handler.create_batch_output_stream_providing_state(
        process_state_name="Discharge"
    )
)

activate_not_cooking_1 = process_step_1.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
    start_process_state=discharge_goods_state_1,
    end_process_state=idle_state_1,
)
process_step_1.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_not_cooking_1
)

activate_filling_1 = process_step_1.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
    start_process_state=idle_state_1,
    end_process_state=fill_raw_materials_state_1,
)

process_step_1.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_filling_1
)

activate_cooking_1 = process_step_1.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
    start_process_state=fill_raw_materials_state_1,
    end_process_state=cooking_state_1,
    delay=datetime.timedelta(minutes=30),
)

process_step_1.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_cooking_1
)


activate_discharging_1 = process_step_1.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_output_stream(
    start_process_state=cooking_state_1,
    end_process_state=discharge_goods_state_1,
)
process_step_1.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_discharging_1
)

# Cooker 2
# Process Step 2

idle_state_2 = process_step_2.process_state_handler.create_idle_process_state(
    process_state_name="Idle"
)
fill_raw_materials_state_2 = (
    process_step_2.process_state_handler.create_batch_input_stream_requesting_state(
        process_state_name="Fill raw materials"
    )
)

cooking_state_2 = process_step_2.process_state_handler.create_intermediate_process_state_energy_based_on_stream_mass(
    process_state_name="Cooking"
)

discharge_goods_state_2 = (
    process_step_2.process_state_handler.create_batch_output_stream_providing_state(
        process_state_name="Discharge"
    )
)

activate_not_cooking_2 = process_step_2.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
    start_process_state=discharge_goods_state_2,
    end_process_state=idle_state_2,
)
process_step_2.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_not_cooking_2
)

activate_filling_2 = process_step_2.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
    start_process_state=idle_state_2,
    end_process_state=fill_raw_materials_state_2,
)

process_step_2.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_filling_2
)

activate_cooking_2 = process_step_2.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
    start_process_state=fill_raw_materials_state_2,
    end_process_state=cooking_state_2,
    delay=datetime.timedelta(minutes=30),
)

process_step_2.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_cooking_2
)


activate_discharging_2 = process_step_2.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_output_stream(
    start_process_state=cooking_state_2,
    end_process_state=discharge_goods_state_2,
)
process_step_2.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_discharging_2
)

# Add Energy Data
electricity_load = LoadType(name="Electricity")
cooking_state_1.create_process_state_energy_data_based_on_stream_mass(
    specific_energy_demand=830.76,
    load_type=electricity_load,
    stream=raw_materials_to_cooking_stream_1,
)
cooking_state_2.create_process_state_energy_data_based_on_stream_mass(
    specific_energy_demand=830.76,
    load_type=electricity_load,
    stream=raw_materials_to_cooking_stream_2,
)

# Add Mass Balance

process_step_1.create_main_mass_balance(
    commodity=output_commodity,
    input_to_output_conversion_factor=1,
    main_input_stream=raw_materials_to_cooking_stream_1,
    main_output_stream=cooking_to_sink_stream_1,
)

process_step_2.create_main_mass_balance(
    commodity=output_commodity,
    input_to_output_conversion_factor=1,
    main_input_stream=raw_materials_to_cooking_stream_2,
    main_output_stream=cooking_to_sink_stream_2,
)


# Add internal storages (required)

process_step_1.process_state_handler.process_step_data.main_mass_balance.create_storage(
    current_storage_level=0
)

process_step_2.process_state_handler.process_step_data.main_mass_balance.create_storage(
    current_storage_level=0
)


# Start the simulation
enterprise.start_simulation(number_of_iterations_in_chain=200)

# Create report of the simulation results
enterprise.create_post_simulation_report(
    start_date=start_date,
    end_date=end_date,
    x_axis_time_delta=datetime.timedelta(hours=1),
    resample_frequency="1min",
    gantt_chart_end_date=end_date,
    gantt_chart_start_date=end_date - datetime.timedelta(hours=1, minutes=45),
)
