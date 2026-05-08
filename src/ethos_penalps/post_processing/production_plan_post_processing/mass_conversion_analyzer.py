from dataclasses import dataclass, field

from ethos_penalps.data_classes import Commodity
from ethos_penalps.organizational_agents.network_level import NetworkLevel
from ethos_penalps.post_processing.production_plan_post_processing.network_analyzer import (
    NetworkAnalyzer,
)
from ethos_penalps.process_nodes.process_chain_storage import ProcessChainStorage
from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.utilities.type_aliases import numbers_alias


@dataclass(kw_only=True)
class CumulatedConversionFactorProcessChain:
    chain_name: str
    product_commodity: Commodity
    raw_material_commodity: Commodity
    input_to_product_conversion_factor: numbers_alias
    list_of_process_step_names: list[str] = field(default_factory=list)
    network_level_cumulated_conversion_factor: "CumulatedConversionFactorNetworkLevel" = None

    def __post_init__(self):
        if self.network_level_cumulated_conversion_factor is not None:
            self.input_to_product_conversion_factor = (
                self.input_to_product_conversion_factor
                * self.network_level_cumulated_conversion_factor.average_conversion_factor
            )
            self.product_commodity = self.network_level_cumulated_conversion_factor.product_commodity

    def add_new_conversion_factor_from_process_step(
        self,
        process_step_name: str,
        conversion_factor: numbers_alias,
        new_raw_material_commodity: Commodity,
    ) -> "CumulatedConversionFactorProcessChain":
        new_list_of_process_step_names = list(self.list_of_process_step_names)
        new_list_of_process_step_names.append(process_step_name)
        new_input_to_product_conversion_factor = self.input_to_product_conversion_factor * conversion_factor

        cumulated_conversion_factor_process_chain = CumulatedConversionFactorProcessChain(
            chain_name=self.chain_name,
            list_of_process_step_names=new_list_of_process_step_names,
            input_to_product_conversion_factor=new_input_to_product_conversion_factor,
            product_commodity=self.product_commodity,
            raw_material_commodity=new_raw_material_commodity,
        )
        return cumulated_conversion_factor_process_chain


@dataclass
class CumulatedConversionFactorNetworkLevel:
    raw_material_to_product_conversion_factor_list: list[CumulatedConversionFactorProcessChain]

    def __post_init__(self):
        number_of_process_chains = len(self.raw_material_to_product_conversion_factor_list)
        sum_of_conversion_factors: numbers_alias = 0
        for cumulated_conversion_factor_process_chain in self.raw_material_to_product_conversion_factor_list:
            sum_of_conversion_factors = (
                sum_of_conversion_factors + cumulated_conversion_factor_process_chain.input_to_product_conversion_factor
            )
        self.average_conversion_factor: numbers_alias = sum_of_conversion_factors / number_of_process_chains

        self.product_commodity: Commodity = self.raw_material_to_product_conversion_factor_list[0].product_commodity
        self.raw_material_commodity: Commodity = self.raw_material_to_product_conversion_factor_list[
            0
        ].raw_material_commodity


