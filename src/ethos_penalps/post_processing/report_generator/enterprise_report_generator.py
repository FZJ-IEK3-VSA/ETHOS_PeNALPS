import datetime
import os
import traceback
import warnings
import webbrowser
from pathlib import Path

import datapane as dp
import matplotlib
import matplotlib.pyplot
import numpy as np
import pandas as pd

from ethos_penalps.data_classes import CurrentProcessNode, LoopCounter
from ethos_penalps.debugging_information import (
    DebuggingInformationLogger,
    NodeOperationViewer,
)
from ethos_penalps.load_profile_calculator import LoadProfileHandler, LoadType
from ethos_penalps.network_level import NetworkLevel
from ethos_penalps.node_operations import ProductionOrder


from ethos_penalps.post_processing.network_analyzer import (
    NetworkAnalyzer,
    ResultSelector,
)
from ethos_penalps.post_processing.process_summary import ProcessOverViewGenerator
from ethos_penalps.post_processing.report_generator.carpet_plot_page import (
    CarpetPlotPageGenerator,
)
from ethos_penalps.post_processing.report_generator.gantt_chart_page import (
    GanttChartPageGenerator,
)
from ethos_penalps.post_processing.report_generator.load_profile_data_page import (
    LoadProfileDataPageGenerator,
)
from ethos_penalps.post_processing.report_generator.process_overview_page import (
    ProcessOverviewPage,
)
from ethos_penalps.post_processing.report_generator.production_plan_data_frame_page import (
    DataFramePageGenerator,
)
from ethos_penalps.post_processing.report_generator.report_options import (
    ReportGeneratorOptions,
)
from ethos_penalps.post_processing.tikz_visualizations.enterprise_graph_builder import (
    EnterpriseGraphBuilderTikz,
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

# Suppresses a warning about the number of open matplot figures
matplotlib.pyplot.rcParams.update({"figure.max_open_warning": 0})


class EnterpriseReportGenerator:
    def __init__(
        self,
        production_plan: ProductionPlan,
        # process_node_dict: dict[float, ProductionOrder],
        # stream_handler: StreamHandler,
        enterprise_name: str,
        list_of_network_level: list[NetworkLevel]
        # production_order_dict: dict[float, ProductionOrder],
    ) -> None:
        self.production_plan: ProductionPlan = production_plan
        self.group_list = []
        self.list_of_network_level: list[NetworkLevel] = list_of_network_level
        # self.load_profile_handler: LoadProfileHandler = load_profile_handler
        # self.process_node_dict: dict[float, ProductionOrder] = process_node_dict
        # self.stream_handler: StreamHandler = stream_handler
        self.open_report_after_creation = True
        self.enterprise_name: str = enterprise_name
        # self.production_order_dict: dict[float, ProductionOrder] = production_order_dict
        self.report_directory: str | None = None
        self.list_of_carpet_plot_output_file_paths: list[str] = []
        self.network_analyzer: NetworkAnalyzer = NetworkAnalyzer(
            list_of_network_level=list_of_network_level
        )
        self.result_selector: ResultSelector = ResultSelector(
            production_plan=production_plan,
            list_of_network_level=list_of_network_level,
            load_profile_handler=production_plan.load_profile_handler,
        )

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

        process_overview_page_generator = ProcessOverviewPage(
            enterprise_name=self.enterprise_name,
            report_directory=self.report_directory,
            list_of_network_level=self.list_of_network_level,
            result_selector=self.result_selector,
        )
        process_overview_page = (
            process_overview_page_generator.create_process_step_overview_page(
                report_generator_options=report_generator_options
            )
        )

        self.group_list.append(process_overview_page)
        if (
            report_generator_options.production_plan_data_frame.create_data_frame_page
            is True
        ):
            data_frame_page_generator = DataFramePageGenerator(
                production_plan=self.production_plan
            )
        data_frame_page = data_frame_page_generator.create_data_frame_page(
            report_generator_options=report_generator_options
        )
        self.group_list.append(data_frame_page)

        load_profile_data_page_generator = LoadProfileDataPageGenerator(
            production_plan=self.production_plan
        )

        load_profile_data_page = (
            load_profile_data_page_generator.create_load_profile_data_page()
        )
        self.group_list.append(load_profile_data_page)
        gantt_chart_page_generator = GanttChartPageGenerator(
            production_plan=self.production_plan,
            network_analyzer=self.network_analyzer,
            report_directory=self.report_directory,
            result_selector=self.result_selector,
        )
        gantt_chart_page = (
            gantt_chart_page_generator.create_network_level_gantt_chart_page(
                report_generator_options=report_generator_options
            )
        )
        # gantt_chart_page = (
        #     gantt_chart_page_generator.create_process_chain_gantt_chart_page(
        #         report_generator_options=report_generator_options
        #     )
        # )
        self.group_list.append(gantt_chart_page)
        carpet_plot_page_generator = CarpetPlotPageGenerator(
            production_plan=self.production_plan, report_directory=self.report_directory
        )
        carpet_plot_page = carpet_plot_page_generator.create_carpet_plot_page(
            report_generator_options=report_generator_options
        )
        self.group_list.append(carpet_plot_page)

        # self.create_carpet_plot_page(report_generator_options=report_generator_options)
        # if report_generator_options.debug_log_options.include is True:
        #     log_data_frame = ITCSLogger.read_log_to_data_frame()

        #     self.group_list.append(
        #         dp.Group(
        #             label="Debug Log",
        #             blocks=[
        #                 dp.HTML(
        #                     html=traceback.format_exc().replace("\n", "<br>"),
        #                     label="Error Message",
        #                 ),
        #                 dp.Table(log_data_frame),
        #             ],
        #         ),
        #     )
        #     excel_debug_log_file_name = os.path.join(
        #         self.report_directory, "excel_debug_log.xlsx"
        #     )
        #     log_data_frame.to_excel(excel_debug_log_file_name)

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
        if len(self.group_list) > 1:
            view = dp.Select(*self.group_list)
        else:
            view = self.group_list[0]

        dp.save_report(
            blocks=view,
            path=path_to_main_file,
            open=self.open_report_after_creation,
            # layout=dp.PageLayout.SIDE,
        )

        logger.info("Generation of report is terminated")

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
