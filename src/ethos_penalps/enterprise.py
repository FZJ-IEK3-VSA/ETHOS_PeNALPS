import datetime
import uuid
import numbers
from dataclasses import dataclass

import cloudpickle

from ethos_penalps.data_classes import Commodity, ProcessChainIdentifier, get_new_uuid
from ethos_penalps.load_profile_calculator import LoadProfileHandlerSimulation
from ethos_penalps.network_level import NetworkLevel
from ethos_penalps.post_processing.report_generator.enterprise_report_generator import (
    EnterpriseReportGenerator,
)
from ethos_penalps.utilities.exceptions_and_warnings import MisconfigurationError
from ethos_penalps.post_processing.report_generator.report_options import (
    standard_simulation_report,
)
from ethos_penalps.process_chain import ProcessChain
from ethos_penalps.process_nodes.process_chain_storage import ProcessChainStorage
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.post_processing.post_processed_data_handler import (
    PostProcessSimulationDataHandler,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger


logger = PeNALPSLogger.get_logger_without_handler()


class Enterprise:
    def __init__(
        self,
        time_data: TimeData,
        name: str = "Enterprise",
        location: str = "",
    ) -> None:
        self.list_of_network_level: list[NetworkLevel] = []
        self.time_data: TimeData = time_data
        self.location: str = location
        self.load_profile_handler: LoadProfileHandlerSimulation = (
            LoadProfileHandlerSimulation()
        )
        self.production_plan = ProductionPlan(
            load_profile_handler=self.load_profile_handler,
            process_step_states_dict={},
            stream_state_dict={},
        )
        self.name: str = name

    def start_simulation(
        self, number_of_iterations_in_chain: numbers.Number | None = None
    ):
        """Start the simulation after the enterprise model has been fully defined.

        Args:
            number_of_iterations_in_chain (numbers.Number | None, optional): Can set a maximum number of internal
                simulation iterations. This can be useful to stop ill defined simulations. Defaults to None.
        """
        self._prepare_process_chains_for_simulation()
        for network_level in self.list_of_network_level:
            main_sink = network_level.get_main_sink()
            main_sink.initialize_sink()
            for process_chain in network_level.list_of_process_chains:
                try:
                    main_sink.prepare_sink_for_next_chain(
                        process_chain_identifier=process_chain.process_chain_identifier
                    )
                    main_source = network_level.get_main_source()
                    main_source.prepare_source_for_next_chain(
                        process_chain_identifier=process_chain.process_chain_identifier
                    )
                    process_chain.create_process_chain_production_plan(
                        max_number_of_iterations=number_of_iterations_in_chain
                    )
                except:
                    process_chain.create_failed_report()

            network_level.main_sink.create_storage_entries()
            network_level.main_source.create_storage_entries()

    def pickle_sink(
        self,
        network_level: NetworkLevel,
        file_name: str = "sink_",
        subdirectory_name: str = "production_plan",
        add_time_stamp_to_filename: bool = True,
    ):
        file_name = file_name + network_level.main_sink.name
        result_path_generator = ResultPathGenerator()
        result_path = result_path_generator.create_path_to_file_relative_to_main_file(
            file_name=file_name,
            subdirectory_name=subdirectory_name,
            add_time_stamp_to_filename=add_time_stamp_to_filename,
            file_extension=".pckl",
        )
        with open(result_path, "wb") as file:
            cloudpickle.dump(network_level.main_sink, file, protocol=None)

    def create_network_level(self) -> NetworkLevel:
        """Creates an instance of a network level which is the next container
        level for each

        Returns:
            NetworkLevel: _description_
        """
        network_level = NetworkLevel(
            production_plan=self.production_plan,
            stream_handler=StreamHandler(),
            time_data=self.time_data,
            load_profile_handler=self.load_profile_handler,
        )
        self.list_of_network_level.append(network_level)
        return network_level

    def _prepare_process_chains_for_simulation(self):
        for network_level in self.list_of_network_level:
            network_level.combine_stream_handler_from_chains()
            network_level.combine_node_dict()

    def get_all_process_steps(self) -> dict[str, ProcessStep]:
        output_dictionary = {}
        for network_level in self.list_of_network_level:
            network_level.combine_node_dict()
            for node_name, process_node in network_level.node_dictionary.items():
                if isinstance(process_node, ProcessStep):
                    output_dictionary[node_name] = process_node
        return output_dictionary

    def _get_combined_stream_handler(self) -> StreamHandler:
        output_stream_handler = StreamHandler()
        for network_level in self.list_of_network_level:
            network_level.combine_stream_handler_from_chains()
            for stream in network_level.stream_handler.stream_dict.values():
                output_stream_handler.add_stream(
                    new_stream=stream, overwrite_stream=True
                )
        return output_stream_handler

    def create_post_simulation_report(
        self,
        gantt_chart_start_date: datetime.datetime,
        gantt_chart_end_date: datetime.datetime,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        x_axis_time_delta: datetime.timedelta,
        resample_frequency: str = "5min",
        number_of_columns: int = 2,
    ):
        """Creates a HTML report from the simulation results. It contains
        - A process overview page
            - A depiction of the modelled process
            - All orders in the sinks and storages of the process
        - A page with the production plan which is downloadable as csv file for
            - The process steps
            - The streams
        - A page with a with all load profiles for each:
            - Process steps
            - Streams
        - A page with a gantt chart for each stream and process step for a selected period
        - A page with a carpet plot for each energy carrier for each stream, process step
            and the sum for each energy carrier.
        Args:
            gantt_chart_start_date (datetime.datetime): Determines the start for the displayed period
                for the Gantt Chart.
            gantt_chart_end_date (datetime.datetime): Determines the end of the displayed  period
                for the Gantt Chart.
            start_date (datetime.datetime): Determines the start for the displayed period
                for the carpet plots.
            end_date (datetime.datetime): Determines the end of the displayed  period
                for the carpet Chart.
            x_axis_time_delta (datetime.timedelta): Determines the duration repetitive period
                on the x axis of the carpet plot.

            resample_frequency (str, optional): The load profiles must have a uniform time step
                to create the carpet plot from them. Thus they must be resampled. The frequency must
                be provided as a string in the the pandas resample style:

                - T, min minutely frequency
                - S secondly frequency
                - H hourly frequency
                - D calendar day frequency
                - W weekly frequency
                - M month end frequency
                - https://pandas.pydata.org/docs/user_guide/timeseries.html#timeseries-offset-aliases
                - defaults to "min"
                Defaults to "1min".. Defaults to "5min".
            number_of_columns (int, optional): Sets the number of columns for the carpet plots. Defaults to 2.
        """

        number_of_periods = (end_date - start_date) / x_axis_time_delta
        if number_of_periods <= 0:
            raise MisconfigurationError(
                "No positive number periods. The start_date: "
                + str(start_date)
                + " must be before the end_date: "
                + str(end_date)
            )

        if not number_of_periods.is_integer():
            raise Exception(
                """(end_date - start_date)/x_axis_time_delta must be an integer to create the carpet plots.
                  number of periods."""
                + " start_date is: "
                + str(start_date)
                + " end_date: "
                + str(end_date)
                + " x_axis_time_delta: "
                + str(x_axis_time_delta)
            )
        standard_simulation_report.full_process_gantt_chart.plot_start_time = (
            gantt_chart_start_date
        )
        standard_simulation_report.full_process_gantt_chart.plot_end_time = (
            gantt_chart_end_date
        )
        standard_simulation_report.full_process_gantt_chart.include_storage_gantt_charts = (
            True
        )
        standard_simulation_report.production_plan_data_frame.include_storage_data_frames = (
            True
        )
        standard_simulation_report.full_process_gantt_chart.include_load_profiles = True
        standard_simulation_report.carpet_plot_options.add_time_data(
            start_date=start_date,
            end_date=end_date,
            x_axis_time_delta=x_axis_time_delta,
            resample_frequency=resample_frequency,
            number_of_columns=number_of_columns,
        )
        standard_simulation_report.debug_log_page.include = False

        post_process_simulation_data_handler = PostProcessSimulationDataHandler(
            production_plan=self.production_plan,
            report_options=standard_simulation_report,
        )
        logger.info("Start to post process load profiles")
        post_process_simulation_data_handler.start_post_processing()
        report_generator = EnterpriseReportGenerator(
            production_plan=self.production_plan,
            enterprise_name=self.name,
            list_of_network_level=self.list_of_network_level,
            post_process_simulation_data_handler=post_process_simulation_data_handler,
        )
        logger.info("Start to create report")
        report_generator.generate_report(
            report_generator_options=standard_simulation_report
        )
