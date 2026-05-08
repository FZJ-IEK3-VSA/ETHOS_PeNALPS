import pathlib
import traceback

import datapane
import pandas
import pint

from ethos_penalps.data_classes import (
    FinalProductEnergySummaryLoad,
    LoadType,
    ProductionOrder,
)
from ethos_penalps.energy.load_profile_calculator import LoadProfileHandlerSimulation
from ethos_penalps.organizational_agents.network_level import NetworkLevel
from ethos_penalps.post_processing.product_energy_handler import NetworkEnergyAnalyzer
from ethos_penalps.post_processing.production_plan_post_processing.network_analyzer import (
    ResultSelector,
)
from ethos_penalps.post_processing.report_generator.report_options import (
    ReportGeneratorOptions,
)
from ethos_penalps.post_processing.specific_energy_demand_sankey import (
    SankeyFlowInput,
    SankeyFlowOutput,
    SankeyLevel,
    SpecificEnergySankeyCreator,
)
from ethos_penalps.post_processing.tikz_visualizations.enterprise_graph_builder import (
    EnterpriseGraphBuilderTikz,
)
from ethos_penalps.utilities.general_functions import dataframe_from_dataclasses
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.type_aliases import numbers_alias
from ethos_penalps.utilities.units import Units

logger = PeNALPSLogger.get_logger_without_handler()


