import numbers
import pint


class Units:
    unit_registry = pint.UnitRegistry(system="SI")
    unit_registry.default_format = "~"
    time_unit: pint.Unit = unit_registry.seconds
    mass_unit: pint.Unit = unit_registry.metric_ton
    power_unit: pint.Unit = unit_registry.watt
    energy_unit: pint.Unit = unit_registry.joule

    def get_unit(unit_string: str) -> pint.Unit:
        return Units.unit_registry.Unit(unit_string)

    def compress_quantity(
        quantity_value: numbers.Number, unit: pint.Unit
    ) -> pint.Quantity:
        output_quantity = quantity_value * unit
        output_quantity_compact = output_quantity.to_compact()
        return output_quantity_compact

    def get_value_from_quantity(quantity: pint.Quantity) -> numbers.Number:
        return quantity.m
