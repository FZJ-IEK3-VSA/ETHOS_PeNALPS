import datetime
from dataclasses import dataclass, field

import pandas

from ethos_penalps.data_classes import (
    EmptyLoadProfileMetadata,
    EmptyMetaDataInformation,
    LoadProfileEntry,
    LoadProfileMetaData,
    LoadProfileMetaDataResampled,
    LoadType,
)
from ethos_penalps.energy.load_profile_calculator import (
    LoadProfileCollection,
    ProcessStepLoadProfileEntryCollection,
    StreamLoadProfileEntryCollection,
)
from ethos_penalps.post_processing.load_profiles.load_profile_entry_post_processor import (
    LoadProfileEntryPostProcessor,
)
from ethos_penalps.post_processing.report_generator.report_options import (
    ReportGeneratorOptions,
)
from ethos_penalps.stream import BatchStream, ContinuousStream
from ethos_penalps.utilities.exceptions_and_warnings import UnexpectedCase
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.to_dataclass_conversions import create_load_profile_entry
from ethos_penalps.utilities.type_aliases import numbers_alias

logger = PeNALPSLogger.get_logger_without_handler()


@dataclass
class StreamLoadProfileEntryCollectionResampled:
    """Summarizes the load profile simulation results of a stream during
    the simulation."""

    object_name: str
    """Name of the stream
    """
    load_type_dict: dict[str, LoadType] = field(default_factory=dict)
    """Dict of all load types that are used for the stream. The key is a uuid
    string of the load type. The Value is the load type itself.
    """
    dict_of_load_entry_meta_data_resampled: dict[str, LoadProfileMetaDataResampled] = field(default_factory=dict)
    """The dictionary contains all load of profile entries for all load types
    of the stream. The key is the uuid string of the load type. The value is
    the list of all load profile entries for the load type.
    """
    dict_of_load_entry_meta_data: dict[str, LoadProfileMetaData] = field(default_factory=dict)

    def add_list_of_load_profile_meta_data_resampled(
        self,
        load_type: LoadType,
        list_of_load_profile_entry_meta_data: LoadProfileMetaDataResampled,
    ):
        """Adds a list LoadProfileEntries for a stream. This method is used
            in post processing to add a complete list of load profile entries.

        Args:
            load_type (LoadType): Defines the energy carrier which is used by the stream.
            load_profile_entry (LoadProfileEntry): Is a representation of the energy usage
                during defined time period of the stream.
        """
        self.load_type_dict[load_type.uuid] = load_type
        if load_type.uuid not in self.dict_of_load_entry_meta_data_resampled:
            self.dict_of_load_entry_meta_data_resampled[load_type.uuid] = list_of_load_profile_entry_meta_data
        else:
            logger.warning(
                """Tries to add another list of load profiles for load type: %s for stream: %s.
                This is an unexpected behavior. The original list of load profiles is:\n %s
                The following list has not been added:\n %s""",
                load_type,
                self.object_name,
                self.dict_of_load_entry_meta_data_resampled[load_type.uuid],
                list_of_load_profile_entry_meta_data,
            )

    def add_list_of_load_profile_meta_data(
        self,
        load_type: LoadType,
        list_of_load_profile_entry_meta_data: LoadProfileMetaData,
    ):
        """Adds a list LoadProfileEntries for a stream. This method is used
            in post processing to add a complete list of load profile entries.

        Args:
            load_type (LoadType): Defines the energy carrier which is used by the stream.
            load_profile_entry (LoadProfileEntry): Is a representation of the energy usage
                during defined time period of the stream.
        """
        self.load_type_dict[load_type.uuid] = load_type
        if load_type.uuid not in self.dict_of_load_entry_meta_data:
            self.dict_of_load_entry_meta_data[load_type.uuid] = list_of_load_profile_entry_meta_data
        else:
            logger.warning(
                """Tries to add another list of load profiles for load type: %s for stream: %s.
                This is an unexpected behavior. The original list of load profiles is:\n %s
                The following list has not been added:\n %s""",
                load_type,
                self.object_name,
                self.dict_of_load_entry_meta_data[load_type.uuid],
                list_of_load_profile_entry_meta_data,
            )


