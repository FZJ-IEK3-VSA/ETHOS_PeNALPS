import datetime
from ethos_penalps.time_data import TimeData
from ethos_penalps.process_chain import ProcessChain
from ethos_penalps.enterprise import Enterprise

from ethos_penalps.order_generator import (
    OrderGenerator,
    WorkTimeConfigurator,
    one_shift_24_hours,
    no_weekends_two_shift_generator,
    no_weekends_one_shift_generator,
    all_day_3_shift_operation,
)
from ethos_penalps.data_classes import LoadType, LoadProfileEntry
from ethos_penalps.data_classes import Commodity
from ethos_penalps.stream import (
    ContinuousStream,
    ContinuousStreamStaticData,
    BatchStreamStaticData,
)


from ethos_penalps.post_processing.enterprise_graph_for_failed_run import (
    GraphVisualization,
)

from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.debugging_information import NodeOperationViewer
from ethos_penalps.post_processing.report_generator.process_chain_report_generator import (
    ResultPathGenerator,
)

from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source


def fill_toffee_preparation_chain_2(
    process_chain: ProcessChain,
    cooled_toffee_sink: Sink,
    raw_toffee_source: Source,
    electricity_load: LoadType,
    natural_gas_load: LoadType,
) -> ProcessChain:
    # Electricity energy demand MJ/ton
    input_stream_electricity = 7.56
    mixing_energy_electricity = 90.72
    cooking_energy_electricity = 30.24
    cooling_energy_electricity = 15.12
    output_stream_electricity = 7.56

    # Natural gas energy demand MJ/ton
    cooking_energy_demand_natural_gas = 1250

    # Process nodes
    batch_input_time = datetime.timedelta(minutes=2)
    batch_output_time = datetime.timedelta(minutes=2)
    mixing_time = datetime.timedelta(minutes=4)
    cooking_time = datetime.timedelta(minutes=10)
    cooling_time = datetime.timedelta(minutes=2)

    process_chain.add_sink(sink=cooled_toffee_sink)
    process_chain.add_source(source=raw_toffee_source)
    toffee_machine = process_chain.create_process_step(name="Toffee Machine 2")
    ## Cold mill process state switches
    """
    Target state: idle ->   create_process_state_switch_at_next_discrete_event
    Target state: Conti input ->   create_process_state_switch_at_input_stream
    Target state: Conti input ->   create_process_state_switch_at_output_stream
    """
    # States and switches for Continuous Caster
    ## States

    filling_state = (
        toffee_machine.process_state_handler.create_batch_input_stream_requesting_state(
            process_state_name="Filling"
        )
    )
    mixing_state = toffee_machine.process_state_handler.create_intermediate_process_state_energy_based_on_stream_mass(
        process_state_name="Mixing"
    )
    cooking_state = toffee_machine.process_state_handler.create_intermediate_process_state_energy_based_on_stream_mass(
        process_state_name="Cooking"
    )
    cooling_state = (
        toffee_machine.process_state_handler.create_intermediate_process_state(
            process_state_name="Cooling"
        )
    )
    discharge_state = (
        toffee_machine.process_state_handler.create_batch_output_stream_providing_state(
            process_state_name="Discharge"
        )
    )

    idle_state = toffee_machine.process_state_handler.create_idle_process_state(
        process_state_name="Idle"
    )

    ## Switches

    activate_filling = toffee_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
        start_process_state=idle_state,
        end_process_state=filling_state,
    )
    toffee_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_filling
    )
    activate_mixing = toffee_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
        delay=mixing_time,
        start_process_state=filling_state,
        end_process_state=mixing_state,
    )
    toffee_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_mixing
    )
    activate_cooking = toffee_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
        delay=cooking_time,
        start_process_state=mixing_state,
        end_process_state=cooking_state,
    )
    toffee_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_cooking
    )
    activate_cooling = toffee_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
        delay=cooling_time,
        start_process_state=cooking_state,
        end_process_state=cooling_state,
    )
    toffee_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_cooling
    )
    activate_discharge_cooling = toffee_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_output_stream(
        start_process_state=cooling_state,
        end_process_state=discharge_state,
    )
    toffee_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_discharge_cooling
    )
    activate_discharge_cooling = toffee_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
        start_process_state=discharge_state,
        end_process_state=idle_state,
    )
    toffee_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_discharge_cooling
    )
    # Streams

    toffee_input_stream = process_chain.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=raw_toffee_source.name,
            end_process_step_name=toffee_machine.name,
            delay=batch_input_time,
            commodity=raw_toffee_source.commodity,
            maximum_batch_mass_value=0.1,
            name_to_display="Input Toffee Machine 2",
        )
    )
    toffee_output_stream = process_chain.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=toffee_machine.name,
            end_process_step_name=cooled_toffee_sink.name,
            delay=batch_output_time,
            commodity=cooled_toffee_sink.commodity,
            maximum_batch_mass_value=0.1,
            name_to_display="Output Toffee Machine 2",
        )
    )

    toffee_input_stream.create_stream_energy_data(
        specific_energy_demand=input_stream_electricity, load_type=electricity_load
    )
    toffee_output_stream.create_stream_energy_data(
        specific_energy_demand=output_stream_electricity, load_type=electricity_load
    )
    mixing_state.create_process_state_energy_data_based_on_stream_mass(
        specific_energy_demand=mixing_energy_electricity,
        load_type=electricity_load,
        stream=toffee_input_stream,
    )

    cooking_state.create_process_state_energy_data_based_on_stream_mass(
        specific_energy_demand=cooking_energy_electricity,
        load_type=natural_gas_load,
        stream=toffee_input_stream,
    )
    cooking_state.create_process_state_energy_data_based_on_stream_mass(
        specific_energy_demand=cooking_energy_demand_natural_gas,
        load_type=natural_gas_load,
        stream=toffee_input_stream,
    )
    cooling_state.create_process_state_energy_data_based_on_stream_mass(
        specific_energy_demand=cooling_energy_electricity,
        load_type=electricity_load,
        stream=toffee_input_stream,
    )

    # Mass balances
    toffee_machine.create_main_mass_balance(
        commodity=cooled_toffee_sink.commodity,
        input_to_output_conversion_factor=1,
        main_input_stream=toffee_input_stream,
        main_output_stream=toffee_output_stream,
    )

    # Add storages
    toffee_machine.process_state_handler.process_step_data.main_mass_balance.create_storage(
        current_storage_level=0
    )

    #
    raw_toffee_source.add_output_stream(
        output_stream=toffee_input_stream,
        process_chain_identifier=process_chain.process_chain_identifier,
    )

    cooled_toffee_sink.add_input_stream(
        input_stream=toffee_output_stream,
        process_chain_identifier=process_chain.process_chain_identifier,
    )
    return process_chain
