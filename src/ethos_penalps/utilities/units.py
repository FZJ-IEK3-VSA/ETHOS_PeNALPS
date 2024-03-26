import datetime
import numbers

import pint


class Units:
    """This object holds all the standard Units
    of the simulation and basic conversion capabilities.
    """

    unit_registry = pint.UnitRegistry(system="SI")
    unit_registry.default_format = "~"
    time_unit: pint.Unit = unit_registry.hour
    mass_unit: pint.Unit = unit_registry.metric_ton
    power_unit: pint.Unit = unit_registry.MW
    energy_unit: pint.Unit = unit_registry.MJ

    @staticmethod
    def get_unit(unit_string: str) -> pint.Unit:
        """Returns a pint unit object based on a string
        to parse the unit.

        Args:
            unit_string (str): Unit string for parsing

        Returns:
            pint.Unit: Unit object based on the parsed
                string.
        """
        return Units.unit_registry.Unit(unit_string)

    @staticmethod
    def compress_quantity(
        quantity_value: numbers.Number, unit: pint.Unit
    ) -> pint.Quantity:
        """Adapts the magnitude of the provided unit
        if necessary.

        Args:
            quantity_value (numbers.Number): Value of
                the quantity.
            unit (pint.Unit): Unit of the quantity.

        Returns:
            pint.Quantity: Quantity based on the value
                and unit provided.
        """
        output_quantity = quantity_value * unit
        output_quantity_compact = output_quantity.to_compact()
        return output_quantity_compact

    @staticmethod
    def get_value_from_quantity(quantity: pint.Quantity) -> numbers.Number:
        """Returns the value from a pint quantity

        Args:
            quantity (pint.Quantity): Quantity that contains the
                value of interest.

        Returns:
            numbers.Number: Value of the quantity provided.
        """
        return quantity.m

    @staticmethod
    def convert_energy_to_power(
        energy_value: float,
        energy_unit: str,
        time_step: datetime.timedelta,
        target_power_unit: str,
    ) -> float:
        """Converts an energy value from a LoadProfileEntry
        to an average power value.

        Args:
            energy_value (float): The energy value of the
                of the load profile that should be converted to power.
            energy_unit (str): String of the energy unit.
            time_step (datetime.timedelta): Time span in which the energy is
                provided or in demand.
            target_power_unit (str): The string of the target power unit.

        Returns:
            float: Value of the power in the target power unit.
        """

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
        """Converts a power value into a total energy
        value in the time span provided.

        Args:
            power_value (float): Average power consumption in
                the time span.
            power_unit (str): Power unit as a string.
            time_step (datetime.timedelta): Time span in which
                the power is in demand or supply.
            target_energy_unit (str): Target unit of the energy value.

        Returns:
            float: Value of energy based on the power provided.
        """

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
