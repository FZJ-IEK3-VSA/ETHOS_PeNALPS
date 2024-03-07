import datetime
import numbers

import pint


class Units:
    unit_registry = pint.UnitRegistry(system="SI")
    unit_registry.default_format = "~"
    time_unit: pint.Unit = unit_registry.hour
    mass_unit: pint.Unit = unit_registry.metric_ton
    power_unit: pint.Unit = unit_registry.MW
    energy_unit: pint.Unit = unit_registry.MJ

    @staticmethod
    def get_unit(unit_string: str) -> pint.Unit:
        return Units.unit_registry.Unit(unit_string)

    @staticmethod
    def compress_quantity(
        quantity_value: numbers.Number, unit: pint.Unit
    ) -> pint.Quantity:
        output_quantity = quantity_value * unit
        output_quantity_compact = output_quantity.to_compact()
        return output_quantity_compact

    @staticmethod
    def get_value_from_quantity(quantity: pint.Quantity) -> numbers.Number:
        return quantity.m

    @staticmethod
    def convert_energy_to_power(
        energy_value: float,
        energy_unit: str,
        time_step: datetime.timedelta,
        target_power_unit: str,
    ) -> float:

        time_quantity = time_step.total_seconds() * Units.get_unit("s")
        energy_quantity = energy_value * Units.get_unit(energy_unit)
        if time_quantity == 0:
            converted_power_value = 0
        else:
            power_value = energy_quantity / time_quantity
            converted_power_quantity = power_value.to(target_power_unit)
            converted_power_value = converted_power_quantity.m
        return converted_power_value

    @staticmethod
    def convert_power_to_energy(
        power_value: float,
        power_unit: str,
        time_step: datetime.timedelta,
        target_energy_unit: str,
    ) -> float:

        time_quantity = time_step.total_seconds() * Units.get_unit("s")
        power_quantity = power_value * Units.get_unit(power_unit)
        energy_quantity = power_quantity * time_quantity
        converted_energy_quantity = energy_quantity.to(target_energy_unit)
        converted_energy_value = converted_energy_quantity.m
        return converted_energy_value


if __name__ == "__main__":
    unit_registry = pint.UnitRegistry(system="SI")

    meter_quant = (0.15 * Units.unit_registry.Unit("kWh")) / (
        650 * Units.unit_registry.Unit("gram")
    )
    print(meter_quant.to("MJ/metric_ton"))
