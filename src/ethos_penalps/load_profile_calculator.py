import datetime
from dataclasses import dataclass, field
import warnings
import pandas as pd
import pint
from ethos_penalps.data_classes import (
    Commodity,
    LoadProfileDataFrameMetaInformation,
    LoadProfileEntry,
    LoadType,
    ProcessStateEnergyLoadData,
    ProcessStateEnergyLoadDataBasedOnStreamMass,
    ProcessStepProductionPlanEntry,
    StreamLoadEnergyData,
    ProcessStateEnergyData,
)
from ethos_penalps.utilities.units import Units

from ethos_penalps.post_processing.load_profile_entry_post_processor import (
    LoadProfileEntryPostProcessor,
)
from ethos_penalps.stream import (
    BatchStreamProductionPlanEntry,
    ContinuousStream,
    ContinuousStreamProductionPlanEntry,
    ProcessStepProductionPlanEntryWithInputStreamState,
    StreamEnergyData,
)
from ethos_penalps.utilities.data_base_interactions import DataBaseInteractions
from ethos_penalps.utilities.exceptions_and_warnings import UnexpectedBehaviorWarning


@dataclass
class StreamLoadProfileEntryCollection:
    object_name: str
    load_type_dict: dict[str, LoadType] = field(default_factory=dict)
    dict_of_load_entry_lists: dict[str, list[LoadProfileEntry]] = field(
        default_factory=dict
    )

    def add_load_profile(
        self,
        load_type: LoadType,
        load_profile_entry: LoadProfileEntry,
    ):
        self.load_type_dict[load_type.uuid] = load_type
        if load_type.uuid in self.dict_of_load_entry_lists:
            self.dict_of_load_entry_lists[load_type.uuid].append(load_profile_entry)
        else:
            self.dict_of_load_entry_lists[load_type.uuid] = [load_profile_entry]


@dataclass
class ProcessStepLoadProfileEntryCollection:
    object_name: str
    load_type_dict: dict[str, LoadType] = field(default_factory=dict)
    dict_of_load_entry_lists: dict[str, list[LoadProfileEntry]] = field(
        default_factory=dict
    )

    def add_load_profiles(
        self,
        load_type: LoadType,
        load_profile_entry: LoadProfileEntry,
    ):
        self.load_type_dict[load_type.uuid] = load_type
        if load_type.uuid in self.dict_of_load_entry_lists:
            self.dict_of_load_entry_lists[load_type.uuid].append(load_profile_entry)
        else:
            self.dict_of_load_entry_lists[load_type.uuid] = [load_profile_entry]


@dataclass
class LoadProfileMetaDataFrameCollection:
    process_step_load_profile_meta_data_frame: dict[
        str, dict[LoadType, LoadProfileDataFrameMetaInformation]
    ] = field(default_factory=dict)
    dict_stream_data_frames: dict[
        str, dict[LoadType, LoadProfileDataFrameMetaInformation]
    ] = field(default_factory=dict)
    target_power_unit: str = Units.power_unit.__str__()
    target_energy_unit: str = Units.energy_unit.__str__()


