import os

import datapane
import matplotlib.pyplot
import pandas

from ethos_penalps.data_classes import LoadType, CarpetPlotMatrix, CarpetPlotMatrixEmpty
from ethos_penalps.post_processing.load_profile_entry_post_processor import (
    LoadProfileEntryPostProcessor,
)
from ethos_penalps.post_processing.tikz_visualizations.carpet_plot_load_profile_generator import (
    CarpetPlotLoadProfileGenerator,
)
from ethos_penalps.post_processing.network_analyzer import NetworkAnalyzer
from ethos_penalps.post_processing.report_generator.report_options import (
    ReportGeneratorOptions,
)
from ethos_penalps.post_processing.time_series_visualizations.gantt_chart import (
    GanttChartGenerator,
)
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class CarpetPlotPageGenerator:
    def __init__(self, production_plan: ProductionPlan, report_directory: str) -> None:
        self.production_plan: ProductionPlan = production_plan
        self.report_directory: str = report_directory

    def create_carpet_plot_page(
        self, report_generator_options: ReportGeneratorOptions
    ) -> datapane.Group:
        if report_generator_options.carpet_plot_options.create_all is True:
            logger.info("Start generation of load profile carpet plot page")

            carpet_plot_list = []
            load_profile_matrix_dict_by_load_profile: dict[
                str, list[CarpetPlotMatrix]
            ] = {}

            load_profile_entry_post_processor_for_start_time_check = (
                LoadProfileEntryPostProcessor()
            )
            list_of_list_of_load_profile_entries = (
                self.production_plan.load_profile_handler.get_list_of_list_of_all_load_profile_entries()
            )

            result_path_generator = ResultPathGenerator()
            load_profile_carpet_plot_directory = "load_profile_carpet_plots"
            load_profile_carpet_plot_directory_path = (
                result_path_generator.create_subdirectory_relative_to_parent(
                    parent_directory_path=self.report_directory,
                    new_directory_name=load_profile_carpet_plot_directory,
                )
            )
            output_file_extension = "png"
            output_file_extension_with_dot = "." + output_file_extension
            output_file_dpi = 900

            combined_carpet_plot_groups = None
            individual_load_profile_group = None

            if list_of_list_of_load_profile_entries:
                combined_load_profile_start_date = load_profile_entry_post_processor_for_start_time_check.determine_earliest_start_date_from_list_of_list_of_load_profile_entries(
                    end_date=report_generator_options.carpet_plot_options.end_date,
                    period=report_generator_options.carpet_plot_options.x_axis_time_delta,
                    list_of_list_of_load_profile_entries=self.production_plan.load_profile_handler.get_list_of_list_of_all_load_profile_entries(),
                )

                for (
                    stream_name,
                    stream_load_profile_collections,
                ) in (
                    self.production_plan.load_profile_handler.load_profile_collection.dict_stream_load_profile_collections.items()
                ):
                    for (
                        load_type_uuid,
                        list_of_load_profile_entries,
                    ) in (
                        stream_load_profile_collections.dict_of_load_entry_lists.items()
                    ):
                        load_type = stream_load_profile_collections.load_type_dict[
                            load_type_uuid
                        ]
                        load_profile_post_processor = CarpetPlotLoadProfileGenerator()
                        load_profile_df_matrix = load_profile_post_processor.convert_lpg_load_profile_to_data_frame_matrix(
                            list_of_load_profile_entries=list_of_load_profile_entries,
                            end_date_time_series=report_generator_options.carpet_plot_options.end_date,
                            start_date_time_series=combined_load_profile_start_date,
                            x_axis_time_period_timedelta=report_generator_options.carpet_plot_options.x_axis_time_delta,
                            resample_frequency=report_generator_options.carpet_plot_options.resample_frequency,
                            object_name=stream_name,
                        )
                        if type(load_profile_df_matrix) is CarpetPlotMatrixEmpty:
                            pass
                        elif type(load_profile_df_matrix) is CarpetPlotMatrix:
                            fig = load_profile_post_processor.plot_load_profile_carpet_from_data_frame_matrix(
                                carpet_plot_load_profile_matrix=load_profile_df_matrix
                            )
                            caption = (
                                "Stream name: "
                                + str(stream_name)
                                + "Load type: "
                                + str(load_type.name)
                            )

                            file_name = (
                                "stream_load_profile_"
                                + str(stream_name)
                                + "-"
                                + str(load_type.name)
                                + output_file_extension_with_dot
                            )
                            file_name = file_name.replace(" ", "_")
                            output_file = os.path.join(
                                load_profile_carpet_plot_directory_path, file_name
                            )
                            fig.savefig(
                                output_file,
                                format=output_file_extension,
                                bbox_inches="tight",
                                dpi=output_file_dpi,
                            )

                            carpet_plot_list.append(
                                datapane.Media(output_file, caption=caption)
                            )
                            if (
                                load_type.name
                                in load_profile_matrix_dict_by_load_profile
                            ):
                                load_profile_matrix_dict_by_load_profile[
                                    load_type.name
                                ].append(load_profile_df_matrix)
                            else:
                                load_profile_matrix_dict_by_load_profile[
                                    load_type.name
                                ] = [load_profile_df_matrix]

                for (
                    process_state_name,
                    process_step_load_profile_collections,
                ) in (
                    self.production_plan.load_profile_handler.load_profile_collection.dict_process_step_load_profile_collections.items()
                ):
                    for (
                        load_type_uuid,
                        load_entry_lists,
                    ) in (
                        process_step_load_profile_collections.dict_of_load_entry_lists.items()
                    ):
                        load_type = (
                            process_step_load_profile_collections.load_type_dict[
                                load_type_uuid
                            ]
                        )
                        load_profile_post_processor = CarpetPlotLoadProfileGenerator()
                        load_profile_df_matrix = load_profile_post_processor.convert_lpg_load_profile_to_data_frame_matrix(
                            list_of_load_profile_entries=load_entry_lists,
                            end_date_time_series=report_generator_options.carpet_plot_options.end_date,
                            start_date_time_series=combined_load_profile_start_date,
                            x_axis_time_period_timedelta=report_generator_options.carpet_plot_options.x_axis_time_delta,
                            resample_frequency=report_generator_options.carpet_plot_options.resample_frequency,
                            object_name=process_state_name,
                        )
                        if type(load_profile_df_matrix) is CarpetPlotMatrixEmpty:
                            pass
                        elif type(load_profile_df_matrix) is CarpetPlotMatrix:
                            fig = load_profile_post_processor.plot_load_profile_carpet_from_data_frame_matrix(
                                carpet_plot_load_profile_matrix=load_profile_df_matrix
                            )

                            file_name = (
                                "process_state_load_profile_"
                                + str(process_state_name)
                                + "-"
                                + str(load_type.name)
                                + output_file_extension_with_dot
                            )
                            output_file = os.path.join(
                                load_profile_carpet_plot_directory_path, file_name
                            )
                            fig.savefig(
                                output_file,
                                format=output_file_extension,
                                bbox_inches="tight",
                                dpi=output_file_dpi,
                            )

                            figure_caption = (
                                "Process state: "
                                + str(process_state_name)
                                + "Load type: "
                                + str(load_type.name)
                            )

                            carpet_plot_list.append(
                                datapane.Media(output_file, caption=figure_caption)
                            )
                            if (
                                load_type.name
                                in load_profile_matrix_dict_by_load_profile
                            ):
                                load_profile_matrix_dict_by_load_profile[
                                    load_type.name
                                ].append(load_profile_df_matrix)
                            else:
                                load_profile_matrix_dict_by_load_profile[
                                    load_type.name
                                ] = [load_profile_df_matrix]

                individual_load_profile_group = datapane.Group(
                    label="Load profile carpet plots",
                    blocks=[
                        datapane.Group(
                            blocks=carpet_plot_list,
                            columns=report_generator_options.carpet_plot_options.number_of_columns,
                        )
                    ],
                )

                list_of_combined_matrix_data_frames = []
                list_of_combined_load_profile_figures = []
                for (
                    current_load_type,
                    list_of_matrix_data_frames,
                ) in load_profile_matrix_dict_by_load_profile.items():
                    load_profile_post_processor = CarpetPlotLoadProfileGenerator()
                    combined_matrix_data_frame_for_load_type = (
                        load_profile_post_processor.combine_matrix_data_frames(
                            list_of_carpet_plot_matrices=list_of_matrix_data_frames,
                            combined_matrix_name="Combined Matrix of load: "
                            + str(current_load_type),
                        )
                    )
                    combined_load_profile_figure = load_profile_post_processor.plot_load_profile_carpet_from_data_frame_matrix(
                        carpet_plot_load_profile_matrix=combined_matrix_data_frame_for_load_type
                    )
                    file_name = (
                        "summary_load_profile-"
                        + str(current_load_type)
                        + output_file_extension_with_dot
                    )
                    output_file = os.path.join(
                        load_profile_carpet_plot_directory_path, file_name
                    )
                    combined_load_profile_figure.savefig(
                        output_file,
                        format=output_file_extension,
                        bbox_inches="tight",
                        dpi=output_file_dpi,
                    )

                    list_of_combined_load_profile_figures.append(
                        datapane.Media(
                            output_file,
                            caption="Whole process energy demand for Load type: "
                            + str(current_load_type),
                        )
                    )
                    list_of_combined_matrix_data_frames.append(
                        combined_matrix_data_frame_for_load_type
                    )

                load_profile_post_processor = CarpetPlotLoadProfileGenerator()
                total_energy_combined_matrix_data_frame = load_profile_post_processor.combine_matrix_data_frames(
                    list_of_combined_matrix_data_frames,
                    combined_matrix_name="Total Energy Demand of all energy carriers",
                )
                total_energy_carpet_plot = load_profile_post_processor.plot_load_profile_carpet_from_data_frame_matrix(
                    carpet_plot_load_profile_matrix=total_energy_combined_matrix_data_frame
                )
                file_name = "total_energy_load_profile" + output_file_extension_with_dot
                output_file = os.path.join(
                    load_profile_carpet_plot_directory_path, file_name
                )
                total_energy_carpet_plot.savefig(
                    output_file,
                    format=output_file_extension,
                    bbox_inches="tight",
                    dpi=output_file_dpi,
                )
                # self.list_of_carpet_plot_output_file_paths

                list_of_combined_load_profile_figures.append(
                    datapane.Media(output_file, caption="Total energy plot")
                )
                combined_carpet_plot_groups = datapane.Group(
                    label="Combined carpet plots",
                    blocks=[
                        datapane.Group(
                            blocks=list_of_combined_load_profile_figures,
                            columns=report_generator_options.carpet_plot_options.number_of_columns,
                        )
                    ],
                )

            if isinstance(combined_carpet_plot_groups, datapane.Group) and isinstance(
                individual_load_profile_group, datapane.Group
            ):
                combined_or_individual_plot_selector = datapane.Select(
                    blocks=[combined_carpet_plot_groups, individual_load_profile_group]
                )
                carpet_plot_page = datapane.Group(
                    label="Carpet plots",
                    blocks=[combined_or_individual_plot_selector],
                )
            else:
                carpet_plot_page = datapane.Group(
                    label="Process Step Load Profiles",
                    blocks=["No load profiles have ben calculated"],
                )

            return carpet_plot_page
            # if carpet_plot_dict_by_load_profile:
            #     pass
