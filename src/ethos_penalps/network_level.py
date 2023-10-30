import uuid
from dataclasses import dataclass

from ethos_penalps.data_classes import (
    Commodity,
    OrderCollection,
    ProcessChainIdentifier,
    get_new_uuid,
)
from ethos_penalps.load_profile_calculator import LoadProfileHandler
from ethos_penalps.process_chain import ProcessChain
from ethos_penalps.process_nodes.process_chain_storage import ProcessChainStorage
from ethos_penalps.process_nodes.process_step import ProcessNode
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.process_nodes.source import Source
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData


class NetworkLevel:
    def __init__(
        self,
        stream_handler: StreamHandler,
        production_plan: ProductionPlan,
        load_profile_handler: LoadProfileHandler,
        time_data: TimeData,
    ) -> None:
        self.stream_handler: StreamHandler = stream_handler
        self.production_plan: ProductionPlan = production_plan
        self.load_profile_handler: LoadProfileHandler = load_profile_handler
        self.main_source: Source | ProcessChainStorage
        self.main_sink: Sink | ProcessChainStorage
        self.node_dictionary: dict[ProcessNode] = {}
        self.list_of_process_chains: list[ProcessChain] = []
        self.time_data: TimeData = time_data
        self.uuid: uuid.UUID = get_new_uuid()

    def create_main_source(self, name: str, commodity: Commodity) -> Source:
        source = Source(
            name=name,
            commodity=commodity,
            stream_handler=self.stream_handler,
            time_data=self.time_data,
            production_plan=self.production_plan,
        )
        self.main_source = source
        return source

    def create_main_sink(
        self, name: str, commodity: Commodity, order_collection: OrderCollection
    ) -> Sink:
        sink = Sink(
            name=name,
            commodity=commodity,
            stream_handler=self.stream_handler,
            order_collection=order_collection,
            production_plan=self.production_plan,
            time_data=TimeData(
                global_start_date=self.time_data.global_start_date,
                global_end_date=self.time_data.global_end_date,
            ),
        )
        self.main_sink = sink
        return sink

    def create_process_chain_storage_as_source(
        self, name: str, commodity: Commodity
    ) -> ProcessChainStorage:
        process_chain_storage = ProcessChainStorage(
            name=name,
            commodity=commodity,
            stream_handler=self.stream_handler,
            production_plan=self.production_plan,
            time_data=TimeData(
                global_start_date=self.time_data.global_start_date,
                global_end_date=self.time_data.global_end_date,
            ),
        )
        self.main_source = process_chain_storage

        return process_chain_storage

    def add_process_chain_storage_as_sink(
        self, process_chain_storage: ProcessChainStorage
    ):
        process_chain_storage.add_sink_from_next_network_level(
            commodity=process_chain_storage.commodity,
            name=process_chain_storage.name,
            stream_handler=self.stream_handler,
            production_plan=self.production_plan,
            time_data=TimeData(
                global_start_date=process_chain_storage.time_data.global_start_date,
                global_end_date=process_chain_storage.time_data.global_end_date,
            ),
        )
        self.main_sink = process_chain_storage

    def create_process_chain(self, process_chain_name: str):
        new_process_chain_number = len(self.list_of_process_chains) + 1
        process_chain_identifier = ProcessChainIdentifier(
            chain_number=new_process_chain_number, chain_name=process_chain_name
        )

        process_chain = ProcessChain(
            time_data=self.time_data,
            process_chain_identifier=process_chain_identifier,
            production_plan=self.production_plan,
            load_profile_handler=self.load_profile_handler,
        )

        self.list_of_process_chains.append(process_chain)
        return process_chain

    def get_order_from_previous_sources(self):
        self.main_sink.get_order_from_parent_source()

    def combine_stream_handler_from_chains(self):
        for process_chain in self.list_of_process_chains:
            self.stream_handler.stream_dict.update(
                process_chain.stream_handler.stream_dict
            )

    def combine_node_dict(self):
        for process_chain in self.list_of_process_chains:
            self.node_dictionary.update(process_chain.process_node_dict)

    def get_main_sink(self) -> Sink | ProcessChainStorage:
        return self.main_sink

    def get_main_source(self) -> Source | ProcessChainStorage:
        return self.main_source

    def get_list_of_process_step_node_names(self) -> list[str]:
        list_of_process_node_names = []
        for chain in self.list_of_process_chains:
            list_of_nodes_in_chain = chain.get_list_of_process_step_names()
            list_of_process_node_names.extend(list_of_nodes_in_chain)
        return list_of_process_node_names
