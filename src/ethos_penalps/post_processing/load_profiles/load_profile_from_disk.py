import datetime
import pathlib
import warnings

import pandas
import pint

from ethos_penalps.data_classes import (
    EmptyLoadProfileMetadata,
    LoadProfileEntry,
    LoadProfileMetaData,
    LoadProfileMetaDataFromDisk,
)
from ethos_penalps.post_processing.load_profiles.load_profile_entry_post_processor import (
    DataFrameLoadProfileAnalyzer,
    LoadProfileEntryPostProcessor,
)
from ethos_penalps.utilities.type_aliases import numbers_alias
from ethos_penalps.utilities.units import Units


class SingleLoadProfileFromDiskLoader(DataFrameLoadProfileAnalyzer):
    def __init__(
        self,
        path_to_data_frame: str | pathlib.Path | None,
        object_type: str = "",
        plot_string: str | None = None,
        minimum_power_display: None | int = None,
    ):
        self.path_to_data_frame: str | pathlib.Path | None = path_to_data_frame
        self.object_type: str = object_type
        self.plot_string: str | None = plot_string
        self.minimum_power_display: None | int = minimum_power_display
        super().__init__()

    def _meta_data_from_data_frame(self, data_frame: pandas.DataFrame) -> LoadProfileMetaDataFromDisk:
        stats = self._extract_stats_from_data_frame(analysis_data_frame=data_frame, object_name=self.object_type)
        load_profile_meta_data = LoadProfileMetaDataFromDisk(
            name=stats.load_type.name,
            object_type=self.object_type,
            data_frame=data_frame,
            first_start_time=stats.first_start_time,
            last_end_time=stats.last_end_time,
            load_type=stats.load_type,
            power_unit=stats.power_unit,
            maximum_power=stats.maximum_power,
            total_energy=stats.total_energy,
            energy_unit=stats.energy_unit,
            maximum_energy=stats.maximum_energy,
            minimum_power=stats.minimum_power,
            plot_string=self.plot_string,
        )
        return load_profile_meta_data

    def _read_data_frame_from_disk(self) -> pandas.DataFrame:
        path = pathlib.Path(self.path_to_data_frame)
        if path.suffix in (".xlsx", ".xls"):
            data_frame = pandas.read_excel(
                io=self.path_to_data_frame, index_col=0, parse_dates=["start_time", "end_time"]
            )
        else:
            data_frame = pandas.read_csv(
                filepath_or_buffer=self.path_to_data_frame, index_col=0, parse_dates=["start_time", "end_time"]
            )
        # If start_time was consumed as the index, restore it as a column
        if "start_time" not in data_frame.columns and data_frame.index.name == "start_time":
            data_frame = data_frame.reset_index()
        # Drop spurious unnamed columns from repeated saves
        data_frame = data_frame.loc[:, ~data_frame.columns.str.startswith("Unnamed:")]
        if data_frame.empty:
            raise Exception("Data frame is empty at path: " + str(self.path_to_data_frame))
        return data_frame

    def create_meta_data_from_disk(
        self,
    ) -> LoadProfileMetaDataFromDisk:
        data_frame = self._read_data_frame_from_disk()
        load_profile_meta_data = self._meta_data_from_data_frame(data_frame=data_frame)
        return load_profile_meta_data

    def create_meta_data(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> LoadProfileMetaData | EmptyLoadProfileMetadata:
        """Read load profile from disk and create a full LoadProfileMetaData
        with populated list_of_load_profiles."""
        data_frame = self._read_data_frame_from_disk()
        meta_data_from_disk = self._meta_data_from_data_frame(data_frame=data_frame)

        entries = []
        for i in range(len(data_frame)):
            row = data_frame.iloc[i]
            entries.append(
                LoadProfileEntry(
                    load_type=meta_data_from_disk.load_type,
                    start_time=pandas.Timestamp(row["start_time"]).to_pydatetime(),
                    end_time=pandas.Timestamp(row["end_time"]).to_pydatetime(),
                    energy_quantity=float(row["energy_quantity"]),
                    energy_unit=str(row["energy_unit"]),
                    average_power_consumption=float(row["average_power_consumption"]),
                    power_unit=str(row["power_unit"]),
                )
            )
        entries.reverse()

        processor = LoadProfileEntryPostProcessor()
        return processor.create_load_profile_meta_data(
            list_of_load_profile_entries=entries,
            start_date_time_series=start_date,
            end_date_time_series=end_date,
            object_name=meta_data_from_disk.name,
            object_type=self.object_type,
        )


class LoadProfileFromDiskSingleModel(DataFrameLoadProfileAnalyzer):
    def __init__(self, plant_name: str):
        super().__init__()
        self.dict_of_load_profiles: dict[str, LoadProfileMetaDataFromDisk] = {}
        self.plant_name: str = plant_name

    def add_data_frame(
        self,
        path_to_pandas_data_frame: str | pathlib.Path,
        object_type: str,
    ) -> LoadProfileMetaDataFromDisk:
        path_to_pandas_data_frame = pathlib.Path(path_to_pandas_data_frame)
        if path_to_pandas_data_frame.suffix == ".xlsx":
            input_data_frame = pandas.read_excel(
                io=path_to_pandas_data_frame, index_col=0, parse_dates=["start_time", "end_time"]
            )
        else:
            input_data_frame = pandas.read_csv(
                filepath_or_buffer=path_to_pandas_data_frame, index_col=0, parse_dates=["start_time", "end_time"]
            )

        if input_data_frame.index.name == "start_time":
            input_data_frame = input_data_frame.reset_index()

        stats = self._extract_stats_from_data_frame(analysis_data_frame=input_data_frame, object_name=object_type)
        load_profile_meta_data = LoadProfileMetaDataFromDisk(
            name=stats.load_type.name,
            load_type=stats.load_type,
            data_frame=input_data_frame,
            object_type=object_type,
            total_energy=stats.total_energy,
            power_unit=stats.power_unit,
            energy_unit=stats.energy_unit,
            minimum_power=stats.minimum_power,
            maximum_power=stats.maximum_power,
            last_end_time=stats.last_end_time,
            first_start_time=stats.first_start_time,
            maximum_energy=stats.maximum_energy,
        )

        if stats.load_type.name in self.dict_of_load_profiles:
            warnings.warn(
                message="""The Load type: """
                + str(stats.load_type.name)
                + """ is already in the scenario dictionary."""
            )

        self.dict_of_load_profiles[stats.load_type.name] = load_profile_meta_data
        return load_profile_meta_data

    def get_first_start_time_from_scenario(
        self,
    ):
        list_of_first_start_times = []
        for current_load_profile_meta_data in self.dict_of_load_profiles.values():
            list_of_first_start_times.append(current_load_profile_meta_data.first_start_time)
        first_start_time = min(list_of_first_start_times)
        return first_start_time

    def get_last_end_time_from_scenario(self):
        list_of_last_end_times = []
        for current_load_profile_meta_data in self.dict_of_load_profiles.values():
            list_of_last_end_times.append(current_load_profile_meta_data.last_end_time)
        last_end_time = max(list_of_last_end_times)
        return last_end_time

    def get_all_load_types(self) -> list[str]:
        list_of_load_names = []
        for current_scenario in self.dict_of_load_profiles:
            for load_profile_meta_data in self.dict_of_load_profiles.values():
                list_of_load_names.append(load_profile_meta_data.load_type.name)
        unique_list_of_load_names = list(set(list_of_load_names))
        return unique_list_of_load_names

    def get_total_energy_for_load_type(self, load_type_string: str) -> pint.Quantity:
        total_energy = 0 * Units.get_unit("MJ")

        if load_type_string in self.dict_of_load_profiles:
            total_energy = total_energy + self.dict_of_load_profiles[load_type_string].total_energy * Units.get_unit(
                self.dict_of_load_profiles[load_type_string].energy_unit
            )

        return total_energy

    def get_load_profile_meta_data(
        self,
        load_type_string: str,
        path_to_load_profile_for_plant_and_load: str | pathlib.Path,
    ) -> LoadProfileMetaDataFromDisk:

        if load_type_string not in self.dict_of_load_profiles:
            self.add_data_frame(
                path_to_pandas_data_frame=path_to_load_profile_for_plant_and_load,
                object_type=self.plant_name + "_" + load_type_string,
            )
        load_profile_meta_data_from_disk = self.dict_of_load_profiles[load_type_string]

        return load_profile_meta_data_from_disk


class LoadProfileCombinator(DataFrameLoadProfileAnalyzer):
    def __init__(self, list_of_load_profile_meta_data: list[LoadProfileMetaDataFromDisk]):
        super().__init__()
        self.list_of_load_profile_meta_data: list[LoadProfileMetaDataFromDisk] = list_of_load_profile_meta_data

    def get_unit_conversion_factor(self, current_unit_string: str, target_unit_string: str):
        unit = Units()
        current_quantity = 1 * unit.get_unit(unit_string=current_unit_string)
        target_unit = unit.get_unit(unit_string=target_unit_string)
        conversion_factor = current_quantity.to(target_unit).m
        return conversion_factor

    def create_combined_load_profiles_for_load_type(
        self,
        target_unit_string_energy: str,
        target_unit_string_power: str,
        path_to_output_file: str | pathlib.Path | None = None,
    ) -> LoadProfileMetaDataFromDisk:

        first_meta_data = self.list_of_load_profile_meta_data[0]
        output_data_frame = first_meta_data.data_frame.copy()
        energy_conversion_factor = self.get_unit_conversion_factor(
            current_unit_string=first_meta_data.energy_unit,
            target_unit_string=target_unit_string_energy,
        )
        power_conversion_factor = self.get_unit_conversion_factor(
            current_unit_string=first_meta_data.power_unit,
            target_unit_string=target_unit_string_power,
        )
        output_data_frame.loc[:, "energy_quantity"] = output_data_frame.loc[:, "energy_quantity"].multiply(
            energy_conversion_factor
        )
        output_data_frame.loc[:, "average_power_consumption"] = output_data_frame.loc[
            :, "average_power_consumption"
        ].multiply(power_conversion_factor)

        output_data_frame.loc[:, "energy_unit"] = target_unit_string_energy
        output_data_frame.loc[:, "power_unit"] = target_unit_string_power

        for current_load_profile_meta_data in self.list_of_load_profile_meta_data[1::]:
            current_data_frame = current_load_profile_meta_data.data_frame
            energy_conversion_factor = self.get_unit_conversion_factor(
                current_unit_string=current_load_profile_meta_data.energy_unit,
                target_unit_string=target_unit_string_energy,
            )
            power_conversion_factor = self.get_unit_conversion_factor(
                current_unit_string=current_load_profile_meta_data.power_unit,
                target_unit_string=target_unit_string_power,
            )

            output_data_frame.loc[:, "average_power_consumption"] = output_data_frame.loc[
                :, "average_power_consumption"
            ] + current_data_frame.loc[:, "average_power_consumption"].multiply(power_conversion_factor)
            output_data_frame.loc[:, "energy_quantity"] = output_data_frame.loc[
                :, "energy_quantity"
            ] + current_data_frame.loc[:, "energy_quantity"].multiply(energy_conversion_factor)

        name_of_load_type = first_meta_data.load_type.name

        stats = self._extract_stats_from_data_frame(analysis_data_frame=output_data_frame)
        combined_load_profile_meta_data: LoadProfileMetaDataFromDisk = LoadProfileMetaDataFromDisk(
            name="Load Profile for " + name_of_load_type,
            object_type="Combined Load Profile",
            data_frame=output_data_frame,
            first_start_time=stats.first_start_time,
            last_end_time=stats.last_end_time,
            load_type=first_meta_data.load_type,
            power_unit=target_unit_string_power,
            energy_unit=target_unit_string_energy,
            maximum_energy=stats.maximum_energy,
            maximum_power=stats.maximum_power,
            minimum_power=stats.minimum_power,
            total_energy=stats.total_energy,
        )
        if path_to_output_file is not None:
            combined_load_profile_meta_data.data_frame.to_csv(path_or_buf=path_to_output_file)
        return combined_load_profile_meta_data