@dataclass
class ProcessStepLoadProfileEntryCollectionResampled:
    """Summarizes the load profile simulation results of a process step during
    the simulation."""

    object_name: str
    """Name of the process step
    """
    load_type_dict: dict[str, LoadType] = field(default_factory=dict)
    """Dict of all load types that are used for the process step. The key is a uuid
    string of the load type. The Value is the load type itself.
    """
    dict_of_load_entry_meta_data_resampled: dict[str, LoadProfileMetaDataResampled] = field(default_factory=dict)
    """# The dictionary contains all load of profile entries for all load types
    # of the stream. The first key is the string of the uuid of the load type.
    # The value is the list of all load profile entries for the load type.
    """
    dict_of_load_entry_meta_data: dict[str, LoadProfileMetaData] = field(default_factory=dict)

    def add_list_of_load_profile_meta_data_resampled(
        self,
        load_type: LoadType,
        list_of_load_profile_entry_meta_data: LoadProfileMetaDataResampled,
    ):
        """Adds a list LoadProfileEntries for a process step. This method is used
            in post processing to add a complete list of load profile entries.

        Args:
            load_type (LoadType): Defines the energy carrier which is used by the stream.
            load_profile_entry (LoadProfileEntry): Is a representation of the energy usage
                during defined time period of the process step.
        """
        self.load_type_dict[load_type.uuid] = load_type
        if load_type.uuid not in self.dict_of_load_entry_meta_data_resampled:
            self.dict_of_load_entry_meta_data_resampled[load_type.uuid] = list_of_load_profile_entry_meta_data
        else:
            logger.warning(
                """Tries to add another list of load profiles for load type: %s for process step: %s.
                This is an unexpected behavior. The original list of load profiles is:\n %s
                The following list has not been added:\n %s""",
                load_type,
                self.object_name,
                self.dict_of_load_entry_meta_data_resampled[load_type.uuid],
                list_of_load_profile_entry_meta_data,
            )

    def add_list_of_load_profile_meta_data(
        self,
        load_type: LoadType,
        list_of_load_profile_entry_meta_data: LoadProfileMetaData,
    ):
        """Adds a list LoadProfileEntries for a stream. This method is used
            in post processing to add a complete list of load profile entries.

        Args:
            load_type (LoadType): Defines the energy carrier which is used by the stream.
            load_profile_entry (LoadProfileEntry): Is a representation of the energy usage
                during defined time period of the stream.
        """
        self.load_type_dict[load_type.uuid] = load_type
        if load_type.uuid not in self.dict_of_load_entry_meta_data:
            self.dict_of_load_entry_meta_data[load_type.uuid] = list_of_load_profile_entry_meta_data
        else:
            logger.warning(
                """Tries to add another list of load profiles for load type: %s for stream: %s.
                This is an unexpected behavior. The original list of load profiles is:\n %s
                The following list has not been added:\n %s""",
                load_type,
                self.object_name,
                self.dict_of_load_entry_meta_data[load_type.uuid],
                list_of_load_profile_entry_meta_data,
            )


