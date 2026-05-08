import cProfile
import datetime
import logging

from ethos_penalps.data_classes import (
    Commodity,
    LoadType,
    OrderDistributorProcessingType,
)
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.organizational_agents.enterprise import Enterprise
from ethos_penalps.post_processing.report_generator.report_options import (
    standard_simulation_report,
)
from ethos_penalps.stream import BatchStreamStaticData, ContinuousStreamStaticData
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger


def define_and_start_simulation():
    profiler = cProfile.Profile()
    profiler.enable()

    start_time = datetime.datetime.now()
    logger = PeNALPSLogger.get_human_readable_logger(logging.INFO)

    logger = PeNALPSLogger.get_logger_to_create_table()
    logger.debug("Definition of the EAF plant begins")

    output_commodity = Commodity(name="Continuous product")
    input_commodity = Commodity(name="Batch educt")

    start_date = datetime.datetime(2022, 1, 2, hour=23)
    end_date = datetime.datetime(2022, 1, 3)
    time_data = TimeData(
        global_start_date=start_date,
        global_end_date=end_date,
    )
    # # Orders

    # Create all order for the simulation
    order_generator = NOrderGenerator(
        commodity=output_commodity,
        mass_per_order=300,
        production_deadline=end_date,
        number_of_orders=2,
    )

    order_collection = order_generator.create_n_order_collection()
    # Enterprise structure
    time_data = TimeData(
        global_start_date=start_date,
        global_end_date=end_date,
    )
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
        order_processing_type=OrderDistributorProcessingType.ORDER_TO_CHAIN_SPLITTER,
    )
    source = network_level.create_main_source(
        name="Source",
        commodity=input_commodity,
    )

    # Create first process chain

    process_chain_1 = network_level.create_process_chain(process_chain_name="Process Chain 1")
    process_chain_2 = network_level.create_process_chain(process_chain_name="Process Chain 2")
    # Add sources and sinks to process chain
    process_chain_1.add_sink(sink=sink, split_factor=0.5)
    process_chain_1.add_source(source=source)
    process_chain_2.add_sink(sink=sink, split_factor=0.5)
    process_chain_2.add_source(source=source)
    process_step_1 = process_chain_1.create_process_step(name="Batch to batch step 1")
    process_step_2 = process_chain_2.create_process_step(name="Batch to batch step 2")
    """ Each process state must have at least the following:
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

    batch_idle_state_1 = process_step_1.process_state_handler.create_idle_process_state(
        process_state_name="Waiting process step"
    )
    batch_input_state_1 = process_step_1.process_state_handler.create_batch_input_stream_requesting_state(
        process_state_name="Batch input state"
    )
    batch_output_state_1 = process_step_1.process_state_handler.create_batch_output_stream_providing_state(
        process_state_name="Batch output state"
    )

    ##

    batch_idle_state_2 = process_step_2.process_state_handler.create_idle_process_state(
        process_state_name="Waiting process step"
    )
    batch_input_state_2 = process_step_2.process_state_handler.create_batch_input_stream_requesting_state(
        process_state_name="Batch input state"
    )
    batch_output_state_2 = process_step_2.process_state_handler.create_batch_output_stream_providing_state(
        process_state_name="Batch output state"
    )

    ## Cold mill process state switches
    """
    Target state: idle ->   create_process_state_switch_at_next_discrete_event
    Target state: Conti input ->   create_process_state_switch_at_input_stream
    Target state: Conti input ->   create_process_state_switch_at_output_stream
    """
    idle_state_activation_1 = process_step_1.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
        start_process_state=batch_output_state_1,
        end_process_state=batch_idle_state_1,
    )
    process_step_1.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=idle_state_activation_1
    )
    batch_input_request_state_switch_1 = process_step_1.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
        start_process_state=batch_idle_state_1,
        end_process_state=batch_input_state_1,
    )

    process_step_1.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=batch_input_request_state_switch_1
    )

    output_providing_activation_1 = process_step_1.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_output_stream(
        start_process_state=batch_input_state_1,
        end_process_state=batch_output_state_1,
    )
    process_step_1.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=output_providing_activation_1
    )
    ##

    idle_state_activation_2 = process_step_2.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
        start_process_state=batch_output_state_2,
        end_process_state=batch_idle_state_2,
    )
    process_step_2.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=idle_state_activation_2
    )
    batch_input_request_state_switch_2 = process_step_2.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
        start_process_state=batch_idle_state_2,
        end_process_state=batch_input_state_2,
    )

    process_step_2.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=batch_input_request_state_switch_2
    )

    output_providing_activation_2 = process_step_2.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_output_stream(
        start_process_state=batch_input_state_2,
        end_process_state=batch_output_state_2,
    )
    process_step_2.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=output_providing_activation_2
    )

    # Streams

    source_to_process_step_1 = process_chain_1.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=source.name,
            end_process_step_name=process_step_1.name,
            delay=datetime.timedelta(minutes=15),
            commodity=input_commodity,
            maximum_batch_mass_value=300,
        )
    )
    process_step_to_sink_1 = process_chain_1.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=process_step_1.name,
            end_process_step_name=sink.name,
            delay=datetime.timedelta(minutes=20),
            commodity=output_commodity,
            maximum_batch_mass_value=300,
        )
    )
    source_to_process_step_2 = process_chain_2.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=source.name,
            end_process_step_name=process_step_2.name,
            delay=datetime.timedelta(minutes=15),
            commodity=input_commodity,
            maximum_batch_mass_value=150,
        )
    )
    process_step_to_sink_2 = process_chain_2.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=process_step_2.name,
            end_process_step_name=sink.name,
            delay=datetime.timedelta(minutes=20),
            commodity=output_commodity,
            maximum_batch_mass_value=150,
        )
    )

    electricity_load = LoadType(name="Electricity")

    process_step_to_sink_1.create_stream_energy_data(specific_energy_demand=2, load_type=electricity_load)
    source_to_process_step_1.create_stream_energy_data(specific_energy_demand=5, load_type=electricity_load)
    process_step_to_sink_2.create_stream_energy_data(specific_energy_demand=2, load_type=electricity_load)
    source_to_process_step_2.create_stream_energy_data(specific_energy_demand=5, load_type=electricity_load)

    # Mass balances
    process_step_1.create_main_mass_balance(
        commodity=output_commodity,
        input_to_output_conversion_factor=1,
        main_input_stream=source_to_process_step_1,
        main_output_stream=process_step_to_sink_1,
    )
    process_step_2.create_main_mass_balance(
        commodity=output_commodity,
        input_to_output_conversion_factor=1,
        main_input_stream=source_to_process_step_2,
        main_output_stream=process_step_to_sink_2,
    )

    # Add storages
    process_step_1.process_state_handler.process_step_data.main_mass_balance.create_storage(current_storage_level=0)
    process_step_2.process_state_handler.process_step_data.main_mass_balance.create_storage(current_storage_level=0)
    #
    source.add_output_stream(
        output_stream=source_to_process_step_1,
        process_chain_identifier=process_chain_1.process_chain_identifier,
    )
    sink.add_input_stream(
        input_stream=process_step_to_sink_1,
        process_chain_identifier=process_chain_1.process_chain_identifier,
    )
    source.add_output_stream(
        output_stream=source_to_process_step_2,
        process_chain_identifier=process_chain_2.process_chain_identifier,
    )
    sink.add_input_stream(
        input_stream=process_step_to_sink_2,
        process_chain_identifier=process_chain_2.process_chain_identifier,
    )
    # Start the simulation
    enterprise.start_simulation(number_of_iterations_in_chain=200, create_storage_entries=False)

    # Create report of the simulation results
    # enterprise.create_post_simulation_report(
    #     start_date=start_date,
    #     end_date=end_date,
    #     x_axis_time_delta=datetime.timedelta(hours=1),
    #     resample_frequency="5min",
    #     gantt_chart_end_date=end_date,
    #     gantt_chart_start_date=start_date,
    # )
    standard_simulation_report.gantt_charts.add_plot_start_and_end_time(start_time=start_date, end_time=end_date)
    standard_simulation_report.carpet_plot_options.add_time_data(
        resample_frequency="5min",
        end_date=end_date,
        start_date=start_date,
        x_axis_time_delta=datetime.timedelta(hours=1),
    )
    standard_simulation_report.gantt_charts.include_storage_gantt_charts
    standard_simulation_report.store_load_profiles_to_csv = True
    standard_simulation_report.number_of_processes_used_for_plotting = 7
    standard_simulation_report.disable_multiprocessing = True
    # standard_simulation_report.path_to_results_folder = (
    #     r"C:\Programming\ethos_penalps\examples\basic_examples\asd"
    # )
    enterprise.create_simulation_report(report_options=standard_simulation_report)
    end_time = datetime.datetime.now()
    total_simulation_time = end_time - start_time
    print("total_simulation_time: ", total_simulation_time)


if __name__ == "__main__":
    define_and_start_simulation()
