import datetime
import logging

from ethos_penalps.data_classes import Commodity, LoadType
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.organizational_agents.enterprise import Enterprise
from ethos_penalps.organizational_agents.process_chain import ProcessChain
from ethos_penalps.process_nodes.process_chain_storage import ProcessChainStorage
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.stream import BatchStreamStaticData, ContinuousStreamStaticData
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger


def fill_blending_process_chain(
    process_chain: ProcessChain,
    raw_commodity: Commodity,
    cooked_commodity: Commodity,
    uncooked_storage: ProcessChainStorage,
    raw_goods_source: Source,
    process_step_name: str,
):

    # Create all sources, sinks and network level storages

    # Create Process nodes
    blender_step = process_chain.create_process_step(name=process_step_name)

    # Streams
    ## Process Chain 1
    raw_materials_to_cooking_stream = process_chain.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=raw_goods_source.name,
            end_process_step_name=blender_step.name,
            delay=datetime.timedelta(minutes=1),
            commodity=raw_commodity,
            maximum_batch_mass_value=0.00065,
        )
    )
    cooking_to_sink_stream = process_chain.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=blender_step.name,
            end_process_step_name=uncooked_storage.name,
            delay=datetime.timedelta(minutes=1),
            commodity=cooked_commodity,
            maximum_batch_mass_value=0.00065,
        )
    )

    # Add streams to sinks and sources
    raw_goods_source.add_output_stream(
        output_stream=raw_materials_to_cooking_stream,
        process_chain_identifier=process_chain.process_chain_identifier,
    )
    uncooked_storage.add_input_stream(
        input_stream=cooking_to_sink_stream,
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

    idle_state = blender_step.process_state_handler.create_idle_process_state(
        process_state_name="Idle"
    )
    fill_raw_materials_state = (
        blender_step.process_state_handler.create_batch_input_stream_requesting_state(
            process_state_name="Fill raw materials"
        )
    )

    blender_state = blender_step.process_state_handler.create_intermediate_process_state_energy_based_on_stream_mass(
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
        end_process_state=idle_state,
    )
    blender_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_not_blending
    )

    activate_filling_blender = blender_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
        start_process_state=idle_state,
        end_process_state=fill_raw_materials_state,
    )

    blender_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_filling_blender
    )

    activate_blender = blender_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
        start_process_state=fill_raw_materials_state,
        end_process_state=blender_state,
        delay=datetime.timedelta(minutes=5),
    )

    blender_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_blender
    )

    activate_discharging_blender = blender_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_output_stream(
        start_process_state=blender_state,
        end_process_state=discharge_goods_state_blender,
    )
    blender_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_discharging_blender
    )

    electricity_load = LoadType(name="Electricity")
    blender_state.create_process_state_energy_data_based_on_stream_mass(
        specific_energy_demand=600,
        load_type=electricity_load,
        stream=raw_materials_to_cooking_stream,
    )

    # Mass balances
    blender_step.create_main_mass_balance(
        commodity=cooked_commodity,
        input_to_output_conversion_factor=1,
        main_input_stream=raw_materials_to_cooking_stream,
        main_output_stream=cooking_to_sink_stream,
    )

    # Add internal storages (required)
    blender_step.process_state_handler.process_step_data.main_mass_balance.create_storage(
        current_storage_level=0
    )
