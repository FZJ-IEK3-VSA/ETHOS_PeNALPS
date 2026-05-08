import datetime
import math
import pathlib
import warnings
from dataclasses import dataclass

import pandas
import pint

from ethos_penalps.data_classes import (
    Commodity,
    LoadProfileMetaDataFromDisk,
    ProcessStepDataFrameMetaInformation,
    StorageDataFrameMetaInformation,
)
from ethos_penalps.post_processing.load_profiles.load_profile_entry_post_processor import (
    DataFrameLoadProfileAnalyzer,
)
from ethos_penalps.stream import StreamDataFrameMetaInformation
from ethos_penalps.utilities.type_aliases import numbers_alias
from ethos_penalps.utilities.units import Units


class BaseMetaData:
    def __init__(self, path_to_data_frame: pathlib.Path, plot_string: str | None):
        self.path_to_data_frame: pathlib.Path = path_to_data_frame
        self.plot_string: str | None = plot_string

    def _read_data_frame(self) -> pandas.DataFrame:
        data_frame = pandas.read_csv(
            filepath_or_buffer=self.path_to_data_frame, index_col=0, header=0, parse_dates=["start_time", "end_time"]
        )
        return data_frame

    def _get_first_start_time(self, analysis_data_frame: pandas.DataFrame) -> datetime.datetime:
        """Returns the first start time of the analysis data frame.

        Args:
            analysis_data_frame (pandas.DataFrame): Is build from a list of
            LoadProfileEntry.

        Returns:
            datetime.datetime: First start time of the analysis data frame.
        """

        assert pandas.api.types.is_datetime64_dtype(analysis_data_frame.loc[:, "start_time"])
        start_time_numpy = analysis_data_frame.loc[:, "start_time"].min()
        start_time = start_time_numpy.to_pydatetime()

        return start_time

    def _get_last_end_time(self, analysis_data_frame: pandas.DataFrame) -> datetime.datetime:
        """Returns the last end time of the analysis data frame.

        Args:
            analysis_data_frame (pandas.DataFrame): Is build from a list of
            LoadProfileEntry.

        Returns:
            datetime.datetime: Last end time of the analysis data frame.
        """

        end_time_numpy = analysis_data_frame.loc[:, "end_time"].max()
        end_time = end_time_numpy.to_pydatetime()
        return end_time


class StreamFromDiskMetaData(BaseMetaData):
    def _get_stream_type(self, analysis_data_frame: pandas.DataFrame) -> str:
        stream_type = analysis_data_frame.loc[0, "stream_type"]
        return stream_type

    def _get_stream_name(self, analysis_data_frame: pandas.DataFrame) -> str:
        stream_name = analysis_data_frame.loc[0, "name"]
        return stream_name

    def _get_mass_unit(self, analysis_data_frame: pandas.DataFrame) -> str:
        mass_unit = analysis_data_frame.loc[0, "mass_unit"]
        return mass_unit

    def _get_commodity(self, analysis_data_frame: pandas.DataFrame) -> str:
        commodity_name = analysis_data_frame.loc[0, "commodity"]
        commodity = Commodity(name=commodity_name)
        return commodity

    def create_meta_data(
        self,
    ) -> StreamDataFrameMetaInformation:

        data_frame = self._read_data_frame()
        first_start_time = self._get_first_start_time(analysis_data_frame=data_frame)
        last_end_time = self._get_last_end_time(analysis_data_frame=data_frame)
        stream_type = self._get_stream_type(analysis_data_frame=data_frame)
        stream_name = self._get_stream_name(analysis_data_frame=data_frame)
        mass_unit = self._get_mass_unit(analysis_data_frame=data_frame)
        commodity = self._get_commodity(analysis_data_frame=data_frame)
        stream_meta_data = StreamDataFrameMetaInformation(
            data_frame=data_frame,
            stream_name=stream_name,
            first_start_time=first_start_time,
            last_end_time=last_end_time,
            stream_type=stream_type,
            mass_unit=mass_unit,
            commodity=commodity,
            name_to_display=stream_name,
            plot_string=self.plot_string,
        )

        return stream_meta_data


class ProcessStepFromDiskMetaData(BaseMetaData):
    def _get_process_step_name(self, analysis_data_frame: pandas.DataFrame) -> str:
        stream_type = analysis_data_frame.loc[0, "process_step_name"]
        return stream_type

    def _get_stream_name(self, analysis_data_frame: pandas.DataFrame) -> str:
        stream_name = analysis_data_frame.loc[0, "name"]
        return stream_name

    def _get_list_of_process_state_names(self, analysis_data_frame: pandas.DataFrame) -> list[str]:
        list_of_process_state_names = analysis_data_frame.loc[:, "process_state_name"].unique().tolist()
        return list_of_process_state_names

    def create_meta_data(
        self,
    ) -> ProcessStepDataFrameMetaInformation:

        data_frame = self._read_data_frame()
        first_start_time = self._get_first_start_time(analysis_data_frame=data_frame)
        last_end_time = self._get_last_end_time(analysis_data_frame=data_frame)
        process_step_name = self._get_process_step_name(analysis_data_frame=data_frame)
        list_of_process_state_names = self._get_list_of_process_state_names(analysis_data_frame=data_frame)

        stream_meta_data = ProcessStepDataFrameMetaInformation(
            data_frame=data_frame,
            process_step_name=process_step_name,
            list_of_process_state_names=list_of_process_state_names,
            first_start_time=first_start_time,
            last_end_time=last_end_time,
            plot_string=self.plot_string,
        )

        return stream_meta_data


class StorageFromDiskMetaData(BaseMetaData):
    def _get_process_step_name(self, analysis_data_frame: pandas.DataFrame) -> str:
        stream_type = analysis_data_frame.loc[0, "process_step_name"]
        return stream_type

    def _get_stream_name(self, analysis_data_frame: pandas.DataFrame) -> str:
        stream_name = analysis_data_frame.loc[0, "name"]
        return stream_name

    def _get_commodity(self, analysis_data_frame: pandas.DataFrame) -> str:
        commodity_name = analysis_data_frame.loc[0, "commodity"]
        commodity = Commodity(name=commodity_name)
        return commodity

    def _get_mass_unit(self, analysis_data_frame: pandas.DataFrame) -> str:
        mass_unit = "t"
        return mass_unit

    def create_meta_data(
        self,
    ) -> StorageDataFrameMetaInformation:

        data_frame = self._read_data_frame()
        first_start_time = self._get_first_start_time(analysis_data_frame=data_frame)
        last_end_time = self._get_last_end_time(analysis_data_frame=data_frame)
        commodity = self._get_commodity(analysis_data_frame=data_frame)
        process_step_name = self._get_process_step_name(analysis_data_frame=data_frame)
        mass_unit = self._get_mass_unit(analysis_data_frame=data_frame)
        stream_meta_data = StorageDataFrameMetaInformation(
            data_frame=data_frame,
            process_step_name=process_step_name,
            commodity=commodity,
            mass_unit=mass_unit,
            first_start_time=first_start_time,
            last_end_time=last_end_time,
            plot_string=self.plot_string,
        )

        return stream_meta_data
