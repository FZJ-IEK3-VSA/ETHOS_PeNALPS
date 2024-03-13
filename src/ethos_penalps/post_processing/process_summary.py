import matplotlib.pyplot
import pandas

from ethos_penalps.data_classes import (
    LoadType,
    ProcessStateEnergyLoadData,
    ProcessStateEnergyLoadDataBasedOnStreamMass,
    ProductEnergyData,
    StreamLoadEnergyData,
)
from ethos_penalps.load_profile_calculator import (
    LoadProfileHandlerSimulation,
    StreamSpecificEnergyDataHandler,
)
from ethos_penalps.node_operations import ProductionOrder
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamProductionPlanEntry,
    ContinuousStream,
    ContinuousStreamProductionPlanEntry,
    ProcessStepProductionPlanEntry,
    StreamDataFrameMetaInformation,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.utilities.general_functions import (
    create_subscript_string_matplotlib,
    get_sub,
    get_super,
)
from ethos_penalps.utilities.units import Units


class ProcessOverViewGenerator:
    def __init__(
        self,
        process_node_dict: dict[str, ProcessNode],
        load_profile_handler: LoadProfileHandlerSimulation,
        stream_handler: StreamHandler,
        order_dictionary: dict[float, ProductionOrder],
        enterprise_name: str,
        production_plan: ProductionPlan,
    ) -> None:
        self.process_node_dict: dict[str, ProcessNode] = process_node_dict
        self.load_profile_handler: LoadProfileHandlerSimulation = load_profile_handler
        self.stream_handler: StreamHandler = stream_handler
        self.load_type_dict_for_product_specific_energy_demand: dict[
            LoadType, ProductEnergyData
        ] = {}
        self.order_dictionary: dict[float, ProductionOrder] = order_dictionary
        self.stream_mass_to_product_mass_dict: dict[str, float] = {}
        self.enterprise_name: str = enterprise_name
        self.production_plan: ProductionPlan = production_plan
        self.stream_specific_energy_demand_product_corrected: dict[
            str, dict[LoadType, float]
        ] = {}

    def determine_total_energy_demand_per_ton_of_end_product(self):
        self.create_empty_product_energy_dict()
        self.determine_stream_mass_to_product_mass_conversion_factors()
        for (
            stream_name
        ) in (
            self.load_profile_handler.stream_energy_data_collection.stream_energy_data_dict
        ):
            stream_to_product_energy_conversion_factor = (
                self.stream_mass_to_product_mass_dict[stream_name]
            )
            self.add_stream_energy_data_to_product_energy_dict(
                product_to_stream_conversion_factor=stream_to_product_energy_conversion_factor,
                stream_name=stream_name,
            )
        for (
            process_step_name
        ) in self.load_profile_handler.process_step_energy_data_handler_dict:
            self.add_process_step_energy_data_to_product_energy_dict(
                process_step_name=process_step_name
            )

    def determine_stream_mass_to_product_mass_conversion_factors(self):
        sink = self.get_sink()
        current_stream_name = sink.get_input_stream_name()
        current_conversion_factor = 1
        self.stream_mass_to_product_mass_dict[current_stream_name] = (
            current_conversion_factor
        )
        previous_stream_to_product_conversion_factor = current_conversion_factor
        stream = self.stream_handler.get_stream(stream_name=current_stream_name)
        current_node_name = stream.get_upstream_node_name()
        current_node = self.process_node_dict[current_node_name]

        while isinstance(current_node, ProcessStep):
            current_conversion_factor = current_node.process_state_handler.process_step_data.main_mass_balance.convert_output_to_input_mass(
                output_mass=1
            )
            current_stream_name = (
                current_node.process_state_handler.process_step_data.main_mass_balance.get_input_stream_name()
            )
            previous_stream_to_product_conversion_factor = (
                previous_stream_to_product_conversion_factor * current_conversion_factor
            )
            self.stream_mass_to_product_mass_dict[current_stream_name] = (
                previous_stream_to_product_conversion_factor
            )
            current_node_name = current_node.get_upstream_node_name()
            current_node = self.process_node_dict[current_node_name]

    def add_stream_energy_data_to_product_energy_dict(
        self,
        product_to_stream_conversion_factor: float,
        stream_name: str,
    ):
        for (
            load_type,
            stream_energy_data,
        ) in self.load_profile_handler.stream_energy_data_collection.stream_energy_data_dict[
            stream_name
        ].items():
            specific_energy_value_to_add = (
                product_to_stream_conversion_factor
                * stream_energy_data.specific_energy_demand
            )
            self.add_stream_specific_energy_data(
                stream_name=stream_name,
                load_type=load_type,
                specific_energy_demand=specific_energy_value_to_add,
            )
            self.update_product_load_type_energy_data(
                load_type=load_type, energy_value_to_add=specific_energy_value_to_add
            )

    def add_stream_specific_energy_data(
        self, stream_name: str, load_type: LoadType, specific_energy_demand: float
    ):
        if stream_name in self.stream_specific_energy_demand_product_corrected:
            if (
                load_type
                in self.stream_specific_energy_demand_product_corrected[stream_name]
            ):
                raise Exception("Load is already in dict")
            self.stream_specific_energy_demand_product_corrected[stream_name][
                load_type
            ] = specific_energy_demand
        else:
            self.stream_specific_energy_demand_product_corrected[stream_name] = {
                load_type: specific_energy_demand
            }

    def add_process_step_energy_data_to_product_energy_dict(
        self, process_step_name: str
    ):
        process_step_energy_data_collection = (
            self.load_profile_handler.get_process_step_energy_data_collection(
                process_step_name=process_step_name
            )
        )
        for (
            process_state_energy_data_dict
        ) in process_step_energy_data_collection.process_state_energy_dict.values():
            for (
                load_type,
                process_state_energy_data,
            ) in process_state_energy_data_dict.items():
                if isinstance(
                    process_state_energy_data,
                    ProcessStateEnergyLoadDataBasedOnStreamMass,
                ):
                    process_state_energy_data.specific_energy_demand

                    product_specific_energy_demand = (
                        process_state_energy_data.specific_energy_demand
                        * self.stream_mass_to_product_mass_dict[
                            process_state_energy_data.stream_name
                        ]
                    )
                    self.update_product_load_type_energy_data(
                        load_type=load_type,
                        energy_value_to_add=product_specific_energy_demand,
                    )

    def update_product_load_type_energy_data(
        self,
        load_type: LoadType,
        energy_value_to_add: float,
    ) -> ProductEnergyData:
        if load_type in self.load_type_dict_for_product_specific_energy_demand:
            product_energy_data_type = (
                self.load_type_dict_for_product_specific_energy_demand[load_type]
            )
            product_energy_data_type.specific_energy_demand = (
                product_energy_data_type.specific_energy_demand + energy_value_to_add
            )
            self.load_type_dict_for_product_specific_energy_demand[load_type] = (
                product_energy_data_type
            )

    def create_empty_product_energy_dict(self):
        list_of_load_types = self.load_profile_handler.get_list_of_load_types()
        sink = self.get_sink()
        current_stream_name = sink.get_input_stream_name()

        stream = self.stream_handler.get_stream(stream_name=current_stream_name)
        product_commodity = stream.static_data.commodity

        for load_type in list_of_load_types:
            product_energy_data = ProductEnergyData(
                specific_energy_demand=0,
                product_commodity=product_commodity,
                load_type=load_type,
            )
            self.load_type_dict_for_product_specific_energy_demand[load_type] = (
                product_energy_data
            )

    def get_sink(self) -> Sink:
        for process_node_name in self.process_node_dict:
            if isinstance(self.process_node_dict[process_node_name], Sink):
                sink = self.process_node_dict[process_node_name]
        return sink

    def get_total_target_mass(self) -> float:
        total_produced_product_mass = 0
        for order in self.order_dictionary.values():
            total_produced_product_mass = (
                order.production_target + total_produced_product_mass
            )
        return total_produced_product_mass

    def calculate_total_energy_demands(self) -> pandas.DataFrame:
        output_list = []
        total_specific_energy = 0
        total_mass = self.get_total_target_mass()

        for (
            load_type,
            product_energy_data,
        ) in self.load_type_dict_for_product_specific_energy_demand.items():
            total_specific_energy = (
                total_specific_energy + product_energy_data.specific_energy_demand
            )
            total_load_specific_energy_demand = (
                product_energy_data.specific_energy_demand * total_mass
            )
            total_load_specific_energy_quantity = Units.compress_quantity(
                quantity_value=total_load_specific_energy_demand,
                unit=product_energy_data.energy_unit,
            )

            output_list.append(
                {
                    "Load Type": load_type.name,
                    "Total Energy Demand": total_load_specific_energy_quantity.m,
                    "Unit": total_load_specific_energy_quantity.u,
                }
            )

        total_energy_demand = total_specific_energy * total_mass

        total_energy_demand_quantity = Units.compress_quantity(
            quantity_value=total_energy_demand,
            unit=product_energy_data.energy_unit,
        )
        if self.load_type_dict_for_product_specific_energy_demand:
            output_list.append(
                {
                    "Load Type": "Combined load types",
                    "Total Energy Demand": total_energy_demand_quantity.m,
                    "Unit": total_energy_demand_quantity.u,
                }
            )
        output_data_frame = pandas.DataFrame(output_list)
        return output_data_frame

    def create_product_energy_pie_chart(self) -> matplotlib.pyplot.Figure | None:
        self.determine_total_energy_demand_per_ton_of_end_product()
        figure, axes = matplotlib.pyplot.subplots()
        figure.set_figwidth(8.27)
        label_list = []
        value_list = []
        total_energy = 0

        for (
            load_type,
            product_energy_data,
        ) in self.load_type_dict_for_product_specific_energy_demand.items():
            mass_specific_energy_demand_quantity = Units.compress_quantity(
                quantity_value=product_energy_data.specific_energy_demand,
                unit=product_energy_data.energy_unit,
            )
            label = (
                str(round(mass_specific_energy_demand_quantity.m, 2))
                + " "
                + create_subscript_string_matplotlib(
                    base=str(mass_specific_energy_demand_quantity.u),
                    subscripted_text=str(product_energy_data.load_type.name),
                )
                + "/"
                + create_subscript_string_matplotlib(
                    base=str(product_energy_data.mass_unit),
                    subscripted_text=str(product_energy_data.product_commodity.name),
                )
            )
            label_list.append(label)
            value_list.append(product_energy_data.specific_energy_demand)
            total_energy = total_energy + product_energy_data.specific_energy_demand
        if self.load_type_dict_for_product_specific_energy_demand:
            total_product_mass_specific_energy_demand_quantity = (
                Units.compress_quantity(
                    quantity_value=total_energy,
                    unit=Units.energy_unit,
                )
            )

            matplotlib.pyplot.title(
                "Total energy demand "
                + str(round(total_product_mass_specific_energy_demand_quantity.m, 2))
                + " "
                + str(total_product_mass_specific_energy_demand_quantity.u)
                + "/"
                + create_subscript_string_matplotlib(
                    base=str(product_energy_data.mass_unit),
                    subscripted_text=str(product_energy_data.product_commodity.name),
                )
                + "\n"
                + " for "
                + str(self.enterprise_name)
            )
            axes.pie(x=value_list, labels=label_list)
        else:
            figure = None

        return figure

    def get_total_mass_for_each_stream(self) -> pandas.DataFrame:
        """Create Data frame with masses and load profiles in each stream"""
        list_of_table_rows = []

        # Loop over each stream with a stream data frame
        for (
            stream_data_frame_meta_data
        ) in self.production_plan.dict_of_stream_meta_data_data_frames.values():
            # Get the total mass in dependence of the stream
            if stream_data_frame_meta_data.stream_type == BatchStream.stream_type:
                total_mass_produced = stream_data_frame_meta_data.data_frame[
                    "batch_mass_value"
                ].sum()
            elif (
                stream_data_frame_meta_data.stream_type == ContinuousStream.stream_type
            ):
                total_mass_produced = stream_data_frame_meta_data.data_frame[
                    "total_mass"
                ].sum()
            else:
                raise Exception("Unexpected datatype")

            energy_demand_row_dictionary = {}
            # Create further columns for each load type associated with the stream
            ## First check if specific energy demands exist for the current stream

            if (
                stream_data_frame_meta_data.stream_name
                in self.stream_specific_energy_demand_product_corrected
            ):
                stream_energy_data_dict = self.load_profile_handler.stream_energy_data_collection.stream_energy_data_dict[
                    stream_data_frame_meta_data.stream_name
                ]
                # Loop over each load for which a product specific energy type exists
                for load_type in self.stream_specific_energy_demand_product_corrected[
                    stream_data_frame_meta_data.stream_name
                ]:
                    specific_energy_demand = (
                        self.stream_specific_energy_demand_product_corrected[
                            stream_data_frame_meta_data.stream_name
                        ][load_type]
                    )
                    stream_energy_data = stream_energy_data_dict[load_type.uuid]

                    ## Stream specific energy demand
                    specific_stream_energy_quantity = Units.compress_quantity(
                        unit=stream_energy_data.energy_unit,
                        quantity_value=specific_energy_demand,
                    )
                    column_name_specific_energy_demand = (
                        "Specific energy demand " + str(load_type.name)
                    )
                    energy_demand_row_dictionary[column_name_specific_energy_demand] = (
                        specific_energy_demand
                    )

                    energy_demand_row_dictionary["Mass specific energy unit"] = (
                        specific_stream_energy_quantity.u / stream_energy_data.mass_unit
                    )

                    ## Stream specific total energy demand
                    ### Value
                    total_energy_demand_column_name = "Total energy demand " + str(
                        load_type.name
                    )
                    total_energy_demand = specific_energy_demand * total_mass_produced

                    ### Unit

                    total_energy_demand_quantity = Units.compress_quantity(
                        unit=stream_energy_data.energy_unit,
                        quantity_value=total_energy_demand,
                    )
                    energy_demand_row_dictionary[total_energy_demand_column_name] = (
                        total_energy_demand_quantity.m
                    )
                    energy_demand_row_dictionary["Total energy unit"] = (
                        total_energy_demand_quantity.u
                    )

                row_dictionary = {
                    "Total stream mass": total_mass_produced,
                    "Mass unit": stream_data_frame_meta_data.mass_unit,
                    "Commodity": stream_data_frame_meta_data.commodity,
                }
                row_dictionary.update(energy_demand_row_dictionary)
                list_of_table_rows.append(row_dictionary)
            else:
                row_dictionary = {
                    "Total stream mass": total_mass_produced,
                    "Mass unit": stream_data_frame_meta_data.mass_unit,
                    "Commodity": stream_data_frame_meta_data.commodity,
                }
                list_of_table_rows.append(row_dictionary)

        output_data_frame = pandas.DataFrame(list_of_table_rows)
        return output_data_frame

    def get_total_mass_and_energy_for_process_step(
        self,
    ) -> pandas.DataFrame:
        list_of_table_entries = []
        for process_step_name in self.process_node_dict:
            if isinstance(self.process_node_dict[process_step_name], ProcessStep):
                process_step_energy_data_collection = (
                    self.load_profile_handler.get_process_step_energy_data_collection(
                        process_step_name=process_step_name
                    )
                )

                process_state_energy_dict_by_process_step_name = (
                    self.load_profile_handler.load_profile_collection.convert_process_state_energy_date()
                )

                for (
                    process_state_energy_data_dict
                ) in (
                    process_step_energy_data_collection.process_state_energy_dict.values()
                ):
                    for (
                        load_type,
                        process_state_energy_data,
                    ) in process_state_energy_data_dict.items():
                        if isinstance(
                            process_state_energy_data,
                            ProcessStateEnergyLoadDataBasedOnStreamMass,
                        ):
                            product_specific_energy_demand = (
                                process_state_energy_data.specific_energy_demand
                                * self.stream_mass_to_product_mass_dict[
                                    process_state_energy_data.stream_name
                                ]
                            )

                            row_dictionary = {
                                "Process step name": process_state_energy_data.process_step_name,
                                "Specific energy demand": product_specific_energy_demand,
                            }
                            if (
                                process_step_name
                                in process_state_energy_dict_by_process_step_name
                            ):
                                if (
                                    load_type
                                    in process_state_energy_dict_by_process_step_name[
                                        process_step_name
                                    ]
                                ):
                                    total_energy = (
                                        process_state_energy_dict_by_process_step_name[
                                            process_step_name
                                        ][load_type]["energy_quantity"].sum()
                                    )

                                    total_energy_demand_quantity = (
                                        Units.compress_quantity(
                                            unit=process_state_energy_data.energy_unit,
                                            quantity_value=total_energy,
                                        )
                                    )
                                    mass_throughput = (
                                        total_energy / product_specific_energy_demand
                                    )

                                    energy_row_dictionary = {
                                        "Total energy: "
                                        + str(
                                            load_type.name
                                        ): total_energy_demand_quantity.value,
                                        "Energy unit": total_energy_demand_quantity.unit,
                                        "Mass throughput": mass_throughput,
                                    }
                                    row_dictionary.update(energy_row_dictionary)
                                list_of_table_entries.append(row_dictionary)
        process_step_summary_df = pandas.DataFrame(list_of_table_entries)

        return process_step_summary_df
