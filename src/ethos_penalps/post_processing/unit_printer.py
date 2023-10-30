import astropy.units


class UnitPrinter:
    def __init__(self) -> None:
        self.base_energy_unit = astropy.units.MJ
        self.base_power_unit = astropy.units.MW

    def compress_energy_units(
        self, input_energy_value: float, input_energy_unit: astropy.units
    ) -> astropy.units.quantity:
        input_quantity = input_energy_value * input_energy_unit
        # index_in_list = self.list_of_power_prefixes.index(value=input_energy_unit)
        energy_in_joule = input_quantity.to(astropy.units.J)
        energy_in_joule_float = float(energy_in_joule / astropy.units.J)

        if energy_in_joule_float < 10**3:
            output_quantity = energy_in_joule
        elif energy_in_joule_float >= 10**3 and energy_in_joule_float < 10**6:
            output_quantity = energy_in_joule.to(astropy.units.kJ)
        elif energy_in_joule_float >= 10**6 and energy_in_joule_float < 10**9:
            output_quantity = energy_in_joule.to(astropy.units.MJ)
        elif energy_in_joule_float >= 10**9 and energy_in_joule_float < 10**12:
            output_quantity = energy_in_joule.to(astropy.units.GJ)
        elif energy_in_joule_float >= 10**12 and energy_in_joule_float < 10**15:
            output_quantity = energy_in_joule.to(astropy.units.TJ)
        elif energy_in_joule_float >= 10**15:
            output_quantity = energy_in_joule.to(astropy.units.PJ)
        return output_quantity

    def compress_power_units(
        self, input_power_value: float, input_power_unit: astropy.units
    ) -> astropy.units.quantity:
        input_quantity = input_power_value * input_power_unit
        # index_in_list = self.list_of_power_prefixes.index(value=input_energy_unit)
        power_in_watt = input_quantity.to(astropy.units.W)
        power_in_watt_float = float(power_in_watt / astropy.units.W)
        if power_in_watt_float < 10**3:
            output_quantity = power_in_watt
        elif power_in_watt_float >= 10**3 and power_in_watt_float < 10**6:
            output_quantity = power_in_watt.to(astropy.units.kW)
        elif power_in_watt_float >= 10**6 and power_in_watt_float < 10**9:
            output_quantity = power_in_watt.to(astropy.units.MW)
        elif power_in_watt_float >= 10**9 and power_in_watt_float < 10**12:
            output_quantity = power_in_watt.to(astropy.units.GW)
        elif power_in_watt_float >= 10**12 and power_in_watt_float < 10**15:
            output_quantity = power_in_watt.to(astropy.units.TW)
        elif power_in_watt_float >= 10**15:
            output_quantity = power_in_watt.to(astropy.units.PW)

        return output_quantity

    def get_compressed_power_float_value(
        self, input_power_value: float, input_power_unit: astropy.units
    ) -> astropy.units.quantity:
        input_quantity = input_power_value * input_power_unit
        # index_in_list = self.list_of_power_prefixes.index(value=input_energy_unit)
        power_in_watt = input_quantity.to(astropy.units.W)
        power_in_watt_float = float(power_in_watt / astropy.units.W)
        if power_in_watt_float < 10**3:
            output_quantity = power_in_watt
            output_float = float(output_quantity / astropy.units.W)
        elif power_in_watt_float >= 10**3 and power_in_watt_float < 10**6:
            output_quantity = power_in_watt.to(astropy.units.kW)
            output_float = float(output_quantity / astropy.units.kW)
        elif power_in_watt_float >= 10**6 and power_in_watt_float < 10**9:
            output_quantity = power_in_watt.to(astropy.units.MW)
            output_float = float(output_quantity / astropy.units.MW)
        elif power_in_watt_float >= 10**9 and power_in_watt_float < 10**12:
            output_quantity = power_in_watt.to(astropy.units.GW)
            output_float = float(output_quantity / astropy.units.GW)
        elif power_in_watt_float >= 10**12 and power_in_watt_float < 10**15:
            output_quantity = power_in_watt.to(astropy.units.TW)
            output_float = float(output_quantity / astropy.units.TW)
        elif power_in_watt_float >= 10**15:
            output_quantity = power_in_watt.to(astropy.units.PW)
            output_float = float(output_quantity / astropy.units.PW)

        return output_float
