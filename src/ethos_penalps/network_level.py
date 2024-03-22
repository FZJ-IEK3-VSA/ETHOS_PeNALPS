import uuid
from dataclasses import dataclass

from ethos_penalps.data_classes import (
    Commodity,
    OrderCollection,
    ProcessChainIdentifier,
    get_new_uuid,
)
from ethos_penalps.load_profile_calculator import LoadProfileHandlerSimulation
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
        load_profile_handler: LoadProfileHandlerSimulation,
        time_data: TimeData,
    ) -> None:
        self.stream_handler: StreamHandler = stream_handler
        self.production_plan: ProductionPlan = production_plan
        self.load_profile_handler: LoadProfileHandlerSimulation = load_profile_handler
        self.main_source: Source | ProcessChainStorage
        self.main_sink: Sink | ProcessChainStorage
        self.node_dictionary: dict[str, ProcessNode] = {}
        self.list_of_process_chains: list[ProcessChain] = []
        self.time_data: TimeData = time_data
        self.uuid: str = get_new_uuid()

    def create_main_source(self, name: str, commodity: Commodity) -> Source:
        """Creates a source that marks the start point of the material flow in
        the NetworkLevel.

        Args:
            name (str): Name of the source. Is used as key for identification
                and is displayed in some figures. Must be unique.
            commodity (Commodity): The commodity that is distributed by the sink.

        Returns:
            Source: Object that marks the start point of the material flow in
                the NetworkLevel.
        """
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
        """Creates a sink that marks the target of the material flow in the NetWorkLevel.

        Args:
            name (str): Name of the sink. Is displayed in some figures
                and used as a key for identification. Must be unique.
            commodity (Commodity): Commodity that is collected by the sink.
            order_collection (OrderCollection): Object that contains all
                product order that should be collected by the sink during the
                simulation.

        Returns:
            Sink: Marks the target of the material flow in the NetWorkLevel.
        """
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
        """Creates a ProcessChainStorage and sets it as a Source in
        this NetworkLevel. The Source determines start start point
        of the material flow in the NetworkLevel.

        Args:
            name (str): Name of the ProcessChainStorage. Must be unique.
            commodity (Commodity): Commodity which is distributed by the
                Storage.

        Returns:
            ProcessChainStorage: Object that determines start start point
                of the material flow in the NetworkLevel
        """
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
        """Adds the ProcessChainStorage instance as a replacement for a sink.
        Marks the target of the material flow in the NetWorkLevel.

        Args:
            process_chain_storage (ProcessChainStorage): Object that marks the
                target of the material flow in this NetworkLevel.
        """
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

    def create_process_chain(self, process_chain_name: str) -> ProcessChain:
        """Creates a new ProcessChain for this NetworkLevel.
        Multiple ProcessChains can be used to simulated equipment
        that operates in parallel.

        Args:
            process_chain_name (str): Name of the new ProcessChain.
                The name must be unique and is displayed in some
                figures.

        Returns:
            ProcessChain: New ProcessChain object that can be filled with
                Process Steps.
        """
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
        """Converts the streams from the downstream
        source to orders for the sink of this
        NetworkLevel.
        """
        self.main_sink.get_order_from_parent_source()

    def combine_stream_handler_from_chains(self):
        """Combines the streams of the StreamHandler of each
        ProcessChain in a single StreamHandler of the
        NetworkLevel.
        """
        for process_chain in self.list_of_process_chains:
            self.stream_handler.stream_dict.update(
                process_chain.stream_handler.stream_dict
            )

    def combine_node_dict(self):
        """Combines the node dictionaries of the process chains in
        a single node dictionary in the NetworkLevel.
        """
        for process_chain in self.list_of_process_chains:
            self.node_dictionary.update(process_chain.process_node_dict)

    def get_main_sink(self) -> Sink | ProcessChainStorage:
        """Returns the Sink of ProcessChainStorage of the
        NetworkLevel

        Returns:
            Sink | ProcessChainStorage: Object that represents
                the target of the material flow in the
                NetworkLevel.
        """
        return self.main_sink

    def get_main_source(self) -> Source | ProcessChainStorage:
        """Returns the Source of ProcessChainStorage of the
        NetworkLevel

        Returns:
            Source | ProcessChainStorage: Object that represents
                the start point of the material flow in the
                NetworkLevel.
        """
        return self.main_source

    def get_list_of_process_step_node_names(self) -> list[str]:
        """Returns a list of the names of all process step nodes in
        the NetworkLevel.

        Returns:
            list[str]: List of the names of all process step nodes in
                the NetworkLevel.
        """
        list_of_process_node_names = []
        for chain in self.list_of_process_chains:
            list_of_nodes_in_chain = chain.get_list_of_process_step_names()
            list_of_process_node_names.extend(list_of_nodes_in_chain)
        return list_of_process_node_names