@dataclass
class LoadProfileCollection:
    dict_stream_load_profile_collections: dict[
        str, StreamLoadProfileEntryCollection
    ] = field(default_factory=dict)
    dict_process_step_load_profile_collections: dict[
        str, ProcessStepLoadProfileEntryCollection
    ] = field(default_factory=dict)
    list_of_load_type: list[LoadType] = field(default_factory=list)
    dict_stream_data_frames: dict[str, dict[LoadType, pd.DataFrame]] = field(
        default_factory=dict
    )
    dict_process_step_data_frames: dict[str, dict[LoadType, pd.DataFrame]] = field(
        default_factory=dict
    )
    dict_stream_data_frames_gantt_chart: dict[
        str, dict[LoadType, pd.DataFrame]
    ] = field(default_factory=dict)
    dict_process_step_data_frames_gantt_chart: dict[
        str, dict[LoadType, pd.DataFrame]
    ] = field(default_factory=dict)
    target_power_unit: str = Units.power_unit
    target_energy_unit: str = Units.energy_unit

    def append_stream_load_profile_entry(
        self,
        stream_name: str,
        load_type: LoadType,
        load_profile_entry: LoadProfileEntry,
    ):
        if stream_name not in self.dict_stream_load_profile_collections:
            stream_load_profile_entry_collection = StreamLoadProfileEntryCollection(
                object_name=stream_name
            )
            self.dict_stream_load_profile_collections[
                stream_name
            ] = stream_load_profile_entry_collection
        else:
            stream_load_profile_entry_collection = (
                self.dict_stream_load_profile_collections[stream_name]
            )
        stream_load_profile_entry_collection.add_load_profile(
            load_type=load_type,
            load_profile_entry=load_profile_entry,
        )

    def append_process_step_energy_data_entry(
        self,
        process_step_name: str,
        load_type: LoadType,
        load_profile_entry: LoadProfileEntry,
    ):
        if process_step_name not in self.dict_process_step_load_profile_collections:
            process_step_lp_collection = (
                self.dict_process_step_load_profile_collections[process_step_name]
            ) = ProcessStepLoadProfileEntryCollection(
                object_name=process_step_name
            )
        else:
            process_step_lp_collection = (
                self.dict_process_step_load_profile_collections[process_step_name]
            )
        process_step_lp_collection.add_load_profiles(
            load_type=load_type, load_profile_entry=load_profile_entry
        )

    def convert_stream_energy_dict_to_data_frame(
        self,
    ) -> dict[str, dict[str, pd.DataFrame]]:
        for (
            stream_name,
            stream_load_profile_collection,
        ) in self.dict_stream_load_profile_collections.items():
            self.dict_stream_data_frames[stream_name] = {}
            for (
                load_type_uuid,
                list_of_load_profile_entries,
            ) in stream_load_profile_collection.dict_of_load_entry_lists.items():
                self.dict_stream_data_frames[stream_name][
                    load_type_uuid
                ] = pd.DataFrame(list_of_load_profile_entries)
        return self.dict_stream_data_frames

    def convert_process_state_energy_date(
        self,
    ) -> dict[str, dict[str, pd.DataFrame]]:
        for (
            process_step_name,
            process_step_load_profile_collection,
        ) in self.dict_process_step_load_profile_collections.items():
            self.dict_process_step_data_frames[process_step_name] = {}
            for (
                load_type_uuid,
                list_of_load_profile_entries,
            ) in process_step_load_profile_collection.dict_of_load_entry_lists.items():
                self.dict_process_step_data_frames[process_step_name][
                    load_type_uuid
                ] = pd.DataFrame(list_of_load_profile_entries)
        return self.dict_process_step_data_frames

    def convert_all_load_lists_to_gantt_chart_data_frames(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        convert_stream_load_profile_entries: bool = True,
        convert_process_state_load_profiles: bool = True,
    ):
        if convert_stream_load_profile_entries is True:
            for (
                stream_name,
                stream_load_profile_collection,
            ) in self.dict_stream_load_profile_collections.items():
                for (
                    load_type_uuid,
                    list_of_load_profile_entries,
                ) in stream_load_profile_collection.dict_of_load_entry_lists.items():
                    load_profile_entry_post_processor = LoadProfileEntryPostProcessor()
                    stream_data_frame = load_profile_entry_post_processor.convert_time_series_to_resampled_load_profile_meta_data(
                        object_name=stream_name,
                        object_type="Stream",
                        list_of_load_profile_entries=list_of_load_profile_entries,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    if stream_name not in self.dict_stream_data_frames_gantt_chart:
                        self.dict_stream_data_frames_gantt_chart[stream_name] = {
                            load_type_uuid: stream_data_frame
                        }
                    else:
                        self.dict_stream_data_frames_gantt_chart[stream_name][
                            load_type_uuid
                        ] = stream_data_frame
        if convert_process_state_load_profiles is True:
            for (
                process_step_name,
                process_step_load_profile_collection,
            ) in self.dict_process_step_load_profile_collections.items():
                for (
                    load_type_uuid,
                    list_of_load_profile_entries,
                ) in (
                    process_step_load_profile_collection.dict_of_load_entry_lists.items()
                ):
                    load_profile_entry_post_processor = LoadProfileEntryPostProcessor()
                    process_step_data_frame_meta_data = load_profile_entry_post_processor.convert_time_series_to_resampled_load_profile_meta_data(
                        object_name=process_step_name,
                        object_type="Process Step",
                        list_of_load_profile_entries=list_of_load_profile_entries,
                        start_date=start_date,
                        end_date=end_date,
                    )

                    if (
                        process_step_name
                        not in self.dict_process_step_data_frames_gantt_chart
                    ):
                        self.dict_process_step_data_frames_gantt_chart[
                            process_step_name
                        ] = {load_type_uuid: process_step_data_frame_meta_data}
                    else:
                        self.dict_process_step_data_frames_gantt_chart[
                            process_step_name
                        ][load_type_uuid] = process_step_data_frame_meta_data


@dataclass
class ProcessStepEnergyDataHandler:
    """Contains the specific energy data to convert the production plan to load profiles"""

    process_step_name: str
    process_state_energy_dict: dict[str, ProcessStateEnergyData] = field(
        default_factory=dict
    )
    dict_of_load_type: dict[str, LoadType] = field(default_factory=dict)
    # First key is the state name
    # Second key is the load type of the respective load

    def get_process_state_energy_data(
        self, process_state_name: str
    ) -> ProcessStateEnergyData:
        return self.process_state_energy_dict[process_state_name]

    def get_dict_of_load_type(self) -> dict[str, LoadType]:
        return self.dict_of_load_type

    def add_process_state_energy_data(
        self,
        process_state_name: str,
        process_state_energy_data: ProcessStateEnergyData,
    ):
        if process_state_name not in self.process_state_energy_dict:
            self.process_state_energy_dict[process_state_name] = {}

        self.process_state_energy_dict[process_state_name] = process_state_energy_data

        self.dict_of_load_type.update(process_state_energy_data.get_dict_of_loads())


@dataclass
class StreamSpecificEnergyDataHandler:
    stream_energy_data_dict: dict[str, StreamEnergyData] = field(default_factory=dict)
    dict_of_all_load_types: dict[str, LoadType] = field(default_factory=dict)

    def add_stream_energy_data(self, stream_energy_data: StreamEnergyData):
        stream_name = stream_energy_data.stream_name
        if stream_name not in self.stream_energy_data_dict:
            self.stream_energy_data_dict[stream_name] = stream_energy_data

        self.dict_of_all_load_types.update(stream_energy_data.load_dict)

    def get_stream_energy_data(self, stream_name: str) -> StreamEnergyData:
        return self.stream_energy_data_dict[stream_name]

    def get_list_of_load_types(self) -> dict[str, LoadType]:
        return self.dict_of_all_load_types


class LoadProfileHandler:
    def __init__(self) -> None:
        self.target_power_unit: str = "MW"
        self.target_energy_unit: str = "MJ"
        self.load_profile_collection: LoadProfileCollection = LoadProfileCollection(
            target_power_unit=self.target_power_unit,
            target_energy_unit=self.target_energy_unit,
        )
        self.process_step_energy_data_handler_dict: dict[
            str, ProcessStepEnergyDataHandler
        ] = {}
        self.stream_energy_data_collection: StreamSpecificEnergyDataHandler = (
            StreamSpecificEnergyDataHandler()
        )

    def get_list_of_load_types(self) -> list[LoadType]:
        output_list_of_load_types = (
            self.stream_energy_data_collection.get_list_of_load_types()
        )

        for (
            process_step_energy_data,
        ) in self.process_step_energy_data_handler_dict.values():
            list_of_process_step_energy_data_load_types = (
                process_step_energy_data.get_list_load_types()
            )

            output_list_of_load_types = list(
                set(
                    output_list_of_load_types
                    + list_of_process_step_energy_data_load_types
                )
            )
        return output_list_of_load_types

    def get_list_of_list_of_all_load_profile_entries(
        self,
    ) -> list[list[LoadProfileEntry]]:
        list_of_list_of_all_load_profile_entries = []
        for (
            stream_name,
            stream_load_profile_collection,
        ) in self.load_profile_collection.dict_stream_load_profile_collections.items():
            for (
                load_type_uuid,
                list_of_load_profiles_entries,
            ) in stream_load_profile_collection.dict_of_load_entry_lists.items():
                list_of_list_of_all_load_profile_entries.append(
                    list_of_load_profiles_entries
                )

        for (
            process_step_name,
            process_step_load_profile_collections,
        ) in (
            self.load_profile_collection.dict_process_step_load_profile_collections.items()
        ):
            for (
                load_type_uuid,
                list_of_load_profiles_entries,
            ) in process_step_load_profile_collections.dict_of_load_entry_lists.items():
                list_of_list_of_all_load_profile_entries.append(
                    list_of_load_profiles_entries
                )
        return list_of_list_of_all_load_profile_entries

    def create_load_profile_entry_from_stream_entry(
        self,
        stream_entry: ContinuousStreamProductionPlanEntry
        | BatchStreamProductionPlanEntry,
        stream_energy_data: StreamLoadEnergyData,
    ) -> LoadProfileEntry:
        if isinstance(stream_entry, ContinuousStreamProductionPlanEntry):
            energy_demand = (
                stream_entry.total_mass * stream_energy_data.specific_energy_demand
            )
        elif isinstance(stream_entry, BatchStreamProductionPlanEntry):
            energy_demand = (
                stream_entry.batch_mass_value
                * stream_energy_data.specific_energy_demand
            )
        else:
            raise Exception("Unexpected datatype in stream entry")
        average_power_consumption = (
            energy_demand
            / (stream_entry.end_time - stream_entry.start_time).total_seconds()
        )
        load_profile_entry = LoadProfileEntry(
            load_type=stream_energy_data.load_type,
            start_time=stream_entry.start_time,
            end_time=stream_entry.end_time,
            energy_quantity=energy_demand,
            energy_unit=stream_energy_data.energy_unit,
            average_power_consumption=average_power_consumption,
            power_unit=self.target_power_unit,
        )

        return load_profile_entry

    def create_all_load_profiles_entries_from_stream_entry(
        self,
        stream_entry: ContinuousStreamProductionPlanEntry
        | BatchStreamProductionPlanEntry,
    ):
        if (
            stream_entry.name
            in self.stream_energy_data_collection.stream_energy_data_dict
        ):
            stream_energy_data = (
                self.stream_energy_data_collection.get_stream_energy_data(
                    stream_name=stream_entry.name
                )
            )
            for (
                stream_energy_load_data
            ) in stream_energy_data.dict_stream_load_energy_data.values():
                load_profile_entry = self.create_load_profile_entry_from_stream_entry(
                    stream_entry=stream_entry,
                    stream_energy_data=stream_energy_load_data,
                )

                self.load_profile_collection.append_stream_load_profile_entry(
                    stream_name=stream_entry.name,
                    load_type=stream_energy_load_data.load_type,
                    load_profile_entry=load_profile_entry,
                )

    def add_process_state_energy_data(
        self,
        process_step_name: str,
        process_state_name: str,
        process_state_energy_data: ProcessStateEnergyData,
    ):
        if process_step_name not in self.process_step_energy_data_handler_dict:
            self.process_step_energy_data_handler_dict[
                process_step_name
            ] = ProcessStepEnergyDataHandler(process_step_name=process_step_name)
        self.process_step_energy_data_handler_dict[
            process_step_name
        ].add_process_state_energy_data(
            process_state_name=process_state_name,
            process_state_energy_data=process_state_energy_data,
        )

    def get_process_step_energy_data_collection(
        self, process_step_name: str
    ) -> ProcessStepEnergyDataHandler:
        return self.process_step_energy_data_handler_dict[process_step_name]

    def create_all_load_profiles_from_process_state_entry(
        self,
        process_state_entry: ProcessStepProductionPlanEntry,
    ):
        if (
            process_state_entry.process_step_name
            in self.process_step_energy_data_handler_dict
        ):
            energy_data_collection = self.process_step_energy_data_handler_dict[
                process_state_entry.process_step_name
            ]

            if (
                process_state_entry.process_state_name
                in energy_data_collection.process_state_energy_dict
            ):
                process_state_energy_data = (
                    energy_data_collection.get_process_state_energy_data(
                        process_state_name=process_state_entry.process_state_name,
                    )
                )
                for (
                    process_state_energy_data
                ) in process_state_energy_data.dict_of_load_energy_data.values():
                    if isinstance(
                        process_state_energy_data,
                        ProcessStateEnergyLoadDataBasedOnStreamMass,
                    ) and isinstance(
                        process_state_entry,
                        ProcessStepProductionPlanEntryWithInputStreamState,
                    ):
                        total_mass = process_state_entry.total_stream_mass
                        energy_demand = (
                            total_mass
                            * process_state_energy_data.specific_energy_demand
                        )

                        average_power_consumption = (
                            energy_demand
                            / (
                                process_state_entry.end_time
                                - process_state_entry.start_time
                            ).total_seconds()
                        )
                        load_profile_entry = LoadProfileEntry(
                            load_type=process_state_energy_data.load_type,
                            start_time=process_state_entry.start_time,
                            end_time=process_state_entry.end_time,
                            energy_quantity=energy_demand,
                            energy_unit=process_state_energy_data.energy_unit,
                            average_power_consumption=average_power_consumption,
                            power_unit=self.target_power_unit,
                        )
                        self.load_profile_collection.append_process_step_energy_data_entry(
                            process_step_name=process_state_entry.process_step_name,
                            load_type=process_state_energy_data.load_type,
                            load_profile_entry=load_profile_entry,
                        )
