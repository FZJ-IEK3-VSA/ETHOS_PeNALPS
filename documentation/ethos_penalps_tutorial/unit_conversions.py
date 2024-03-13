from ethos_penalps.utilities.units import Units

# The specific energy demand to heat potatoes
meter_quant = (0.15 * Units.unit_registry.Unit("kWh")) / (
    650 * Units.unit_registry.Unit("gram")
)
print(
    "The total specific energy demand to heat the potatoes is ",
    meter_quant.to("MJ/metric_ton"),
    " MJ/metric_ton",
)


energy_in_6_minutes_full_power_heating = (
    2000 * Units.unit_registry.Unit("W") * 6 * Units.unit_registry.Unit("minutes")
)
print(
    "In 6 minute full power heating ",
    energy_in_6_minutes_full_power_heating.to("kWh"),
    " kWh would be required",
)

# Determine the required energy to heat water from 20°C to 100°C
cp_water = 4.2 * Units.unit_registry.Unit("kJ/(kg*K)")
energy_water_20_to_100_degree = (
    650
    * Units.unit_registry.Unit("gram")
    * 80
    * Units.unit_registry.Unit("K")
    * cp_water
)


# Determine time until the 100°C is reached using a  2000W power source
print(
    "The energy to heat 650 gram of water and potatoes to is: ",
    energy_water_20_to_100_degree.to("kWh"),
    " kWh",
)
time = energy_water_20_to_100_degree / (2000 * Units.unit_registry.Unit("W"))
print("Time required to heat to 100°C", time.to("minute"))

total_cooking_energy = 0.15 * Units.unit_registry.Unit("kWh")

#
specific_energy_heating_state = (energy_water_20_to_100_degree) / (
    650 * Units.unit_registry.Unit("gram")
)
print(
    "Specific heat demand heating state",
    specific_energy_heating_state.to("MJ/t"),
    " MJ/t",
)

specific_energy_hold_temperature_state = (
    total_cooking_energy - energy_water_20_to_100_degree
) / (650 * Units.unit_registry.Unit("gram"))
print(
    "Specific heat demand hold temperature",
    specific_energy_hold_temperature_state.to("MJ/t"),
)
total_energy_demand_during_hold_temperature_state = (
    specific_energy_hold_temperature_state * 650 * Units.unit_registry.Unit("gram")
)
print(
    "Total energy demand hold temperature state: ",
    total_energy_demand_during_hold_temperature_state.to("kWh"),
)

# Blender energy demand
specific_energy_blending_state = (
    1300 * Units.unit_registry.Unit("W") * 5 * Units.unit_registry.Unit("minutes")
) / (650 * Units.unit_registry.Unit("gram"))
print(
    "Specific energy demand blending state", specific_energy_blending_state.to("MJ/t")
)
