import datetime
import os
from dataclasses import dataclass

import datapane
import matplotlib.pyplot
import pandas
import proplot

from ethos_penalps.data_classes import (
    EmptyLoadProfileMetadata,
    EmptyMetaDataInformation,
    LoadProfileMetaData,
    LoadProfileMetaDataResampled,
    ProcessStepDataFrameMetaInformation,
    ProductionOrderMetadata,
    StorageDataFrameMetaInformation,
)
from ethos_penalps.post_processing.production_plan_post_processing.network_analyzer import (
    # NetworkAnalyzer,
    ResultSelector,
)
from ethos_penalps.post_processing.report_generator.report_options import (
    ReportGeneratorOptions,
)
from ethos_penalps.post_processing.time_series_visualizations.gantt_chart import (
    GanttChartGenerator,
)
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream import StreamDataFrameMetaInformation
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.multiprocessor import AsynchronousMultiProcessor
from ethos_penalps.utilities.type_aliases import numbers_alias

logger = PeNALPSLogger.get_logger_without_handler()


@dataclass
class GanttChartInputData:
    list_of_meta_data: list[
        StorageDataFrameMetaInformation
        | LoadProfileMetaData
        | LoadProfileMetaDataResampled
        | ProcessStepDataFrameMetaInformation
        | StreamDataFrameMetaInformation
        | ProductionOrderMetadata
        | EmptyLoadProfileMetadata
        | EmptyMetaDataInformation
    ]
    start_date: datetime.datetime
    end_date: datetime.datetime
    gantt_chart_title: str
    gantt_chart_file_path: str
    output_format: str

    def check_if_contains_non_empty_data(self) -> bool:
        contains_non_empty_data = False
        for current_meta_data in self.list_of_meta_data:
            if isinstance(
                current_meta_data,
                (
                    StorageDataFrameMetaInformation,
                    LoadProfileMetaData,
                    LoadProfileMetaDataResampled,
                    ProcessStepDataFrameMetaInformation,
                    StreamDataFrameMetaInformation,
                    ProductionOrderMetadata,
                ),
            ):
                contains_non_empty_data = True
        return contains_non_empty_data