class LoadProfileCollectionPostProcessing:
    """Contains all post processed load profiles."""

    def __init__(
        self,
        load_profile_collection: LoadProfileCollection,
        report_options: ReportGeneratorOptions,
    ) -> None:
        """
        Args:
            load_profile_collection (LoadProfileCollection): LoadProfileCollection
                that contains all unprocessed simulation results.
            report_options (ReportGeneratorOptions): Object that contains
                modification options for the report.
        """
        self.load_profile_collection: LoadProfileCollection = load_profile_collection
        self.report_generator_options: ReportGeneratorOptions = report_options
        self.load_profile_entry_post_processor = LoadProfileEntryPostProcessor()
        # Contains the load profile data for all streams
        # The key is the stream name
        self.dict_stream_load_profile_collections: dict[str, StreamLoadProfileEntryCollectionResampled] = {}
        # Contains the load profile data for all streams
        # The key is the process step
        self.dict_process_step_load_profile_collections: dict[str, ProcessStepLoadProfileEntryCollectionResampled] = {}
        self.dict_of_total_process_load_profiles_resampled: dict[str, LoadProfileMetaDataResampled] = {}

    def start_post_processing(self):
        """Starts the post processing of the streams and process steps.
        The most important modifications are the resampling and extraction
        of meta data of the simulation results. This meta data are e.g.
        maximum power demand and total energy demand.
        """
        dict_stream_load_profile_collections: dict[str, StreamLoadProfileEntryCollectionResampled] = (
            self.resample_stream_load_profiles()
        )
        self.dict_stream_load_profile_collections.update(dict_stream_load_profile_collections)
        dict_process_step_load_profile_collections: dict[str, ProcessStepLoadProfileEntryCollectionResampled] = (
            self.resample_process_step_load_profiles()
        )
        self.dict_process_step_load_profile_collections.update(dict_process_step_load_profile_collections)

        self.create_combined_load_profiles_per_load_type()

    def resample_stream_load_profiles(
        self,
    ) -> dict[str, StreamLoadProfileEntryCollectionResampled]:
        """Post processes the stream simulation results. The most
        important modifications are the resampling and extraction
        of meta data of the simulation results. This meta data are e.g.
        maximum power demand and total energy demand.

        Returns:
            dict[str, StreamLoadProfileEntryCollectionResampled]: Collection of
                post processed stream simulation results.
        """
        dict_of_resampled_load_profile_meta_data = {}
        for (
            stream_name,
            stream_load_profile_collections,
        ) in self.load_profile_collection.dict_stream_load_profile_collections.items():
            stream_load_profile_entry_collection = StreamLoadProfileEntryCollectionResampled(object_name=stream_name)
            logger.debug("Start post processing stream_name: %s", stream_name)
            for (
                load_type_uuid,
                list_of_load_profile_entries,
            ) in stream_load_profile_collections.dict_of_load_entry_lists.items():
                load_type = stream_load_profile_collections.load_type_dict[load_type_uuid]
                logger.debug("Start to create load profile meta data: %s", stream_name)
                load_profile_meta_data = self.load_profile_entry_post_processor.create_load_profile_meta_data(
                    object_name=stream_name,
                    list_of_load_profile_entries=list_of_load_profile_entries,
                    start_date_time_series=self.report_generator_options.carpet_plot_options.start_date,
                    end_date_time_series=self.report_generator_options.carpet_plot_options.end_date,
                    object_type="Stream",
                )
                if type(load_profile_meta_data) is LoadProfileMetaData:
                    stream_load_profile_entry_collection.add_list_of_load_profile_meta_data(
                        load_type=load_type,
                        list_of_load_profile_entry_meta_data=load_profile_meta_data,
                    )
                    logger.debug("Start resampling stream_name: %s", stream_name)
                    resampled_load_profile_meta_data = (
                        self.load_profile_entry_post_processor.resample_load_profile_meta_data(
                            load_profile_meta_data=load_profile_meta_data,
                            start_date=self.report_generator_options.carpet_plot_options.start_date,
                            end_date=self.report_generator_options.carpet_plot_options.end_date,
                            resample_frequency=self.report_generator_options.carpet_plot_options.resample_frequency,
                        )
                    )
                    if type(resampled_load_profile_meta_data) is LoadProfileMetaDataResampled:
                        stream_load_profile_entry_collection.add_list_of_load_profile_meta_data_resampled(
                            load_type=load_type,
                            list_of_load_profile_entry_meta_data=resampled_load_profile_meta_data,
                        )
                    else:
                        raise UnexpectedCase(
                            "Received unexpected datatype during resampling of load profile for stream:"
                            + str(stream_name)
                        )
                elif type(load_profile_meta_data) is EmptyLoadProfileMetadata:
                    pass
                else:
                    raise UnexpectedCase(
                        "Received unexpected datatype during resampling of load profile for stream:" + str(stream_name)
                    )
            dict_of_resampled_load_profile_meta_data[stream_name] = stream_load_profile_entry_collection

        return dict_of_resampled_load_profile_meta_data

    def resample_process_step_load_profiles(
        self,
    ) -> dict[str, ProcessStepLoadProfileEntryCollectionResampled]:
        """Post processes the process step simulation results. The most
        important modifications are the resampling and extraction
        of meta data of the simulation results. This meta data are e.g.
        maximum power demand and total energy demand.

        Returns:
            dict[str, ProcessStepLoadProfileEntryCollectionResampled]: Collection of
                post processed process step simulation results.
        """

        dict_of_resampled_load_profile_meta_data = {}

        for (
            process_step_name,
            process_step_load_profile_collections,
        ) in self.load_profile_collection.dict_process_step_load_profile_collections.items():
            logger.info("Start resampling process step: %s", process_step_name)
            process_step_load_profile_entry_collection = ProcessStepLoadProfileEntryCollectionResampled(
                object_name=process_step_name
            )
            for (
                load_type_uuid,
                list_of_load_profile_entries,
            ) in process_step_load_profile_collections.dict_of_load_entry_lists.items():
                load_type = process_step_load_profile_collections.load_type_dict[load_type_uuid]
                load_profile_meta_data = self.load_profile_entry_post_processor.create_load_profile_meta_data(
                    object_name=process_step_name,
                    list_of_load_profile_entries=list_of_load_profile_entries,
                    start_date_time_series=self.report_generator_options.carpet_plot_options.start_date,
                    end_date_time_series=self.report_generator_options.carpet_plot_options.end_date,
                    object_type="Process Step",
                )
                if type(load_profile_meta_data) is LoadProfileMetaData:
                    process_step_load_profile_entry_collection.add_list_of_load_profile_meta_data(
                        load_type=load_type,
                        list_of_load_profile_entry_meta_data=load_profile_meta_data,
                    )
                    resampled_load_profile_meta_data = self.load_profile_entry_post_processor.resample_load_profile_meta_data(
                        load_profile_meta_data=load_profile_meta_data,
                        start_date=self.report_generator_options.carpet_plot_options.start_date,
                        end_date=self.report_generator_options.carpet_plot_options.end_date,
                        # x_axis_time_period_timedelta=self.report_generator_options.carpet_plot_options.x_axis_time_delta,
                        resample_frequency=self.report_generator_options.carpet_plot_options.resample_frequency,
                    )
                    if type(resampled_load_profile_meta_data) is LoadProfileMetaDataResampled:
                        process_step_load_profile_entry_collection.add_list_of_load_profile_meta_data_resampled(
                            load_type=load_type,
                            list_of_load_profile_entry_meta_data=resampled_load_profile_meta_data,
                        )

                    else:
                        raise UnexpectedCase(
                            "Received unexpected datatype during resampling of load profile for process step:"
                            + str(process_step_name)
                        )
                elif type(load_profile_meta_data) is EmptyMetaDataInformation:
                    pass
                else:
                    raise UnexpectedCase(
                        "Received unexpected datatype during resampling of load profile for process step:"
                        + str(process_step_name)
                    )

            dict_of_resampled_load_profile_meta_data[process_step_name] = process_step_load_profile_entry_collection

        return dict_of_resampled_load_profile_meta_data

    # def convert_all_load_lists_to_gantt_chart_data_frames(
    #     self,
    #     start_date: datetime.datetime,
    #     end_date: datetime.datetime,
    #     convert_stream_load_profile_entries: bool = True,
    #     convert_process_state_load_profiles: bool = True,
    # ):
    #     if convert_stream_load_profile_entries is True:
    #         for (
    #             stream_name,
    #             stream_load_profile_collection,
    #         ) in self.dict_stream_load_profile_collections.items():
    #             for (
    #                 load_type_uuid,
    #                 list_of_load_profile_entries,
    #             ) in (
    #                 stream_load_profile_collection.dict_of_load_entry_meta_data_resampled.items()
    #             ):
    #                 load_profile_entry_post_processor = LoadProfileEntryPostProcessor()
    #                 stream_data_frame = load_profile_entry_post_processor.convert_time_series_to_resampled_load_profile_meta_data(
    #                     object_name=stream_name,
    #                     object_type="Stream",
    #                     list_of_load_profile_entries=list_of_load_profile_entries,
    #                     start_date=start_date,
    #                     end_date=end_date,
    #                 )
    #                 if stream_name not in self.dict_stream_data_frames_gantt_chart:
    #                     self.dict_stream_data_frames_gantt_chart[stream_name] = {
    #                         load_type_uuid: stream_data_frame
    #                     }
    #                 else:
    #                     self.dict_stream_data_frames_gantt_chart[stream_name][
    #                         load_type_uuid
    #                     ] = stream_data_frame

    def sort_all_resampled_load_profile_meta_data_by_energy_carrier(
        self,
    ) -> dict[str, list[LoadProfileMetaDataResampled]]:

        load_profile_meta_data_keyed_by_load_type: dict[str, list[LoadProfileMetaDataResampled]] = {}
        for stream_load_profile_collections in self.dict_stream_load_profile_collections.values():
            stream_load_profile_collections: StreamLoadProfileEntryCollectionResampled
            for (
                load_type_uid,
                resampled_load_profile_meta_data,
            ) in stream_load_profile_collections.dict_of_load_entry_meta_data_resampled.items():
                if load_type_uid in load_profile_meta_data_keyed_by_load_type:
                    load_profile_meta_data_keyed_by_load_type[load_type_uid].append(resampled_load_profile_meta_data)
                else:
                    load_profile_meta_data_keyed_by_load_type[load_type_uid] = [resampled_load_profile_meta_data]
        for process_step_load_profile_collections in self.dict_process_step_load_profile_collections.values():
            process_step_load_profile_collections: ProcessStepLoadProfileEntryCollectionResampled
            for (
                load_type_uid,
                resampled_load_profile_meta_data,
            ) in process_step_load_profile_collections.dict_of_load_entry_meta_data_resampled.items():
                if load_type_uid in load_profile_meta_data_keyed_by_load_type:
                    load_profile_meta_data_keyed_by_load_type[load_type_uid].append(resampled_load_profile_meta_data)
                else:
                    load_profile_meta_data_keyed_by_load_type[load_type_uid] = [resampled_load_profile_meta_data]
        return load_profile_meta_data_keyed_by_load_type

    def create_combined_load_profiles_per_load_type(self):

        list_of_load_profile_meta_data_keyed_by_load_type = (
            self.sort_all_resampled_load_profile_meta_data_by_energy_carrier()
        )

        for (
            load_type_uuid,
            resampled_load_profile_meta_data_list,
        ) in list_of_load_profile_meta_data_keyed_by_load_type.items():
            previous_data_frame = None

            first_meta_data = resampled_load_profile_meta_data_list[0]

            for resampled_load_profile_meta_data in resampled_load_profile_meta_data_list:
                if previous_data_frame is None:
                    previous_data_frame = resampled_load_profile_meta_data.data_frame.copy()
                else:
                    previous_data_frame.loc[:, "average_power_consumption"] = (
                        previous_data_frame.loc[:, "average_power_consumption"]
                        + resampled_load_profile_meta_data.data_frame.loc[:, "average_power_consumption"]
                    )
                    previous_data_frame.loc[:, "energy_quantity"] = (
                        previous_data_frame.loc[:, "energy_quantity"]
                        + resampled_load_profile_meta_data.data_frame.loc[:, "energy_quantity"]
                    )

            name_of_load_type = first_meta_data.load_type.name

            list_of_load_profiles = create_load_profile_entry(data=previous_data_frame)
            stats = self.load_profile_entry_post_processor._extract_stats_from_data_frame(
                analysis_data_frame=previous_data_frame
            )

            combined_load_profile_meta_data: LoadProfileMetaDataResampled | LoadProfileMetaData = (
                LoadProfileMetaDataResampled(
                    name="Load Profile for " + name_of_load_type,
                    object_type="Combined Load Profile",
                    list_of_load_profiles=list_of_load_profiles,
                    data_frame=previous_data_frame,
                    energy_unit=first_meta_data.energy_unit,
                    power_unit=first_meta_data.power_unit,
                    load_type=first_meta_data.load_type,
                    time_step=first_meta_data.time_step,
                    total_energy=stats.total_energy,
                    maximum_power=stats.maximum_power,
                    minimum_power=stats.minimum_power,
                    resample_frequency=first_meta_data.resample_frequency,
                    first_start_time=stats.first_start_time,
                    last_end_time=stats.last_end_time,
                )
            )
            combined_load_profile_meta_data = (
                self.load_profile_entry_post_processor._compress_power_in_meta_data_if_necessary(
                    list_of_load_profile_meta_data=combined_load_profile_meta_data
                )
            )
            self.dict_of_total_process_load_profiles_resampled[load_type_uuid] = combined_load_profile_meta_data
        pass

    def get_list_of_combined_load_profiles(self) -> list[LoadProfileMetaDataResampled]:
        list_of_load_profiles_meta_data = []
        for current_resampled_meta_data in self.dict_of_total_process_load_profiles_resampled.values():
            list_of_load_profiles_meta_data.append(current_resampled_meta_data)

        return list_of_load_profiles_meta_data
