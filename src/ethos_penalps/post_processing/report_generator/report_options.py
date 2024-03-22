import datetime
from dataclasses import dataclass


@dataclass
class FullProcessGanttChartOptions:
    """Contains all customization options for the Gantt
    chart page.
    """

    create_gantt_chart: bool
    """Determines if the Gantt chart page should be created.
    """
    display_stream_data_frame: bool
    """Determines if the stream data frames should be included.
    """
    display_process_state_data_frame: bool
    """Determines if the process state data frames should be included.
    """
    include_order_dict: bool
    """Determines if the order dictionaries should be included.
    """
    plot_start_time: datetime.datetime | None = None
    """ The first displayed start time of the Gantt chart.
    """
    plot_end_time: datetime.datetime | None = None
    """ The last displayed end time of the Gantt chart.
    """
    include_load_profiles: bool = False
    """Determines if the load profiles should be included.
    """
    maximum_number_of_vertical_plots: int = 10
    """Determines the maximum number of vertical plots in a single
    Gantt chart.
    """
    include_storage_gantt_charts: bool = True
    """Determines if the storage plots should be included 
    in the Gantt chart.
    """
    include_order_visualization: bool = False
    """Determines if the orders should be displayed as own
    Gantt charts.
    """

    def add_plot_start_and_end_time(
        self, start_time: datetime.datetime | None, end_time: datetime.datetime | None
    ):
        """Adds the start and end time to the Gantt chart options

        Args:
            start_time (datetime.datetime | None): The first displayed start time of the Gantt chart.
            end_time (datetime.datetime | None): The last displayed end time of the Gantt chart.
        """
        self.plot_start_time: datetime.datetime | None = start_time
        self.plot_end_time: datetime.datetime | None = end_time


@dataclass
class DebugLogPage:
    """Contains the options for the debug log page."""

    include: bool
    """Determines if the debug log page is created
    """


@dataclass
class ProductionPlanDataFrame:
    """Contains the options for the production plan data frame page"""

    include_stream_data_frames: bool = True
    """Determines if the stream data frames should be included.
    """
    include_process_step_data_frames: bool = True
    """Determines if the process step data frames should be included.
    """
    include_storage_data_frames: bool = False
    """Determines if the storage data frames should be included.
    """

    def __post_init__(self):
        """Determines which data frames are required for post processing."""
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
    """Contains all options for the enterprise visualization."""

    include: bool
    """Determines if the Enterprise visualization should be included.
    """


@dataclass
class LoadProfileDataPageOptions:
    """Contains all options for the load profile data frame page."""

    include: bool
    """Determines if all data frames should be included.
    """


@dataclass
class NodeOperationPageOptions:
    """Contains all options for the NodeOperationPage"""

    include: bool
    """Determine if the NodeOperation page should be included.
    """


@dataclass
class ProcessOverviewPageOptions:
    """Contains all options for the process overview page."""

    include_enterprise_graph: bool
    """Determines if the EnterpriseOverview page should be included."""


@dataclass
class CarpetPlotOptions:
    """Contains all options for the carpet plot page"""

    create_all: bool
    """Determines if all carpet plots should be created.
    """
    number_of_columns: int = 2
    """Determines the number of columns which should be
    used to display the carpet plots.
    """

    def add_time_data(
        self,
        x_axis_time_delta: datetime.timedelta,
        resample_frequency: str,
        end_date: datetime.datetime,
        start_date: datetime.datetime,
        number_of_columns: int = 2,
    ):
        """Adds the time that is relevant to the carpet plots.

        Args:
            x_axis_time_delta (datetime.timedelta): Is the period
                that is incremented on the x-axis. Its tested for

                - datetime.timedelta(hour=1)
                - datetime.timedelta(day=1)
                - datetime.timedelta(week=1)

            resample_frequency (str): The target frequency to which all
                load profiles should be resampled to display them in the
                carpet plot.
            end_date (datetime.datetime): The last displayed end time.
            start_date (datetime.datetime): The first displayed start time.
            number_of_columns (int, optional): The number of columns
                for display or multiple carpet plots. Defaults to 2.
        """
        self.start_date: datetime.datetime = start_date
        self.end_date: datetime.datetime = end_date
        self.x_axis_time_delta: datetime.timedelta = x_axis_time_delta
        self.resample_frequency: str = resample_frequency
        self.number_of_columns: int = number_of_columns


@dataclass
class StorageStatePage:
    """Contains all customization options for the storage state page"""

    create: bool = True
    """Determines if the storage states should be displayed.
    """


@dataclass
class ReportGeneratorOptions:
    """Contains all customization options for the simulation report"""

    report_name: str
    """Save name of the report.
    """
    debug_log_page: DebugLogPage
    """Options for the debug log page
    """
    process_overview_page_options: ProcessOverviewPageOptions
    """Options for the overview page.
    """
    production_plan_data_frame: ProductionPlanDataFrame
    """Options for the production plan data frame page.
    """
    load_profile_data_page: LoadProfileDataPageOptions
    """Options for the load profile data frame page.
    """
    full_process_gantt_chart: FullProcessGanttChartOptions
    """Options for the gantt chart page.
    """
    node_operation_page_options: NodeOperationPageOptions
    """Options for the Node operation page.
    """
    carpet_plot_options: CarpetPlotOptions
    """Options for the carpet plot page.
    """

    def check_if_stream_state_conversion_is_necessary(self) -> bool:
        """Checks if it is necessary to convert the stream states.

        Returns:
            bool: returns True if a conversion of the stream states is necessary.
        """

        stream_state_conversion_is_necessary = False
        if (
            self.production_plan_data_frame.include_process_step_data_frames is True
            or self.full_process_gantt_chart.create_gantt_chart is True
            or self.full_process_gantt_chart.display_stream_data_frame is True
        ):
            stream_state_conversion_is_necessary = True
        return stream_state_conversion_is_necessary

    def check_if_process_state_conversion_is_necessary(self) -> bool:
        """Checks if a conversion of the process state data frames is necessary.

        Returns:
            bool: returns True if a conversion of the process state states is necessary.
        """
        process_state_conversion_is_necessary = False
        if (
            self.full_process_gantt_chart.create_gantt_chart is True
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
    load_profile_data_page=LoadProfileDataPageOptions(include=True),
    node_operation_page_options=NodeOperationPageOptions(include=False),
    carpet_plot_options=CarpetPlotOptions(create_all=True),
    process_overview_page_options=ProcessOverviewPageOptions(
        include_enterprise_graph=True
    ),
)
