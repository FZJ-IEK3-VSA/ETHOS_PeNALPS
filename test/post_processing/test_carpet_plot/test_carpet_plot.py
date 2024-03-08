import datetime
import itertools
import os
import pathlib
from collections.abc import Iterable
from dataclasses import dataclass

import pint
import pytest
from ethos_penalps.utilities.general_functions import (
    convert_date_time_to_string,
    ResultPathGenerator,
)
from ethos_penalps.data_classes import LoadProfileEntry, LoadType
from ethos_penalps.post_processing.tikz_visualizations.carpet_plot_load_profile_generator import (
    CarpetPlotLoadProfileGenerator,
    CarpetPlotMatrix,
)
from ethos_penalps.utilities.units import Units


from test.post_processing.load_profile_generator_for_tests import (
    EnergyData,
    PowerData,
    BaseLoadProfileGeneratorClass,
)

pytestmark = pytest.mark.carpet_plot_tests


class TestCarpetPlot(BaseLoadProfileGeneratorClass):

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
    def test_carpet_plot_creation(
        self,
        x_axis_time_period_timedelta: datetime.timedelta,
        total_start_time: datetime.datetime,
        total_end_time: datetime.datetime,
        time_step: datetime.timedelta,
        resample_frequency: str,
    ):

        list_of_load_profile_entries = self.create_load_profile_entry_list(
            total_start_time=total_start_time,
            total_end_time=total_end_time,
            time_step=time_step,
        )
        load_profile_post_processor = CarpetPlotLoadProfileGenerator()
        load_profile_matrix = (
            load_profile_post_processor.convert_lpg_load_profile_to_data_frame_matrix(
                list_of_load_profile_entries=list_of_load_profile_entries,
                start_date_time_series=total_start_time,
                end_date_time_series=total_end_time,
                x_axis_time_period_timedelta=x_axis_time_period_timedelta,
                resample_frequency=resample_frequency,
                object_name="Test row",
            )
        )
        figure = (
            load_profile_post_processor.plot_load_profile_carpet_from_data_frame_matrix(
                carpet_plot_load_profile_matrix=load_profile_matrix,
            )
        )
        if x_axis_time_period_timedelta == datetime.timedelta(days=1):
            folder_name = "x_axis_1_day"
        elif x_axis_time_period_timedelta == datetime.timedelta(hours=1):
            folder_name = "x_axis_1_hour"
        elif x_axis_time_period_timedelta == datetime.timedelta(weeks=1):
            folder_name = "x_axis_1_week"

        time_step_string = convert_date_time_to_string(td=time_step)
        output_file_name = (
            "carpet_plot_figure_"
            + "_time_step_"
            + time_step_string
            + "_freq_"
            + resample_frequency
            + ".png"
        )

        parent_directory = pathlib.Path(__file__).parent.absolute()
        result_path_generator = ResultPathGenerator()
        result_folder = result_path_generator.create_subdirectory_relative_to_parent(
            parent_directory_path=str(parent_directory), new_directory_name=folder_name
        )
        path_to_figure = os.path.join(result_folder, output_file_name)

        figure.savefig(fname=path_to_figure, bbox_inches="tight")
