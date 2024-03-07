import datetime
import pytest
import warnings
from ethos_penalps.post_processing.load_profile_entry_post_processor import (
    ListOfLoadProfileEntryAnalyzer,
)
from ethos_penalps.data_classes import LoadProfileEntry, LoadType
from ethos_penalps.utilities.units import Units
from ethos_penalps.utilities.exceptions_and_warnings import (
    LoadProfileInconsistencyWarning,
)

list_of_load_profile_entry_analyzer = ListOfLoadProfileEntryAnalyzer()

load_type = LoadType(name="Electricity")
energy_unit = "MJ"
power_unit = "MW"

pytestmark = pytest.mark.load_profile_entry_analyzer


def test_correct_order_load_profiles():
    # Asserts that no LoadProfileInconsistencyWarning is raised
    with warnings.catch_warnings():
        warnings.simplefilter(action="error", category=LoadProfileInconsistencyWarning)
        start_time_1 = datetime.datetime(year=2022, month=1, day=1)
        end_time_1 = datetime.datetime(year=2022, month=1, day=2)
        energy_value_1 = 1000
        start_time_2 = datetime.datetime(year=2022, month=1, day=2)
        end_time_2 = datetime.datetime(year=2022, month=1, day=2)
        energy_value_2 = 0
        start_time_3 = datetime.datetime(year=2022, month=1, day=2)
        end_time_3 = datetime.datetime(year=2022, month=1, day=3)
        energy_value_3 = 1000
        list_of_load_profiles = [
            LoadProfileEntry(
                load_type=load_type,
                start_time=start_time_1,
                end_time=end_time_1,
                energy_quantity=energy_value_1,
                energy_unit=energy_unit,
                average_power_consumption=Units.convert_energy_to_power(
                    energy_value=1000,
                    energy_unit=energy_unit,
                    time_step=end_time_1 - start_time_1,
                    target_power_unit=power_unit,
                ),
                power_unit=power_unit,
            ),
            LoadProfileEntry(
                load_type=load_type,
                start_time=start_time_2,
                end_time=end_time_2,
                energy_quantity=energy_value_2,
                energy_unit=energy_unit,
                average_power_consumption=Units.convert_energy_to_power(
                    energy_value=0,
                    energy_unit=energy_unit,
                    time_step=end_time_2 - start_time_2,
                    target_power_unit=power_unit,
                ),
                power_unit=power_unit,
            ),
            LoadProfileEntry(
                load_type=load_type,
                start_time=start_time_3,
                end_time=end_time_3,
                energy_quantity=energy_value_3,
                energy_unit=energy_unit,
                average_power_consumption=Units.convert_energy_to_power(
                    energy_value=1000,
                    energy_unit=energy_unit,
                    time_step=end_time_3 - start_time_3,
                    target_power_unit=power_unit,
                ),
                power_unit=power_unit,
            ),
        ]
        load_profile_meta_data = (
            list_of_load_profile_entry_analyzer.create_list_of_load_profile_meta_data(
                list_of_load_profiles=list_of_load_profiles, object_name="Test Object"
            )
        )
        list_of_load_profile_entry_analyzer.check_load_profile_for_temporal_consistency(
            list_of_load_profile_meta_data=load_profile_meta_data,
            object_name="Test Object",
        )
        list_of_load_profile_entry_analyzer.check_if_power_and_energy_match(
            list_of_load_profile_meta_data=load_profile_meta_data
        )


