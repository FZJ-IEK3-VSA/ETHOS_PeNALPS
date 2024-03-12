import datetime

from ethos_penalps.data_classes import Commodity, LoadType
from ethos_penalps.process_chain import ProcessChain
from ethos_penalps.process_nodes.process_chain_storage import ProcessChainStorage
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.stream import BatchStreamStaticData, ContinuousStreamStaticData


def fill_cutting_and_heating_chain(
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
    coil_cutter = process_chain.create_process_step(name="Coil Cutter")
    roller_hearth_furnace = process_chain.create_process_step(
        name="Roller Hearth Furnace"
    )

    # Create process state petri nets
    # Coil cutter
    load_steel_strip = (
        coil_cutter.process_state_handler.create_batch_input_stream_requesting_state(
            process_state_name="Load"
        )
    )
    cut_steel_strip = coil_cutter.process_state_handler.create_intermediate_process_state_energy_based_on_stream_mass(
        process_state_name="Cut"
    )
    discharge_strip = (
        coil_cutter.process_state_handler.create_batch_output_stream_providing_state(
            process_state_name="Discharge"
        )
    )

    idle_cutter = coil_cutter.process_state_handler.create_idle_process_state(
        process_state_name="Idle"
    )

    # Create transitions of petri nets
    activate_load_steel_strip = coil_cutter.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
        start_process_state=idle_cutter,
        end_process_state=load_steel_strip,
    )
    coil_cutter.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_load_steel_strip
    )

    activate_cut_steel_strip = coil_cutter.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
        start_process_state=load_steel_strip,
        end_process_state=cut_steel_strip,
        delay=datetime.timedelta(seconds=10),
    )
    coil_cutter.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_cut_steel_strip
    )
    activate_discharge_cut_steel = coil_cutter.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_output_stream(
        start_process_state=cut_steel_strip,
        end_process_state=discharge_strip,
    )
    coil_cutter.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_discharge_cut_steel
    )
    activate_idle_cutter = coil_cutter.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
        start_process_state=discharge_strip,
        end_process_state=idle_cutter,
    )
    coil_cutter.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_idle_cutter
    )

    # Create Petri Net of Heating
    furnace_heating_state = roller_hearth_furnace.process_state_handler.create_state_for_parallel_input_and_output_stream_with_storage(
        process_state_name="Heating"
    )
    idle_furnace = (
        roller_hearth_furnace.process_state_handler.create_idle_process_state(
            process_state_name="Idle"
        )
    )

    activate_step_1_2 = roller_hearth_furnace.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
        start_process_state=furnace_heating_state,
        end_process_state=idle_furnace,
    )
    roller_hearth_furnace.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_step_1_2
    )
    deactivate_step_1_2 = roller_hearth_furnace.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
        start_process_state=idle_furnace,
        end_process_state=furnace_heating_state,
    )
    roller_hearth_furnace.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=deactivate_step_1_2
    )

    # Create Streams

    steel_strip_stream = process_chain.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=source.name,
            end_process_step_name=coil_cutter.name,
            commodity=steel_strip,
            maximum_batch_mass_value=0.006,
            delay=datetime.timedelta(seconds=5),
        )
    )

    cut_steel_stream = process_chain.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=coil_cutter.name,
            end_process_step_name=roller_hearth_furnace.name,
            commodity=cold_blank,
            maximum_batch_mass_value=0.006,
            delay=datetime.timedelta(seconds=5),
        )
    )
    heated_blank_stream = process_chain.stream_handler.create_continuous_stream(
        continuous_stream_static_data=ContinuousStreamStaticData(
            start_process_step_name=roller_hearth_furnace.name,
            end_process_step_name=sink.name,
            commodity=hot_blank,
            maximum_operation_rate=0.5267,
        )
    )

    # Add Energy Data

    # energy demands MJ/t
    blanking_electricity = 374.396
    heating_electricity = 198.61

    electricity_load = LoadType(name="Electricity")
    natural_gas_load = LoadType(name="Natural Gas")
    other_fuels_load = LoadType(name="Other Fuels")

    cut_steel_strip.create_process_state_energy_data_based_on_stream_mass(
        specific_energy_demand=blanking_electricity,
        load_type=electricity_load,
        stream=steel_strip_stream,
    )

    heated_blank_stream.create_stream_energy_data(
        specific_energy_demand=heating_electricity,
        load_type=electricity_load,
    )

    # Create Mass Balances in Process Steps (Required)
    coil_cutter.create_main_mass_balance(
        commodity=cold_blank,
        input_to_output_conversion_factor=1,
        main_input_stream=steel_strip_stream,
        main_output_stream=cut_steel_stream,
    )
    roller_hearth_furnace.create_main_mass_balance(
        input_to_output_conversion_factor=1,
        main_input_stream=cut_steel_stream,
        main_output_stream=heated_blank_stream,
        commodity=hot_blank,
    )

    # Add Internal Storages (Required)
    coil_cutter.process_state_handler.process_step_data.main_mass_balance.create_storage(
        current_storage_level=0
    )
    roller_hearth_furnace.process_state_handler.process_step_data.main_mass_balance.create_storage(
        current_storage_level=0
    )

    # Add Streams to Sinks and Sources
    source.add_output_stream(
        output_stream=steel_strip_stream,
        process_chain_identifier=process_chain.process_chain_identifier,
    )
    sink.add_input_stream(
        input_stream=heated_blank_stream,
        process_chain_identifier=process_chain.process_chain_identifier,
    )

    return process_chain
