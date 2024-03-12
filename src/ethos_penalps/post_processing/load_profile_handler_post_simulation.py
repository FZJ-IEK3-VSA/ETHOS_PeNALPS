import datetime
from dataclasses import dataclass, field

import pandas

from ethos_penalps.data_classes import (
    EmptyMetaDataInformation,
    LoadProfileMetaDataResampled,
    EmptyLoadProfileMetadata,
    LoadProfileEntry,
    LoadType,
    LoadProfileMetaData,
)
from ethos_penalps.load_profile_calculator import (
    LoadProfileCollection,
    ProcessStepLoadProfileEntryCollection,
    StreamLoadProfileEntryCollection,
)
from ethos_penalps.post_processing.load_profile_entry_post_processor import (
    LoadProfileEntryPostProcessor,
)
from ethos_penalps.post_processing.report_generator.report_options import (
    ReportGeneratorOptions,
)
from ethos_penalps.stream import BatchStream, ContinuousStream
from ethos_penalps.utilities.exceptions_and_warnings import UnexpectedCase
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


@dataclass
class StreamLoadProfileEntryCollectionResampled:
    """Summarizes the load profile simulation results of a stream during
    the simulation."""

    # Name of the stream
    object_name: str
    # Dict of all load types for which load entries are available
    # The key is a string of the uuid of the load type. The Value is the
    # load type itself.
    load_type_dict: dict[str, LoadType] = field(default_factory=dict)
    # The dictionary contains all load of profile entries for all load types
    # of the stream. The first key is the string of the uuid of the load type.
    # The value is the list of all load profile entries for the load type.
    dict_of_load_entry_meta_data_resampled: dict[str, LoadProfileMetaDataResampled] = (
        field(default_factory=dict)
    )
    dict_of_load_entry_meta_data: dict[str, LoadProfileMetaData] = field(
        default_factory=dict
    )

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
            self.dict_of_load_entry_meta_data_resampled[load_type.uuid] = (
                list_of_load_profile_entry_meta_data
            )
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
            self.dict_of_load_entry_meta_data[load_type.uuid] = (
                list_of_load_profile_entry_meta_data
            )
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

    # Name of the process step
    object_name: str
    # Dict of all load types for which load entries are available
    # The key is a string of the uuid of the load type. The Value is the
    # load type itself.
    load_type_dict: dict[str, LoadType] = field(default_factory=dict)
    # The dictionary contains all load of profile entries for all load types
    # of the stream. The first key is the string of the uuid of the load type.
    # The value is the list of all load profile entries for the load type.
    dict_of_load_entry_meta_data_resampled: dict[str, LoadProfileMetaDataResampled] = (
        field(default_factory=dict)
    )
    dict_of_load_entry_meta_data: dict[str, LoadProfileMetaData] = field(
        default_factory=dict
    )

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
            self.dict_of_load_entry_meta_data_resampled[load_type.uuid] = (
                list_of_load_profile_entry_meta_data
            )
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
            self.dict_of_load_entry_meta_data[load_type.uuid] = (
                list_of_load_profile_entry_meta_data
            )
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
    def __init__(
        self,
        load_profile_collection: LoadProfileCollection,
        report_options: ReportGeneratorOptions,
    ) -> None:
        self.load_profile_collection: LoadProfileCollection = load_profile_collection
        self.report_generator_options: ReportGeneratorOptions = report_options
        self.load_profile_entry_post_processor = LoadProfileEntryPostProcessor()
        # Contains the load profile data for all streams
        # The key is the stream name
        self.dict_stream_load_profile_collections: dict[
            str, StreamLoadProfileEntryCollectionResampled
        ] = {}
        # Contains the load profile data for all streams
        # The key is the process step
        self.dict_process_step_load_profile_collections: dict[
            str, ProcessStepLoadProfileEntryCollectionResampled
        ] = {}

    def start_post_processing(self):
        dict_stream_load_profile_collections: dict[
            str, StreamLoadProfileEntryCollectionResampled
        ] = self.resample_stream_load_profiles()
        self.dict_stream_load_profile_collections.update(
            dict_stream_load_profile_collections
        )
        dict_process_step_load_profile_collections: dict[
            str, ProcessStepLoadProfileEntryCollectionResampled
        ] = self.resample_process_step_load_profiles()
        self.dict_process_step_load_profile_collections.update(
            dict_process_step_load_profile_collections
        )

    def resample_stream_load_profiles(
        self,
    ) -> dict[str, StreamLoadProfileEntryCollectionResampled]:
        dict_of_resampled_load_profile_meta_data = {}
        for (
            stream_name,
            stream_load_profile_collections,
        ) in self.load_profile_collection.dict_stream_load_profile_collections.items():
            stream_load_profile_entry_collection = (
                StreamLoadProfileEntryCollectionResampled(object_name=stream_name)
            )
            logger.info("Start post processing stream_name: %s", stream_name)
            for (
                load_type_uuid,
                list_of_load_profile_entries,
            ) in stream_load_profile_collections.dict_of_load_entry_lists.items():
                load_type = stream_load_profile_collections.load_type_dict[
                    load_type_uuid
                ]
                logger.info("Start to create load profile meta data: %s", stream_name)
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
                    logger.info("Start resampling stream_name: %s", stream_name)
                    resampled_load_profile_meta_data = self.load_profile_entry_post_processor.resample_load_profile_meta_data(
                        load_profile_meta_data=load_profile_meta_data,
                        start_date=self.report_generator_options.carpet_plot_options.start_date,
                        end_date=self.report_generator_options.carpet_plot_options.end_date,
                        x_axis_time_period_timedelta=self.report_generator_options.carpet_plot_options.x_axis_time_delta,
                        resample_frequency=self.report_generator_options.carpet_plot_options.resample_frequency,
                    )
                    if (
                        type(resampled_load_profile_meta_data)
                        is LoadProfileMetaDataResampled
                    ):
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
                        "Received unexpected datatype during resampling of load profile for stream:"
                        + str(stream_name)
                    )
            dict_of_resampled_load_profile_meta_data[stream_name] = (
                stream_load_profile_entry_collection
            )

        return dict_of_resampled_load_profile_meta_data

    def resample_process_step_load_profiles(
        self,
    ) -> dict[str, ProcessStepLoadProfileEntryCollectionResampled]:
        dict_of_resampled_load_profile_meta_data = {}

        for (
            process_step_name,
            process_step_load_profile_collections,
        ) in (
            self.load_profile_collection.dict_process_step_load_profile_collections.items()
        ):
            logger.info("Start resampling process step: %s", process_step_name)
            process_step_load_profile_entry_collection = (
                ProcessStepLoadProfileEntryCollectionResampled(
                    object_name=process_step_name
                )
            )
            for (
                load_type_uuid,
                list_of_load_profile_entries,
            ) in process_step_load_profile_collections.dict_of_load_entry_lists.items():
                load_type = process_step_load_profile_collections.load_type_dict[
                    load_type_uuid
                ]
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
                        x_axis_time_period_timedelta=self.report_generator_options.carpet_plot_options.x_axis_time_delta,
                        resample_frequency=self.report_generator_options.carpet_plot_options.resample_frequency,
                    )
                    if (
                        type(resampled_load_profile_meta_data)
                        is LoadProfileMetaDataResampled
                    ):
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

            dict_of_resampled_load_profile_meta_data[process_step_name] = (
                process_step_load_profile_entry_collection
            )

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
