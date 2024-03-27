import datetime
import logging

from ethos_penalps.data_classes import Commodity, LoadType
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.organizational_agents.enterprise import Enterprise
from ethos_penalps.stream import BatchStreamStaticData, ContinuousStreamStaticData
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_human_readable_logger(logging.DEBUG)

# Enterprise structure

# Set simulation time data
start_date = datetime.datetime(2022, 1, 2, hour=23)
end_date = datetime.datetime(2022, 1, 3)
time_data = TimeData(
    global_start_date=start_date,
    global_end_date=end_date,
)


# Determine all relevant commodities
raw_commodity = Commodity(name="Raw Goods")
uncooked_commodity = Commodity(name="Uncooked Goods")
output_commodity = Commodity(name="Cooked Goods")


# Create all order for the simulation
order_generator = NOrderGenerator(
    commodity=output_commodity,
    mass_per_order=0.00065,
    production_deadline=end_date,
    number_of_orders=2,
)

order_collection = order_generator.create_n_order_collection()

# Initialize enterprise
enterprise = Enterprise(time_data=time_data, name="Cooking Example")

# Create network level
network_level = enterprise.create_network_level()
# Create first process chain

process_chain = network_level.create_process_chain(process_chain_name="Cooker Chain 1")
# Create all sources, sinks and network level storages
sink = network_level.create_main_sink(
    name="Cooked Goods Storage",
    commodity=output_commodity,
    order_collection=order_collection,
)
source = network_level.create_main_source(
    name="Raw Material Storage",
    commodity=raw_commodity,
)


# Add sources and sinks to process chain
process_chain.add_sink(sink=sink)
process_chain.add_source(source=source)

# Create Process nodes
blender_step = process_chain.create_process_step(name="Blender")
cooker_step = process_chain.create_process_step(name="Cooker")

# Streams
## Process Chain 1
raw_materials_to_blender_stream = process_chain.stream_handler.create_batch_stream(
    batch_stream_static_data=BatchStreamStaticData(
        start_process_step_name=source.name,
        end_process_step_name=blender_step.name,
        delay=datetime.timedelta(minutes=1),
        commodity=raw_commodity,
        maximum_batch_mass_value=0.00065,
    )
)
blender_to_cooker_stream = process_chain.stream_handler.create_batch_stream(
    batch_stream_static_data=BatchStreamStaticData(
        start_process_step_name=blender_step.name,
        end_process_step_name=cooker_step.name,
        delay=datetime.timedelta(minutes=1),
        commodity=output_commodity,
        maximum_batch_mass_value=0.00065,
    )
)

cooker_to_sink_stream = process_chain.stream_handler.create_batch_stream(
    batch_stream_static_data=BatchStreamStaticData(
        start_process_step_name=cooker_step.name,
        end_process_step_name=sink.name,
        delay=datetime.timedelta(minutes=1),
        commodity=raw_commodity,
        maximum_batch_mass_value=0.00065,
    )
)

# Add streams to sinks and sources
source.add_output_stream(
    output_stream=raw_materials_to_blender_stream,
    process_chain_identifier=process_chain.process_chain_identifier,
)
sink.add_input_stream(
    input_stream=cooker_to_sink_stream,
    process_chain_identifier=process_chain.process_chain_identifier,
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
# Process Step 1

idle_state_blender = blender_step.process_state_handler.create_idle_process_state(
    process_state_name="Idle"
)
fill_raw_materials_state_1 = (
    blender_step.process_state_handler.create_batch_input_stream_requesting_state(
        process_state_name="Fill raw materials"
    )
)

blending_state = blender_step.process_state_handler.create_intermediate_process_state_energy_based_on_stream_mass(
    process_state_name="Blend"
)

discharge_goods_state_blender = (
    blender_step.process_state_handler.create_batch_output_stream_providing_state(
        process_state_name="Discharge"
    )
)


# Petri net transitions

activate_not_blending = blender_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
    start_process_state=discharge_goods_state_blender,
    end_process_state=idle_state_blender,
)
blender_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_not_blending
)

activate_filling_blender = blender_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
    start_process_state=idle_state_blender,
    end_process_state=fill_raw_materials_state_1,
)

blender_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_filling_blender
)

activate_blending = blender_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
    start_process_state=fill_raw_materials_state_1,
    end_process_state=blending_state,
    delay=datetime.timedelta(minutes=5),
)

blender_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_blending
)


activate_discharging_blender = blender_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_output_stream(
    start_process_state=blending_state,
    end_process_state=discharge_goods_state_blender,
)
blender_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_discharging_blender
)

# Cooker

idle_state_cooker = cooker_step.process_state_handler.create_idle_process_state(
    process_state_name="Idle"
)
fill_raw_materials_state_cooker = (
    cooker_step.process_state_handler.create_batch_input_stream_requesting_state(
        process_state_name="Fill raw materials"
    )
)

cooking_state = cooker_step.process_state_handler.create_intermediate_process_state_energy_based_on_stream_mass(
    process_state_name="Cooking"
)

discharge_goods_state_cooker = (
    cooker_step.process_state_handler.create_batch_output_stream_providing_state(
        process_state_name="Discharge"
    )
)


# Petri net transitions

activate_not_cooking = cooker_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
    start_process_state=discharge_goods_state_cooker,
    end_process_state=idle_state_cooker,
)
cooker_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_not_cooking
)

activate_filling_cooker = cooker_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
    start_process_state=idle_state_cooker,
    end_process_state=fill_raw_materials_state_cooker,
)

cooker_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_filling_cooker
)

activate_cooking = cooker_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
    start_process_state=fill_raw_materials_state_cooker,
    end_process_state=cooking_state,
    delay=datetime.timedelta(minutes=24),
)

cooker_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_cooking
)


activate_discharging_cooker = cooker_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_output_stream(
    start_process_state=cooking_state,
    end_process_state=discharge_goods_state_cooker,
)
cooker_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_discharging_cooker
)


electricity_load = LoadType(name="Electricity")
blending_state.create_process_state_energy_data_based_on_stream_mass(
    specific_energy_demand=600,
    load_type=electricity_load,
    stream=raw_materials_to_blender_stream,
)
cooking_state.create_process_state_energy_data_based_on_stream_mass(
    specific_energy_demand=830.76,
    load_type=electricity_load,
    stream=blender_to_cooker_stream,
)


# Mass balances
blender_step.create_main_mass_balance(
    commodity=output_commodity,
    input_to_output_conversion_factor=1,
    main_input_stream=raw_materials_to_blender_stream,
    main_output_stream=blender_to_cooker_stream,
)

# Add internal storages (required)
blender_step.process_state_handler.process_step_data.main_mass_balance.create_storage(
    current_storage_level=0
)

# Mass balances
cooker_step.create_main_mass_balance(
    commodity=output_commodity,
    input_to_output_conversion_factor=1,
    main_input_stream=blender_to_cooker_stream,
    main_output_stream=cooker_to_sink_stream,
)

# Add internal storages (required)
cooker_step.process_state_handler.process_step_data.main_mass_balance.create_storage(
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
    gantt_chart_start_date=start_date,
)
