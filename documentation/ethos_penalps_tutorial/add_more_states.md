# Add more states

The behavior of the cooker [of the previous example](single_cooker_process_chain.md) can be modeled in greater detail by adding more states. Instead of modeling a single cooking phase two phases are implemented. One heating phase which uses the maximum power to reach the desired temperature and seconds hold temperature phase in which needs less power to hold the temperature. Additionally a cleaning phase is added after the discharge phase.

```
idle_state = process_step.process_state_handler.create_idle_process_state(
    process_state_name="Idle"
)
fill_raw_materials_state = (
    process_step.process_state_handler.create_batch_input_stream_requesting_state(
        process_state_name="Fill raw materials"
    )
)

heating_state = process_step.process_state_handler.create_intermediate_process_state_energy_based_on_stream_mass(
    process_state_name="Heating"
)

hold_temperature_state = process_step.process_state_handler.create_intermediate_process_state_energy_based_on_stream_mass(
    process_state_name="Hold Temperature"
)

discharge_goods_state = (
    process_step.process_state_handler.create_batch_output_stream_providing_state(
        process_state_name="Discharge"
    )
)

cleaning_state = process_step.process_state_handler.create_intermediate_process_state_energy_based_on_stream_mass(
    process_state_name="Cleaning"
)
```

Each of the new states is connected with an additional process state switch delay. 

```
activate_not_cooking = process_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_next_discrete_event(
    start_process_state=cleaning_state,
    end_process_state=idle_state,
)
process_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_not_cooking
)

activate_filling = process_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_input_stream(
    start_process_state=idle_state,
    end_process_state=fill_raw_materials_state,
)

process_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_filling
)

activate_heating = process_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
    start_process_state=fill_raw_materials_state,
    end_process_state=heating_state,
    delay=datetime.timedelta(minutes=15),
)

process_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_heating
)
activate_hold_temperature = process_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
    start_process_state=heating_state,
    end_process_state=hold_temperature_state,
    delay=datetime.timedelta(minutes=15),
)

process_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_hold_temperature
)


activate_discharging = process_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_at_output_stream(
    start_process_state=hold_temperature_state,
    end_process_state=discharge_goods_state,
)
process_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_discharging
)
activate_hold_temperature = process_step.process_state_handler.process_state_switch_selector_handler.process_state_switch_handler.create_process_state_switch_delay(
    start_process_state=discharge_goods_state,
    end_process_state=cleaning_state,
    delay=datetime.timedelta(minutes=3),
)

process_step.process_state_handler.process_state_switch_selector_handler.create_single_choice_selector(
    process_state_switch=activate_hold_temperature
)

```

Now the the energy data must be updated to model the different energy usage in both states. In this case it is assumed that no energy is used during the cleaning.

```
electricity_load = LoadType(name="Electricity")
heating_state.create_process_state_energy_data_based_on_stream_mass(
    specific_energy_demand=1.8,
    load_type=electricity_load,
    stream=raw_materials_to_cooking_stream,
)
hold_temperature_state.create_process_state_energy_data_based_on_stream_mass(
    specific_energy_demand=1.8,
    load_type=electricity_load,
    stream=raw_materials_to_cooking_stream,
)
```
