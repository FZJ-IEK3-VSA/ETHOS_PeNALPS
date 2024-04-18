import traceback

import datapane
import pandas

from ethos_penalps.data_classes import ProductionOrder
from ethos_penalps.organizational_agents.network_level import NetworkLevel
from ethos_penalps.post_processing.network_analyzer import ResultSelector
from ethos_penalps.post_processing.report_generator.report_options import (
    ReportGeneratorOptions,
)
from ethos_penalps.post_processing.tikz_visualizations.enterprise_graph_builder import (
    EnterpriseGraphBuilderTikz,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class ProcessOverviewPage:
    """Creates an depiction of the material flow model."""

    def __init__(
        self,
        enterprise_name: str,
        report_directory: str,
        list_of_network_level: list[NetworkLevel],
        result_selector: ResultSelector,
    ) -> None:
        """

        Args:
            enterprise_name (str): Name of the modeled enterprise.
            report_directory (str): Path to the report output directory.
            list_of_network_level (list[NetworkLevel]): List of all
                NetworkLevel of the process model.
            result_selector (ResultSelector): Object that contains
                the simulation in a structure that resembles the
                material flow simulation.
        """
        self.enterprise_name: str = enterprise_name
        self.report_directory: str = report_directory
        self.list_of_network_level: list[NetworkLevel] = list_of_network_level
        self.result_selector: ResultSelector = result_selector

    def create_process_step_overview_page(
        self, report_generator_options: ReportGeneratorOptions
    ):
        """Creates the overview page of the result report.

        Args:
            report_generator_options (ReportGeneratorOptions): s an object
                that contains the parameters to adjust the report
                appearance.

        Returns:
            _type_: DataPane object that represents the overview page of the
                report. Contains a depiction of the model and the orders that
                were fulfilled during the simulation.
        """
        if (
            report_generator_options.process_overview_page_options.include_enterprise_graph
            is True
        ):
            block_list = []
            # process_overview_generator = ProcessOverViewGenerator(
            #     process_node_dict=self.process_node_dict,
            #     load_profile_handler=self.production_plan.load_profile_handler,
            #     stream_handler=self.stream_handler,
            #     order_dictionary=self.production_order_dict,
            #     enterprise_name=self.enterprise_name,
            #     production_plan=self.production_plan,
            # )
            # pie_chart_figure = (
            #     process_overview_generator.create_product_energy_pie_chart()
            # )
            # total_energy_data_frame = (
            #     process_overview_generator.calculate_total_energy_demands()
            # )
            # total_stream_mass_data_frame = (
            #     process_overview_generator.get_total_mass_for_each_stream()
            # )
            # process_mass_and_energy_data_frame = (
            #     process_overview_generator.get_total_mass_and_energy_for_process_step()
            # )

            try:
                logger.info("Start generation of enterprise visualization")
                graph_builder = EnterpriseGraphBuilderTikz(
                    enterprise_name=self.enterprise_name,
                    list_of_network_level=self.list_of_network_level,
                )

                path_to_enterprise_structure_graph_png = (
                    graph_builder.create_enterprise_graph(
                        show_graph=False,
                        path_to_results_folder=self.report_directory,
                        output_format="png",
                    )
                )
                block_list.append(
                    datapane.Media(file=path_to_enterprise_structure_graph_png)
                )

                # list_of_datapane_order_tables = []
                # for network_level in self.list_of_network_level:
                #     order_data_frame = (
                #         network_level.main_sink.order_collection.order_data_frame
                #     )

                #     list_of_datapane_order_tables.append(
                #         datapane.DataTable(
                #             df=order_data_frame,
                #             caption=network_level.main_sink.name,
                #             label=network_level.main_sink.name,
                #         )
                #     )

                # if len(list_of_datapane_order_tables) == 1:
                #     block_list.extend(list_of_datapane_order_tables)
                # elif len(list_of_datapane_order_tables) == 0:
                #     pass
                # else:
                #     block_list.append(
                #         datapane.Select(
                #             blocks=list_of_datapane_order_tables,
                #             label="Production Order Tables",
                #         )
                #     )

            except:
                block_list.append(
                    datapane.HTML(
                        html=traceback.format_exc().replace("\n", "<br>"),
                        label="Enterprise structure graph could ne be created",
                    ),
                )
            structured_network_results = (
                self.result_selector.get_structured_network_results()
            )
            list_of_orders_for_network_level = []
            network_level_counter = 1
            for (
                network_level_results
            ) in (
                structured_network_results.get_network_level_in_material_flow_direction()
            ):
                order_data_frame = (
                    network_level_results.main_sink_results.order_collection.order_data_frame
                )
                list_of_order_tables = []
                list_of_order_tables.append(
                    datapane.DataTable(
                        df=order_data_frame,
                        caption="Complete Orders for Sink: "
                        + network_level_results.main_sink_results.name,
                    )
                )
                total_order_mass = network_level_results.main_sink_results.order_collection.order_data_frame.loc[
                    :, "production_target"
                ].sum()
                list_of_order_tables.append(
                    datapane.HTML("Total order mass is: " + str(total_order_mass))
                )
                total_splitted_mass = 0
                for (
                    process_chain_identifier,
                    splitted_order,
                ) in (
                    network_level_results.main_sink_results.dict_of_splitted_order_collection.items()
                ):
                    list_of_order_tables.append(
                        datapane.DataTable(
                            df=splitted_order.order_data_frame,
                            caption="Orders for chain: "
                            + str(splitted_order.process_chain_identifier.chain_name),
                            # name="Orders for chain: "
                            # + str(splitted_order.process_chain_identifier.chain_name),
                        )
                    )
                    splitted_order_mass = (
                        splitted_order.order_data_frame.loc[:, "production_target"]
                    ).sum()
                    list_of_order_tables.append(
                        datapane.HTML(
                            "The splitted order mass of "
                            + process_chain_identifier.chain_name
                            + " : "
                            + str(splitted_order_mass)
                        )
                    )
                    total_splitted_mass = splitted_order_mass + total_splitted_mass
                list_of_order_tables.append(
                    datapane.HTML(
                        "Total mass of all splitted orders is: "
                        + str(total_splitted_mass)
                    )
                )
                network_level_name = "Network Level " + str(network_level_counter)
                list_of_orders_for_network_level.append(
                    datapane.Group(
                        blocks=list_of_order_tables,
                        # name=network_level_results.main_sink_results.name,
                        label=network_level_results.main_sink_results.name,
                    )
                )

                network_level_counter = network_level_counter + 1
            if len(list_of_orders_for_network_level) > 1:
                network_order_tables = datapane.Select(
                    blocks=list_of_orders_for_network_level,
                    label="Network Orders",
                    # name="Network Orders",
                )
            else:
                network_order_tables = datapane.Group(
                    blocks=list_of_orders_for_network_level,
                    label="Network Orders",
                    # name="Network Orders",
                )
            block_list.append(network_order_tables)

            # if pie_chart_figure is not None:
            #     block_list.append(dp.Plot(pie_chart_figure, responsive=False))
            # block_list.append(
            #     dp.Table(
            #         total_stream_mass_data_frame,
            #         caption="Total stream masses based on simulation results",
            #     )
            # )
            # block_list.append(
            #     dp.Table(
            #         total_energy_data_frame,
            #         caption="Total process energy demand based on production order targets",
            #     )
            # )
            # block_list.append(
            #     dp.Table(
            #         process_mass_and_energy_data_frame,
            #         caption="Summary on energy relevant process steps",
            #     )
            # )

            process_overview_page = datapane.Group(
                label="Process Overview",
                blocks=block_list,
            )
            return process_overview_page
