import datetime
import multiprocessing
import os
import traceback
import warnings
import webbrowser
from dataclasses import dataclass
from pathlib import Path

import datapane as dp
import matplotlib
import matplotlib.pyplot
import numpy as np
import pandas as pd
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

from ethos_penalps.data_classes import CurrentProcessNode, LoopCounter
from ethos_penalps.debugging_information import (
    DebuggingInformationLogger,
    NodeOperationViewer,
)
from ethos_penalps.load_profile_calculator import LoadProfileHandler, LoadType
from ethos_penalps.node_operations import ProductionOrder
from ethos_penalps.post_processing.enterprise_graph_for_failed_run import (
    GraphVisualization,
)
from ethos_penalps.post_processing.load_profile_post_processor import (
    LoadProfilePostProcessor,
)
from ethos_penalps.post_processing.load_profile_entry_post_processor import (
    LoadProfileEntryPostProcessor,
)
from ethos_penalps.post_processing.process_summary import ProcessOverViewGenerator
from ethos_penalps.post_processing.report_generator.report_options import (
    ReportGeneratorOptions,
)
from ethos_penalps.post_processing.tikz_visualizations.process_chain_graph_builder import (
    GraphBuilder,
)
from ethos_penalps.post_processing.time_series_visualizations.gantt_chart import (
    GanttChartGenerator,
)
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class ReportGeneratorProcessChain:
    def __init__(
        self,
        production_plan: ProductionPlan,
        debugging_information_logger: DebuggingInformationLogger,
        process_node_dict: dict[float, ProductionOrder],
        stream_handler: StreamHandler,
        enterprise_name: str,
        production_order_dict: dict[float, ProductionOrder],
    ) -> None:
        self.production_plan: ProductionPlan = production_plan
        self.group_list = []

        # self.load_profile_handler: LoadProfileHandler = load_profile_handler
        self.debugging_information_logger: DebuggingInformationLogger = (
            debugging_information_logger
        )
        self.process_node_dict: dict[float, ProductionOrder] = process_node_dict
        self.stream_handler: StreamHandler = stream_handler
        self.open_report_after_creation = True
        self.enterprise_name: str = enterprise_name
        self.production_order_dict: dict[float, ProductionOrder] = production_order_dict
        self.report_directory: str | None = None
        self.list_of_carpet_plot_output_file_paths: list[str] = []

    def add_output_directory(self, output_directory: str | None):
        if isinstance(output_directory, str):
            Path(output_directory).mkdir(exist_ok=True)
            self.report_directory = output_directory

    def generate_report(self, report_generator_options: ReportGeneratorOptions):
        logger.info("Generation of report starts")
        LoopCounter.loop_number = "Report_creation"
        CurrentProcessNode.node_name = "Report_creator"
        if self.report_directory is None:
            if hasattr(PeNALPSLogger, "directory_to_log"):
                self.report_directory = PeNALPSLogger.directory_to_log
            else:
                result_path_generator = ResultPathGenerator()
                self.report_directory: str = (
                    result_path_generator.create_result_folder_relative_to_main_file(
                        subdirectory_name="report"
                    )
                )

        if report_generator_options.check_if_process_state_conversion_is_necessary():
            self.production_plan.convert_stream_entries_to_meta_data_data_frames()

        if report_generator_options.check_if_stream_state_conversion_is_necessary():
            self.production_plan.convert_process_state_dictionary_to_list_of_data_frames()

        self.create_process_step_overview_page(
            report_generator_options=report_generator_options
        )
        self.create_stream_state_page(report_generator_options=report_generator_options)
        # self.create_process_state_page(
        #     report_generator_options=report_generator_options
        # )

        self.create_page_only_with_process_state_data_frames(
            report_generator_options=report_generator_options
        )
        self.create_page_only_with_stream_data_frames(
            report_generator_options=report_generator_options
        )
        self.create_storage_state_data_frame_page(
            report_generator_options=report_generator_options
        )
        self.create_full_process_gantt_chart_page(
            report_generator_options=report_generator_options
        )
        self.create_process_step_gantt_charts_page(
            report_generator_options=report_generator_options
        )
        self.create_load_profile_data_page(
            report_generator_options=report_generator_options
        )
        self.create_enterprise_visualization_page(
            report_generator_options=report_generator_options
        )
        self.create_node_operations_graph(
            report_generator_options=report_generator_options
        )
        self.create_carpet_plot_page(report_generator_options=report_generator_options)
        if report_generator_options.debug_log_page.include is True:
            log_data_frame = PeNALPSLogger.read_log_to_data_frame()

            self.group_list.append(
                dp.Group(
                    label="Debug Log",
                    blocks=[
                        dp.HTML(
                            html=traceback.format_exc().replace("\n", "<br>"),
                            label="Error Message",
                        ),
                        dp.Table(log_data_frame),
                    ],
                ),
            )
            excel_debug_log_file_name = os.path.join(
                self.report_directory, "excel_debug_log.xlsx"
            )
            log_data_frame.to_excel(excel_debug_log_file_name)

        if self.report_directory is None:
            result_path_generator = ResultPathGenerator()
            path_to_main_file = (
                result_path_generator.create_path_to_file_relative_to_main_file(
                    file_name=report_generator_options.report_name,
                    subdirectory_name="results",
                    file_extension=".html",
                )
            )
        else:
            result_path_generator = ResultPathGenerator()
            path_to_main_file = os.path.join(
                self.report_directory, report_generator_options.report_name + ".html"
            )
            # path_to_main_file = os.path.join(
            #     self.report_directory, "post_simulation_report.html"
            # )
        if len(self.group_list) > 1:
            view = dp.Select(*self.group_list)
        else:
            view = self.group_list[0]

        report = dp.save_report(
            blocks=view,
            path=path_to_main_file,
            open=self.open_report_after_creation
            # layout=dp.PageLayout.SIDE,
        )

        # https://github.com/datapane/datapane-docs/tree/v2/reports/blocks#report-types
        # if not self.datapane_page_list:
        #     raise Exception("Tried to create empty report")
        # report.save(
        #     path=path_to_main_file,
        #     # path=r"example\asd.html",
        #     formatting=dp.ReportFormatting(width=dp.ReportWidth.FULL),
        # )
        # if self.open_report_after_creation:
        #     webbrowser.open(path_to_main_file)
        logger.info("Generation of report is terminated")

    def create_page_only_with_process_state_data_frames(
        self, report_generator_options: ReportGeneratorOptions
    ):
        if report_generator_options.process_state_display_options.include is True:
            logger.info("Start generation of page with process state data frames")
            process_state_block_list = []
            process_state_data_frame_list = (
                self.production_plan.dict_of_process_step_data_frames
            )
            for (
                process_state_data_frame_meta_information
            ) in process_state_data_frame_list:
                if process_state_data_frame_meta_information.data_frame.empty:
                    pass
                else:
                    process_state_block_list.append(
                        dp.DataTable(
                            process_state_data_frame_meta_information.data_frame
                        )
                    )

            if process_state_block_list:
                self.group_list.append(
                    dp.Group(
                        label="Process State Data Frames",
                        blocks=[
                            *process_state_block_list,
                        ],
                    ),
                )

    def create_full_process_gantt_chart_page(
        self, report_generator_options: ReportGeneratorOptions
    ):
        full_process_page_block = []
        if report_generator_options.full_process_gantt_chart.create_gantt_chart is True:
            logger.info("Start generation of full process state gantt chart")
            gantt_chart_generator = GanttChartGenerator(
                production_plan=self.production_plan,
                process_node_dict=self.process_node_dict,
                stream_handler=self.stream_handler,
            )
            list_of_full_process_gantt_chart = gantt_chart_generator.create_gantt_chart_from_meta_data_list(
                show_graph=False,
                start_date=report_generator_options.full_process_gantt_chart.plot_start_time,
                end_date=report_generator_options.full_process_gantt_chart.plot_end_time,
                include_process_state_load_profiles=report_generator_options.full_process_gantt_chart.include_load_profiles,
                include_stream_load_profiles=report_generator_options.full_process_gantt_chart.include_load_profiles,
                maximum_number_of_rows=report_generator_options.full_process_gantt_chart.maximum_number_of_vertical_plots,
                include_storage_gantt_chart=report_generator_options.full_process_gantt_chart.include_storage_gantt_charts,
            )
            file_iterator = 0
            for full_process_gantt_chart in list_of_full_process_gantt_chart:
                full_process_gantt_chart: matplotlib.pyplot.Figure
                result_path_generator = ResultPathGenerator()
                process_gantt_chart_directory = "gantt_charts"
                gantt_chart_directory_path = (
                    result_path_generator.create_subdirectory_relative_to_parent(
                        parent_directory_path=self.report_directory,
                        new_directory_name=process_gantt_chart_directory,
                    )
                )
                file_extension = ".png"
                file_name = (
                    "full_process_gantt_chart_" + str(file_iterator) + file_extension
                )
                """Exception has occurred: ValueError       (note: full exception trace is shown but execution is paused at: <module>) bottom cannot be >= top
                """
                # Solution reduce number of plots in graph
                output_file = os.path.join(gantt_chart_directory_path, file_name)
                full_process_gantt_chart.savefig(output_file, format="png")
                file_iterator = file_iterator + 1
            for full_process_gantt_chart in list_of_full_process_gantt_chart:
                full_process_page_block.append(
                    dp.Plot(full_process_gantt_chart, responsive=False)
                )

        if report_generator_options.full_process_gantt_chart.include_order_dict is True:
            order_data_frame = pd.DataFrame(list(self.production_order_dict.values()))

            full_process_page_block.append(dp.DataTable(order_data_frame))

        if full_process_page_block:
            self.group_list.append(
                dp.Group(
                    label="Full process gantt chart",
                    blocks=full_process_page_block,
                )
            )

    def create_process_step_gantt_charts_page(
        self, report_generator_options: ReportGeneratorOptions
    ):
        full_process_page_block = []
        if (
            report_generator_options.process_step_gantt_chart_options.create_gantt_chart
            is True
        ):
            logger.info("Start generation of process step gantt charts")
            gantt_chart_generator = GanttChartGenerator(
                production_plan=self.production_plan,
                process_node_dict=self.process_node_dict,
                stream_handler=self.stream_handler,
            )
            list_of_full_process_gantt_chart = gantt_chart_generator.create_gantt_charts_for_each_process_step(
                start_date=report_generator_options.process_step_gantt_chart_options.plot_start_time,
                end_date=report_generator_options.process_step_gantt_chart_options.plot_end_time,
                include_input_streams=report_generator_options.process_step_gantt_chart_options.include_input_streams,
                include_each_output_stream=report_generator_options.process_step_gantt_chart_options.include_each_output_stream,
                only_include_output_stream_to_sink=report_generator_options.process_step_gantt_chart_options.only_include_output_stream_to_sink,
                include_process_state_load_profiles=report_generator_options.process_step_gantt_chart_options.include_load_profiles,
                include_stream_load_profiles=report_generator_options.process_step_gantt_chart_options.include_load_profiles,
                maximum_number_of_rows=report_generator_options.process_step_gantt_chart_options.maximum_number_of_vertical_plots,
                include_storage_gantt_chart=report_generator_options.process_step_gantt_chart_options.include_storage_gantt_chart,
            )
            file_iterator = 0
            for full_process_gantt_chart in list_of_full_process_gantt_chart:
                full_process_gantt_chart: matplotlib.pyplot.Figure
                result_path_generator = ResultPathGenerator()
                process_gantt_chart_directory = "process_step_gantt_charts"
                gantt_chart_directory_path = (
                    result_path_generator.create_subdirectory_relative_to_parent(
                        parent_directory_path=self.report_directory,
                        new_directory_name=process_gantt_chart_directory,
                    )
                )
                file_extension = ".svg"
                file_name = (
                    "full_process_gantt_chart_" + str(file_iterator) + file_extension
                )
                """Exception has occurred: ValueError       (note: full exception trace is shown but execution is paused at: <module>) bottom cannot be >= top
                """
                # Solution reduce number of plots in graph
                output_file = os.path.join(gantt_chart_directory_path, file_name)
                full_process_gantt_chart.savefig(output_file, format="svg")
                file_iterator = file_iterator + 1
            for full_process_gantt_chart in list_of_full_process_gantt_chart:
                full_process_page_block.append(
                    dp.Plot(full_process_gantt_chart, responsive=False)
                )

        if report_generator_options.full_process_gantt_chart.include_order_dict is True:
            order_data_frame = pd.DataFrame(list(self.production_order_dict.values()))

            full_process_page_block.append(dp.DataTable(order_data_frame))

        if full_process_page_block:
            self.group_list.append(
                dp.Group(
                    label="Process Step Gantt Charts",
                    blocks=full_process_page_block,
                )
            )

    def create_storage_state_data_frame_page(
        self, report_generator_options: ReportGeneratorOptions
    ):
        logger.info("Start generation storage state data frame page")
        if report_generator_options.storage_state_page.create is True:
            storage_block_list = []
            storage_state_dictionary = self.production_plan.storage_state_dict
            for process_step_name in storage_state_dictionary:
                for commodity in storage_state_dictionary[process_step_name]:
                    storage_data_frame = pd.DataFrame(
                        storage_state_dictionary[process_step_name][commodity]
                    )
                    storage_block_list.append(dp.DataTable(storage_data_frame))
            if storage_block_list:
                self.group_list.append(
                    dp.Group(
                        label="Storage Data Frames",
                        blocks=[
                            *storage_block_list,
                        ],
                    ),
                )

    def create_enterprise_visualization_page(
        self, report_generator_options: ReportGeneratorOptions
    ) -> str:
        if (
            report_generator_options.process_overview_page_options.include_enterprise_graph
            is True
        ):
            try:
                path_to_enterprise_structure_graph_png = (
                    self.create_enterprise_visualization()
                )
                self.group_list.append(
                    dp.Group(
                        label="Process Overview",
                        blocks=[
                            dp.Media(
                                file=path_to_enterprise_structure_graph_png,
                            )
                        ],
                    )
                )

            except:
                self.group_list.append(
                    dp.HTML(
                        html=traceback.format_exc().replace("\n", "<br>"),
                        label="Enterprise structure graph could ne be created",
                    ),
                )

    def create_enterprise_visualization(
        self,
    ) -> str:
        logger.info("Start generation of enterprise visualization")

        graph_builder = GraphBuilder(
            process_node_dict=self.process_node_dict,
            enterprise_name=self.enterprise_name,
            stream_handler=self.stream_handler,
        )
        path_to_enterprise_structure_graph_png = graph_builder.create_enterprise_graph(
            show_graph=False,
            path_to_results_folder=self.report_directory,
            output_format="png",
        )

        return path_to_enterprise_structure_graph_png

    def create_load_profile_data_page(
        self, report_generator_options: ReportGeneratorOptions
    ):
        if report_generator_options.load_profile_data_page.include is True:
            logger.info("Start generation of load profile data page")

            dict_stream_load_profile_data_frames = (
                self.production_plan.load_profile_handler.load_profile_collection.convert_stream_energy_dict_to_data_frame()
            )
            stream_load_profile_table_list = []
            for (
                stream_name,
                load_type_profile_dict,
            ) in dict_stream_load_profile_data_frames.items():
                for (
                    load_type,
                    load_profile_data_frame,
                ) in load_type_profile_dict.items():
                    caption = stream_name + ": " + load_type.name

                    stream_load_profile_table_list.append(
                        dp.DataTable(load_profile_data_frame, caption=caption)
                    )
            if stream_load_profile_table_list:
                self.group_list.append(
                    dp.Group(
                        label="Stream Load Profiles",
                        blocks=stream_load_profile_table_list,
                    )
                )
            dict_process_step_load_profile_data_frames = (
                self.production_plan.load_profile_handler.load_profile_collection.convert_process_state_energy_date()
            )
            process_step_load_profile_table_list = []
            for (
                process_step_name,
                load_type_profile_dict,
            ) in dict_process_step_load_profile_data_frames.items():
                for (
                    load_type,
                    load_profile_data_frame,
                ) in load_type_profile_dict.items():
                    caption = process_step_name + ": " + load_type.name

                    process_step_load_profile_table_list.append(
                        dp.DataTable(load_profile_data_frame, caption=caption)
                    )
            if process_step_load_profile_table_list:
                self.group_list.append(
                    dp.Group(
                        label="Process Step Load Profiles",
                        blocks=process_step_load_profile_table_list,
                    )
                )

    def create_node_operations_graph(
        self, report_generator_options: ReportGeneratorOptions
    ):
        if report_generator_options.node_operation_page_options.include:
            logger.info("Start generation of node operation visualization")
            node_operation_viewer = self.create_node_operation_viewer()

            node_operation_viewer.create_all_node_visualizations()
            block_list = []
            for path_to_file_svg in node_operation_viewer.list_of_paths_to_images:
                block_list.append(dp.Media(path_to_file_svg))

            if block_list:
                self.group_list.append(
                    dp.Group(
                        label="Node Operation Graphs",
                        blocks=block_list,
                    )
                )

    def create_node_operation_viewer(self) -> NodeOperationViewer:
        node_operation_visualization_directory = os.path.join(
            self.report_directory, "node_operation_visualizations"
        )

        node_operation_viewer = NodeOperationViewer(
            debugging_information_logger=self.debugging_information_logger,
            process_node_dict=self.process_node_dict,
            stream_handler=self.stream_handler,
            graph_directory=node_operation_visualization_directory,
        )
        return node_operation_viewer

    def create_process_step_overview_page(
        self, report_generator_options: ReportGeneratorOptions
    ):
        if (
            report_generator_options.process_overview_page_options.include_enterprise_graph
            is True
        ):
            block_list = []
            process_overview_generator = ProcessOverViewGenerator(
                process_node_dict=self.process_node_dict,
                load_profile_handler=self.production_plan.load_profile_handler,
                stream_handler=self.stream_handler,
                order_dictionary=self.production_order_dict,
                enterprise_name=self.enterprise_name,
                production_plan=self.production_plan,
            )
            pie_chart_figure = (
                process_overview_generator.create_product_energy_pie_chart()
            )
            total_energy_data_frame = (
                process_overview_generator.calculate_total_energy_demands()
            )
            total_stream_mass_data_frame = (
                process_overview_generator.get_total_mass_for_each_stream()
            )
            process_mass_and_energy_data_frame = (
                process_overview_generator.get_total_mass_and_energy_for_process_step()
            )

            try:
                path_to_enterprise_structure_graph_png = (
                    self.create_enterprise_visualization()
                )

                block_list.append(dp.Media(file=path_to_enterprise_structure_graph_png))

            except:
                block_list.append(
                    dp.HTML(
                        html=traceback.format_exc().replace("\n", "<br>"),
                        label="Enterprise structure graph could ne be created",
                    ),
                )

            if pie_chart_figure is not None:
                block_list.append(dp.Plot(pie_chart_figure, responsive=False))
            block_list.append(
                dp.Table(
                    total_stream_mass_data_frame,
                    caption="Total stream masses based on simulation results",
                )
            )
            block_list.append(
                dp.Table(
                    total_energy_data_frame,
                    caption="Total process energy demand based on production order targets",
                )
            )
            block_list.append(
                dp.Table(
                    process_mass_and_energy_data_frame,
                    caption="Summary on energy relevant process steps",
                )
            )

            self.group_list.append(
                dp.Group(
                    label="Process Overview",
                    blocks=block_list,
                )
            )

    def create_carpet_plot_page(self, report_generator_options: ReportGeneratorOptions):
        if report_generator_options.carpet_plot_options.create_all is True:
            logger.info("Start generation of load profile carpet plot page")
            carpet_plot_list = []
            load_profile_matrix_dict_by_load_profile: dict[
                load_type, list[pd.DataFrame]
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

            if list_of_list_of_load_profile_entries:
                combined_load_profile_start_date = load_profile_entry_post_processor_for_start_time_check.determine_earliest_start_date_from_list_of_list_of_load_profile_entries(
                    end_date=report_generator_options.carpet_plot_options.end_date,
                    period=report_generator_options.carpet_plot_options.x_axis_time_delta,
                    list_of_list_of_load_profile_entries=self.production_plan.load_profile_handler.get_list_of_list_of_all_load_profile_entries(),
                )
                for (
                    stream_name
                ) in (
                    self.production_plan.load_profile_handler.load_profile_collection.dict_stream_load_profile_collections
                ):
                    for (
                        load_type
                    ) in self.production_plan.load_profile_handler.load_profile_collection.dict_stream_load_profile_collections[
                        stream_name
                    ]:
                        load_profile_post_processor = LoadProfilePostProcessor()
                        load_profile_df_matrix = load_profile_post_processor.convert_lpg_load_profile_to_data_frame_matrix(
                            list_of_load_profile_entries=self.production_plan.load_profile_handler.load_profile_collection.dict_stream_load_profile_collections[
                                stream_name
                            ][
                                load_type
                            ],
                            end_date_time_series=report_generator_options.carpet_plot_options.end_date,
                            start_date_time_series=combined_load_profile_start_date,
                            x_axis_time_period_timedelta=report_generator_options.carpet_plot_options.x_axis_time_delta,
                            resample_frequency=report_generator_options.carpet_plot_options.resample_frequency,
                        )
                        fig = load_profile_post_processor.plot_load_profile_carpet_from_data_frame_matrix(
                            start_date=combined_load_profile_start_date,
                            end_date=report_generator_options.carpet_plot_options.end_date,
                            load_profile_matrix=load_profile_df_matrix,
                            x_axis_whole_period=report_generator_options.carpet_plot_options.x_axis_time_delta,
                            resample_frequency=report_generator_options.carpet_plot_options.resample_frequency,
                            load_type_name=load_type,
                        )
                        caption = (
                            "Stream name: "
                            + str(stream_name)
                            + "Load type: "
                            + str(load_profile_post_processor.load_type)
                        )

                        file_name = (
                            "stream_load_profile_"
                            + str(stream_name)
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

                        carpet_plot_list.append(dp.Media(output_file, caption=caption))
                        if load_type in load_profile_matrix_dict_by_load_profile:
                            load_profile_matrix_dict_by_load_profile[load_type].append(
                                load_profile_df_matrix
                            )
                        else:
                            load_profile_matrix_dict_by_load_profile[load_type] = [
                                load_profile_df_matrix
                            ]

                for (
                    process_state_name
                ) in (
                    self.production_plan.load_profile_handler.load_profile_collection.dict_process_step_load_profile_collections
                ):
                    for (
                        load_type
                    ) in self.production_plan.load_profile_handler.load_profile_collection.dict_process_step_load_profile_collections[
                        process_state_name
                    ]:
                        load_profile_post_processor = LoadProfilePostProcessor()
                        load_profile_df_matrix = load_profile_post_processor.convert_lpg_load_profile_to_data_frame_matrix(
                            list_of_load_profile_entries=self.production_plan.load_profile_handler.load_profile_collection.dict_process_step_load_profile_collections[
                                process_state_name
                            ][
                                load_type
                            ],
                            end_date_time_series=report_generator_options.carpet_plot_options.end_date,
                            start_date_time_series=combined_load_profile_start_date,
                            x_axis_time_period_timedelta=report_generator_options.carpet_plot_options.x_axis_time_delta,
                            resample_frequency=report_generator_options.carpet_plot_options.resample_frequency,
                        )
                        fig = load_profile_post_processor.plot_load_profile_carpet_from_data_frame_matrix(
                            start_date=combined_load_profile_start_date,
                            end_date=report_generator_options.carpet_plot_options.end_date,
                            load_profile_matrix=load_profile_df_matrix,
                            x_axis_whole_period=report_generator_options.carpet_plot_options.x_axis_time_delta,
                            resample_frequency=report_generator_options.carpet_plot_options.resample_frequency,
                            load_type_name=load_type,
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
                            + str(load_profile_post_processor.load_type)
                        )

                        carpet_plot_list.append(
                            dp.Media(output_file, caption=figure_caption)
                        )
                        if load_type in load_profile_matrix_dict_by_load_profile:
                            load_profile_matrix_dict_by_load_profile[load_type].append(
                                load_profile_df_matrix
                            )
                        else:
                            load_profile_matrix_dict_by_load_profile[load_type] = [
                                load_profile_df_matrix
                            ]
                if carpet_plot_list:
                    self.group_list.append(
                        dp.Group(
                            label="Load profile carpet plots",
                            blocks=[
                                dp.Group(
                                    blocks=carpet_plot_list,
                                    columns=report_generator_options.carpet_plot_options.number_of_columns,
                                )
                            ],
                        )
                    )

                list_of_combined_matrix_data_frames = []
                list_of_combined_load_profile_figures = []
                for load_type in load_profile_matrix_dict_by_load_profile:
                    load_profile_post_processor = LoadProfilePostProcessor()
                    combined_matrix_data_frame_for_load_type = load_profile_post_processor.combine_matrix_data_frames(
                        list_of_carpet_plot_matrices=load_profile_matrix_dict_by_load_profile[
                            load_type
                        ]
                    )
                    combined_load_profile_figure = load_profile_post_processor.plot_load_profile_carpet_from_data_frame_matrix(
                        load_profile_matrix=combined_matrix_data_frame_for_load_type,
                        start_date=combined_load_profile_start_date,
                        end_date=report_generator_options.carpet_plot_options.end_date,
                        x_axis_whole_period=report_generator_options.carpet_plot_options.x_axis_time_delta,
                        resample_frequency=report_generator_options.carpet_plot_options.resample_frequency,
                        load_type_name=load_type,
                    )
                    file_name = (
                        "summary_load_profile-"
                        + str(load_type.name)
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
                        dp.Media(
                            output_file,
                            caption="Whole process energy demand for Load type: "
                            + str(load_type),
                        )
                    )
                    list_of_combined_matrix_data_frames.append(
                        combined_matrix_data_frame_for_load_type
                    )

                load_profile_post_processor = LoadProfilePostProcessor()
                total_energy_combined_matrix_data_frame = (
                    load_profile_post_processor.combine_matrix_data_frames(
                        list_of_combined_matrix_data_frames
                    )
                )
                total_energy_carpet_plot = load_profile_post_processor.plot_load_profile_carpet_from_data_frame_matrix(
                    load_profile_matrix=total_energy_combined_matrix_data_frame,
                    start_date=combined_load_profile_start_date,
                    end_date=report_generator_options.carpet_plot_options.end_date,
                    x_axis_whole_period=report_generator_options.carpet_plot_options.x_axis_time_delta,
                    resample_frequency=report_generator_options.carpet_plot_options.resample_frequency,
                    load_type_name=LoadType(name="Combined Load Types"),
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
                    dp.Media(output_file, caption="Total energy plot")
                )
                self.group_list.append(
                    dp.Group(
                        label="Combined carpet plots",
                        blocks=[
                            dp.Group(
                                blocks=list_of_combined_load_profile_figures,
                                columns=report_generator_options.carpet_plot_options.number_of_columns,
                            )
                        ],
                    )
                )
            # if carpet_plot_dict_by_load_profile:
            #     pass
