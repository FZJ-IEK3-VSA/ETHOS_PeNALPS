from dataclasses import field

import pandas

from ethos_penalps.data_classes import (
    Commodity,
    EmptyMetaDataInformation,
    LoadProfileMetaData,
    ProcessStepDataFrameMetaInformation,
    StorageDataFrameMetaInformation,
)
from ethos_penalps.load_profile_calculator import LoadProfileHandlerSimulation
from ethos_penalps.post_processing.load_profile_handler_post_simulation import (
    LoadProfileCollectionPostProcessing,
)
from ethos_penalps.post_processing.report_generator.report_options import (
    ReportGeneratorOptions,
)
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream import (
    BatchStreamProductionPlanEntry,
    ContinuousStreamProductionPlanEntry,
    StreamDataFrameMetaInformation,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class PostProcessSimulationDataHandler:
    def __init__(
        self,
        production_plan: ProductionPlan,
        report_options: ReportGeneratorOptions,
    ) -> None:
        self.production_plan: ProductionPlan = production_plan
        self.load_profile_handler_simulation: LoadProfileHandlerSimulation = (
            self.production_plan.load_profile_handler
        )
        self.report_options: ReportGeneratorOptions = report_options
        self.load_profile_collection_post_processing = LoadProfileCollectionPostProcessing(
            load_profile_collection=self.load_profile_handler_simulation.load_profile_collection,
            report_options=report_options,
        )
        self.dict_of_stream_meta_data_data_frames: dict[
            str, StreamDataFrameMetaInformation | EmptyMetaDataInformation
        ] = {}
        self.dict_of_storage_meta_data_data_frames: dict[
            str,
            dict[Commodity, StorageDataFrameMetaInformation | EmptyMetaDataInformation],
        ] = {}

        self.dict_of_process_step_data_frames: dict[
            str, ProcessStepDataFrameMetaInformation | EmptyMetaDataInformation
        ] = {}
        self.postprocessing_is_initialized: bool = False

    def start_post_processing(self):
        logger.info("Start load profile post processing")
        self.load_profile_collection_post_processing.start_post_processing()
        logger.info("Stream Entry Post Processing")
        self.convert_stream_entries_to_meta_data_data_frames()
        self.convert_process_state_dictionary_to_list_of_data_frames()
        self.convert_list_of_storage_entries_to_meta_data()
        self.postprocessing_is_initialized = True

    def convert_stream_entries_to_meta_data_data_frames(
        self,
    ):
        for (
            stream_name,
            list_of_stream_entries,
        ) in self.production_plan.stream_state_dict.items():
            stream_data_frame = pandas.DataFrame(list_of_stream_entries)
            stream_data_frame_meta_information: (
                EmptyMetaDataInformation | StreamDataFrameMetaInformation
            )
            if stream_data_frame.empty is True:
                stream_data_frame_meta_information = EmptyMetaDataInformation(
                    name=stream_name, object_type="stream"
                )
                self.dict_of_stream_meta_data_data_frames[stream_name] = (
                    stream_data_frame_meta_information
                )
            else:
                first_start_time = stream_data_frame["start_time"].min()
                last_end_time = stream_data_frame["end_time"].max()
                first_stream_entry = list_of_stream_entries[0]

                if isinstance(first_stream_entry, ContinuousStreamProductionPlanEntry):
                    stream_type = first_stream_entry.stream_type
                    mass_unit = first_stream_entry.mass_unit

                elif isinstance(first_stream_entry, BatchStreamProductionPlanEntry):
                    stream_type = first_stream_entry.stream_type
                    mass_unit = first_stream_entry.batch_mass_unit

                else:
                    raise Exception("Unexpected datatype here")
                if first_stream_entry.name_to_display is None:
                    name_to_display = first_stream_entry.name
                else:
                    name_to_display = first_stream_entry.name_to_display
                stream_data_frame_meta_information = StreamDataFrameMetaInformation(
                    data_frame=stream_data_frame,
                    stream_name=stream_name,
                    first_start_time=first_start_time,
                    last_end_time=last_end_time,
                    stream_type=stream_type,
                    mass_unit=mass_unit,
                    commodity=first_stream_entry.commodity,
                    name_to_display=name_to_display,
                )
                self.dict_of_stream_meta_data_data_frames[stream_name] = (
                    stream_data_frame_meta_information
                )

    def convert_process_state_dictionary_to_list_of_data_frames(
        self,
    ):
        for (
            process_step_name,
            list_of_process_state_entries,
        ) in self.production_plan.process_step_states_dict.items():
            process_state_data_frame = pandas.DataFrame(list_of_process_state_entries)
            if process_state_data_frame.empty is True:
                process_step_data_meta_information = EmptyMetaDataInformation(
                    name=process_step_name, object_type="process step"
                )
                self.dict_of_process_step_data_frames[process_step_name] = (
                    process_step_data_meta_information
                )

            else:
                unique_process_state_names = process_state_data_frame[
                    "process_state_name"
                ].unique()
                first_start_time = process_state_data_frame["start_time"].min()
                last_end_time = process_state_data_frame["end_time"].max()
                process_step_data_meta_information = (
                    ProcessStepDataFrameMetaInformation(
                        data_frame=process_state_data_frame,
                        process_step_name=process_step_name,
                        list_of_process_state_names=unique_process_state_names,
                        first_start_time=first_start_time,
                        last_end_time=last_end_time,
                    )
                )
                self.dict_of_process_step_data_frames[process_step_name] = (
                    process_step_data_meta_information
                )

    def convert_list_of_storage_entries_to_meta_data(self):
        for process_step_name in self.production_plan.storage_state_dict:
            self.dict_of_storage_meta_data_data_frames[process_step_name] = {}
            for commodity in self.production_plan.storage_state_dict[process_step_name]:
                list_of_storage_entries = self.production_plan.storage_state_dict[
                    process_step_name
                ][commodity]
                storage_entry_data_frame = pandas.DataFrame(list_of_storage_entries)
                if storage_entry_data_frame.empty is True:
                    storage_meta_data = EmptyMetaDataInformation(
                        name=process_step_name, object_type="storage"
                    )
                    self.dict_of_storage_meta_data_data_frames[process_step_name][
                        commodity
                    ] = storage_meta_data
                else:
                    storage_meta_data = StorageDataFrameMetaInformation(
                        data_frame=storage_entry_data_frame,
                        process_step_name=process_step_name,
                        commodity=commodity,
                        first_start_time=storage_entry_data_frame["start_time"].min(),
                        last_end_time=storage_entry_data_frame["end_time"].max(),
                        mass_unit="T",
                    )
                    self.dict_of_storage_meta_data_data_frames[process_step_name][
                        commodity
                    ] = storage_meta_data

    def get_list_object_meta_data(
        self,
        list_of_object_names: list[str],
        maximum_number_of_rows: int,
        include_stream_load_profiles: bool = True,
        include_process_state_load_profiles: bool = True,
        include_internal_storage_gantt_chart: bool = False,
        include_external_storage_gantt_chart: bool = True,
    ) -> list[
        list[
            StreamDataFrameMetaInformation
            | ProcessStepDataFrameMetaInformation
            | LoadProfileMetaData
            | StorageDataFrameMetaInformation
        ]
    ]:
        list_of_list_of_object_meta_data: list[list] = [[]]

        list_of_object_meta_data = list_of_list_of_object_meta_data[0]
        for object_name in list_of_object_names:
            intermediate_list = []
            if include_external_storage_gantt_chart is True:
                if object_name in self.dict_of_storage_meta_data_data_frames:
                    for commodity in self.dict_of_storage_meta_data_data_frames[
                        object_name
                    ]:
                        intermediate_list.append(
                            self.dict_of_storage_meta_data_data_frames[object_name][
                                commodity
                            ]
                        )

            for stream_meta_data in self.dict_of_stream_meta_data_data_frames.values():
                if object_name == stream_meta_data.stream_name:
                    if (
                        include_stream_load_profiles is True
                        and object_name
                        in self.production_plan.load_profile_handler.load_profile_collection.dict_stream_data_frames_gantt_chart
                    ):
                        dict_of_load_profile_stream_meta_data_frame = self.production_plan.load_profile_handler.load_profile_collection.dict_stream_data_frames_gantt_chart[
                            object_name
                        ]
                        for (
                            stream_load_profile_meta_data_frame
                        ) in dict_of_load_profile_stream_meta_data_frame.values():
                            intermediate_list.append(
                                stream_load_profile_meta_data_frame
                            )

                    intermediate_list.append(stream_meta_data)

            for (
                process_step_meta_data
            ) in self.dict_of_process_step_data_frames.values():
                if process_step_meta_data.process_step_name == object_name:
                    if (
                        include_process_state_load_profiles is True
                        and object_name
                        in self.production_plan.load_profile_handler.load_profile_collection.dict_process_step_data_frames_gantt_chart
                    ):
                        dict_of_load_profile_process_step_data = self.production_plan.load_profile_handler.load_profile_collection.dict_process_step_data_frames_gantt_chart[
                            object_name
                        ]
                        for (
                            process_step_meta_data_load_profile
                        ) in dict_of_load_profile_process_step_data.values():
                            intermediate_list.append(
                                process_step_meta_data_load_profile
                            )
                    if include_internal_storage_gantt_chart is True:
                        if object_name in self.dict_of_storage_meta_data_data_frames:
                            for commodity in self.dict_of_storage_meta_data_data_frames[
                                object_name
                            ]:
                                intermediate_list.append(
                                    self.dict_of_storage_meta_data_data_frames[
                                        object_name
                                    ][commodity]
                                )
                    intermediate_list.append(process_step_meta_data)
            if (
                len(intermediate_list) + len(list_of_object_meta_data)
                > maximum_number_of_rows
            ):
                list_of_list_of_object_meta_data.append(intermediate_list)
                list_of_object_meta_data = intermediate_list
            else:
                list_of_object_meta_data.extend(intermediate_list)

        return list_of_list_of_object_meta_data

    def get_stream_meta_data_by_name(
        self, stream_name: str
    ) -> StreamDataFrameMetaInformation | EmptyMetaDataInformation:
        stream_meta_data_data_frame = self.dict_of_stream_meta_data_data_frames[
            stream_name
        ]
        return stream_meta_data_data_frame

    def get_process_step_meta_data_by_name(
        self, process_step_name: str
    ) -> ProcessStepDataFrameMetaInformation | EmptyMetaDataInformation:
        process_step_meta_data_data_frame = self.dict_of_process_step_data_frames[
            process_step_name
        ]
        return process_step_meta_data_data_frame

    def get_storage_meta_data_by_name(
        self, storage_name: str
    ) -> StorageDataFrameMetaInformation | EmptyMetaDataInformation:
        storage_meta_data_data_frame = next(
            iter(self.dict_of_storage_meta_data_data_frames[storage_name].values())
        )
        return storage_meta_data_data_frame
