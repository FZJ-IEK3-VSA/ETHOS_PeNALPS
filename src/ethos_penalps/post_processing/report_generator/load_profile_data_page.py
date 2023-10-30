import datapane
import pandas

from ethos_penalps.post_processing.report_generator.report_options import (
    ReportGeneratorOptions,
)
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class LoadProfileDataPageGenerator:
    def __init__(self, production_plan: ProductionPlan) -> None:
        self.production_plan: ProductionPlan = production_plan

    def create_stream_group_or_select(self) -> datapane.Group | datapane.Select:
        logger.info("Start generation of load profile data page")

        dict_stream_load_profile_data_frames = (
            self.production_plan.load_profile_handler.load_profile_collection.convert_stream_energy_dict_to_data_frame()
        )

        stream_selector_list = []
        for (
            stream_name,
            load_type_profile_dict,
        ) in dict_stream_load_profile_data_frames.items():
            stream_load_profile_data_frame_list = []
            for (
                load_type,
                load_profile_data_frame,
            ) in load_type_profile_dict.items():
                caption = load_type + ": " + stream_name
                stream_load_profile_data_frame_list.append(
                    datapane.DataTable(
                        load_profile_data_frame, caption=caption, label=caption
                    )
                )
            if stream_load_profile_data_frame_list:
                if len(stream_load_profile_data_frame_list) == 1:
                    stream_load_profile_selector = stream_load_profile_data_frame_list[
                        0
                    ]

                    stream_load_profile_selector = stream_load_profile_data_frame_list[
                        0
                    ]
                else:
                    stream_load_profile_selector = datapane.Select(
                        blocks=stream_load_profile_data_frame_list,
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
                blocks=["# There are no stream Load Profiles"],
            )
        return stream_group

    def create_process_state_load_profile_group(
        self,
    ) -> datapane.Group | datapane.Select:
        process_step_selector_list = []
        dict_process_step_load_profile_data_frames = (
            self.production_plan.load_profile_handler.load_profile_collection.convert_process_state_energy_date()
        )
        process_step_group = datapane.Group(
            label="Process Step Load Profiles",
            blocks=["No process step load profiles have ben calculated"],
        )
        for (
            process_step_name,
            load_type_profile_dict,
        ) in dict_process_step_load_profile_data_frames.items():
            process_step_load_profile_data_frame_list = []
            for (
                load_type_name,
                load_profile_data_frame,
            ) in load_type_profile_dict.items():
                caption = process_step_name + ": " + load_type_name

                process_step_load_profile_data_frame_list.append(
                    datapane.DataTable(
                        load_profile_data_frame, caption=caption, label=caption
                    )
                )
            if process_step_load_profile_data_frame_list:
                if len(process_step_load_profile_data_frame_list) <= 1:
                    process_step_selector = process_step_load_profile_data_frame_list[0]
                else:
                    process_step_selector = datapane.Select(
                        blocks=process_step_load_profile_data_frame_list,
                        label=process_step_name,
                    )
                process_step_selector_list.append(process_step_selector)

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
                    blocks=["No process step load profiles have ben calculated"],
                )
        return process_step_group

    def create_load_profile_data_page(self) -> datapane.Group:
        logger.info("Create generate load profile data page")
        stream_group = self.create_stream_group_or_select()
        process_state_group = self.create_process_state_load_profile_group()
        stream_and_process_state_selector = datapane.Select(
            blocks=[stream_group, process_state_group]
        )
        load_profile_page = datapane.Group(
            blocks=["# Load profile page", stream_and_process_state_selector],
            label="Load Profile Data Frames",
        )

        return load_profile_page