@dataclass
class ConversionFactorHandler:
    list_of_network_level: list[NetworkLevel]
    dict_of_process_step_conversion_handler: dict[str, CumulatedConversionFactorProcessChain] = field(
        default_factory=dict
    )
    dict_of_stream_conversion_handler: dict[str, CumulatedConversionFactorProcessChain] = field(default_factory=dict)

    def __post_init__(self):
        self.create_all_conversion_factors()

    def get_stream_input_to_output_factor(self, stream_name: str) -> CumulatedConversionFactorProcessChain:
        return self.dict_of_stream_conversion_handler[stream_name]

    def get_process_step_input_to_output_conversion_factor(
        self, process_step_name: str
    ) -> CumulatedConversionFactorProcessChain:
        return self.dict_of_process_step_conversion_handler[process_step_name]

    def add_stream_cumulated_conversion_factor(
        self,
        cumulated_conversion_factor: CumulatedConversionFactorProcessChain,
        stream_name: str,
    ):
        self.dict_of_stream_conversion_handler[stream_name] = cumulated_conversion_factor

    def add_process_step_cumulated_conversion_factor(
        self,
        cumulated_conversion_factor: CumulatedConversionFactorProcessChain,
        process_step_name: str,
    ):
        self.dict_of_process_step_conversion_handler[process_step_name] = cumulated_conversion_factor

    def create_all_conversion_factors(self):
        previous_cumulated_conversion_factor_network_level = None
        for network_level in self.list_of_network_level:
            list_of_cumulated_process_chain_factors: list[CumulatedConversionFactorProcessChain] = []
            for process_chain in network_level.list_of_process_chains:
                current_sink = process_chain.sink
                if isinstance(current_sink, Sink):
                    input_stream = current_sink.get_stream_to_process_chain(
                        process_chain_identifier=process_chain.process_chain_identifier
                    )
                elif isinstance(current_sink, ProcessChainStorage):
                    input_stream = current_sink.sink.get_stream_to_process_chain(
                        process_chain_identifier=process_chain.process_chain_identifier
                    )
                if previous_cumulated_conversion_factor_network_level is None:
                    cumulated_conversion_factor_process_chain = CumulatedConversionFactorProcessChain(
                        raw_material_commodity=current_sink.commodity,
                        product_commodity=current_sink.commodity,
                        input_to_product_conversion_factor=1,
                        chain_name=process_chain.process_chain_identifier.chain_name,
                    )
                elif isinstance(
                    previous_cumulated_conversion_factor_network_level,
                    CumulatedConversionFactorNetworkLevel,
                ):
                    cumulated_conversion_factor_process_chain = CumulatedConversionFactorProcessChain(
                        raw_material_commodity=previous_cumulated_conversion_factor_network_level.raw_material_commodity,
                        product_commodity=previous_cumulated_conversion_factor_network_level.product_commodity,
                        input_to_product_conversion_factor=1,
                        chain_name=process_chain.process_chain_identifier.chain_name,
                        network_level_cumulated_conversion_factor=previous_cumulated_conversion_factor_network_level,
                    )

                self.add_stream_cumulated_conversion_factor(
                    cumulated_conversion_factor=cumulated_conversion_factor_process_chain,
                    stream_name=input_stream.name,
                )
                current_node_name = input_stream.get_upstream_node_name()
                current_node = process_chain.process_node_dict[current_node_name]
                while isinstance(current_node, ProcessStep):
                    input_stream_name = current_node.get_input_stream_name()
                    input_stream = process_chain.stream_handler.get_stream(stream_name=input_stream_name)
                    process_step_conversion_factor = current_node.process_state_handler.process_step_data.main_mass_balance.input_to_output_conversion_factor
                    cumulated_conversion_factor_process_chain = (
                        cumulated_conversion_factor_process_chain.add_new_conversion_factor_from_process_step(
                            process_step_name=current_node.name,
                            conversion_factor=process_step_conversion_factor,
                            new_raw_material_commodity=input_stream.static_data.commodity,
                        )
                    )
                    self.add_stream_cumulated_conversion_factor(
                        stream_name=input_stream_name,
                        cumulated_conversion_factor=cumulated_conversion_factor_process_chain,
                    )
                    self.add_process_step_cumulated_conversion_factor(
                        process_step_name=current_node.name,
                        cumulated_conversion_factor=cumulated_conversion_factor_process_chain,
                    )
                    current_node_name = input_stream.get_upstream_node_name()
                    current_node = process_chain.process_node_dict[current_node_name]

                list_of_cumulated_process_chain_factors.append(cumulated_conversion_factor_process_chain)
            previous_cumulated_conversion_factor_network_level = CumulatedConversionFactorNetworkLevel(
                raw_material_to_product_conversion_factor_list=list_of_cumulated_process_chain_factors
            )
