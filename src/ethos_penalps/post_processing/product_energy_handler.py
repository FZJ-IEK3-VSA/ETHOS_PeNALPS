from dataclasses import dataclass, field

import pint

from ethos_penalps.data_classes import (
    Commodity,
    FinalProductEnergyData,
    LoadType,
    ProcessStateEnergyLoadData,
    ProcessStepProductEnergyLoadData,
    StreamLoadEnergyData,
    StreamProductEnergyLoadData,
)
from ethos_penalps.energy.load_profile_calculator import (
    LoadProfileHandlerSimulation,
    ProcessStateEnergyData,
    ProcessStepEnergyDataHandler,
    StreamEnergyData,
)
from ethos_penalps.organizational_agents.network_level import NetworkLevel
from ethos_penalps.organizational_agents.process_chain import (
    LoadProfileHandlerSimulation,
    ProcessChain,
)
from ethos_penalps.post_processing.production_plan_post_processing.mass_conversion_analyzer import (
    ConversionFactorHandler,
    CumulatedConversionFactorProcessChain,
)
from ethos_penalps.post_processing.production_plan_post_processing.network_analyzer import (
    NetworkAnalyzer,
)
from ethos_penalps.process_nodes.process_chain_storage import ProcessChainStorage
from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.stream import (
    BatchStream,
    ContinuousStream,
    StreamDataFrameMetaInformation,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.utilities.type_aliases import numbers_alias
from ethos_penalps.utilities.units import Units


@dataclass
class StreamProductEnergyData:
    stream_energy_data: StreamEnergyData
    cumulated_conversion_factor_process_chain: CumulatedConversionFactorProcessChain

    def __post_init__(self):
        self.dict_of_loads: dict[str, LoadType] = {}
        self.dict_of_product_load_energy_data: dict[str, StreamProductEnergyLoadData] = {}
        self.stream_name: str = self.stream_energy_data.stream_name
        for stream_load_energy_data in self.stream_energy_data.dict_stream_load_energy_data.values():
            if self.stream_name != stream_load_energy_data.stream_name:
                raise Exception("Misconfiguration")
            converted_energy_data = (
                stream_load_energy_data.specific_energy_demand
                / self.cumulated_conversion_factor_process_chain.input_to_product_conversion_factor
            )

            stream_product_load_energy_data = StreamProductEnergyLoadData(
                stream_name=self.stream_name,
                specific_energy_demand=converted_energy_data,
                load_type=stream_load_energy_data.load_type,
                mass_unit=stream_load_energy_data.mass_unit,
                energy_unit=stream_load_energy_data.energy_unit,
            )
            self.dict_of_loads[stream_product_load_energy_data.load_type.uuid] = (
                stream_product_load_energy_data.load_type
            )
            self.dict_of_product_load_energy_data[stream_product_load_energy_data.load_type.uuid] = (
                stream_product_load_energy_data
            )


@dataclass
class ProcessStateProductEnergyData:
    process_state_energy_data: ProcessStateEnergyData
    cumulated_conversion_factor_process_chain: CumulatedConversionFactorProcessChain

    def __post_init__(self):
        self.process_step_name: str = self.process_state_energy_data.process_step_name
        self.process_state_name: str = self.process_state_energy_data.process_state_name
        self.dict_of_loads: dict[str, LoadType] = {}
        self.dict_of_load_energy_data: dict[str, ProcessStateEnergyLoadData] = {}
        for process_state_energy_load_data in self.process_state_energy_data.dict_of_load_energy_data.values():
            converted_specific_energy_data = (
                process_state_energy_load_data.specific_energy_demand
                / self.cumulated_conversion_factor_process_chain.input_to_product_conversion_factor
            )
            process_state_energy_product_load_data = ProcessStateEnergyLoadData(
                process_state_name=process_state_energy_load_data.process_state_name,
                process_step_name=process_state_energy_load_data.process_step_name,
                specific_energy_demand=converted_specific_energy_data,
                mass_unit=process_state_energy_load_data.mass_unit,
                energy_unit=process_state_energy_load_data.energy_unit,
                load_type=process_state_energy_load_data.load_type,
            )
            self.dict_of_load_energy_data[process_state_energy_product_load_data.load_type.uuid] = (
                process_state_energy_product_load_data
            )
            self.dict_of_loads[process_state_energy_product_load_data.load_type.uuid] = (
                process_state_energy_product_load_data.load_type
            )


@dataclass
class ProcessStepProductEnergyData:
    process_step_energy_data: ProcessStepEnergyDataHandler
    cumulated_conversion_factor_process_chain: CumulatedConversionFactorProcessChain

    def __post_init__(self):
        self.process_state_energy_load_data_dict: dict[str, ProcessStateProductEnergyData] = {}
        self.process_state_name: str
        self.dict_of_loads: dict[str, LoadType] = {}

        for process_state_energy_data in self.process_step_energy_data.process_state_energy_dict.values():
            process_state_product_energy_data = ProcessStateProductEnergyData(
                process_state_energy_data=process_state_energy_data,
                cumulated_conversion_factor_process_chain=self.cumulated_conversion_factor_process_chain,
            )
            self.process_state_energy_load_data_dict[process_state_product_energy_data.process_state_name] = (
                process_state_product_energy_data
            )
            self.dict_of_loads.update(process_state_product_energy_data.dict_of_loads)


@dataclass
class SpecificProductEnergyData:
    load_type: LoadType
    specific_energy_data_demand: numbers_alias
    raw_material_commodity: Commodity
    product_commodity: Commodity
    unit: str


@dataclass
class ProcessChainEnergyData:
    process_chain: ProcessChain
    load_profile_handler_simulation: LoadProfileHandlerSimulation
    conversion_factor_handler: ConversionFactorHandler
    product_energy_dict: dict[str, SpecificProductEnergyData] = field(default_factory=dict)
    dict_of_load: dict[str, LoadType] = field(default_factory=dict)

    def __post_init__(self):

        sink = self.process_chain.get_sink()
        if isinstance(sink, Sink):
            input_stream = sink.get_stream_to_process_chain(
                process_chain_identifier=self.process_chain.process_chain_identifier
            )
        elif isinstance(sink, ProcessChainStorage):
            input_stream = sink.sink.get_stream_to_process_chain(
                process_chain_identifier=self.process_chain.process_chain_identifier
            )
        else:
            raise Exception(
                "Sink of process chain: "
                + str(self.process_chain.process_chain_identifier.chain_name)
                + " is not a sink object."
            )

        self.add_stream_energy_data(
            stream=input_stream,
        )
        process_node_name = input_stream.get_upstream_node_name()
        process_node = self.process_chain.get_process_node(process_node_name=process_node_name)
        number_of_nodes = len(self.process_chain.process_node_dict)
        iterator = 0
        while isinstance(process_node, ProcessStep) and iterator <= number_of_nodes:
            input_stream_name = process_node.get_input_stream_name()
            input_stream = self.process_chain.stream_handler.get_stream(stream_name=input_stream_name)
            self.add_stream_energy_data(
                stream=input_stream,
            )
            self.add_process_step_product_energy_data(
                process_step=process_node,
            )

            process_node_name = input_stream.get_upstream_node_name()
            process_node = self.process_chain.get_process_node(process_node_name=process_node_name)

            iterator = iterator + 1

    def add_process_step_product_energy_data(
        self,
        process_step: ProcessStep,
    ):
        cumulated_conversion_factor = self.conversion_factor_handler.get_process_step_input_to_output_conversion_factor(
            process_step_name=process_step.name
        )
        process_step_energy_data = self.load_profile_handler_simulation.process_step_energy_data_handler_dict[
            process_step.name
        ]
        process_step_product_energy_data = ProcessStepProductEnergyData(
            process_step_energy_data=process_step_energy_data,
            cumulated_conversion_factor_process_chain=cumulated_conversion_factor,
        )

        for (
            process_state_name,
            process_state_energy_data,
        ) in process_step_product_energy_data.process_state_energy_load_data_dict.items():
            self.dict_of_load.update(process_state_energy_data.dict_of_loads)
            for (
                load_type_uuid,
                process_state_energy_load_data,
            ) in process_state_energy_data.dict_of_load_energy_data.items():
                if load_type_uuid in self.product_energy_dict:
                    new_specific_energy_demand = (
                        self.product_energy_dict[load_type_uuid].specific_energy_data_demand
                        + process_state_energy_load_data.specific_energy_demand
                    )
                    self.product_energy_dict[load_type_uuid].specific_energy_data_demand = new_specific_energy_demand
                else:
                    self.product_energy_dict[load_type_uuid] = SpecificProductEnergyData(
                        load_type=process_state_energy_load_data.load_type,
                        specific_energy_data_demand=process_state_energy_load_data.specific_energy_demand,
                        raw_material_commodity=cumulated_conversion_factor.raw_material_commodity,
                        product_commodity=cumulated_conversion_factor.product_commodity,
                        unit=process_state_energy_load_data.energy_unit
                        + r"/"
                        + process_state_energy_load_data.mass_unit,
                    )

    def add_stream_energy_data(
        self,
        stream: ContinuousStream | BatchStream,
    ):

        cumulated_conversion_factor = self.conversion_factor_handler.get_stream_input_to_output_factor(
            stream_name=stream.name
        )
        stream_product_energy_data = StreamProductEnergyData(
            stream_energy_data=stream.stream_energy_data,
            cumulated_conversion_factor_process_chain=cumulated_conversion_factor,
        )

        for (
            load_type_uuid,
            stream_product_load_data,
        ) in stream_product_energy_data.dict_of_product_load_energy_data.items():
            self.dict_of_load.update(stream_product_energy_data.dict_of_loads)
            if load_type_uuid in self.product_energy_dict:
                new_specific_energy_demand = (
                    self.product_energy_dict[load_type_uuid].specific_energy_data_demand
                    + stream_product_load_data.specific_energy_demand
                )
                self.product_energy_dict[load_type_uuid].specific_energy_data_demand = new_specific_energy_demand

            else:
                self.product_energy_dict[load_type_uuid] = SpecificProductEnergyData(
                    load_type=stream_product_load_data.load_type,
                    specific_energy_data_demand=stream_product_load_data.specific_energy_demand,
                    raw_material_commodity=cumulated_conversion_factor.raw_material_commodity,
                    product_commodity=cumulated_conversion_factor.product_commodity,
                    unit=stream_product_load_data.energy_unit + r"/" + stream_product_load_data.mass_unit,
                )


# @dataclass
# class ProcessChainSpecificEnergyShare:
#     chain_name: str
#     specific_energy_data: pint.Quantity
#     load_type: LoadType


@dataclass
class NetworkLevelProductEnergy:
    network_level: NetworkLevel
    load_profile_handler_simulation: LoadProfileHandlerSimulation
    conversion_factor_handler: ConversionFactorHandler
    # list_of_process_chain_product_energy_data: list[ProcessChainEnergyData] = field(
    #     default_factory=list
    # )

    def __post_init__(self):
        self.dict_of_averaged_energy_values: dict[str, SpecificProductEnergyData] = {}
        dict_of_chain_energy_list: dict[str, list[SpecificProductEnergyData]] = {}
        self.dict_of_load: dict[str, LoadType] = {}
        self.dict_of_averaged_chain_energy_list: dict[str, SpecificProductEnergyData] = {}
        for process_chain in self.network_level.list_of_process_chains:
            process_chain_energy_data = ProcessChainEnergyData(
                process_chain=process_chain,
                load_profile_handler_simulation=self.load_profile_handler_simulation,
                conversion_factor_handler=self.conversion_factor_handler,
            )
            self.dict_of_load.update(process_chain_energy_data.dict_of_load)
            for (
                load_uuid,
                product_energy_load_data,
            ) in process_chain_energy_data.product_energy_dict.items():
                # quantity = (
                #     product_energy_load_data.specific_energy_data_demand
                #     * Units.get_unit(unit_string=product_energy_load_data.unit)
                # )
                # process_chain_specific_energy_share = ProcessChainSpecificEnergyShare(
                #     chain_name=process_chain.process_chain_identifier.chain_name,
                #     specific_energy_data=quantity,
                #     load_type=product_energy_load_data.load_type,
                # )
                if load_uuid in dict_of_chain_energy_list:
                    dict_of_chain_energy_list[load_uuid].append(product_energy_load_data)
                else:
                    dict_of_chain_energy_list[load_uuid] = [product_energy_load_data]

        for (
            load_uuid,
            process_chain_specific_energy_share_list,
        ) in dict_of_chain_energy_list.items():
            number_of_specific_values_to_average = len(process_chain_specific_energy_share_list)
            sum_of_specific_energy_data: numbers_alias = 0

            for process_chain_specific_energy_share in process_chain_specific_energy_share_list:
                sum_of_specific_energy_data = (
                    sum_of_specific_energy_data + process_chain_specific_energy_share.specific_energy_data_demand
                )
                process_chain_specific_energy_share.load_type
                raw_material_commodity = process_chain_specific_energy_share.raw_material_commodity
                product_commodity = process_chain_specific_energy_share.product_commodity
                unit = process_chain_specific_energy_share.unit
            averaged_specific_energy = sum_of_specific_energy_data / number_of_specific_values_to_average
            load_type = self.dict_of_load[load_uuid]
            specific_product_energy_data = SpecificProductEnergyData(
                load_type=load_type,
                specific_energy_data_demand=averaged_specific_energy,
                unit=unit,
                raw_material_commodity=raw_material_commodity,
                product_commodity=product_commodity,
            )
            self.dict_of_averaged_chain_energy_list[load_uuid] = specific_product_energy_data


@dataclass
class NetworkEnergyAnalyzer(NetworkAnalyzer):
    list_of_network_level: list[NetworkLevel]
    load_profile_handler_simulation: LoadProfileHandlerSimulation

    def __post_init__(self):
        self.conversion_factor_handler = ConversionFactorHandler(list_of_network_level=self.list_of_network_level)

        self.dict_of_product_energy: dict[str, SpecificProductEnergyData] = {}
        list_of_network_level_energy: list[NetworkLevelProductEnergy] = []
        for network_level in self.list_of_network_level:
            network_level_product_energy = NetworkLevelProductEnergy(
                network_level=network_level,
                load_profile_handler_simulation=self.load_profile_handler_simulation,
                conversion_factor_handler=self.conversion_factor_handler,
            )
            list_of_network_level_energy.append(network_level_product_energy)

        for network_level_energy in list_of_network_level_energy:
            for (
                load_uuid,
                product_energy_network_level_load,
            ) in network_level_energy.dict_of_averaged_chain_energy_list.items():
                if load_uuid in self.dict_of_product_energy:
                    self.dict_of_product_energy[load_uuid].specific_energy_data_demand = (
                        self.dict_of_product_energy[load_uuid].specific_energy_data_demand
                        + product_energy_network_level_load.specific_energy_data_demand
                    )
                else:
                    self.dict_of_product_energy[load_uuid] = product_energy_network_level_load

    def get_total_specific_energy_demand(self) -> SpecificProductEnergyData:
        total_specific_energy_demand: numbers_alias = 0
        for load_specific_product_energy_data in self.dict_of_product_energy.values():
            total_specific_energy_demand = (
                total_specific_energy_demand + load_specific_product_energy_data.specific_energy_data_demand
            )

        # TODO: check for unequal units
        total_specific_product_energy_data = SpecificProductEnergyData(
            load_type=LoadType(name="Total Energy"),
            specific_energy_data_demand=total_specific_energy_demand,
            raw_material_commodity=load_specific_product_energy_data.raw_material_commodity,
            product_commodity=load_specific_product_energy_data.product_commodity,
            unit=load_specific_product_energy_data.unit,
        )
        return total_specific_product_energy_data


if __name__ == "__main__":
    pass