# Filters all warnings because this test is intended to raise a warning
@pytest.mark.filterwarnings("ignore:")
def test_wrong_order_load_profiles():
    # Asserts that a LoadProfileInconsistencyWarning is raised
    with warnings.catch_warnings():
        pytest.warns(LoadProfileInconsistencyWarning)
        start_time_1 = datetime.datetime(year=2022, month=1, day=4)
        end_time_1 = datetime.datetime(year=2022, month=1, day=5)
        energy_value_1 = 1000
        start_time_2 = datetime.datetime(year=2022, month=1, day=2)
        end_time_2 = datetime.datetime(year=2022, month=1, day=2)
        energy_value_2 = 0
        start_time_3 = datetime.datetime(year=2022, month=1, day=2)
        end_time_3 = datetime.datetime(year=2022, month=1, day=3)
        energy_value_3 = 1000
        list_of_load_profiles = [
            LoadProfileEntry(
                load_type=load_type,
                start_time=start_time_1,
                end_time=end_time_1,
                energy_quantity=energy_value_1,
                energy_unit=energy_unit,
                average_power_consumption=Units.convert_energy_to_power(
                    energy_value=1000,
                    energy_unit=energy_unit,
                    time_step=end_time_1 - start_time_1,
                    target_power_unit=power_unit,
                ),
                power_unit=power_unit,
            ),
            LoadProfileEntry(
                load_type=load_type,
                start_time=start_time_2,
                end_time=end_time_2,
                energy_quantity=energy_value_2,
                energy_unit=energy_unit,
                average_power_consumption=Units.convert_energy_to_power(
                    energy_value=0,
                    energy_unit=energy_unit,
                    time_step=end_time_2 - start_time_2,
                    target_power_unit=power_unit,
                ),
                power_unit=power_unit,
            ),
            LoadProfileEntry(
                load_type=load_type,
                start_time=start_time_3,
                end_time=end_time_3,
                energy_quantity=energy_value_3,
                energy_unit=energy_unit,
                average_power_consumption=Units.convert_energy_to_power(
                    energy_value=1000,
                    energy_unit=energy_unit,
                    time_step=end_time_3 - start_time_3,
                    target_power_unit=power_unit,
                ),
                power_unit=power_unit,
            ),
        ]
        load_profile_meta_data = (
            list_of_load_profile_entry_analyzer.create_list_of_load_profile_meta_data(
                list_of_load_profiles=list_of_load_profiles, object_name="Test Object"
            )
        )
        list_of_load_profile_entry_analyzer.check_load_profile_for_temporal_consistency(
            list_of_load_profile_meta_data=load_profile_meta_data,
            object_name="Test Object",
        )
        list_of_load_profile_entry_analyzer.check_if_power_and_energy_match(
            list_of_load_profile_meta_data=load_profile_meta_data
        )


def test_correct_0_time_length_order_load_profiles():
    # Asserts that no LoadProfileInconsistencyWarning is raised
    with warnings.catch_warnings():
        warnings.simplefilter(action="error", category=LoadProfileInconsistencyWarning)
        start_time_1 = datetime.datetime(year=2022, month=1, day=1)
        end_time_1 = datetime.datetime(year=2022, month=1, day=2)
        energy_value_1 = 1000
        start_time_2 = datetime.datetime(year=2022, month=1, day=2)
        end_time_2 = datetime.datetime(year=2022, month=1, day=2)
        energy_value_2 = 0
        start_time_3 = datetime.datetime(year=2022, month=1, day=2)
        end_time_3 = datetime.datetime(year=2022, month=1, day=3)
        energy_value_3 = 1000
        list_of_load_profiles = [
            LoadProfileEntry(
                load_type=load_type,
                start_time=start_time_1,
                end_time=end_time_1,
                energy_quantity=energy_value_1,
                energy_unit=energy_unit,
                average_power_consumption=Units.convert_energy_to_power(
                    energy_value=1000,
                    energy_unit=energy_unit,
                    time_step=end_time_1 - start_time_1,
                    target_power_unit=power_unit,
                ),
                power_unit=power_unit,
            ),
            LoadProfileEntry(
                load_type=load_type,
                start_time=start_time_2,
                end_time=end_time_2,
                energy_quantity=energy_value_2,
                energy_unit=energy_unit,
                average_power_consumption=Units.convert_energy_to_power(
                    energy_value=0,
                    energy_unit=energy_unit,
                    time_step=end_time_2 - start_time_2,
                    target_power_unit=power_unit,
                ),
                power_unit=power_unit,
            ),
            LoadProfileEntry(
                load_type=load_type,
                start_time=start_time_3,
                end_time=end_time_3,
                energy_quantity=energy_value_3,
                energy_unit=energy_unit,
                average_power_consumption=Units.convert_energy_to_power(
                    energy_value=1000,
                    energy_unit=energy_unit,
                    time_step=end_time_3 - start_time_3,
                    target_power_unit=power_unit,
                ),
                power_unit=power_unit,
            ),
        ]
        load_profile_meta_data = (
            list_of_load_profile_entry_analyzer.create_list_of_load_profile_meta_data(
                list_of_load_profiles=list_of_load_profiles, object_name="Test Object"
            )
        )
        list_of_load_profile_entry_analyzer.check_load_profile_for_temporal_consistency(
            list_of_load_profile_meta_data=load_profile_meta_data,
            object_name="Test Object",
        )
        list_of_load_profile_entry_analyzer.check_if_power_and_energy_match(
            list_of_load_profile_meta_data=load_profile_meta_data
        )


