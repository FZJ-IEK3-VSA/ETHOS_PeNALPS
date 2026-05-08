import os
from dataclasses import dataclass

import datapane
import matplotlib.pyplot
import pandas

from ethos_penalps.data_classes import CarpetPlotMatrix, CarpetPlotMatrixEmpty, LoadType
from ethos_penalps.post_processing.production_plan_post_processing.post_processed_data_handler import (
    PostProcessSimulationDataHandler,
)
from ethos_penalps.post_processing.report_generator.report_options import (
    ReportGeneratorOptions,
)
from ethos_penalps.post_processing.time_series_visualizations.carpet_plot_load_profile_generator import (
    CarpetPlotLoadProfileGenerator,
)
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.multiprocessor import AsynchronousMultiProcessor
from ethos_penalps.utilities.type_aliases import numbers_alias

logger = PeNALPSLogger.get_logger_without_handler()


@dataclass
class CarpetPlotInputData:
    carpet_plot_matrix: CarpetPlotMatrix
    output_path: str
    display_name_report: str
    output_file_extension: str


class CarpetPlotPageGenerator:
    """Is used to generate carpet plots from the simulation and post simulation data."""

    def __init__(
        self,
        production_plan: ProductionPlan,
        report_directory: str,
        post_process_simulation_data_handler: PostProcessSimulationDataHandler,
        output_file_format: str = "png",
        dpi: int = 300,
        figure_folder_name: str = "load_profile_carpet_plots",
    ) -> None:
        """

        Args:
            production_plan (ProductionPlan): Contains the unprocessed simulation data.
            report_directory (str): Path to the report folder.
            post_process_simulation_data_handler (PostProcessSimulationDataHandler): Contains
                the post processed simulation data.
        """
        self.production_plan: ProductionPlan = production_plan
        self.report_directory: str = report_directory
        self.post_process_simulation_data_handler: PostProcessSimulationDataHandler = (
            post_process_simulation_data_handler
        )
        self.output_file_format: str = output_file_format
        self.output_file_format_with_dot: str = "." + output_file_format
        self.dpi: int = dpi
        self.figure_folder_name: str = figure_folder_name
        result_path_generator = ResultPathGenerator()
        self.carpet_plot_directory_path = result_path_generator.create_subdirectory_relative_to_parent(
            parent_directory_path=self.report_directory,
            new_directory_name=figure_folder_name,
        )

    def collect_single_carpet_plot_input_data(
        self, report_generator_options: ReportGeneratorOptions
    ) -> tuple[list[CarpetPlotInputData], dict[str, list[CarpetPlotInputData]]]:
        load_profile_matrix_dict_by_load_profile: dict[str, list[CarpetPlotInputData]] = {}

        list_of_list_of_load_profile_entries = (
            self.production_plan.load_profile_handler.get_list_of_list_of_all_load_profile_entries()
        )

        carpet_plot_load_profile_generator = CarpetPlotLoadProfileGenerator()
        list_of_process_step_and_stream_carpet_plot_data: list[CarpetPlotInputData] = []
        if list_of_list_of_load_profile_entries:
            for (
                stream_name,
                stream_load_profile_collections,
            ) in self.post_process_simulation_data_handler.load_profile_collection_post_processing.dict_stream_load_profile_collections.items():
                for (
                    load_type_uuid,
                    load_profile_meta_data_resampled,
                ) in stream_load_profile_collections.dict_of_load_entry_meta_data_resampled.items():
                    load_type = stream_load_profile_collections.load_type_dict[load_type_uuid]

                    carpet_plot_matrix = (
                        carpet_plot_load_profile_generator.convert_load_profile_meta_data_to_carpet_plot_matrix(
                            load_profile_meta_data_resampled=load_profile_meta_data_resampled,
                            x_axis_period_time_delta=report_generator_options.carpet_plot_options.x_axis_time_delta,
                            start_date_time_series=report_generator_options.carpet_plot_options.start_date,
                            end_date_time_series=report_generator_options.carpet_plot_options.end_date,
                            resample_frequency=report_generator_options.carpet_plot_options.resample_frequency,
                            object_name=stream_name,
                        )
                    )

                    if type(carpet_plot_matrix) is CarpetPlotMatrixEmpty:
                        pass
                    elif type(carpet_plot_matrix) is CarpetPlotMatrix:
                        carpet_plot_matrix = (
                            carpet_plot_load_profile_generator.compress_power_of_carpet_plot_matrix_if_necessary(
                                carpet_plot_load_profile_matrix=carpet_plot_matrix
                            )
                        )

                        caption = "Stream name: " + str(stream_name) + "Load type: " + str(load_type.name)

                        file_name = (
                            "stream_load_profile_"
                            + str(stream_name)
                            + "-"
                            + str(load_type.name)
                            + self.output_file_format_with_dot
                        )
                        file_name = file_name.replace(" ", "_")
                        output_file = os.path.join(self.carpet_plot_directory_path, file_name)

                        carpet_plot_input_data = CarpetPlotInputData(
                            carpet_plot_matrix=carpet_plot_matrix,
                            output_path=output_file,
                            output_file_extension=self.output_file_format,
                            display_name_report=caption,
                        )
                        list_of_process_step_and_stream_carpet_plot_data.append(carpet_plot_input_data)
                        if load_type.name in load_profile_matrix_dict_by_load_profile:
                            load_profile_matrix_dict_by_load_profile[load_type.name].append(carpet_plot_input_data)
                        else:
                            load_profile_matrix_dict_by_load_profile[load_type.name] = [carpet_plot_input_data]

            for (
                process_step_name,
                process_step_load_profile_collections,
            ) in self.post_process_simulation_data_handler.load_profile_collection_post_processing.dict_process_step_load_profile_collections.items():
                for (
                    load_type_uuid,
                    load_profile_meta_data_resampled,
                ) in process_step_load_profile_collections.dict_of_load_entry_meta_data_resampled.items():
                    load_type = process_step_load_profile_collections.load_type_dict[load_type_uuid]

                    carpet_plot_matrix = (
                        carpet_plot_load_profile_generator.convert_load_profile_meta_data_to_carpet_plot_matrix(
                            load_profile_meta_data_resampled=load_profile_meta_data_resampled,
                            x_axis_period_time_delta=report_generator_options.carpet_plot_options.x_axis_time_delta,
                            start_date_time_series=report_generator_options.carpet_plot_options.start_date,
                            end_date_time_series=report_generator_options.carpet_plot_options.end_date,
                            resample_frequency=report_generator_options.carpet_plot_options.resample_frequency,
                            object_name=process_step_name,
                        )
                    )
                    if type(carpet_plot_matrix) is CarpetPlotMatrixEmpty:
                        pass
                    elif type(carpet_plot_matrix) is CarpetPlotMatrix:
                        carpet_plot_matrix = (
                            carpet_plot_load_profile_generator.compress_power_of_carpet_plot_matrix_if_necessary(
                                carpet_plot_load_profile_matrix=carpet_plot_matrix
                            )
                        )

                        file_name = (
                            "process_state_load_profile_"
                            + str(process_step_name)
                            + "-"
                            + str(load_type.name)
                            + self.output_file_format_with_dot
                        )
                        output_file = os.path.join(self.carpet_plot_directory_path, file_name)

                        figure_caption = "Process Step: " + str(process_step_name) + "Load type: " + str(load_type.name)
                        carpet_plot_input_data = CarpetPlotInputData(
                            carpet_plot_matrix=carpet_plot_matrix,
                            output_path=output_file,
                            display_name_report=figure_caption,
                            output_file_extension=self.output_file_format,
                        )
                        list_of_process_step_and_stream_carpet_plot_data.append(carpet_plot_input_data)

                        if load_type.name in load_profile_matrix_dict_by_load_profile:
                            load_profile_matrix_dict_by_load_profile[load_type.name].append(carpet_plot_input_data)
                        else:
                            load_profile_matrix_dict_by_load_profile[load_type.name] = [carpet_plot_input_data]
        return (
            list_of_process_step_and_stream_carpet_plot_data,
            load_profile_matrix_dict_by_load_profile,
        )

    def collect_combined_load_carpet_plot_input_data(
        self,
        load_profile_matrix_dict_by_load_profile: dict[str, list[CarpetPlotInputData]],
    ) -> list[CarpetPlotInputData]:
        list_of_combined_load_type_carpet_plot_data: list[CarpetPlotInputData] = []
        list_of_combined_carpet_plot_matrices: list[CarpetPlotMatrix] = []
        for (
            current_load_type,
            list_of_carpet_plot_input_data,
        ) in load_profile_matrix_dict_by_load_profile.items():
            list_of_carpet_plot_matrices = []
            for carpet_plot_input_data in list_of_carpet_plot_input_data:
                list_of_carpet_plot_matrices.append(carpet_plot_input_data.carpet_plot_matrix)
            carpet_plot_load_profile_generator = CarpetPlotLoadProfileGenerator()
            combined_matrix_data_frame_for_load_type = carpet_plot_load_profile_generator.combine_matrix_data_frames(
                list_of_carpet_plot_matrices=list_of_carpet_plot_matrices,
                combined_matrix_name="Combined Matrix of load: " + str(current_load_type),
            )

            file_name = "summary_load_profile-" + str(current_load_type) + self.output_file_format_with_dot
            output_file = os.path.join(self.carpet_plot_directory_path, file_name)

            list_of_combined_carpet_plot_matrices.append(combined_matrix_data_frame_for_load_type)
            caption = "Whole process energy demand for Load type: " + str(current_load_type)
            combined_input_data = CarpetPlotInputData(
                carpet_plot_matrix=combined_matrix_data_frame_for_load_type,
                output_path=output_file,
                display_name_report=caption,
                output_file_extension=self.output_file_format,
            )

            list_of_combined_load_type_carpet_plot_data.append(combined_input_data)

        carpet_plot_load_profile_generator = CarpetPlotLoadProfileGenerator()
        total_energy_combined_matrix_data_frame = carpet_plot_load_profile_generator.combine_matrix_data_frames(
            list_of_combined_carpet_plot_matrices,
            combined_matrix_name="Total Energy Demand of all energy carriers",
            combined_load_type=LoadType(name="Combined Load Type"),
        )

        file_name = "total_energy_load_profile" + self.output_file_format_with_dot
        output_file = os.path.join(self.carpet_plot_directory_path, file_name)
        combined_input_data = CarpetPlotInputData(
            carpet_plot_matrix=total_energy_combined_matrix_data_frame,
            output_path=output_file,
            display_name_report="All energy carriers combined",
            output_file_extension=self.output_file_format,
        )

        list_of_combined_load_type_carpet_plot_data.append(combined_input_data)
        return list_of_combined_load_type_carpet_plot_data

    def create_carpet_plot_page(self, report_generator_options: ReportGeneratorOptions) -> datapane.Group:
        """Creates the carpet plot page of the result report.

        Args:
            report_generator_options (ReportGeneratorOptions): Contains
                the options to adjust the appearance of the report.

        Returns:
            datapane.Group: DataPane object that represents the carpet plot page of the
                report.
        """
        if report_generator_options.carpet_plot_options.create_all is True:
            logger.info("Start generation of load profile carpet plot page")

            (
                list_of_process_step_and_stream_carpet_plot_data,
                load_profile_matrix_dict_by_load_profile,
            ) = self.collect_single_carpet_plot_input_data(report_generator_options=report_generator_options)
            list_of_combined_load_type_carpet_plot_data = self.collect_combined_load_carpet_plot_input_data(
                load_profile_matrix_dict_by_load_profile=load_profile_matrix_dict_by_load_profile
            )
            all_carpet_plot_input_data_list = [
                *list_of_process_step_and_stream_carpet_plot_data,
                *list_of_combined_load_type_carpet_plot_data,
            ]
            if report_generator_options.disable_multiprocessing is True:
                self.plot_matrices_single_core(matrix_input_data_list=all_carpet_plot_input_data_list)
            else:
                self.plot_matrices(
                    matrix_input_data_list=all_carpet_plot_input_data_list,
                    report_generator_options=report_generator_options,
                )

            if list_of_process_step_and_stream_carpet_plot_data:
                carpet_plot_list = self.create_datapane_plot(
                    matrix_input_data_list=list_of_process_step_and_stream_carpet_plot_data
                )
                individual_load_profile_group = datapane.Group(
                    label="Load profile carpet plots",
                    blocks=[
                        datapane.Group(
                            blocks=carpet_plot_list,
                            columns=report_generator_options.carpet_plot_options.number_of_columns,
                        )
                    ],
                )
            else:
                individual_load_profile_group = None
            if list_of_combined_load_type_carpet_plot_data:
                list_of_combined_load_profile_figures = self.create_datapane_plot(
                    matrix_input_data_list=list_of_combined_load_type_carpet_plot_data
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
            else:
                combined_carpet_plot_groups = None

            # self.list_of_carpet_plot_output_file_paths

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
                    blocks=[datapane.HTML("No Load Profiles have been Created")],
                )

            return carpet_plot_page
            # if carpet_plot_dict_by_load_profile:
            #     pass

    def create_carpet_plot(self, carpet_plot_input_data: CarpetPlotInputData) -> str:
        carpet_plot_load_profile_generator = CarpetPlotLoadProfileGenerator()
        carpet_plot = carpet_plot_load_profile_generator.plot_load_profile_carpet_from_data_frame_matrix(
            carpet_plot_load_profile_matrix=carpet_plot_input_data.carpet_plot_matrix
        )
        carpet_plot.savefig(
            carpet_plot_input_data.output_path,
            format=carpet_plot_input_data.output_file_extension,
            bbox_inches="tight",
            dpi=300,
        )
        return carpet_plot_input_data.output_path

    def plot_matrices(
        self,
        matrix_input_data_list: list[CarpetPlotInputData],
        report_generator_options: ReportGeneratorOptions,
    ) -> list[str]:

        asynchronous_multi_processor = AsynchronousMultiProcessor(
            number_of_process=report_generator_options.number_of_processes_used_for_plotting
        )

        list_of_output_paths = asynchronous_multi_processor.run_function_in_parallel(
            func=self.create_carpet_plot, iterable=matrix_input_data_list
        )  # get all results

        return list_of_output_paths

    def plot_matrices_single_core(
        self,
        matrix_input_data_list: list[CarpetPlotInputData],
    ) -> list[str]:

        list_of_output_paths = []
        for carpet_plot_input_data in matrix_input_data_list:
            self.create_carpet_plot(carpet_plot_input_data=carpet_plot_input_data)
            list_of_output_paths.append(carpet_plot_input_data.output_path)

        return list_of_output_paths

    def create_datapane_plot(self, matrix_input_data_list: list[CarpetPlotInputData]) -> list[datapane.Media]:
        list_of_data_pane_plots = []
        for input_matrix in matrix_input_data_list:
            datapane_plot = datapane.Media(file=input_matrix.output_path, caption=input_matrix.display_name_report)
            list_of_data_pane_plots.append(datapane_plot)

        return list_of_data_pane_plots
