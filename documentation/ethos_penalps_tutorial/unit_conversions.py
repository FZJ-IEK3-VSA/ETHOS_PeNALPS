from ethos_penalps.utilities.units import Units

meter_quant = (0.15 * Units.unit_registry.Unit("kWh")) / (
    650 * Units.unit_registry.Unit("gram")
)
print(meter_quant.to("MJ/metric_ton"))


a = 2000 * Units.unit_registry.Unit("W") * 6 * Units.unit_registry.Unit("minutes")
print(a.to("kWh"))


cp_water = 4.2 * Units.unit_registry.Unit("kJ/(kg*K)")
energy_water = (
    650
    * Units.unit_registry.Unit("gram")
    * 80
    * Units.unit_registry.Unit("K")
    * cp_water
)

print("Energy", energy_water.to("kWh"))
time = energy_water / (2000 * Units.unit_registry.Unit("W"))
print(time.to("minute"))

energy_output = (
    0.09 * Units.unit_registry.Unit("kWh") / (650 * Units.unit_registry.Unit("gram"))
)
print(energy_output.to("MJ/t"))

energy_output = (
    0.06 * Units.unit_registry.Unit("kWh") / (650 * Units.unit_registry.Unit("gram"))
)
print(energy_output.to("MJ/t"))

# Blender energy demand
energy_output = (
    1300 * Units.unit_registry.Unit("W") * 5 * Units.unit_registry.Unit("minutes")
) / (650 * Units.unit_registry.Unit("gram"))
print(energy_output.to("MJ/t"))
