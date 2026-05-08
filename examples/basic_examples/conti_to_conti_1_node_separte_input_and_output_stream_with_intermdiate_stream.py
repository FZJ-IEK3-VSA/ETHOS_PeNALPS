import datetime
import logging

from typeguard import install_import_hook

install_import_hook("ethos_penalps")

from ethos_penalps.data_classes import Commodity, LoadType
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.organizational_agents.enterprise import Enterprise
from ethos_penalps.stream import BatchStreamStaticData, ContinuousStreamStaticData
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger


def define_and_start_simulation():
    logger = PeNALPSLogger.get_human_readable_logger(logging.INFO)

    # Set simulation time data
    start_date = datetime.datetime(2022, 1, 2, hour=23)
    end_date = datetime.datetime(2022, 1, 3)
    time_data = TimeData(
        global_start_date=start_date,
        global_end_date=end_date,
    )

    # Create all commodity for the simulation
    output_commodity = Commodity(name="Product")
    input_commodity = Commodity(name="Educt")

    # Create all order for the simulation
    order_generator = NOrderGenerator(
        commodity=output_commodity,
        mass_per_order=300,
        production_deadline=end_date,
        number_of_orders=1,
    )

    order_collection = order_generator.create_n_order_collection()

    # Enterprise
    enterprise = Enterprise(
        time_data=time_data,
    )

    # Create network level
    network_level = enterprise.create_network_level()

    # Create all sources, sinks and network level storages
    sink = network_level.create_main_sink(
        name="Sink",
        commodity=output_commodity,
        order_collection=order_collection,
    )
    source = network_level.create_main_source(
        name="Source",
        commodity=input_commodity,
    )

    # Create first process chain

    process_chain = network_level.create_process_chain(process_chain_name="Process Chain")

    # Add sources and sinks to process chain
    process_chain.add_sink(sink=sink)
    process_chain.add_source(source=source)
    process_step = process_chain.create_process_step(name="Batch to batch step")

    input_batch_delay = datetime.timedelta(minutes=20)
    output_batch_delay = datetime.timedelta(minutes=40)

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
    # Cold mill process states (Is assumed to be continuous currently)

    idle_state = process_step.process_state_handler.create_idle_process_state(process_state_name="Idle state")
    input_state = process_step.process_state_handler.create_continuous_input_stream_requesting_state(
        process_state_name="Input state"
    )
    intermediate_state = (
        process_step.process_state_handler.create_intermediate_process_state_energy_based_on_stream_mass(
            process_state_name="Intermediate state"
        )
    )
    output_state = process_step.process_state_handler.create_continuous_output_stream_providing_state(
        process_state_name="Output state"
    )

    ## Cold mill process state switches
    """
    Target state: idle ->   create_process_state_switch_at_next_discrete_event
    Target state: Conti input ->   create_process_state_switch_at_input_stream
    Target state: Conti input ->   create_process_state_switch_at_output_stream
    """

    idle_state_activation = process_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
        start_process_state=output_state,
        end_process_state=idle_state,
    )
    process_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=idle_state_activation
    )

    conti_input_activation = process_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
        start_process_state=idle_state, end_process_state=input_state
    )

    process_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=conti_input_activation
    )
    intermediate_activation = process_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
        start_process_state=input_state,
        end_process_state=intermediate_state,
        delay=datetime.timedelta(minutes=15),
    )
    process_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=intermediate_activation
    )
    output_providing_activation = process_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_output_stream(
        start_process_state=intermediate_state,
        end_process_state=output_state,
    )
    process_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=output_providing_activation
    )

    # Streams

    source_to_process_step = process_chain.stream_handler.create_continuous_stream(
        continuous_stream_static_data=ContinuousStreamStaticData(
            start_process_step_name=source.name,
            end_process_step_name=process_step.name,
            commodity=output_commodity,
            maximum_operation_rate=2500,
        )
    )
    process_step_to_sink = process_chain.stream_handler.create_continuous_stream(
        continuous_stream_static_data=ContinuousStreamStaticData(
            start_process_step_name=process_step.name,
            end_process_step_name=sink.name,
            commodity=input_commodity,
            maximum_operation_rate=2500,
        )
    )

    electricity_load = LoadType(name="Electricity")
    intermediate_state.create_process_state_energy_data_based_on_stream_mass(
        specific_energy_demand=5,
        load_type=electricity_load,
        stream=source_to_process_step,
    )

    process_step_to_sink.create_stream_energy_data(specific_energy_demand=2, load_type=electricity_load)
    source_to_process_step.create_stream_energy_data(specific_energy_demand=5, load_type=electricity_load)

    # Mass balances
    process_step.create_main_mass_balance(
        commodity=output_commodity,
        input_to_output_conversion_factor=1,
        main_input_stream=source_to_process_step,
        main_output_stream=process_step_to_sink,
    )

    # Add storages
    """Storage Level must be =0 currently
    """
    process_step.process_state_handler.process_step_data.main_mass_balance.create_storage(current_storage_level=0)
    #
    source.add_output_stream(
        output_stream=source_to_process_step,
        process_chain_identifier=process_chain.process_chain_identifier,
    )
    sink.add_input_stream(
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


if __name__ == "__main__":
    define_and_start_simulation()
