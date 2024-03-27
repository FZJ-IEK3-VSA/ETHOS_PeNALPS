import datetime

from ethos_penalps.data_classes import Commodity, LoadProfileEntry, LoadType
from ethos_penalps.utilities.debugging_information import NodeOperationViewer
from ethos_penalps.organizational_agents.enterprise import Enterprise

from ethos_penalps.organizational_agents.process_chain import ProcessChain
from ethos_penalps.process_nodes.process_chain_storage import ProcessChainStorage
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.stream import (
    BatchStreamStaticData,
    ContinuousStream,
    ContinuousStreamStaticData,
)
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger


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
    # # Orders

    # Process nodes
    process_chain.add_sink(sink=sink)

    process_chain.add_source(source=source)

    coil_cutter = process_chain.create_process_step(name="Coil Cutter")
    open_hearth_furnace = process_chain.create_process_step(name="Open Hearth Furnace")
    # forming_and_quenching = process_chain.create_process_step(name="Forming Quenching")
    # trimming = process_chain.create_process_step(name="Trimming")
    # Coil Cutter states
    load_steel_strip = coil_cutter.process_state_handler.create_continuous_input_stream_requesting_state(
        process_state_name="Load"
    )
    cut_steel_strip = coil_cutter.process_state_handler.create_intermediate_process_state_energy_based_on_stream_mass(
        process_state_name="Cut"
    )
    discharge_strip = coil_cutter.process_state_handler.create_continuous_output_stream_providing_state(
        process_state_name="discharge"
    )

    idle_cutter = coil_cutter.process_state_handler.create_idle_process_state(
        process_state_name="Idle"
    )
    # Switches
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

    # Furnace States
    furnace_heating_state = open_hearth_furnace.process_state_handler.create_state_for_parallel_input_and_output_stream_with_storage(
        process_state_name="Heating"
    )
    idle_furnace = open_hearth_furnace.process_state_handler.create_idle_process_state(
        process_state_name="Idle"
    )

    activate_step_1_2 = open_hearth_furnace.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
        start_process_state=furnace_heating_state,
        end_process_state=idle_furnace,
    )
    open_hearth_furnace.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_step_1_2
    )
    deactivate_step_1_2 = open_hearth_furnace.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
        start_process_state=idle_furnace,
        end_process_state=furnace_heating_state,
    )
    open_hearth_furnace.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=deactivate_step_1_2
    )

    # Streams

    steel_strip_stream = process_chain.stream_handler.create_continuous_stream(
        continuous_stream_static_data=ContinuousStreamStaticData(
            start_process_step_name=source.name,
            end_process_step_name=coil_cutter.name,
            commodity=steel_strip,
            maximum_operation_rate=200,
        )
    )

    cut_steel_stream = process_chain.stream_handler.create_continuous_stream(
        continuous_stream_static_data=ContinuousStreamStaticData(
            start_process_step_name=coil_cutter.name,
            end_process_step_name=open_hearth_furnace.name,
            commodity=cold_blank,
            maximum_operation_rate=200,
        )
    )
    heated_blank_stream = process_chain.stream_handler.create_continuous_stream(
        continuous_stream_static_data=ContinuousStreamStaticData(
            start_process_step_name=open_hearth_furnace.name,
            end_process_step_name=sink.name,
            commodity=hot_blank,
            maximum_operation_rate=200,
        )
    )

    electricity_load = LoadType(name="Electricity")
    natural_gas_load = LoadType(name="Natural Gas")
    other_fuels_load = LoadType(name="Other Fuels")

    cut_steel_strip.create_process_state_energy_data_based_on_stream_mass(
        specific_energy_demand=1260,
        load_type=electricity_load,
        stream=steel_strip_stream,
    )
    cut_steel_stream.create_stream_energy_data(
        specific_energy_demand=100, load_type=electricity_load
    )

    # Mass balances
    coil_cutter.create_main_mass_balance(
        commodity=cold_blank,
        input_to_output_conversion_factor=1,
        main_input_stream=steel_strip_stream,
        main_output_stream=cut_steel_stream,
    )
    open_hearth_furnace.create_main_mass_balance(
        input_to_output_conversion_factor=1,
        main_input_stream=cut_steel_stream,
        main_output_stream=heated_blank_stream,
        commodity=hot_blank,
    )

    # Add storages
    coil_cutter.process_state_handler.process_step_data.main_mass_balance.create_storage(
        current_storage_level=0
    )
    open_hearth_furnace.process_state_handler.process_step_data.main_mass_balance.create_storage(
        current_storage_level=0
    )
    #

    source.add_output_stream(
        output_stream=steel_strip_stream,
        process_chain_identifier=process_chain.process_chain_identifier,
    )
    sink.add_input_stream(
        input_stream=heated_blank_stream,
        process_chain_identifier=process_chain.process_chain_identifier,
    )

    return process_chain
