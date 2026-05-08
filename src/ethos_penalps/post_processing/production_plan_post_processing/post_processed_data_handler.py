from __future__ import annotations

import os
import pathlib
from dataclasses import field
from typing import TYPE_CHECKING

import pandas

from ethos_penalps.data_classes import (
    Commodity,
    EmptyLoadProfileMetadata,
    EmptyMetaDataInformation,
    LoadProfileMetaData,
    LoadProfileMetaDataResampled,
    ProcessStepDataFrameMetaInformation,
    StorageDataFrameMetaInformation,
)

if TYPE_CHECKING:
    from ethos_penalps.organizational_agents.network_level import NetworkLevel
from ethos_penalps.energy.load_profile_calculator import LoadProfileHandlerSimulation
from ethos_penalps.post_processing.load_profiles.load_profile_handler_post_simulation import (
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
from ethos_penalps.utilities.exceptions_and_warnings import UnexpectedCase
from ethos_penalps.utilities.general_functions import dataframe_from_dataclasses
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.type_aliases import numbers_alias

logger = PeNALPSLogger.get_logger_without_handler()


class PostProcessSimulationDataHandler:
    def __init__(
        self,
        production_plan: ProductionPlan,
        report_options: ReportGeneratorOptions,
    ) -> None:
        self.production_plan: ProductionPlan = production_plan
        self.load_profile_handler_simulation: LoadProfileHandlerSimulation = self.production_plan.load_profile_handler
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
        self.convert_stream_entries_to_meta_data_data_frames()
        self.convert_process_state_dictionary_to_list_of_data_frames()
        if self.report_options.gantt_charts.include_storage_gantt_charts is True:
            self.convert_list_of_storage_entries_to_meta_data()
        self.postprocessing_is_initialized = True
        if self.report_options.store_load_profiles_to_csv is True:
            self.store_all_load_profiles_to_csv()
        if self.report_options.store_production_plan_to_csv is True:
            self.store_production_plan_to_csv()

    def convert_stream_entries_to_meta_data_data_frames(
        self,
    ):
        for (
            stream_name,
            list_of_stream_entries,
        ) in self.production_plan.stream_state_dict.items():
            stream_data_frame = dataframe_from_dataclasses(list_of_stream_entries)
            stream_data_frame_meta_information: EmptyMetaDataInformation | StreamDataFrameMetaInformation
            if stream_data_frame.empty is True:
                stream_data_frame_meta_information = EmptyMetaDataInformation(name=stream_name, object_type="stream")
                self.dict_of_stream_meta_data_data_frames[stream_name] = stream_data_frame_meta_information
            else:
                first_start_time = stream_data_frame["start_time"].min()
                last_end_time = stream_data_frame["end_time"].max()
                first_stream_entry = list_of_stream_entries[0]

                if isinstance(first_stream_entry, ContinuousStreamProductionPlanEntry):
                    stream_type = first_stream_entry.stream_type
                    mass_unit = first_stream_entry.mass_unit

                elif isinstance(first_stream_entry, BatchStreamProductionPlanEntry):
                    stream_type = first_stream_entry.stream_type
                    mass_unit = first_stream_entry.mass_unit

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
                self.dict_of_stream_meta_data_data_frames[stream_name] = stream_data_frame_meta_information

    def convert_process_state_dictionary_to_list_of_data_frames(
        self,
    ):
        for (
            process_step_name,
            list_of_process_state_entries,
        ) in self.production_plan.process_step_states_dict.items():
            process_state_data_frame = dataframe_from_dataclasses(list_of_process_state_entries)
            process_step_data_meta_information: EmptyMetaDataInformation | ProcessStepDataFrameMetaInformation
            if process_state_data_frame.empty is True:
                process_step_data_meta_information = EmptyMetaDataInformation(
                    name=process_step_name, object_type="process step"
                )
                self.dict_of_process_step_data_frames[process_step_name] = process_step_data_meta_information

            else:
                unique_process_state_names = process_state_data_frame["process_state_name"].unique()
                first_start_time = process_state_data_frame["start_time"].min()
                last_end_time = process_state_data_frame["end_time"].max()
                process_step_data_meta_information = ProcessStepDataFrameMetaInformation(
                    data_frame=process_state_data_frame,
                    process_step_name=process_step_name,
                    list_of_process_state_names=unique_process_state_names,
                    first_start_time=first_start_time,
                    last_end_time=last_end_time,
                )
                self.dict_of_process_step_data_frames[process_step_name] = process_step_data_meta_information

    def convert_list_of_storage_entries_to_meta_data(self):
        for process_step_name in self.production_plan.storage_state_dict:
            self.dict_of_storage_meta_data_data_frames[process_step_name] = {}
            for commodity in self.production_plan.storage_state_dict[process_step_name]:
                storage_meta_data: EmptyMetaDataInformation | StorageDataFrameMetaInformation
                list_of_storage_entries = self.production_plan.storage_state_dict[process_step_name][commodity]
                storage_entry_data_frame = dataframe_from_dataclasses(list_of_storage_entries)
                if storage_entry_data_frame.empty is True:
                    storage_meta_data = EmptyMetaDataInformation(name=process_step_name, object_type="storage")
                    self.dict_of_storage_meta_data_data_frames[process_step_name][commodity.name] = storage_meta_data
                else:
                    storage_meta_data = StorageDataFrameMetaInformation(
                        data_frame=storage_entry_data_frame,
                        process_step_name=process_step_name,
                        commodity=commodity,
                        first_start_time=storage_entry_data_frame["start_time"].min(),
                        last_end_time=storage_entry_data_frame["end_time"].max(),
                        mass_unit="T",
                    )
                    self.dict_of_storage_meta_data_data_frames[process_step_name][commodity] = storage_meta_data

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
                    for commodity in self.dict_of_storage_meta_data_data_frames[object_name]:
                        intermediate_list.append(self.dict_of_storage_meta_data_data_frames[object_name][commodity])

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
                        for stream_load_profile_meta_data_frame in dict_of_load_profile_stream_meta_data_frame.values():
                            intermediate_list.append(stream_load_profile_meta_data_frame)

                    intermediate_list.append(stream_meta_data)

            for process_step_meta_data in self.dict_of_process_step_data_frames.values():
                if process_step_meta_data.process_step_name == object_name:
                    if (
                        include_process_state_load_profiles is True
                        and object_name
                        in self.production_plan.load_profile_handler.load_profile_collection.dict_process_step_data_frames_gantt_chart
                    ):
                        dict_of_load_profile_process_step_data = self.production_plan.load_profile_handler.load_profile_collection.dict_process_step_data_frames_gantt_chart[
                            object_name
                        ]
                        for process_step_meta_data_load_profile in dict_of_load_profile_process_step_data.values():
                            intermediate_list.append(process_step_meta_data_load_profile)
                    if include_internal_storage_gantt_chart is True:
                        if object_name in self.dict_of_storage_meta_data_data_frames:
                            for commodity in self.dict_of_storage_meta_data_data_frames[object_name]:
                                intermediate_list.append(
                                    self.dict_of_storage_meta_data_data_frames[object_name][commodity]
                                )
                    intermediate_list.append(process_step_meta_data)
            if len(intermediate_list) + len(list_of_object_meta_data) > maximum_number_of_rows:
                list_of_list_of_object_meta_data.append(intermediate_list)
                list_of_object_meta_data = intermediate_list
            else:
                list_of_object_meta_data.extend(intermediate_list)

        return list_of_list_of_object_meta_data

    def get_stream_meta_data_by_name(
        self, stream_name: str
    ) -> StreamDataFrameMetaInformation | EmptyMetaDataInformation:
        stream_meta_data_data_frame = self.dict_of_stream_meta_data_data_frames[stream_name]
        return stream_meta_data_data_frame

    def get_process_step_meta_data_by_name(
        self, process_step_name: str
    ) -> ProcessStepDataFrameMetaInformation | EmptyMetaDataInformation:
        process_step_meta_data_data_frame = self.dict_of_process_step_data_frames[process_step_name]
        return process_step_meta_data_data_frame

    def get_storage_meta_data_by_name(
        self, storage_name: str
    ) -> StorageDataFrameMetaInformation | EmptyMetaDataInformation:
        if storage_name in self.dict_of_storage_meta_data_data_frames:
            storage_meta_data_data_frame = next(iter(self.dict_of_storage_meta_data_data_frames[storage_name].values()))
        else:
            storage_meta_data_data_frame = EmptyMetaDataInformation(name=storage_name, object_type="Storage")
        return storage_meta_data_data_frame

    def get_list_of_stream_load_profile_resampled_meta_data(
        self, stream_name: str
    ) -> list[LoadProfileMetaDataResampled]:

        list_of_resampled_load_profile_meta_data = []
        dict_stream_load_profile_collections = (
            self.load_profile_collection_post_processing.dict_stream_load_profile_collections
        )

        if stream_name in dict_stream_load_profile_collections:
            stream_load_profile_collections = dict_stream_load_profile_collections[stream_name]
            for (
                load_type_uuid,
                load_type,
            ) in stream_load_profile_collections.load_type_dict.items():
                load_entry_meta_data_resampled = stream_load_profile_collections.dict_of_load_entry_meta_data_resampled[
                    load_type_uuid
                ]

                list_of_resampled_load_profile_meta_data.append(load_entry_meta_data_resampled)

        return list_of_resampled_load_profile_meta_data

    def get_list_of_stream_load_profile_meta_data(self, stream_name: str) -> list[LoadProfileMetaData]:

        list_of_load_profile_meta_data = []
        dict_stream_load_profile_collections = (
            self.load_profile_collection_post_processing.dict_stream_load_profile_collections
        )
        if stream_name in dict_stream_load_profile_collections:
            stream_load_profile_collections = dict_stream_load_profile_collections[stream_name]
            for (
                load_type_uuid,
                load_type,
            ) in stream_load_profile_collections.load_type_dict.items():
                load_entry_meta_data = stream_load_profile_collections.dict_of_load_entry_meta_data[load_type_uuid]

                list_of_load_profile_meta_data.append(load_entry_meta_data)

        return list_of_load_profile_meta_data

    def get_list_of_process_step_load_profile_meta_data(self, process_step_name: str) -> list[LoadProfileMetaData]:
        list_of_load_profile_meta_data = []
        dict_process_step_load_profile_collections = (
            self.load_profile_collection_post_processing.dict_process_step_load_profile_collections
        )

        if process_step_name in dict_process_step_load_profile_collections:
            process_step_load_profile_collections = dict_process_step_load_profile_collections[process_step_name]
            for (
                load_type_uuid,
                load_type,
            ) in process_step_load_profile_collections.load_type_dict.items():
                load_entry_meta_data = process_step_load_profile_collections.dict_of_load_entry_meta_data[
                    load_type_uuid
                ]

                list_of_load_profile_meta_data.append(load_entry_meta_data)

        return list_of_load_profile_meta_data

    def get_list_of_process_step_load_profile_meta_data_resampled(
        self, process_step_name: str
    ) -> list[LoadProfileMetaDataResampled]:
        list_of_load_profile_meta_data_resampled = []
        dict_process_step_load_profile_collections = (
            self.load_profile_collection_post_processing.dict_process_step_load_profile_collections
        )
        if process_step_name in dict_process_step_load_profile_collections:
            process_step_load_profile_collections = dict_process_step_load_profile_collections[process_step_name]
            for (
                load_type_uuid,
                load_type,
            ) in process_step_load_profile_collections.load_type_dict.items():
                load_entry_meta_data_resampled = (
                    process_step_load_profile_collections.dict_of_load_entry_meta_data_resampled[load_type_uuid]
                )

                list_of_load_profile_meta_data_resampled.append(load_entry_meta_data_resampled)

        return list_of_load_profile_meta_data_resampled

    def store_all_load_profiles_to_csv(self):
        dict_process_step_load_profile_collections = (
            self.load_profile_collection_post_processing.dict_process_step_load_profile_collections
        )
        result_folder = self.report_options.path_to_results_folder
        if self.report_options.path_to_results_folder is None:
            raise Exception("The results path has not been set.")
        elif isinstance(self.report_options.path_to_results_folder, str):
            path_to_process_step_results = pathlib.Path(result_folder).joinpath("process_step_load_profiles")
        path_to_process_step_results.mkdir(parents=True, exist_ok=True)
        for (
            process_step_name,
            process_step_load_profile_collections,
        ) in dict_process_step_load_profile_collections.items():
            for (
                load_type_uuid,
                load_type,
            ) in process_step_load_profile_collections.load_type_dict.items():
                load_entry_meta_data_resampled = (
                    process_step_load_profile_collections.dict_of_load_entry_meta_data_resampled[load_type_uuid]
                )
                file_name_process_step_resampled = process_step_name + "_" + load_type.name + "_resampled.csv"
                path_to_process_step_file_resampled = pathlib.Path(path_to_process_step_results).joinpath(
                    file_name_process_step_resampled
                )

                load_entry_meta_data_resampled.data_frame.to_csv(path_or_buf=path_to_process_step_file_resampled)
                load_entry_meta_data = process_step_load_profile_collections.dict_of_load_entry_meta_data[
                    load_type_uuid
                ]
                file_name_process_step = process_step_name + "_" + load_type.name + ".csv"
                path_to_process_step_file = pathlib.Path(path_to_process_step_results).joinpath(file_name_process_step)
                load_entry_meta_data.data_frame.to_csv(path_or_buf=path_to_process_step_file)

        dict_stream_load_profile_collections = (
            self.load_profile_collection_post_processing.dict_stream_load_profile_collections
        )
        result_folder = self.report_options.path_to_results_folder
        path_to_stream_results = pathlib.Path(result_folder).joinpath("stream_load_profiles")
        path_to_stream_results.mkdir(parents=True, exist_ok=True)
        for (
            stream_name,
            stream_load_profile_collections,
        ) in dict_stream_load_profile_collections.items():
            for (
                load_type_uuid,
                load_type,
            ) in stream_load_profile_collections.load_type_dict.items():
                load_entry_meta_data_resampled = stream_load_profile_collections.dict_of_load_entry_meta_data_resampled[
                    load_type_uuid
                ]
                file_name_stream_resampled = stream_name + "_" + load_type.name + "_resampled.csv"
                path_to_stream_file_resampled = pathlib.Path(path_to_stream_results).joinpath(
                    file_name_stream_resampled
                )
                load_entry_meta_data_resampled.data_frame.to_csv(path_or_buf=path_to_stream_file_resampled)
                load_entry_meta_data = stream_load_profile_collections.dict_of_load_entry_meta_data[load_type_uuid]
                file_name_stream = stream_name + "_" + load_type.name + ".csv"
                path_to_stream_file = pathlib.Path(path_to_stream_results).joinpath(file_name_stream)
                load_entry_meta_data.data_frame.to_csv(path_or_buf=path_to_stream_file)
        result_folder = self.report_options.path_to_results_folder
        path_to_combined_load_profiles = pathlib.Path(result_folder).joinpath("combined_load_profiles")
        path_to_combined_load_profiles.mkdir(parents=True, exist_ok=True)

        for (
            load_uuid,
            combined_load_profile_meta_data,
        ) in self.load_profile_collection_post_processing.dict_of_total_process_load_profiles_resampled.items():
            file_name_stream_resampled = (
                combined_load_profile_meta_data.load_type.name + "_combined_load_profile" + ".csv"
            )
            path_to_stream_file_resampled = pathlib.Path(path_to_combined_load_profiles).joinpath(
                file_name_stream_resampled
            )
            combined_load_profile_meta_data.data_frame.to_csv(path_or_buf=path_to_stream_file_resampled)
        pass

    def store_production_plan_to_csv(self):
        self.dict_of_stream_meta_data_data_frames

        path_to_stream_results = pathlib.Path(self.report_options.path_to_results_folder).joinpath("stream_plan")
        path_to_stream_results.mkdir(exist_ok=True)
        for key, current_meta_data in self.dict_of_stream_meta_data_data_frames.items():
            if isinstance(current_meta_data, EmptyMetaDataInformation):
                pass
            elif isinstance(current_meta_data, StreamDataFrameMetaInformation):
                path_to_output_data_frame = path_to_stream_results.joinpath(current_meta_data.name_to_display + ".csv")
                current_meta_data.data_frame.to_csv(path_or_buf=path_to_output_data_frame)
            else:
                raise UnexpectedCase("Unexpected data: " + str(current_meta_data) + "type for entry: " + str(key))
        path_to_storage_results = pathlib.Path(self.report_options.path_to_results_folder).joinpath("storage_plan")
        path_to_storage_results.mkdir(exist_ok=True)
        for (
            key,
            current_meta_data,
        ) in self.dict_of_storage_meta_data_data_frames.items():
            current_meta_data = next(iter(current_meta_data.values()))
            if isinstance(current_meta_data, EmptyMetaDataInformation):
                pass
            elif isinstance(current_meta_data, StorageDataFrameMetaInformation):
                path_to_output_data_frame = path_to_storage_results.joinpath(
                    current_meta_data.process_step_name + ".csv"
                )
                current_meta_data.data_frame.to_csv(path_or_buf=path_to_output_data_frame)
            else:
                raise UnexpectedCase("Unexpected data: " + str(current_meta_data) + "type for entry: " + str(key))

        path_to_process_step_results = pathlib.Path(self.report_options.path_to_results_folder).joinpath(
            "process_step_plan"
        )
        path_to_process_step_results.mkdir(exist_ok=True)
        for (
            key,
            current_meta_data,
        ) in self.dict_of_process_step_data_frames.items():
            if isinstance(current_meta_data, EmptyMetaDataInformation):
                pass
            elif isinstance(current_meta_data, ProcessStepDataFrameMetaInformation):
                path_to_output_data_frame = path_to_process_step_results.joinpath(
                    current_meta_data.process_step_name + ".csv"
                )
                current_meta_data.data_frame.to_csv(path_or_buf=path_to_output_data_frame)
            else:
                raise UnexpectedCase("Unexpected data: " + str(current_meta_data) + "type for entry: " + str(key))

    def store_production_orders_to_csv(
        self,
        list_of_network_level: list[NetworkLevel],
    ):
        """Stores production orders from all sinks and process chain storages
        to CSV files.

        Args:
            list_of_network_level (list[NetworkLevel]): List of all network levels
                in the enterprise.
        """
        from ethos_penalps.process_nodes.process_chain_storage import ProcessChainStorage
        from ethos_penalps.process_nodes.sink import Sink

        if self.report_options.path_to_results_folder is None:
            raise Exception("The results path has not been set.")

        path_to_order_results = pathlib.Path(self.report_options.path_to_results_folder).joinpath("production_orders")
        path_to_order_results.mkdir(parents=True, exist_ok=True)

        for network_level in list_of_network_level:
            main_sink = network_level.get_main_sink()
            if isinstance(main_sink, Sink):
                self._save_order_collection_to_csv(
                    order_collection=main_sink.order_collection,
                    order_distributor=main_sink.order_distributor,
                    node_name=main_sink.name,
                    output_directory=path_to_order_results,
                )
            elif isinstance(main_sink, ProcessChainStorage):
                self._save_order_collection_to_csv(
                    order_collection=main_sink.sink.order_collection,
                    order_distributor=main_sink.sink.order_distributor,
                    node_name=main_sink.name,
                    output_directory=path_to_order_results,
                )

    def _save_order_collection_to_csv(
        self,
        order_collection,
        order_distributor,
        node_name: str,
        output_directory: pathlib.Path,
    ):
        """Saves the total and per-chain order collections to CSV.

        Args:
            order_collection: The OrderCollection of the node.
            order_distributor: The order distributor containing splitted orders.
            node_name (str): Name of the node (sink or storage).
            output_directory (pathlib.Path): Directory to write CSV files to.
        """
        file_name = node_name + "_total_orders.csv"
        path_to_file = output_directory.joinpath(file_name)
        order_collection.order_data_frame.to_csv(path_or_buf=path_to_file)

        if hasattr(order_distributor, "dict_of_splitted_order"):
            for chain_identifier, splitted_order in order_distributor.dict_of_splitted_order.items():
                chain_name = chain_identifier if isinstance(chain_identifier, str) else chain_identifier.chain_name
                file_name = node_name + "_" + chain_name + "_orders.csv"
                path_to_file = output_directory.joinpath(file_name)
                splitted_order.order_data_frame.to_csv(path_or_buf=path_to_file)