class GanttChartPageGenerator:
    """Creates the GanttChart Page of the report."""

    def __init__(
        self,
        production_plan: ProductionPlan,
        result_selector: ResultSelector,
        report_directory: str,
        output_file_format: str = "png",
        dpi: int = 300,
        figure_folder_name: str = "gantt_chart_plots",
    ) -> None:
        """

        Args:
            production_plan (ProductionPlan): Contains the unprocessed
                simulation results.
            result_selector (ResultSelector): Object that contains
                the simulation in a structure that resembles the
                material flow simulation.
            report_directory (str): Path to the
                report directory. If set to None a folder relative
                to the main file is created. Defaults to None.
        """
        self.production_plan: ProductionPlan = production_plan
        self.result_selector: ResultSelector = result_selector
        self.report_directory: str = report_directory
        self.gantt_chart_generator = GanttChartGenerator(
            production_plan=self.production_plan,
            process_node_dict={},
            stream_handler=None,
        )
        self.output_file_format: str = output_file_format
        self.output_file_format_with_dot: str = "." + output_file_format
        self.dpi: int = dpi
        self.figure_folder_name: str = figure_folder_name
        result_path_generator = ResultPathGenerator()
        self.gantt_chart_directory_path = result_path_generator.create_subdirectory_relative_to_parent(
            parent_directory_path=self.report_directory,
            new_directory_name=figure_folder_name,
        )

    def create_network_level_gantt_chart_page(self, report_generator_options: ReportGeneratorOptions) -> datapane.Group:
        """Create Gantt Charts for all Network Level.

        Args:
            report_generator_options (ReportGeneratorOptions): Is an object
                that contains the parameters to adjust the report
                appearance.

        Returns:
            datapane.Group: DataPane object that represents the Gantt chart page of the
                report.
        """
        figure_list = []
        output_file_extension = "png"

        if report_generator_options.gantt_charts.create_gantt_chart is True:
            logger.info("Start generation of process step gantt charts")

            structured_network_results = self.result_selector.get_structured_network_results(
                report_options=report_generator_options
            )
            current_network_level_counter = 0
            list_of_gantt_chart_input_data: list[GanttChartInputData] = []
            for (
                structured_network_level_results
            ) in structured_network_results.get_network_level_in_material_flow_direction():
                # Check if Network Level is
                if current_network_level_counter == structured_network_results.upstream_network_level_position:
                    source_meta_data_frame_list = structured_network_level_results.main_source_results.get_streams_and_storage_meta_data(
                        include_order_meta_data=report_generator_options.gantt_charts.include_order_visualization,
                        include_storage_meta_data=report_generator_options.gantt_charts.include_storage_gantt_charts,
                    )
                    if isinstance(
                        structured_network_level_results.main_source_results.storage_meta_data_frame,
                        EmptyMetaDataInformation,
                    ):
                        gantt_chart_title = (
                            structured_network_level_results.main_source_results.storage_meta_data_frame.name
                        )
                    else:
                        gantt_chart_title = structured_network_level_results.main_source_results.storage_meta_data_frame.process_step_name
                    file_name = "gantt_chart" + str(gantt_chart_title) + self.output_file_format_with_dot
                    file_name = file_name.replace(" ", "_")
                    output_file = os.path.join(self.gantt_chart_directory_path, file_name)
                    gantt_chart_input_data = GanttChartInputData(
                        list_of_meta_data=source_meta_data_frame_list,
                        gantt_chart_title=gantt_chart_title,
                        start_date=report_generator_options.gantt_charts.plot_start_time,
                        end_date=report_generator_options.gantt_charts.plot_end_time,
                        gantt_chart_file_path=output_file,
                        output_format=output_file_extension,
                    )
                    list_of_gantt_chart_input_data.append(gantt_chart_input_data)
                    # source_figure = gantt_chart_generator.create_gantt_chart_from_list_of_meta_data(
                    #     list_of_meta_data=source_meta_data_frame_list,
                    #     gantt_chart_title=gantt_chart_title,
                    #     start_date=report_generator_options.gantt_charts.plot_start_time,
                    #     end_date=report_generator_options.gantt_charts.plot_end_time,
                    # )
                    # if source_figure is not None:
                    #     figure_list.append(
                    #         datapane.Plot(
                    #             source_figure,
                    #             caption=gantt_chart_title,
                    #         )
                    #     )
                list_of_process_chain_meta_data_results = (
                    structured_network_level_results.get_list_of_process_chain_meta_data_results()
                )
                for process_chain_meta_data_results in list_of_process_chain_meta_data_results:
                    process_chain_meta_data_frame_list = process_chain_meta_data_results.get_process_chain_without_sources_and_sinks(
                        include_internal_storages=True,
                        include_load_profiles=report_generator_options.gantt_charts.include_load_profiles,
                        include_load_profiles_resampled=report_generator_options.gantt_charts.include_load_profiles_resampled,
                    )
                    file_name = (
                        "gantt_chart"
                        + str(process_chain_meta_data_results.process_chain_name)
                        + self.output_file_format_with_dot
                    )
                    file_name = file_name.replace(" ", "_")
                    output_file = os.path.join(self.gantt_chart_directory_path, file_name)
                    gantt_chart_input_data = GanttChartInputData(
                        list_of_meta_data=process_chain_meta_data_frame_list,
                        gantt_chart_title=process_chain_meta_data_results.process_chain_name,
                        start_date=report_generator_options.gantt_charts.plot_start_time,
                        end_date=report_generator_options.gantt_charts.plot_end_time,
                        gantt_chart_file_path=output_file,
                        output_format=output_file_extension,
                    )
                    list_of_gantt_chart_input_data.append(gantt_chart_input_data)
                    # process_chain_figure = gantt_chart_generator.create_gantt_chart_from_list_of_meta_data(
                    #     list_of_meta_data=process_chain_meta_data_frame_list,
                    #     gantt_chart_title=process_chain_meta_data_results.process_chain_name,
                    #     start_date=report_generator_options.gantt_charts.plot_start_time,
                    #     end_date=report_generator_options.gantt_charts.plot_end_time,
                    # )
                    # if process_chain_figure is not None:
                    #     figure_list.append(
                    #         datapane.Plot(
                    #             process_chain_figure,
                    #             caption=process_chain_meta_data_results.process_chain_name,
                    #         )
                    #     )
                sink_meta_data_frame_list = (
                    structured_network_level_results.main_sink_results.get_streams_and_storage_meta_data(
                        include_order_meta_data=report_generator_options.gantt_charts.include_order_visualization,
                        include_storage_meta_data=report_generator_options.gantt_charts.include_storage_gantt_charts,
                    )
                )
                if isinstance(
                    structured_network_level_results.main_sink_results.storage_meta_data_frame,
                    EmptyMetaDataInformation,
                ):
                    sink_gantt_chart_title = (
                        structured_network_level_results.main_sink_results.storage_meta_data_frame.name
                    )
                else:
                    sink_gantt_chart_title = (
                        structured_network_level_results.main_sink_results.storage_meta_data_frame.process_step_name
                    )
                file_name = "gantt_chart" + str(sink_gantt_chart_title) + self.output_file_format_with_dot
                file_name = file_name.replace(" ", "_")
                output_file = os.path.join(self.gantt_chart_directory_path, file_name)
                gantt_chart_input_data = GanttChartInputData(
                    list_of_meta_data=sink_meta_data_frame_list,
                    gantt_chart_title=sink_gantt_chart_title,
                    start_date=report_generator_options.gantt_charts.plot_start_time,
                    end_date=report_generator_options.gantt_charts.plot_end_time,
                    gantt_chart_file_path=output_file,
                    output_format=output_file_extension,
                )
                list_of_gantt_chart_input_data.append(gantt_chart_input_data)

                # sink_figure = gantt_chart_generator.create_gantt_chart_from_list_of_meta_data(
                #     list_of_meta_data=sink_meta_data_frame_list,
                #     gantt_chart_title=sink_gantt_chart_title,
                #     start_date=report_generator_options.gantt_charts.plot_start_time,
                #     end_date=report_generator_options.gantt_charts.plot_end_time,
                # )
                # if sink_figure is not None:
                #     figure_list.append(
                #         datapane.Plot(
                #             sink_figure,
                #             caption=sink_gantt_chart_title,
                #         )
                #     )
                current_network_level_counter = current_network_level_counter + 1

        list_of_combined_load_profiles = self.result_selector.post_process_simulation_data_handler.load_profile_collection_post_processing.get_list_of_combined_load_profiles()
        gantt_chart_title = "Combined and Resampled Profiles"
        file_name = "gantt_chart" + str(gantt_chart_title) + self.output_file_format_with_dot
        file_name = file_name.replace(" ", "_")
        output_file = os.path.join(self.gantt_chart_directory_path, file_name)
        gantt_chart_input_data = GanttChartInputData(
            list_of_meta_data=list_of_combined_load_profiles,
            gantt_chart_title="Combined and Resampled Profiles",
            start_date=report_generator_options.gantt_charts.plot_start_time,
            end_date=report_generator_options.gantt_charts.plot_end_time,
            gantt_chart_file_path=output_file,
            output_format=output_file_extension,
        )
        list_of_gantt_chart_input_data.append(gantt_chart_input_data)

        # combined_load_profile_plot = (
        #     gantt_chart_generator.create_gantt_chart_from_list_of_meta_data(
        #         list_of_meta_data=list_of_combined_load_profiles,
        #         gantt_chart_title="Combined and Resampled Profiles",
        #         start_date=report_generator_options.gantt_charts.plot_start_time,
        #         end_date=report_generator_options.gantt_charts.plot_end_time,
        #     )
        # )
        # figure_list.append(combined_load_profile_plot)
        figure_list = self.create_list_of_gantt_charts(
            list_of_gantt_chart_input_data=list_of_gantt_chart_input_data,
            report_generator_options=report_generator_options,
        )
        if figure_list:
            network_level_page = datapane.Group(
                blocks=figure_list,
                label="Process Gantt Charts",
            )
        else:
            network_level_page = datapane.Group(
                blocks=[datapane.HTML("No entries for the gantt chart were available in the specified time range")],
                label="Process Gantt Charts",
            )
        return network_level_page

    def create_proplot_figure(self, input_data: GanttChartInputData):
        combined_load_profile_plot = self.gantt_chart_generator.create_gantt_chart_from_list_of_meta_data(
            list_of_meta_data=input_data.list_of_meta_data,
            gantt_chart_title=input_data.gantt_chart_title,
            start_date=input_data.start_date,
            end_date=input_data.end_date,
            output_file_path=input_data.gantt_chart_file_path,
            image_format=self.output_file_format,
            dpi=self.dpi,
        )

        return input_data.gantt_chart_file_path

    def create_list_of_gantt_charts(
        self,
        list_of_gantt_chart_input_data: list[GanttChartInputData],
        report_generator_options: ReportGeneratorOptions,
    ) -> list[datapane.Media]:
        list_of_non_empty_chart_input_data = []
        for current_input_data in list_of_gantt_chart_input_data:
            if current_input_data.check_if_contains_non_empty_data() is True:
                list_of_non_empty_chart_input_data.append(current_input_data)

        if report_generator_options.disable_multiprocessing is True:
            for gantt_chart_input_data in list_of_gantt_chart_input_data:
                self.create_proplot_figure(input_data=gantt_chart_input_data)
        else:
            asynchronous_multi_processor = AsynchronousMultiProcessor(
                number_of_process=report_generator_options.number_of_processes_used_for_plotting
            )

            asynchronous_multi_processor.run_function_in_parallel(
                func=self.create_proplot_figure,
                iterable=list_of_non_empty_chart_input_data,
            )
        list_of_datapane_plots = []
        for gantt_chart_input_data in list_of_non_empty_chart_input_data:
            datapane_plot = datapane.Media(
                gantt_chart_input_data.gantt_chart_file_path,
                caption=gantt_chart_input_data.gantt_chart_title,
            )
            list_of_datapane_plots.append(datapane_plot)

        return list_of_datapane_plots
