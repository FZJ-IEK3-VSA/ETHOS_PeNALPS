import datetime

from ethos_penalps.data_classes import Commodity, LoadType
from ethos_penalps.organizational_agents.process_chain import ProcessChain
from ethos_penalps.process_nodes.process_chain_storage import ProcessChainStorage
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.stream import BatchStreamStaticData, ContinuousStreamStaticData


def fill_forming_quenching_and_trimming_chain(
    process_chain: ProcessChain,
    sink: Sink | ProcessChainStorage,
    source: Source | ProcessChainStorage,
    steel_strip: Commodity,
    cold_blank: Commodity,
    hot_blank: Commodity,
    formed_and_quenched_part: Commodity,
    trimmed_part: Commodity,
) -> ProcessChain:
    # Add sink and source to chain
    process_chain.add_sink(sink=sink)
    process_chain.add_source(source=source)

    # Create process steps
    forming_and_quenching_machine = process_chain.create_process_step(
        name="Forming Quenching"
    )
    trimming_machine = process_chain.create_process_step(name="Trimming")

    # Create process state petri nets
    # Forming and quenching
    load_press_state = forming_and_quenching_machine.process_state_handler.create_batch_input_stream_requesting_state(
        process_state_name="Load"
    )
    pressing_state = forming_and_quenching_machine.process_state_handler.create_intermediate_process_state_energy_based_on_stream_mass(
        process_state_name="Press"
    )
    cooling_state = forming_and_quenching_machine.process_state_handler.create_intermediate_process_state(
        process_state_name="Cooling"
    )
    discharge_press_state = forming_and_quenching_machine.process_state_handler.create_batch_output_stream_providing_state(
        process_state_name="Discharge"
    )
    idle_press_state = (
        forming_and_quenching_machine.process_state_handler.create_idle_process_state(
            process_state_name="Idle"
        )
    )

    # Create transitions of petri nets
    activate_load_hot_steel_strip = forming_and_quenching_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
        start_process_state=idle_press_state,
        end_process_state=load_press_state,
    )

    forming_and_quenching_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_load_hot_steel_strip
    )

    activate_pressing_state = forming_and_quenching_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
        start_process_state=load_press_state,
        end_process_state=pressing_state,
        delay=datetime.timedelta(seconds=15),
    )
    forming_and_quenching_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_pressing_state
    )
    activate_pressing_state = forming_and_quenching_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
        start_process_state=pressing_state,
        end_process_state=cooling_state,
        delay=datetime.timedelta(seconds=15),
    )
    forming_and_quenching_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_pressing_state
    )
    activate_discharge_press = forming_and_quenching_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_output_stream(
        start_process_state=cooling_state,
        end_process_state=discharge_press_state,
    )
    forming_and_quenching_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_discharge_press
    )
    activate_idle_press = forming_and_quenching_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
        start_process_state=discharge_press_state,
        end_process_state=idle_press_state,
    )
    forming_and_quenching_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_idle_press
    )
    # Trimming
    load_trimmer_state = trimming_machine.process_state_handler.create_batch_input_stream_requesting_state(
        process_state_name="Load"
    )
    trimming_state = trimming_machine.process_state_handler.create_intermediate_process_state_energy_based_on_stream_mass(
        process_state_name="Trimmer"
    )
    discharge_trimmer_state = trimming_machine.process_state_handler.create_batch_output_stream_providing_state(
        process_state_name="Discharge"
    )

    idle_trimmer_state = (
        trimming_machine.process_state_handler.create_idle_process_state(
            process_state_name="Idle"
        )
    )

    # Create transitions of petri nets
    # Furnace States
    activate_trimmer_load_state = trimming_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
        start_process_state=idle_trimmer_state,
        end_process_state=load_trimmer_state,
    )

    trimming_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_trimmer_load_state
    )

    activate_pressing_state = trimming_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
        start_process_state=load_trimmer_state,
        end_process_state=trimming_state,
        delay=datetime.timedelta(seconds=30),
    )

    trimming_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_pressing_state
    )
    activate_discharge_press = trimming_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_output_stream(
        start_process_state=trimming_state,
        end_process_state=discharge_trimmer_state,
    )
    trimming_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_discharge_press
    )
    activate_idle_press = trimming_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
        start_process_state=discharge_trimmer_state,
        end_process_state=idle_press_state,
    )
    trimming_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_idle_press
    )

    # Streams
    forming_input_stream = process_chain.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=source.name,
            end_process_step_name=forming_and_quenching_machine.name,
            commodity=hot_blank,
            maximum_batch_mass_value=0.006,
            delay=datetime.timedelta(seconds=6),
        )
    )

    forming_output_stream = process_chain.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=forming_and_quenching_machine.name,
            end_process_step_name=trimming_machine.name,
            commodity=formed_and_quenched_part,
            maximum_batch_mass_value=0.006,
            delay=datetime.timedelta(seconds=6),
        )
    )
    trimmer_output_stream = process_chain.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=trimming_machine.name,
            end_process_step_name=sink.name,
            commodity=trimmed_part,
            maximum_batch_mass_value=0.006,
            delay=datetime.timedelta(seconds=6),
        )
    )

    # Add energy data

    electricity_load = LoadType(name="Electricity")
    natural_gas_load = LoadType(name="Natural Gas")
    other_fuels_load = LoadType(name="Other Fuels")

    # Electricity demand MJ/t

    forming_electricity = 1871.98
    trimming_electricity = 198.61

    pressing_state.create_process_state_energy_data_based_on_stream_mass(
        specific_energy_demand=forming_electricity,
        load_type=electricity_load,
        stream=forming_input_stream,
    )
    trimming_state.create_process_state_energy_data_based_on_stream_mass(
        specific_energy_demand=trimming_electricity,
        load_type=electricity_load,
        stream=forming_output_stream,
    )

    # Create mass balances in process steps (required)
    forming_and_quenching_machine.create_main_mass_balance(
        commodity=formed_and_quenched_part,
        input_to_output_conversion_factor=1,
        main_input_stream=forming_input_stream,
        main_output_stream=forming_output_stream,
    )
    trimming_machine.create_main_mass_balance(
        input_to_output_conversion_factor=1,
        main_input_stream=forming_output_stream,
        main_output_stream=trimmer_output_stream,
        commodity=trimmed_part,
    )

    # Add internal storages (required)
    forming_and_quenching_machine.process_state_handler.process_step_data.main_mass_balance.create_storage(
        current_storage_level=0
    )
    trimming_machine.process_state_handler.process_step_data.main_mass_balance.create_storage(
        current_storage_level=0
    )

    # Add streams to sinks and sources
    source.add_output_stream(
        output_stream=forming_input_stream,
        process_chain_identifier=process_chain.process_chain_identifier,
    )
    sink.add_input_stream(
        input_stream=trimmer_output_stream,
        process_chain_identifier=process_chain.process_chain_identifier,
    )

    return process_chain
