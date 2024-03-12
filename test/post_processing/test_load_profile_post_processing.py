import datetime
import math
import os
import pathlib
import warnings
from test.post_processing.load_profile_generator_for_tests import (
    BaseLoadProfileGeneratorClass,
)

import pytest
from ethos_penalps.data_classes import (
    CarpetPlotMatrix,
    LoadProfileMetaData,
    LoadProfileMetaDataResampled,
)
from ethos_penalps.post_processing.load_profile_entry_post_processor import (
    LoadProfileEntryPostProcessor,
)
from ethos_penalps.post_processing.time_series_visualizations.carpet_plot_load_profile_generator import (
    CarpetPlotLoadProfileGenerator,
)
from ethos_penalps.utilities.exceptions_and_warnings import (
    LoadProfileInconsistencyWarning,
)
from ethos_penalps.utilities.general_functions import (
    ResultPathGenerator,
    convert_date_time_to_string,
)
from ethos_penalps.utilities.units import Units

pytestmark = pytest.mark.test_load_profile_post_processing


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
    def test_load_profile_post_processing(
        self,
        x_axis_time_period_timedelta: datetime.timedelta,
        time_step: datetime.timedelta,
        total_start_time: datetime.datetime,
        total_end_time: datetime.datetime,
        resample_frequency: str,
    ):

        with warnings.catch_warnings():
            # Check that no Inconsistency warning occur during tests
            warnings.simplefilter(
                action="error", category=LoadProfileInconsistencyWarning
            )
            # Get test load profile entry
            list_of_load_profile_entries = self.create_load_profile_entry_list(
                total_start_time=total_start_time,
                total_end_time=total_end_time,
                time_step=time_step,
            )

            # Get Load Profile Entry Meta Data
            load_profile_entry_process_process = LoadProfileEntryPostProcessor()
            load_profile_meta_data = (
                load_profile_entry_process_process.create_load_profile_meta_data(
                    list_of_load_profile_entries=list_of_load_profile_entries,
                    object_name="Test Name",
                    object_type="Test Object",
                    start_date_time_series=total_start_time,
                    end_date_time_series=total_end_time,
                )
            )
            assert type(load_profile_meta_data) is LoadProfileMetaData
            # Check Load Profile Entry Meta Data
            load_profile_entry_process_process.check_if_power_and_energy_match(
                list_of_load_profile_meta_data=load_profile_meta_data
            )
            load_profile_meta_data_compressed = load_profile_entry_process_process._compress_power_in_meta_data_if_necessary(
                list_of_load_profile_meta_data=load_profile_meta_data
            )
            assert type(load_profile_meta_data_compressed) is LoadProfileMetaData
            load_profile_entry_process_process.check_if_power_and_energy_match(
                list_of_load_profile_meta_data=load_profile_meta_data_compressed
            )
            meta_data_total_energy_quantity = (
                load_profile_meta_data_compressed.total_energy
                * Units.get_unit(
                    unit_string=load_profile_meta_data_compressed.energy_unit
                )
            )
            # Resample meta data
            load_profile_meta_data_resampled = (
                load_profile_entry_process_process.resample_load_profile_meta_data(
                    load_profile_meta_data=load_profile_meta_data_compressed,
                    start_date=total_start_time,
                    end_date=total_end_time,
                    x_axis_time_period_timedelta=x_axis_time_period_timedelta,
                    resample_frequency=resample_frequency,
                )
            )
            load_profile_entry_process_process.check_if_power_and_energy_match(
                list_of_load_profile_meta_data=load_profile_meta_data_resampled
            )

            total_energy_quantity_resampled = (
                load_profile_meta_data_resampled.total_energy
                * Units.get_unit(
                    unit_string=load_profile_meta_data_resampled.energy_unit
                )
            )
            total_energy_quantity_resampled_converted = (
                total_energy_quantity_resampled.to(
                    meta_data_total_energy_quantity.units
                )
            )
            assert (
                type(load_profile_meta_data_resampled) is LoadProfileMetaDataResampled
            )
            assert math.isclose(
                total_energy_quantity_resampled_converted.m,
                meta_data_total_energy_quantity.m,
            )
            # Create CarpetPlotMatrix
            carpet_plot_load_profile_generator = CarpetPlotLoadProfileGenerator()
            load_profile_matrix = carpet_plot_load_profile_generator.convert_load_profile_meta_data_to_carpet_plot_matrix(
                load_profile_meta_data_resampled=load_profile_meta_data_resampled,
                start_date_time_series=total_start_time,
                end_date_time_series=total_end_time,
                x_axis_period_time_delta=x_axis_time_period_timedelta,
                resample_frequency=resample_frequency,
                object_name="Test row",
            )
            assert type(load_profile_matrix) is CarpetPlotMatrix
            load_profile_matrix = carpet_plot_load_profile_generator.compress_power_of_carpet_plot_matrix_if_necessary(
                carpet_plot_load_profile_matrix=load_profile_matrix
            )

            total_energy_from_power_matrix = (
                carpet_plot_load_profile_generator.get_energy_amount_from_power_matrix(
                    carpet_plot_matrix=load_profile_matrix,
                )
            )
            total_energy_power_matrix_quantity = (
                total_energy_from_power_matrix
                * Units.get_unit(unit_string=load_profile_matrix.energy_unit)
            )
            total_energy_power_matrix_quantity_converted = (
                total_energy_power_matrix_quantity.to(meta_data_total_energy_quantity.u)
            )

            assert type(load_profile_matrix) is CarpetPlotMatrix
            assert type(load_profile_meta_data) is LoadProfileMetaData
            assert math.isclose(
                meta_data_total_energy_quantity.m,
                total_energy_power_matrix_quantity_converted.m,
            )
            # Create Carpet plots from post processed data
            figure = carpet_plot_load_profile_generator.plot_load_profile_carpet_from_data_frame_matrix(
                carpet_plot_load_profile_matrix=load_profile_matrix,
            )

            # Create file names
            # if x_axis_time_period_timedelta == datetime.timedelta(days=1):
            #     folder_name = "x_axis_1_day"
            # elif x_axis_time_period_timedelta == datetime.timedelta(hours=1):
            #     folder_name = "x_axis_1_hour"
            # elif x_axis_time_period_timedelta == datetime.timedelta(weeks=1):
            #     folder_name = "x_axis_1_week"

            # time_step_string = convert_date_time_to_string(td=time_step)
            # output_file_name = (
            #     "carpet_plot_figure_"
            #     + "_time_step_"
            #     + time_step_string
            #     + "_freq_"
            #     + resample_frequency
            #     + ".png"
            # )

            # parent_directory = pathlib.Path(__file__).parent.absolute()
            # result_path_generator = ResultPathGenerator()
            # result_folder = (
            #     result_path_generator.create_subdirectory_relative_to_parent(
            #         parent_directory_path=str(parent_directory),
            #         new_directory_name=folder_name,
            #     )
            # )
            # path_to_figure = os.path.join(result_folder, output_file_name)

            # figure.savefig(fname=path_to_figure, bbox_inches="tight")
