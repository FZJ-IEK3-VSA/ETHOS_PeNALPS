import datetime
from ethos_penalps.utilities.units import Units


def test_convert_megawatt_to_kilowatt():
    mw_1 = 2 * Units.get_unit(unit_string="MW")
    kw_target = 2000
    kw_converted = mw_1.to("kW").m
    assert kw_target == kw_converted


def test_convert_ton_metric_to_kg():
    mass_ton = 2 * Units.get_unit(unit_string="metric_ton")
    kg_target = 2000
    mass_converted = mass_ton.to("kg").m
    assert kg_target == mass_converted


def test_convert_energy_in_time_step_to_power():
    converted_power_value = Units.convert_energy_to_power(
        energy_value=60,
        energy_unit="MJ",
        time_step=datetime.timedelta(seconds=60),
        target_power_unit="MW",
    )
    mw_target = 1

    assert converted_power_value == mw_target


def test_convert_power_to_energy_in_time_step():
    converted_energy_value = Units.convert_power_to_energy(
        power_value=3,
        power_unit="MW",
        time_step=datetime.timedelta(seconds=60),
        target_energy_unit="MJ",
    )
    mj_target = 180

    assert converted_energy_value == mj_target


def test_compress_units():
    mw_1 = 0.02 * Units.get_unit(unit_string="MW")
    kw_target = 20
    kw_converted_quantity = mw_1.to_compact()
    kw_converted_value = kw_converted_quantity.m
    assert kw_target == kw_converted_value
