import datetime
from dataclasses import dataclass


@dataclass
class FullProcessGanttChartOptions:
    create_gantt_chart: bool
    display_stream_data_frame: bool
    display_process_state_data_frame: bool
    include_order_dict: bool
    plot_start_time: datetime.datetime | None = None
    plot_end_time: datetime.datetime | None = None
    include_load_profiles: bool = False
    maximum_number_of_vertical_plots: int = 10
    include_storage_gantt_charts: bool = True
    include_order_visualization: bool = False

    def add_plot_start_and_end_time(
        self, start_time: datetime.datetime | None, end_time: datetime.datetime | None
    ):
        self.plot_start_time: datetime.datetime | None = start_time
        self.plot_end_time: datetime.datetime | None = end_time


@dataclass
class ProcessStepGanttChartOptions:
    create_gantt_chart: bool
    include_input_streams: bool = True
    include_each_output_stream: bool = False
    only_include_output_stream_to_sink: bool = True
    include_process_state_load_profiles: bool = True
    include_storage_gantt_chart: bool = False
    plot_start_time: datetime.datetime | None = None
    plot_end_time: datetime.datetime | None = None
    include_load_profiles: bool = False
    maximum_number_of_vertical_plots: int = 10
    include_storage_gantt_charts: bool = True

    def add_plot_start_and_end_time(
        self, start_time: datetime.datetime | None, end_time: datetime.datetime | None
    ):
        self.plot_start_time: datetime.datetime | None = start_time
        self.plot_end_time: datetime.datetime | None = end_time


@dataclass
class DebugLogPage:
    include: bool


@dataclass
class ProductionPlanDataFrame:
    include_stream_data_frames: bool = True
    include_process_step_data_frames: bool = True
    include_storage_data_frames: bool = False

    def __post_init__(self):
        if (
            self.include_stream_data_frames is True
            or self.include_process_step_data_frames is True
            or self.include_storage_data_frames is True
        ):
            self.create_data_frame_page = True
        else:
            self.create_data_frame_page = False


@dataclass
class EnterpriseVisualizationOptions:
    include: bool


@dataclass
class LoadProfileDataPageOptions:
    include: bool


@dataclass
class NodeOperationPageOptions:
    include: bool


@dataclass
class ProcessOverviewPageOptions:
    include_enterprise_graph: bool


@dataclass
class CarpetPlotOptions:
    create_all: bool
    number_of_columns: int = 2

    def add_time_data(
        self,
        x_axis_time_delta: datetime.timedelta,
        resample_frequency: str,
        end_date: datetime.datetime,
        start_date: datetime.datetime,
        number_of_columns: int = 2,
    ):
        self.start_date: datetime.datetime = start_date
        self.end_date: datetime.datetime = end_date
        self.x_axis_time_delta: datetime.timedelta = x_axis_time_delta
        self.resample_frequency: str = resample_frequency
        self.number_of_columns: int = number_of_columns


@dataclass
class StorageStatePage:
    create: bool = True


@dataclass
class ReportGeneratorOptions:
    report_name: str
    debug_log_page: DebugLogPage
    process_overview_page_options: ProcessOverviewPageOptions
    production_plan_data_frame: ProductionPlanDataFrame
    load_profile_data_page: LoadProfileDataPageOptions
    full_process_gantt_chart: FullProcessGanttChartOptions
    node_operation_page_options: NodeOperationPageOptions
    carpet_plot_options: CarpetPlotOptions
    process_step_gantt_chart_options: ProcessStepGanttChartOptions

    def check_if_stream_state_conversion_is_necessary(self) -> bool:
        stream_state_conversion_is_necessary = False
        if (
            self.production_plan_data_frame.include_process_step_data_frames is True
            or self.full_process_gantt_chart.create_gantt_chart is True
            or self.full_process_gantt_chart.display_stream_data_frame is True
            or self.process_step_gantt_chart_options is True
        ):
            stream_state_conversion_is_necessary = True
        return stream_state_conversion_is_necessary

    def check_if_process_state_conversion_is_necessary(self):
        process_state_conversion_is_necessary = False
        if (
            self.process_step_gantt_chart_options.create_gantt_chart is True
            or self.full_process_gantt_chart.create_gantt_chart is True
            or self.full_process_gantt_chart.display_process_state_data_frame is True
        ):
            process_state_conversion_is_necessary = True
        return process_state_conversion_is_necessary


standard_simulation_report = ReportGeneratorOptions(
    report_name="concise_post_simulation_report",
    debug_log_page=DebugLogPage(include=False),
    production_plan_data_frame=ProductionPlanDataFrame(),
    full_process_gantt_chart=FullProcessGanttChartOptions(
        create_gantt_chart=True,
        include_order_dict=False,
        include_storage_gantt_charts=True,
        display_process_state_data_frame=False,
        display_stream_data_frame=False,
        include_load_profiles=False,
    ),
    process_step_gantt_chart_options=ProcessStepGanttChartOptions(
        create_gantt_chart=True,
        include_input_streams=True,
        only_include_output_stream_to_sink=True,
        include_each_output_stream=False,
        include_storage_gantt_chart=False,
        include_load_profiles=True,
        maximum_number_of_vertical_plots=20,
    ),
    load_profile_data_page=LoadProfileDataPageOptions(include=True),
    node_operation_page_options=NodeOperationPageOptions(include=False),
    carpet_plot_options=CarpetPlotOptions(create_all=True),
    process_overview_page_options=ProcessOverviewPageOptions(
        include_enterprise_graph=True
    ),
)