class ProcessOverviewPage:
    """Creates an depiction of the material flow model."""

    def __init__(
        self,
        enterprise_name: str,
        report_directory: str,
        list_of_network_level: list[NetworkLevel],
        result_selector: ResultSelector,
        load_profile_handler_simulation: LoadProfileHandlerSimulation,
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
        self.load_profile_handler_simulation: LoadProfileHandlerSimulation = load_profile_handler_simulation

    def create_process_step_overview_page(self, report_generator_options: ReportGeneratorOptions):
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
        if report_generator_options.process_overview_page_options.include_enterprise_graph is True:
            block_list = []

            try:
                logger.info("Start generation of enterprise visualization")
                graph_builder = EnterpriseGraphBuilderTikz(
                    enterprise_name=self.enterprise_name,
                    list_of_network_level=self.list_of_network_level,
                )

                path_to_enterprise_structure_graph_png = graph_builder.create_enterprise_graph(
                    show_graph=False,
                    path_to_results_folder=self.report_directory,
                    output_format="png",
                )
                block_list.append(datapane.Media(file=path_to_enterprise_structure_graph_png))

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
            structured_network_results = self.result_selector.get_structured_network_results(
                report_options=report_generator_options
            )
            datapane_sankey = self.create_sankey()
            block_list.append(datapane_sankey)
            list_of_orders_for_network_level = []
            network_level_counter = 1
            for network_level_results in structured_network_results.get_network_level_in_material_flow_direction():
                order_data_frame = network_level_results.main_sink_results.order_collection.order_data_frame
                list_of_order_tables = []
                if order_data_frame.empty:
                    list_of_order_tables.append(
                        datapane.HTML(
                            "Order Data Frame for sink: " + network_level_results.main_sink_results.name + " was empty."
                        )
                    )
                else:
                    list_of_order_tables.append(
                        datapane.DataTable(
                            df=order_data_frame,
                            caption="Complete Orders for Sink: " + network_level_results.main_sink_results.name,
                        )
                    )
                    total_order_mass = network_level_results.main_sink_results.order_collection.order_data_frame.loc[
                        :, "production_target"
                    ].sum()
                    list_of_order_tables.append(datapane.HTML("Total order mass is: " + str(total_order_mass)))
                total_splitted_mass = 0
                for (
                    process_chain_identifier,
                    splitted_order,
                ) in network_level_results.main_sink_results.dict_of_splitted_order_collection.items():
                    if splitted_order.order_data_frame.empty:
                        list_of_order_tables.append(
                            datapane.HTML(
                                "Order Data Frame for sink: "
                                + network_level_results.main_sink_results.name
                                + " was empty."
                            )
                        )
                        splitted_order_mass = 0
                    else:
                        list_of_order_tables.append(
                            datapane.DataTable(
                                df=splitted_order.order_data_frame,
                                caption="Orders for chain: " + str(splitted_order.process_chain_identifier.chain_name),
                                # name="Orders for chain: "
                                # + str(splitted_order.process_chain_identifier.chain_name),
                            )
                        )
                        splitted_order_mass = (splitted_order.order_data_frame.loc[:, "production_target"]).sum()
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
                    datapane.HTML("Total mass of all splitted orders is: " + str(total_splitted_mass))
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
            # product_energy_datapane_table = self.create_specific_energy_table(
            #     report_generator_options=report_generator_options
            # )

            # block_list.append(product_energy_datapane_table)
            total_energy_table_not_resampled = self.get_total_energy_load_profiles_not_resampled()
            block_list.append(total_energy_table_not_resampled)
            total_energy_table_resampled = self.get_total_energy_load_profiles_resampled()
            block_list.append(total_energy_table_resampled)
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

    def create_specific_energy_table(self, report_generator_options: ReportGeneratorOptions) -> datapane.DataTable:

        network_energy_analyzer = NetworkEnergyAnalyzer(
            list_of_network_level=self.list_of_network_level,
            load_profile_handler_simulation=self.load_profile_handler_simulation,
        )
        product_energy_dict = network_energy_analyzer.dict_of_product_energy

        structured_network_results = self.result_selector.get_structured_network_results(
            report_options=report_generator_options
        )
        structured_network_results_in_material_flow_direction = (
            structured_network_results.get_network_level_in_material_flow_direction()
        )

        last_network_level = structured_network_results_in_material_flow_direction[0]
        order_data_frame_main_results = last_network_level.main_sink_results.order_collection.order_data_frame

        total_mass = order_data_frame_main_results.loc[:, "production_target"].sum()
        unit_array = order_data_frame_main_results.loc[:, "mass_unit"].unique()
        total_mass_unit = unit_array[0]
        list_of_energy_summary_data = []
        for product_energy in product_energy_dict.values():
            total_energy = (
                product_energy.specific_energy_data_demand
                * Units.get_unit(product_energy.unit)
                * total_mass
                * Units.get_unit(unit_string=total_mass_unit)
            )

            compressed_quantity = Units.compress_quantity(
                quantity_value=total_energy.m,
                unit=Units.get_unit(unit_string=product_energy.unit),
            )
            final_product_energy_summary_load = FinalProductEnergySummaryLoad(
                product_commodity=product_energy.product_commodity,
                specific_energy_demand=product_energy.specific_energy_data_demand,
                load_type=product_energy.load_type.name,
                specific_energy_unit=product_energy.unit,
                total_mass_value=total_mass,
                total_mass_unit=total_mass_unit,
                energy_unit_total=str(compressed_quantity.u),
                energy_value_total=Units.get_value_from_quantity(quantity=compressed_quantity),
            )
            list_of_energy_summary_data.append(final_product_energy_summary_load)

        product_energy_data_frame = dataframe_from_dataclasses(list_of_energy_summary_data)
        product_energy_datapane_table = datapane.DataTable(
            df=product_energy_data_frame, caption="Summary of Product Energy Data"
        )
        return product_energy_datapane_table

    def get_total_energy_load_profiles_not_resampled(
        self,
    ) -> datapane.DataTable:

        dict_of_total_energy: dict[str, pint.Quantity] = {}
        load_dict: dict[str, LoadType] = {}
        for process_step_load_profile_collection in self.result_selector.post_process_simulation_data_handler.load_profile_collection_post_processing.dict_process_step_load_profile_collections.values():
            for (
                load_profile_uuid,
                load_profile_meta_data,
            ) in process_step_load_profile_collection.dict_of_load_entry_meta_data.items():
                load_dict.update(process_step_load_profile_collection.load_type_dict)
                if load_profile_uuid in dict_of_total_energy:
                    dict_of_total_energy[load_profile_uuid] = dict_of_total_energy[
                        load_profile_uuid
                    ] + load_profile_meta_data.total_energy * Units.get_unit(
                        unit_string=load_profile_meta_data.energy_unit
                    )
                else:
                    dict_of_total_energy[load_profile_uuid] = load_profile_meta_data.total_energy * Units.get_unit(
                        unit_string=load_profile_meta_data.energy_unit
                    )
        for stream_load_profile_collection in self.result_selector.post_process_simulation_data_handler.load_profile_collection_post_processing.dict_stream_load_profile_collections.values():
            for (
                load_profile_uuid,
                load_profile_meta_data,
            ) in stream_load_profile_collection.dict_of_load_entry_meta_data.items():
                load_dict.update(stream_load_profile_collection.load_type_dict)
                if load_profile_uuid in dict_of_total_energy:
                    dict_of_total_energy[load_profile_uuid] = dict_of_total_energy[
                        load_profile_uuid
                    ] + load_profile_meta_data.total_energy * Units.get_unit(
                        unit_string=load_profile_meta_data.energy_unit
                    )
                else:
                    dict_of_total_energy[load_profile_uuid] = load_profile_meta_data.total_energy * Units.get_unit(
                        unit_string=load_profile_meta_data.energy_unit
                    )
        data_frame_dict: dict[str, list[float]] = {
            "Total Energy": [],
            "Unit": [],
            "Load Name": [],
        }

        for load_uuid, total_energy_quantity in dict_of_total_energy.items():
            load_type = load_dict[load_uuid]
            compressed_total_energy_quantity = Units.compress_quantity(
                quantity_value=total_energy_quantity.m, unit=total_energy_quantity.u
            )
            data_frame_dict["Total Energy"].append(compressed_total_energy_quantity.m)
            data_frame_dict["Load Name"].append(load_type.name)
            data_frame_dict["Unit"].append(compressed_total_energy_quantity.u)
        data_frame = pandas.DataFrame.from_dict(data_frame_dict)
        data_pane_table = datapane.DataTable(df=data_frame)
        return data_pane_table

    def create_sankey(self) -> datapane.Media:
        network_energy_analyzer = NetworkEnergyAnalyzer(
            list_of_network_level=self.list_of_network_level,
            load_profile_handler_simulation=self.load_profile_handler_simulation,
        )

        product_energy_dict = network_energy_analyzer.dict_of_product_energy

        # Input values
        list_of_input_flow_values = []
        list_of_input_flow_label = []
        for load_type_specific_energy_demand in product_energy_dict.values():
            list_of_input_flow_values.append(load_type_specific_energy_demand.specific_energy_data_demand)
            input_flow_label = load_type_specific_energy_demand.load_type.name
            list_of_input_flow_label.append(input_flow_label)

        # Output Values
        list_of_output_flow_values = []
        list_of_output_flow_label = []
        total_specific_energy_demand = network_energy_analyzer.get_total_specific_energy_demand()
        output_flow_label = total_specific_energy_demand.load_type.name
        list_of_output_flow_label.append(output_flow_label)
        list_of_output_flow_values.append(total_specific_energy_demand.specific_energy_data_demand)
        sankey_level = SankeyLevel(
            list_of_input_flows_values=list_of_input_flow_values,
            list_of_input_labels=list_of_input_flow_label,
            list_of_output_flows_values=list_of_output_flow_values,
            list_of_output_labels=list_of_output_flow_label,
            normalization_factor=total_specific_energy_demand.specific_energy_data_demand,
            unit_string=total_specific_energy_demand.unit,
            number_of_decimal_points=2,
        )
        specific_energy_sankey_creator = SpecificEnergySankeyCreator(list_of_sankey_flows=[sankey_level])
        sankey_diagram = specific_energy_sankey_creator.create_standard_sankey(
            unit_string=total_specific_energy_demand.unit
        )
        path_to_specific_energy_sankey = pathlib.Path(self.report_directory).joinpath("specific_energy_sankey.png")
        sankey_diagram.savefig(path_to_specific_energy_sankey, format="png", dpi=1000)
        datapane_sankey = datapane.Media(
            file=path_to_specific_energy_sankey,
            label="Product Specific Energy Overview",
        )
        return datapane_sankey

    def get_total_energy_load_profiles_resampled(
        self,
    ) -> datapane.DataTable:

        dict_of_total_energy: dict[str, pint.Quantity] = {}
        load_dict: dict[str, LoadType] = {}
        for process_step_load_profile_collection in self.result_selector.post_process_simulation_data_handler.load_profile_collection_post_processing.dict_process_step_load_profile_collections.values():
            for (
                load_profile_uuid,
                load_profile_meta_data,
            ) in process_step_load_profile_collection.dict_of_load_entry_meta_data_resampled.items():
                load_dict.update(process_step_load_profile_collection.load_type_dict)
                if load_profile_uuid in dict_of_total_energy:
                    dict_of_total_energy[load_profile_uuid] = dict_of_total_energy[
                        load_profile_uuid
                    ] + load_profile_meta_data.total_energy * Units.get_unit(
                        unit_string=load_profile_meta_data.energy_unit
                    )
                else:
                    dict_of_total_energy[load_profile_uuid] = load_profile_meta_data.total_energy * Units.get_unit(
                        unit_string=load_profile_meta_data.energy_unit
                    )
        for stream_load_profile_collection in self.result_selector.post_process_simulation_data_handler.load_profile_collection_post_processing.dict_stream_load_profile_collections.values():
            for (
                load_profile_uuid,
                load_profile_meta_data,
            ) in stream_load_profile_collection.dict_of_load_entry_meta_data_resampled.items():
                load_dict.update(stream_load_profile_collection.load_type_dict)
                if load_profile_uuid in dict_of_total_energy:
                    dict_of_total_energy[load_profile_uuid] = dict_of_total_energy[
                        load_profile_uuid
                    ] + load_profile_meta_data.total_energy * Units.get_unit(
                        unit_string=load_profile_meta_data.energy_unit
                    )
                else:
                    dict_of_total_energy[load_profile_uuid] = load_profile_meta_data.total_energy * Units.get_unit(
                        unit_string=load_profile_meta_data.energy_unit
                    )
        data_frame_dict = {"Total Energy": [], "Unit": [], "Load Name": []}

        for load_uuid, total_energy_quantity in dict_of_total_energy.items():
            load_type = load_dict[load_uuid]
            compressed_total_energy_quantity = Units.compress_quantity(
                quantity_value=total_energy_quantity.m, unit=total_energy_quantity.u
            )
            data_frame_dict["Total Energy"].append(compressed_total_energy_quantity.m)
            data_frame_dict["Load Name"].append(load_type.name)
            data_frame_dict["Unit"].append(compressed_total_energy_quantity.u)
        data_frame = pandas.DataFrame.from_dict(data_frame_dict)
        data_pane_table = datapane.DataTable(df=data_frame)
        return data_pane_table
