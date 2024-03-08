import datetime
import itertools
import math
import os
import pathlib
from dataclasses import dataclass
from test.post_processing.load_profile_generator_for_tests import (
    BaseLoadProfileGeneratorClass,
    EnergyData,
    PowerData,
)

import pint
import pytest
from ethos_penalps.data_classes import (
    CarpetPlotMatrix,
    EmptyLoadProfileMetadata,
    LoadProfileMetaDataResampled,
    LoadProfileEntry,
    LoadType,
)
from ethos_penalps.post_processing.tikz_visualizations.carpet_plot_load_profile_generator import (
    CarpetPlotLoadProfileGenerator,
    CarpetPlotMatrix,
    LoadProfileEntryPostProcessor,
)
from ethos_penalps.post_processing.load_profile_entry_post_processor import (
    ListOfLoadProfileEntryAnalyzer,
    LoadProfileEntryPostProcessor,
)
from ethos_penalps.utilities.general_functions import convert_date_time_to_string
from ethos_penalps.utilities.units import Units

pytestmark = pytest.mark.resample_load_profile_meta_data


class TestResamplingAntMatrixConversion(BaseLoadProfileGeneratorClass):
    @pytest.mark.parametrize(
        ("x_axis_time_period_timedelta"),
        [
            (datetime.timedelta(hours=1)),
            (datetime.timedelta(days=1)),
            (datetime.timedelta(weeks=1)),
        ],
    )
    @pytest.mark.parametrize(
        ("time_step"),
        [
            (datetime.timedelta(minutes=5)),
            (datetime.timedelta(minutes=30)),
            (datetime.timedelta(minutes=60)),
            (datetime.timedelta(minutes=90)),
        ],
    )
    @pytest.mark.parametrize(
        (
            "total_start_time",
            "total_end_time",
        ),
        [
            (
                datetime.datetime(year=2022, month=1, day=1),
                datetime.datetime(year=2022, month=12, day=31),
            )
        ],
    )
    @pytest.mark.parametrize(
        ("resample_frequency"),
        [("5min"), ("30min"), ("1h")],
    )
    def test_resampling_and_matrix_conversion(
        self,
        x_axis_time_period_timedelta: datetime.timedelta,
        time_step: datetime.timedelta,
        total_start_time: datetime.datetime,
        total_end_time: datetime.datetime,
        resample_frequency: str,
    ):

        list_of_load_profile_entries = self.create_load_profile_entry_list(
            total_start_time=total_start_time,
            total_end_time=total_end_time,
            time_step=time_step,
        )
        carpet_plot_generator = CarpetPlotLoadProfileGenerator()

        load_profile_entry_process_process = ListOfLoadProfileEntryAnalyzer()
        list_of_load_profile_meta_data = (
            load_profile_entry_process_process.create_list_of_load_profile_meta_data(
                list_of_load_profiles=list_of_load_profile_entries,
                object_name="Test Name",
            )
        )
        assert type(list_of_load_profile_meta_data) is LoadProfileMetaDataResampled

        load_profile_entry_process_process.check_if_power_and_energy_match(
            list_of_load_profile_meta_data=list_of_load_profile_meta_data
        )
        list_of_load_profile_meta_data = load_profile_entry_process_process._compress_power_in_meta_data_if_necessary(
            list_of_load_profile_meta_data=list_of_load_profile_meta_data
        )
        load_profile_entry_process_process.check_if_power_and_energy_match(
            list_of_load_profile_meta_data=list_of_load_profile_meta_data
        )
        meta_data_total_energy_quantity = (
            list_of_load_profile_meta_data.total_energy
            * Units.get_unit(unit_string=list_of_load_profile_meta_data.energy_unit)
        )

        load_profile_matrix = (
            carpet_plot_generator.convert_lpg_load_profile_to_data_frame_matrix(
                list_of_load_profile_entries=list_of_load_profile_entries,
                start_date_time_series=total_start_time,
                end_date_time_series=total_end_time,
                x_axis_time_period_timedelta=x_axis_time_period_timedelta,
                resample_frequency=resample_frequency,
                object_name="Test row",
            )
        )
        assert type(load_profile_matrix) is CarpetPlotMatrix
        load_profile_matrix = (
            carpet_plot_generator.compress_power_of_carpet_plot_matrix_if_necessary(
                carpet_plot_load_profile_matrix=load_profile_matrix
            )
        )

        total_energy_power_matrix = (
            carpet_plot_generator.get_energy_amount_from_power_matrix(
                carpet_plot_matrix=load_profile_matrix,
            )
        )
        total_energy_power_matrix_quantity = total_energy_power_matrix * Units.get_unit(
            unit_string=load_profile_matrix.energy_unit
        )
        total_energy_power_matrix_quantity_converted = (
            total_energy_power_matrix_quantity.to(meta_data_total_energy_quantity.u)
        )

        assert type(load_profile_matrix) is CarpetPlotMatrix
        assert type(list_of_load_profile_meta_data) is LoadProfileMetaDataResampled
        assert math.isclose(
            meta_data_total_energy_quantity.m,
            total_energy_power_matrix_quantity_converted.m,
        )