# Filters all warnings because this test is intended to raise a warning
@pytest.mark.filterwarnings("ignore:")
def test_wrong_energy_power_combination():
    # Asserts that a LoadProfileInconsistencyWarning is raised
    with warnings.catch_warnings():
        pytest.warns(LoadProfileInconsistencyWarning)
        start_time_1 = datetime.datetime(year=2022, month=1, day=1)
        end_time_1 = datetime.datetime(year=2022, month=1, day=2)
        energy_value_1 = 1000
        power_value_1 = 1050

        list_of_load_profiles = [
            LoadProfileEntry(
                load_type=load_type,
                start_time=start_time_1,
                end_time=end_time_1,
                energy_quantity=energy_value_1,
                energy_unit=energy_unit,
                average_power_consumption=power_value_1,
                power_unit=power_unit,
            ),
        ]
        load_profile_meta_data = (
            list_of_load_profile_entry_analyzer.create_list_of_load_profile_meta_data(
                list_of_load_profiles=list_of_load_profiles, object_name="Test Object"
            )
        )
        list_of_load_profile_entry_analyzer.check_if_power_and_energy_match(
            list_of_load_profile_meta_data=load_profile_meta_data
        )


# Filters all warnings because this test is intended to raise a warning
@pytest.mark.filterwarnings("ignore:")
def test_wrong_combinations_of_load_types():
    # Asserts that a LoadProfileInconsistencyWarning is raised
    with warnings.catch_warnings():
        pytest.warns(LoadProfileInconsistencyWarning)
        start_time_1 = datetime.datetime(year=2022, month=1, day=1)
        end_time_1 = datetime.datetime(year=2022, month=1, day=2)
        energy_value_1 = 1000
        load_type_1 = LoadType("Electricity")
        start_time_2 = datetime.datetime(year=2022, month=1, day=2)
        end_time_2 = datetime.datetime(year=2022, month=1, day=2)
        energy_value_2 = 0
        load_type_2 = LoadType("Natural Gas")
        list_of_load_profiles = [
            LoadProfileEntry(
                load_type=load_type_1,
                start_time=start_time_1,
                end_time=end_time_1,
                energy_quantity=energy_value_1,
                energy_unit=energy_unit,
                average_power_consumption=Units.convert_energy_to_power(
                    energy_value=1000,
                    energy_unit=energy_unit,
                    time_step=end_time_1 - start_time_1,
                    target_power_unit=power_unit,
                ),
                power_unit=power_unit,
            ),
            LoadProfileEntry(
                load_type=load_type_2,
                start_time=start_time_2,
                end_time=end_time_2,
                energy_quantity=energy_value_2,
                energy_unit=energy_unit,
                average_power_consumption=Units.convert_energy_to_power(
                    energy_value=0,
                    energy_unit=energy_unit,
                    time_step=end_time_2 - start_time_2,
                    target_power_unit=power_unit,
                ),
                power_unit=power_unit,
            ),
        ]
        load_profile_meta_data = (
            list_of_load_profile_entry_analyzer.create_list_of_load_profile_meta_data(
                list_of_load_profiles=list_of_load_profiles, object_name="Test Object"
            )
        )
        list_of_load_profile_entry_analyzer.check_load_profile_for_temporal_consistency(
            list_of_load_profile_meta_data=load_profile_meta_data,
            object_name="Test Object",
        )
