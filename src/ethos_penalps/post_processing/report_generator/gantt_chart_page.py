import os

import datapane
import matplotlib.pyplot
import pandas

from ethos_penalps.data_classes import (
    LoadProfileDataFrameMetaInformation,
    ProcessStepDataFrameMetaInformation,
    StorageDataFrameMetaInformation,
)
from ethos_penalps.post_processing.network_analyzer import (
    NetworkAnalyzer,
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

logger = PeNALPSLogger.get_logger_without_handler()


class GanttChartPageGenerator:
    def __init__(
        self,
        production_plan: ProductionPlan,
        network_analyzer: NetworkAnalyzer,
        result_selector: ResultSelector,
        report_directory: str,
    ) -> None:
        self.production_plan: ProductionPlan = production_plan
        self.network_analyzer: NetworkAnalyzer = network_analyzer
        self.result_selector: ResultSelector = result_selector
        self.report_directory: str = report_directory

    def create_network_level_gantt_chart_page(
        self, report_generator_options: ReportGeneratorOptions
    ) -> datapane.Group:
        figure_list = []
        if report_generator_options.full_process_gantt_chart.create_gantt_chart is True:
            logger.info("Start generation of process step gantt charts")
            gantt_chart_generator = GanttChartGenerator(
                production_plan=self.production_plan,
                process_node_dict={},
                stream_handler=None,
            )

            structured_network_results = (
                self.result_selector.get_structured_network_results()
            )
            current_network_level_counter = 0
            for (
                structured_network_level_results
            ) in (
                structured_network_results.get_network_level_in_material_flow_direction()
            ):
                if (
                    current_network_level_counter
                    == structured_network_results.upstream_network_level_position
                ):
                    source_meta_data_frame_list = (
                        structured_network_level_results.main_source_results.get_streams_and_storage_meta_data()
                    )
                    source_figure = gantt_chart_generator.create_gantt_chart_from_list_of_meta_data(
                        list_of_meta_data=source_meta_data_frame_list,
                        gantt_chart_title=structured_network_level_results.main_source_results.storage_meta_data_frame.process_step_name,
                        start_date=report_generator_options.full_process_gantt_chart.plot_start_time,
                        end_date=report_generator_options.full_process_gantt_chart.plot_end_time,
                    )
                    if source_figure is not None:
                        figure_list.append(
                            datapane.Plot(
                                source_figure,
                                caption=structured_network_level_results.main_source_results.storage_meta_data_frame.process_step_name,
                            )
                        )
                list_of_process_chain_meta_data_results = (
                    structured_network_level_results.get_list_of_process_chain_meta_data_results()
                )
                for (
                    process_chain_meta_data_results
                ) in list_of_process_chain_meta_data_results:
                    process_chain_meta_data_frame_list = process_chain_meta_data_results.get_process_chain_without_sources_and_sinks(
                        include_internal_storages=True
                    )
                    process_chain_figure = gantt_chart_generator.create_gantt_chart_from_list_of_meta_data(
                        list_of_meta_data=process_chain_meta_data_frame_list,
                        gantt_chart_title=process_chain_meta_data_results.process_chain_name,
                        start_date=report_generator_options.full_process_gantt_chart.plot_start_time,
                        end_date=report_generator_options.full_process_gantt_chart.plot_end_time,
                    )
                    if process_chain_figure is not None:
                        figure_list.append(
                            datapane.Plot(
                                process_chain_figure,
                                caption=process_chain_meta_data_results.process_chain_name,
                            )
                        )
                sink_meta_data_frame_list = (
                    structured_network_level_results.main_sink_results.get_streams_and_storage_meta_data()
                )
                sink_figure = gantt_chart_generator.create_gantt_chart_from_list_of_meta_data(
                    list_of_meta_data=sink_meta_data_frame_list,
                    gantt_chart_title=structured_network_level_results.main_sink_results.storage_meta_data_frame.process_step_name,
                    start_date=report_generator_options.full_process_gantt_chart.plot_start_time,
                    end_date=report_generator_options.full_process_gantt_chart.plot_end_time,
                )
                if sink_figure is not None:
                    figure_list.append(
                        datapane.Plot(
                            sink_figure,
                            caption=structured_network_level_results.main_sink_results.storage_meta_data_frame.process_step_name,
                        )
                    )
                current_network_level_counter = current_network_level_counter + 1

        if figure_list:
            network_level_page = datapane.Group(
                blocks=figure_list,
                label="Process Gantt Charts",
            )
        else:
            network_level_page = datapane.Group(
                blocks=[
                    datapane.HTML(
                        "No entries for the gantt chart were available in the specified time range"
                    )
                ],
                label="Process Gantt Charts",
            )
        return network_level_page
