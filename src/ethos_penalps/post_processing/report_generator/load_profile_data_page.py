import datapane
import pandas

from ethos_penalps.post_processing.production_plan_post_processing.post_processed_data_handler import (
    PostProcessSimulationDataHandler,
)
from ethos_penalps.post_processing.report_generator.report_options import (
    ReportGeneratorOptions,
)
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.type_aliases import numbers_alias

logger = PeNALPSLogger.get_logger_without_handler()


class LoadProfileDataPageGenerator:
    """Create the report page that contains all load profiles."""

    def __init__(
        self,
        production_plan: ProductionPlan,
        post_process_simulation_data_handler: PostProcessSimulationDataHandler,
    ) -> None:
        """

        Args:
            production_plan (ProductionPlan): Contains the unprocessed simulation data.
            report_directory (str): Path to the report folder.
            post_process_simulation_data_handler (PostProcessSimulationDataHandler): Contains
                the post processed simulation data.
        """
        self.production_plan: ProductionPlan = production_plan
        self.post_process_simulation_data_handler: PostProcessSimulationDataHandler = (
            post_process_simulation_data_handler
        )

    def create_stream_group_or_select(self) -> datapane.Group | datapane.Select:
        """Create the group of load profile page that contains the stream load profiles.

        Returns:
            datapane.Group | datapane.Select:  DataPane object that represents the
            stream load profiles of the load profile page of the report.
        """
        logger.info("Start generation of load profile data page")

        dict_stream_load_profile_collections = self.post_process_simulation_data_handler.load_profile_collection_post_processing.dict_stream_load_profile_collections

        stream_selector_list = []
        for (
            stream_name,
            stream_load_profile_collections,
        ) in dict_stream_load_profile_collections.items():
            resampled_not_resampled_selector_list = []

            for (
                load_type_uuid,
                load_type,
            ) in stream_load_profile_collections.load_type_dict.items():
                load_entry_meta_data = stream_load_profile_collections.dict_of_load_entry_meta_data[load_type_uuid]

                load_entry_meta_data_resampled = stream_load_profile_collections.dict_of_load_entry_meta_data_resampled[
                    load_type_uuid
                ]

                caption = (
                    "Direct Simulation Output "
                    + load_type.name
                    + ". The total energy is "
                    + str(load_entry_meta_data.total_energy)
                    + " "
                    + str(load_entry_meta_data.energy_unit)
                )

                caption_resampled = (
                    "Resampled "
                    + load_type.name
                    + ". The total energy is "
                    + str(load_entry_meta_data_resampled.total_energy)
                    + " "
                    + str(load_entry_meta_data_resampled.energy_unit)
                )

                not_resampled_table = datapane.DataTable(
                    load_entry_meta_data.data_frame, caption=caption, label=caption
                )
                resampled_table = datapane.DataTable(
                    load_entry_meta_data_resampled.data_frame,
                    caption=caption_resampled,
                    label=caption_resampled,
                )

                resampled_not_resampled_table_list = [
                    not_resampled_table,
                    resampled_table,
                ]
                resampled_not_resampled_selector = datapane.Select(
                    blocks=resampled_not_resampled_table_list,
                    label=load_type.name,
                )
                resampled_not_resampled_selector_list.append(resampled_not_resampled_selector)
            if resampled_not_resampled_selector_list:
                if len(resampled_not_resampled_selector_list) == 1:
                    stream_load_profile_selector = datapane.Group(
                        blocks=resampled_not_resampled_selector_list[0],
                        label=stream_name,
                    )
                else:
                    stream_load_profile_selector = datapane.Select(
                        blocks=resampled_not_resampled_selector_list,
                        label=stream_name,
                    )
                stream_selector_list.append(stream_load_profile_selector)

        if len(stream_selector_list) > 1:
            stream_group = datapane.Select(
                label="Stream Load Profiles",
                blocks=stream_selector_list,
            )
        elif len(stream_selector_list) == 1:
            stream_group = datapane.Group(
                label="Stream Load Profiles",
                blocks=stream_selector_list,
            )

        else:
            stream_group = datapane.Group(
                label="Stream Load Profiles",
                blocks=[datapane.HTML("There are no stream Load Profiles")],
            )
        return stream_group

    def create_process_state_load_profile_group(
        self,
    ) -> datapane.Group | datapane.Select:
        """Create the group of load profile page that contains the process step load profiles.

        Returns:
            datapane.Group | datapane.Select:  DataPane object that represents the
            process step load profiles of the load profile page of the report.
        """
        process_step_selector_list = []
        dict_process_step_load_profile_collections = self.post_process_simulation_data_handler.load_profile_collection_post_processing.dict_process_step_load_profile_collections
        process_step_group = datapane.Group(
            label="Process Step Load Profiles",
            blocks=["No process step load profiles have ben calculated"],
        )
        for (
            process_step_name,
            process_step_load_profile_collections,
        ) in dict_process_step_load_profile_collections.items():
            process_step_load_profile_resampled_not_resampled_selector_list = []
            for (
                load_type_uuid,
                load_type,
            ) in process_step_load_profile_collections.load_type_dict.items():
                resampled_not_resampled_table_list = []
                load_entry_meta_data = process_step_load_profile_collections.dict_of_load_entry_meta_data[
                    load_type_uuid
                ]
                caption = (
                    "Direct Simulation Output "
                    + load_type.name
                    + ". The total energy is "
                    + str(load_entry_meta_data.total_energy)
                    + " "
                    + str(load_entry_meta_data.energy_unit)
                )

                resampled_not_resampled_table_list.append(
                    datapane.DataTable(load_entry_meta_data.data_frame, caption=caption, label=caption)
                )
                load_entry_meta_data_resampled = (
                    process_step_load_profile_collections.dict_of_load_entry_meta_data_resampled[load_type_uuid]
                )

                caption_resampled = (
                    "Resampled "
                    + load_type.name
                    + ". The total energy is "
                    + str(load_entry_meta_data_resampled.total_energy)
                    + " "
                    + str(load_entry_meta_data_resampled.energy_unit)
                )
                resampled_not_resampled_table_list.append(
                    datapane.DataTable(
                        load_entry_meta_data_resampled.data_frame,
                        caption=caption_resampled,
                        label=caption_resampled,
                    )
                )
                process_step_load_profile_resampled_not_resampled_selector_list.append(
                    datapane.Select(
                        blocks=resampled_not_resampled_table_list,
                        label=caption_resampled,
                    )
                )
            if process_step_load_profile_resampled_not_resampled_selector_list:
                if len(process_step_load_profile_resampled_not_resampled_selector_list) == 1:
                    process_step_selector = process_step_load_profile_resampled_not_resampled_selector_list[0]
                    process_step_selector_list.append(process_step_selector)
                elif len(process_step_load_profile_resampled_not_resampled_selector_list) > 1:
                    process_step_selector = datapane.Select(
                        blocks=process_step_load_profile_resampled_not_resampled_selector_list,
                        label=process_step_name,
                    )
                    process_step_selector_list.append(process_step_selector)
                else:
                    pass

            if len(process_step_selector_list) > 1:
                process_step_group = datapane.Select(
                    label="Process Step Load Profiles",
                    blocks=process_step_selector_list,
                )
            elif len(process_step_selector_list) == 1:
                process_step_group = datapane.Group(
                    label="Process Step Load Profiles",
                    blocks=process_step_selector_list,
                )
            else:
                process_step_group = datapane.Group(
                    label="Process Step Load Profiles",
                    blocks=[datapane.HTML("No process step load profiles have ben calculated")],
                )
        return process_step_group

    def get_combined_load_profile_group(self):
        dict_of_total_load_profile_meta_data = self.post_process_simulation_data_handler.load_profile_collection_post_processing.dict_of_total_process_load_profiles_resampled
        list_of_total_load_profiles_tables = []
        for load_profile_meta_data in dict_of_total_load_profile_meta_data.values():
            list_of_total_load_profiles_tables.append(
                datapane.DataTable(
                    df=load_profile_meta_data.data_frame,
                    caption=load_profile_meta_data.load_type.name
                    + " Load Profile of the whole Process. Contains: "
                    + str(load_profile_meta_data.total_energy)
                    + " "
                    + str(load_profile_meta_data.energy_unit),
                )
            )

        if list_of_total_load_profiles_tables:
            process_step_group = datapane.Group(
                label="Load Profiles for whole Process",
                blocks=list_of_total_load_profiles_tables,
            )
        else:
            process_step_group = datapane.Group(
                label="Load Profiles for whole Process",
                blocks=[datapane.HTML("No process step load profiles have ben calculated")],
            )

        return process_step_group

    def create_load_profile_data_page(self) -> datapane.Group:
        """Create the load profile page that contains all load profiles of the simulation.

        Returns:
            datapane.Group | datapane.Select:  DataPane object that represents all
            of load profiles.
        """
        logger.info("Create generate load profile data page")
        stream_group = self.create_stream_group_or_select()
        process_state_group = self.create_process_state_load_profile_group()
        combined_load_profile_group = self.get_combined_load_profile_group()
        stream_and_process_state_selector = datapane.Select(
            blocks=[stream_group, process_state_group, combined_load_profile_group]
        )

        load_profile_page = datapane.Group(
            blocks=["# Load profile page", stream_and_process_state_selector],
            label="Load Profile Data Frames",
        )

        return load_profile_page
