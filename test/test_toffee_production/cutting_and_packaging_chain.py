import datetime

from ethos_penalps.data_classes import Commodity, LoadType
from ethos_penalps.organizational_agents.process_chain import ProcessChain
from ethos_penalps.process_nodes.process_chain_storage import ProcessChainStorage
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.stream import BatchStreamStaticData, ContinuousStreamStaticData


def fill_cutting_and_packaging_chain(
    process_chain: ProcessChain,
    sink: Sink | ProcessChainStorage,
    source: Source | ProcessChainStorage,
    cooled_toffee: Commodity,
    cut_toffee_commodity: Commodity,
    packaged_toffee_commodity: Commodity,
    electricity_load: LoadType,
) -> ProcessChain:
    # Add sink and source to chain
    process_chain.add_sink(sink=sink)
    process_chain.add_source(source=source)

    # Create process steps
    cutting_machine = process_chain.create_process_step(name="Cutting Machine")
    packaging_machine = process_chain.create_process_step(name="Packaging Machine")

    # Create process state petri nets
    # Cutting Machine
    cutting_state = cutting_machine.process_state_handler.create_state_for_parallel_input_and_output_stream_with_storage(
        process_state_name="Continuous Cutting"
    )

    idle_state = cutting_machine.process_state_handler.create_idle_process_state(
        process_state_name="Idle State"
    )

    # Create transitions of petri nets
    activate_cutting = cutting_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
        start_process_state=cutting_state,
        end_process_state=idle_state,
    )
    cutting_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_cutting
    )
    deactivate_step_1_2 = cutting_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
        start_process_state=idle_state,
        end_process_state=cutting_state,
    )
    cutting_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=deactivate_step_1_2
    )

    # Create process state petri net
    # Packaging machine
    packing_state = packaging_machine.process_state_handler.create_state_for_parallel_input_and_output_stream_with_storage(
        process_state_name="Packaging"
    )

    idle_state_packing = (
        packaging_machine.process_state_handler.create_idle_process_state(
            process_state_name="Idle"
        )
    )

    # Create transitions of petri net
    activate_step_1_2 = packaging_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
        start_process_state=packing_state,
        end_process_state=idle_state_packing,
    )
    packaging_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=activate_step_1_2
    )
    deactivate_step_1_2 = packaging_machine.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
        start_process_state=idle_state_packing,
        end_process_state=packing_state,
    )
    packaging_machine.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
        process_state_switch=deactivate_step_1_2
    )

    # Streams
    cold_toffee_storage_to_cutter = process_chain.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=source.name,
            end_process_step_name=cutting_machine.name,
            delay=datetime.timedelta(minutes=0.5),
            commodity=source.commodity,
            maximum_batch_mass_value=0.13,
            name_to_display="Input Stream Cutter",
        )
    )
    cutter_to_packaging = process_chain.stream_handler.create_continuous_stream(
        continuous_stream_static_data=ContinuousStreamStaticData(
            start_process_step_name=cutting_machine.name,
            end_process_step_name=packaging_machine.name,
            commodity=sink.commodity,
            maximum_operation_rate=0.78,
            name_to_display="Output Stream Cutter",
        )
    )
    packaging_to_sink = process_chain.stream_handler.create_continuous_stream(
        continuous_stream_static_data=ContinuousStreamStaticData(
            start_process_step_name=packaging_machine.name,
            end_process_step_name=sink.name,
            commodity=sink.commodity,
            maximum_operation_rate=0.78,
            name_to_display="Output Stream Packaging",
        )
    )

    # Add energy data
    # Electricity demand MJ/ton
    conveyor_belt_electricity = 1.3846
    packaging_machine_electricity = 6.2307
    cutting_machine_electricity = 6.2307

    # All energy demands are attributed to the same stream because
    # The packaging machine, cutting machine and conveyor belt

    combined_energy_demand = (
        conveyor_belt_electricity
        + packaging_machine_electricity
        + cutting_machine_electricity
    )

    cutter_to_packaging.create_stream_energy_data(
        specific_energy_demand=combined_energy_demand,
        load_type=electricity_load,
        energy_unit="MJ",
        mass_unit="metric_ton",
    )

    # Create mass balances in process steps (required)
    cutting_machine.create_main_mass_balance(
        commodity=sink.commodity,
        input_to_output_conversion_factor=1,
        main_input_stream=cold_toffee_storage_to_cutter,
        main_output_stream=cutter_to_packaging,
    )

    # Add storages
    cutting_machine.process_state_handler.process_step_data.main_mass_balance.create_storage(
        current_storage_level=0
    )

    # Mass balances
    packaging_machine.create_main_mass_balance(
        commodity=sink.commodity,
        input_to_output_conversion_factor=1,
        main_input_stream=cutter_to_packaging,
        main_output_stream=packaging_to_sink,
    )

    # Add internal storages (required)
    packaging_machine.process_state_handler.process_step_data.main_mass_balance.create_storage(
        current_storage_level=0
    )

    # Add streams to sinks and sources
    source.add_output_stream(
        output_stream=cold_toffee_storage_to_cutter,
        process_chain_identifier=process_chain.process_chain_identifier,
    )

    sink.add_input_stream(
        input_stream=packaging_to_sink,
        process_chain_identifier=process_chain.process_chain_identifier,
    )
    return process_chain
