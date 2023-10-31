import datetime
import logging

from ethos_penalps.data_classes import Commodity, LoadType
from ethos_penalps.enterprise import Enterprise
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.stream import (
    BatchStreamStaticData,
    ContinuousStreamStaticData,
)
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_human_readable_logger(logging.INFO)

# Enterprise structure

# Set simulation time data
start_date = datetime.datetime(2022, 1, 2, hour=23)
end_date = datetime.datetime(2022, 1, 3)
time_data = TimeData(
    global_start_date=start_date,
    global_end_date=end_date,
)

# Initialize enterprise
enterprise = Enterprise(
    time_data=time_data,
)

# Create network level
network_level = enterprise.create_network_level()

input_batch_delay = datetime.timedelta(minutes=20)
output_batch_delay = datetime.timedelta(minutes=40)

# Determine all relevant commodities
batch_product = Commodity(name="Continuous product")
batch_raw_material = Commodity(name="Batch educt")


# Create all order for the simulation
order_generator = NOrderGenerator(
    commodity=batch_product,
    mass_per_order=300,
    production_deadline=end_date,
    number_of_orders=1,
)

order_collection = order_generator.create_n_order_collection()

# Create all sources, sinks and network level storages
continuous_sink = network_level.create_main_sink(
    name="Batch sink",
    commodity=batch_product,
    order_collection=order_collection,
)
batch_source = network_level.create_main_source(
    name="Batch source",
    commodity=batch_raw_material,
)

# Create first process chain

process_chain = network_level.create_process_chain(
    process_chain_name="Test process chain"
)

# Add sources and sinks to process chain
process_chain.add_sink(sink=continuous_sink)
process_chain.add_source(source=batch_source)

# Create Process nodes
batch_to_batch_step = process_chain.create_process_step(name="Batch to batch step")


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

batch_idle_state = batch_to_batch_step.process_state_handler.create_idle_process_state(
    process_state_name="Waiting process step"
)
batch_input_state = batch_to_batch_step.process_state_handler.create_batch_input_stream_requesting_state(
    process_state_name="Batch input state"
)
batch_output_state = batch_to_batch_step.process_state_handler.create_batch_output_stream_providing_state(
    process_state_name="Batch output state"
)


# Petri net transitions

idle_state_activation = batch_to_batch_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
    start_process_state=batch_output_state,
    end_process_state=batch_idle_state,
)
batch_to_batch_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=idle_state_activation
)
batch_input_request_state = batch_to_batch_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
    start_process_state=batch_idle_state,
    end_process_state=batch_input_state,
)

batch_to_batch_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=batch_input_request_state
)


output_providing_activation = batch_to_batch_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_output_stream(
    start_process_state=batch_input_state,
    end_process_state=batch_output_state,
)
batch_to_batch_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=output_providing_activation
)

# Streams
source_to_process_step = process_chain.stream_handler.create_batch_stream(
    batch_stream_static_data=BatchStreamStaticData(
        start_process_step_name=batch_source.name,
        end_process_step_name=batch_to_batch_step.name,
        delay=input_batch_delay,
        commodity=batch_raw_material,
        maximum_batch_mass_value=300,
    )
)
process_step_to_sink = process_chain.stream_handler.create_batch_stream(
    batch_stream_static_data=BatchStreamStaticData(
        start_process_step_name=batch_to_batch_step.name,
        end_process_step_name=continuous_sink.name,
        delay=output_batch_delay,
        commodity=batch_product,
        maximum_batch_mass_value=300,
    )
)


electricity_load = LoadType(name="Electricity")

process_step_to_sink.create_stream_energy_data(
    specific_energy_demand=2, load_type=electricity_load
)
source_to_process_step.create_stream_energy_data(
    specific_energy_demand=5, load_type=electricity_load
)


# Mass balances
batch_to_batch_step.create_main_mass_balance(
    commodity=batch_product,
    input_to_output_conversion_factor=1,
    main_input_stream=source_to_process_step,
    main_output_stream=process_step_to_sink,
)

# Add internal storages (required)
batch_to_batch_step.process_state_handler.process_step_data.main_mass_balance.create_storage(
    current_storage_level=0
)

# Add streams to sinks and sources
batch_source.add_output_stream(
    output_stream=source_to_process_step,
    process_chain_identifier=process_chain.process_chain_identifier,
)
continuous_sink.add_input_stream(
    input_stream=process_step_to_sink,
    process_chain_identifier=process_chain.process_chain_identifier,
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
