import datetime
import os
import traceback
import warnings
import webbrowser
from pathlib import Path

import datapane
import matplotlib
import matplotlib.pyplot

from ethos_penalps.data_classes import CurrentProcessNode, LoopCounter
from ethos_penalps.load_profile_calculator import LoadProfileHandlerSimulation, LoadType
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
from ethos_penalps.utilities.debugging_information import (
    DebuggingInformationLogger,
    NodeOperationViewer,
)
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.post_processing.load_profile_entry_post_processor import (
    LoadProfileEntryPostProcessor,
)
from ethos_penalps.post_processing.post_processed_data_handler import (
    PostProcessSimulationDataHandler,
)

logger = PeNALPSLogger.get_logger_without_handler()

# Suppresses a warning about the number of open matplot figures
matplotlib.pyplot.rcParams.update({"figure.max_open_warning": 0})


class EnterpriseReportGenerator:
    """Creates a report for the simulation results of the complete Enterprise."""

    def __init__(
        self,
        production_plan: ProductionPlan,
        # process_node_dict: dict[float, ProductionOrder],
        # stream_handler: StreamHandler,
        enterprise_name: str,
        list_of_network_level: list[NetworkLevel],
        post_process_simulation_data_handler: PostProcessSimulationDataHandler,
        # production_order_dict: dict[float, ProductionOrder],
    ) -> None:
        """

        Args:
            production_plan (ProductionPlan): Contains the unprocessed simulation results.
            enterprise_name (str): Name of the simulated Enterprise. Is used in figures.
            list_of_network_level (list[NetworkLevel]): A list of all NetworkLevel of the
                Enterprise.
            post_process_simulation_data_handler (PostProcessSimulationDataHandler): Contains
                the post processed simulation results.
        """
        self.production_plan: ProductionPlan = production_plan
        self.group_list: list[datapane.Group] = []
        self.list_of_network_level: list[NetworkLevel] = list_of_network_level
        self.post_process_simulation_data_handler: PostProcessSimulationDataHandler = (
            post_process_simulation_data_handler
        )
        self.open_report_after_creation = True
        self.enterprise_name: str = enterprise_name
        self.report_directory: str | None = None
        self.list_of_carpet_plot_output_file_paths: list[str] = []
        self.network_analyzer: NetworkAnalyzer = NetworkAnalyzer(
            list_of_network_level=list_of_network_level
        )
        self.result_selector: ResultSelector = ResultSelector(
            production_plan=production_plan,
            list_of_network_level=list_of_network_level,
            load_profile_handler=production_plan.load_profile_handler,
            post_process_simulation_data_handler=post_process_simulation_data_handler,
        )

    def add_output_directory(self, output_directory: str | None):
        """Manually adds a path to the report output directory.

        Args:
            output_directory (str | None): Path to the report output directory.
        """
        if isinstance(output_directory, str):
            Path(output_directory).mkdir(exist_ok=True)
            self.report_directory = output_directory

    def generate_report(self, report_generator_options: ReportGeneratorOptions):
        """Starts to create a HTML report from the simulation results. The
        appearance can be influenced using the report generator options.

        Args:
            report_generator_options (ReportGeneratorOptions): Is an object
                that contains the parameters to adjust the report
                appearance.
        """
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
        # Create Process Overview Page
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
        # Create Production Plan Data Frame Page
        if (
            report_generator_options.production_plan_data_frame.create_data_frame_page
            is True
        ):
            data_frame_page_generator = DataFramePageGenerator(
                production_plan=self.production_plan,
                post_process_simulation_data_handler=self.post_process_simulation_data_handler,
            )
        data_frame_page = data_frame_page_generator.create_data_frame_page(
            report_generator_options=report_generator_options
        )
        self.group_list.append(data_frame_page)

        # Create Load Profile Overview Page
        load_profile_data_page_generator = LoadProfileDataPageGenerator(
            production_plan=self.production_plan,
            post_process_simulation_data_handler=self.post_process_simulation_data_handler,
        )
        load_profile_data_page = (
            load_profile_data_page_generator.create_load_profile_data_page()
        )
        self.group_list.append(load_profile_data_page)

        # Create Data Frame Page
        gantt_chart_page_generator = GanttChartPageGenerator(
            production_plan=self.production_plan,
            report_directory=self.report_directory,
            result_selector=self.result_selector,
        )
        gantt_chart_page = (
            gantt_chart_page_generator.create_network_level_gantt_chart_page(
                report_generator_options=report_generator_options
            )
        )
        self.group_list.append(gantt_chart_page)
        carpet_plot_page_generator = CarpetPlotPageGenerator(
            production_plan=self.production_plan,
            report_directory=self.report_directory,
            post_process_simulation_data_handler=self.post_process_simulation_data_handler,
        )
        carpet_plot_page = carpet_plot_page_generator.create_carpet_plot_page(
            report_generator_options=report_generator_options
        )
        self.group_list.append(carpet_plot_page)

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
            view = datapane.Select(*self.group_list)
        else:
            view = self.group_list[0]

        datapane.save_report(
            blocks=view,
            path=path_to_main_file,
            open=self.open_report_after_creation,
            # layout=dp.PageLayout.SIDE,
        )

        logger.info("Generation of report is terminated")

    # def create_node_operations_graph(
    #     self, report_generator_options: ReportGeneratorOptions
    # ):
    #     if report_generator_options.node_operation_page_options.include:
    #         logger.info("Start generation of node operation visualization")
    #         node_operation_viewer = self.create_node_operation_viewer()

    #         node_operation_viewer.create_all_node_visualizations()
    #         block_list = []
    #         for path_to_file_svg in node_operation_viewer.list_of_paths_to_images:
    #             block_list.append(datapane.Media(path_to_file_svg))

    #         if block_list:
    #             self.group_list.append(
    #                 datapane.Group(
    #                     label="Node Operation Graphs",
    #                     blocks=block_list,
    #                 )
    #             )

    # def create_node_operation_viewer(self) -> NodeOperationViewer:
    #     node_operation_visualization_directory = os.path.join(
    #         self.report_directory, "node_operation_visualizations"
    #     )

    #     node_operation_viewer = NodeOperationViewer(
    #         debugging_information_logger=self.debugging_information_logger,
    #         process_node_dict=self.process_node_dict,
    #         stream_handler=self.stream_handler,
    #         graph_directory=node_operation_visualization_directory,
    #     )
    #     return node_operation_viewer
