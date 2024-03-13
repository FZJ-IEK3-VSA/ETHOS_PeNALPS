from dataclasses import dataclass

from ethos_penalps.data_classes import (
    EmptyMetaDataInformation,
    LoadProfileMetaData,
    ProcessChainIdentifier,
    ProcessStepDataFrameMetaInformation,
    ProductionOrderMetadata,
    StorageDataFrameMetaInformation,
)
from ethos_penalps.load_profile_calculator import LoadProfileHandlerSimulation
from ethos_penalps.network_level import NetworkLevel
from ethos_penalps.order_generator import OrderCollection
from ethos_penalps.post_processing.time_series_visualizations.order_plot import (
    post_process_order_collection,
)
from ethos_penalps.process_chain import ProcessChain
from ethos_penalps.process_nodes.process_chain_storage import ProcessChainStorage
from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.process_nodes.sink import Sink, Source
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream import StreamDataFrameMetaInformation
from ethos_penalps.stream_node_distributor import SplittedOrderCollection
from ethos_penalps.post_processing.post_processed_data_handler import (
    PostProcessSimulationDataHandler,
)


class NetworkAnalyzer:
    def __init__(self, list_of_network_level: list[NetworkLevel]) -> None:
        self.list_of_network_level: list[NetworkLevel] = list_of_network_level

    def get_list_of_all_stream_process_step_names(self) -> list[str]:
        list_of_object_names = []
        for network_level in self.list_of_network_level:
            list_of_process_step_node_names = (
                network_level.get_list_of_process_step_node_names()
            )
            list_of_object_names.extend(list_of_process_step_node_names)
        return list_of_object_names

    def get_dictionary_of_nodes_names_keyed_by_chain_names(
        self,
    ) -> dict[str, list[str]]:
        object_name_dictionary = {}
        include_sink = True
        for network_level in self.list_of_network_level:
            for process_chain in network_level.list_of_process_chains:
                list_of_nodes = process_chain.get_list_of_process_step_names(
                    include_sink=include_sink, include_source=True
                )
                object_name_dictionary[
                    process_chain.process_chain_identifier.chain_name
                ] = list_of_nodes
                include_sink = False

        return object_name_dictionary

    def get_downstream_stream_name(
        self, process_chain: ProcessChain, process_step_name: str
    ) -> str:
        process_step = process_chain.get_process_node(
            process_node_name=process_step_name
        )
        if type(process_step) is ProcessStep:
            output_stream_name = (
                process_step.process_state_handler.process_step_data.main_mass_balance.get_output_stream_name()
            )
        return output_stream_name

    def get_upstream_stream_name(
        self, process_chain: ProcessChain, process_step_name: str
    ) -> str:
        process_step = process_chain.get_process_node(
            process_node_name=process_step_name
        )
        if type(process_step) is ProcessStep:
            input_stream_name = (
                process_step.process_state_handler.process_step_data.main_mass_balance.get_input_stream_name
            )
        return input_stream_name

    def get_source_name_from_network_level(self, network_level: NetworkLevel) -> str:
        return network_level.get_main_source()

    def get_sink_name_from_network_level(self, network_level: NetworkLevel) -> str:
        return network_level.get_main_sink()


@dataclass
class StreamResults:
    stream_meta_data_frame: StreamDataFrameMetaInformation
    list_of_load_profile_meta_data: list[LoadProfileMetaData]

    def get_stream_meta_data_list(
        self,
    ) -> list[StreamDataFrameMetaInformation | EmptyMetaDataInformation]:
        return [self.stream_meta_data_frame]

    def get_stream_and_load_profile_meta_data_list(
        self, load_profiles_above: bool = True
    ) -> list[
        StreamDataFrameMetaInformation | LoadProfileMetaData | EmptyMetaDataInformation
    ]:
        output_meta_data_list = []
        if load_profiles_above is True:
            output_meta_data_list.extend(self.list_of_load_profile_meta_data)
        output_meta_data_list.append(self.stream_meta_data_frame)
        if load_profiles_above is False:
            output_meta_data_list.extend(self.list_of_load_profile_meta_data)
        return output_meta_data_list


@dataclass
class ProcessStepResults:
    process_step_meta_data_frame: ProcessStepDataFrameMetaInformation
    list_of_input_stream_results: list[StreamResults]
    list_of_output_stream_results: list[StreamResults]
    internal_storage_meta_data: StorageDataFrameMetaInformation
    load_profile_meta_data_frame: list[LoadProfileMetaData]

    def get_meta_data_list_with_input_and_output_streams(
        self, input_at_top: bool = True, include_internal_storage: bool = False
    ) -> list[ProcessStepDataFrameMetaInformation | StreamDataFrameMetaInformation]:
        output_meta_data_list = []

        if input_at_top is True:
            upper_stream_list = self.list_of_input_stream_results
            lower_stream_list = self.list_of_output_stream_results
        elif input_at_top is False:
            upper_stream_list = self.list_of_output_stream_results
            lower_stream_list = self.list_of_input_stream_results

        for stream_result in upper_stream_list:
            output_meta_data_list.extend(stream_result.get_stream_meta_data_list())
        if include_internal_storage is True:
            output_meta_data_list.append(self.internal_storage_meta_data)
        output_meta_data_list.append(self.process_step_meta_data_frame)
        for stream_result in lower_stream_list:
            output_meta_data_list.extend(stream_result.get_stream_meta_data_list())

        return output_meta_data_list

    def get_meta_data_list_and_input_streams(
        self, input_at_top: bool = True, include_internal_storages: bool = False
    ) -> list[ProcessStepDataFrameMetaInformation | StreamDataFrameMetaInformation]:
        output_meta_data_list = []

        if input_at_top is True:
            upper_stream_list = self.list_of_input_stream_results
            lower_stream_list = []
        elif input_at_top is False:
            upper_stream_list = []
            lower_stream_list = self.list_of_input_stream_results

        for stream_result in upper_stream_list:
            output_meta_data_list.extend(stream_result.get_stream_meta_data_list())
        if include_internal_storages is True:
            output_meta_data_list.append(self.internal_storage_meta_data)
        output_meta_data_list.append(self.process_step_meta_data_frame)
        for stream_result in lower_stream_list:
            output_meta_data_list.extend(stream_result.get_stream_meta_data_list())
        return output_meta_data_list

    def get_meta_data_list_with__output_streams(
        self, output_at_top: bool = True
    ) -> list[ProcessStepDataFrameMetaInformation | StreamDataFrameMetaInformation]:
        output_meta_data_list = []

        if output_at_top is True:
            upper_stream_list = []
            lower_stream_list = self.list_of_output_stream_results
        elif output_at_top is False:
            upper_stream_list = self.list_of_output_stream_results
            lower_stream_list = []

        for stream_result in upper_stream_list:
            output_meta_data_list.extend(stream_result.get_stream_meta_data_list())
        output_meta_data_list.append(self.process_step_meta_data_frame)
        for stream_result in lower_stream_list:
            output_meta_data_list.extend(stream_result.get_stream_meta_data_list())
        return output_meta_data_list


@dataclass
class SinkResults:
    name: str
    storage_meta_data_frame: StorageDataFrameMetaInformation
    list_of_input_stream_results: list[StreamResults]
    order_collection: OrderCollection
    dict_of_splitted_order_collection: dict[str, SplittedOrderCollection]
    total_order_collection_metadata: ProductionOrderMetadata
    dict_of_splitted_order_meta_data_frame: dict[str, ProductionOrderMetadata]

    def get_streams_and_storage_meta_data(
        self, include_order_meta_data: bool = True
    ) -> list[
        StorageDataFrameMetaInformation
        | StreamDataFrameMetaInformation
        | ProductionOrderMetadata
    ]:
        output_meta_data_list = []
        for input_stream_result in self.list_of_input_stream_results:
            if include_order_meta_data is True:
                splitted_order_meta_data = self._get_splitted_order_meta_data(
                    stream_name=input_stream_result.stream_meta_data_frame.stream_name
                )
                output_meta_data_list.append(splitted_order_meta_data)
            output_meta_data_list.extend(
                input_stream_result.get_stream_meta_data_list()
            )

        if include_order_meta_data is True:
            output_meta_data_list.append(self.total_order_collection_metadata)
        output_meta_data_list.append(self.storage_meta_data_frame)

        return output_meta_data_list

    def _get_splitted_order_meta_data(
        self, stream_name: str
    ) -> ProductionOrderMetadata:
        splitted_order_meta_data = self.dict_of_splitted_order_meta_data_frame[
            stream_name
        ]
        return splitted_order_meta_data


@dataclass
class ProcessChainStorageResults:
    name: str
    storage_meta_data_frame: StorageDataFrameMetaInformation
    list_of_input_stream_results: list[StreamResults]
    list_of_output_stream_results: list[StreamResults]
    order_collection: OrderCollection
    dict_of_splitted_order_collection: dict[
        ProcessChainIdentifier, SplittedOrderCollection
    ]
    total_order_collection_metadata: ProductionOrderMetadata
    dict_of_splitted_order_meta_data_frame: dict[str, ProductionOrderMetadata]

    def get_streams_and_storage_meta_data(
        self, include_order_meta_data: bool = True
    ) -> list[
        StorageDataFrameMetaInformation
        | StreamDataFrameMetaInformation
        | ProductionOrderMetadata
    ]:
        output_meta_data_list = []
        for input_stream_result in self.list_of_input_stream_results:
            if include_order_meta_data is True:
                output_meta_data_list.append(
                    self._get_splitted_order_meta_data(
                        stream_name=input_stream_result.stream_meta_data_frame.stream_name
                    )
                )
            output_meta_data_list.extend(
                input_stream_result.get_stream_meta_data_list()
            )
        if include_order_meta_data is True:
            output_meta_data_list.append(self.total_order_collection_metadata)
        output_meta_data_list.append(self.storage_meta_data_frame)
        for output_stream_result in self.list_of_output_stream_results:
            output_meta_data_list.extend(
                output_stream_result.get_stream_meta_data_list()
            )
        return output_meta_data_list

    def _get_splitted_order_meta_data(
        self, stream_name: str
    ) -> ProductionOrderMetadata:
        splitted_order_meta_data = self.dict_of_splitted_order_meta_data_frame[
            stream_name
        ]
        return splitted_order_meta_data


@dataclass
class SourceResults:
    name: str
    storage_meta_data_frame: StorageDataFrameMetaInformation
    list_of_output_stream_results: list[StreamResults]

    def get_streams_and_storage_meta_data(
        self, include_order_meta_data: bool = True
    ) -> list[StorageDataFrameMetaInformation | StreamDataFrameMetaInformation]:
        output_meta_data_list = []
        output_meta_data_list.append(self.storage_meta_data_frame)
        for output_stream_result in self.list_of_output_stream_results:
            output_meta_data_list.extend(
                output_stream_result.get_stream_meta_data_list()
            )
        return output_meta_data_list


@dataclass
class ProcessChainResults:
    process_chain_name: str
    list_of_process_step_results: list[ProcessStepResults]
    downstream_end_node_position: int
    upstream_end_node_position: int
    # List order is expected from upstream to downstream

    def get_process_chain_without_sources_and_sinks(
        self, include_internal_storages: bool
    ) -> list[StreamDataFrameMetaInformation | ProcessStepDataFrameMetaInformation]:
        """Returns a list of StreamDataFrameMetaInformation | ProcessStepDataFrameMetaInformation in order
        from the upstream to the downstream node

        :param include_internal_storages: _description_
        :type include_internal_storages: bool
        :return: _description_
        :rtype: list[StreamDataFrameMetaInformation | ProcessStepDataFrameMetaInformation]
        """
        output_meta_data_list = []
        node_position_counter = 0
        if self.upstream_end_node_position > self.downstream_end_node_position:
            self.list_of_process_step_results = list(
                reversed(self.list_of_process_step_results)
            )
            self.downstream_end_node_position = len(self.list_of_process_step_results)
            self.upstream_end_node_position = 0

        for process_step_results in self.list_of_process_step_results:
            node_position_counter = node_position_counter + 1
            if node_position_counter == self.downstream_end_node_position:
                output_meta_data_list.extend(
                    process_step_results.get_meta_data_list_with_input_and_output_streams(
                        include_internal_storage=include_internal_storages
                    )
                )
            else:
                output_meta_data_list.extend(
                    process_step_results.get_meta_data_list_and_input_streams(
                        include_internal_storages=include_internal_storages
                    )
                )

        return output_meta_data_list


@dataclass
class StructuredNetworkLevelResults:
    main_sink_results: SinkResults | ProcessChainStorageResults
    main_source_results: SourceResults | ProcessChainStorageResults
    list_of_process_chain_results: list[ProcessChainResults]

    # def get_list_of_process_chain_meta_data_lists(
    #     self,
    # ) -> list[
    #     list[StreamDataFrameMetaInformation | ProcessStepDataFrameMetaInformation]
    # ]:
    #     list_of_output_meta_data_lists = []
    #     for process_chain_results in self.list_of_process_chain_results:
    #         list_of_output_meta_data_lists.append(
    #             process_chain_results.get_process_chain_without_sources_and_sinks()
    #         )
    #     return list_of_output_meta_data_lists
    def get_list_of_process_chain_meta_data_results(self) -> list[ProcessChainResults]:
        return self.list_of_process_chain_results


@dataclass
class StructuredNetworkResults:
    list_of_structured_level_results: list[StructuredNetworkLevelResults]
    downstream_network_level_position: int
    upstream_network_level_position: int

    def get_network_level_in_material_flow_direction(
        self,
    ) -> list[StructuredNetworkLevelResults]:
        self.downstream_network_level_position = len(
            self.list_of_structured_level_results
        )
        self.upstream_network_level_position = 0
        return list(reversed(self.list_of_structured_level_results))

    def get_network_level_in_reversed_material_flow_direction(
        self,
    ) -> list[StructuredNetworkLevelResults]:
        self.downstream_network_level_position = 0
        self.upstream_network_level_position = len(
            self.list_of_structured_level_results
        )
        return self.list_of_structured_level_results


class ResultSelector:
    def __init__(
        self,
        production_plan: ProductionPlan,
        list_of_network_level: list[NetworkLevel],
        load_profile_handler: LoadProfileHandlerSimulation,
        post_process_simulation_data_handler: PostProcessSimulationDataHandler,
    ) -> None:
        self.production_plan: ProductionPlan = production_plan
        self.list_of_network_level: list[NetworkLevel] = list_of_network_level
        self.network_analyzer: NetworkAnalyzer = NetworkAnalyzer(
            list_of_network_level=list_of_network_level
        )
        self.load_profile_handler: LoadProfileHandlerSimulation = load_profile_handler
        self.post_process_simulation_data_handler: PostProcessSimulationDataHandler = (
            post_process_simulation_data_handler
        )

    def get_structured_network_results(self) -> StructuredNetworkResults:
        list_of_structured_level_results = []
        assert (
            self.post_process_simulation_data_handler.postprocessing_is_initialized
            is True
        )
        for network_level in self.list_of_network_level:
            structured_network_level_results = (
                self._create_structured_network_level_results(
                    network_level=network_level
                )
            )
            list_of_structured_level_results.append(structured_network_level_results)
        structured_network_results = StructuredNetworkResults(
            list_of_structured_level_results=list_of_structured_level_results,
            downstream_network_level_position=0,
            upstream_network_level_position=len(list_of_structured_level_results),
        )
        return structured_network_results

    def _create_structured_network_level_results(
        self, network_level: NetworkLevel
    ) -> StructuredNetworkLevelResults:

        source_results: ProcessChainStorageResults | SourceResults
        if type(network_level.main_source) is Source:
            source_results = self._get_source_results(source=network_level.main_source)
        elif type(network_level.main_source) is ProcessChainStorage:
            source_results = self._get_process_chain_storage_results(
                process_chain_storage=network_level.main_source
            )
        sink_results: ProcessChainStorageResults | SinkResults
        if type(network_level.main_sink) is Sink:
            sink_results = self._get_sink_results(sink=network_level.main_sink)
        elif type(network_level.main_sink) is ProcessChainStorage:
            sink_results = self._get_process_chain_storage_results(
                process_chain_storage=network_level.main_sink
            )
        list_of_process_chain_results = []
        for process_chain in network_level.list_of_process_chains:
            list_of_process_chain_results.append(
                self._get_process_chain_results(process_chain=process_chain)
            )

        structured_network_level_results = StructuredNetworkLevelResults(
            main_source_results=source_results,
            main_sink_results=sink_results,
            list_of_process_chain_results=list_of_process_chain_results,
        )
        return structured_network_level_results

    def _get_process_chain_results(
        self, process_chain: ProcessChain
    ) -> ProcessChainResults:
        list_of_process_step_results = []
        current_node = process_chain.sink
        current_node.prepare_sink_for_next_chain(
            process_chain_identifier=process_chain.process_chain_identifier
        )
        current_node_name = current_node.get_upstream_node_name()
        current_node = process_chain.process_node_dict[current_node_name]
        while isinstance(current_node, ProcessStep):
            list_of_process_step_results.append(
                self._get_process_step_results(process_step=current_node)
            )
            current_node_name = current_node.get_upstream_node_name()
            current_node = process_chain.process_node_dict[current_node_name]
        process_chain_results = ProcessChainResults(
            process_chain_name=process_chain.process_chain_identifier.chain_name,
            list_of_process_step_results=list_of_process_step_results,
            downstream_end_node_position=0,
            upstream_end_node_position=len(list_of_process_step_results),
        )
        return process_chain_results

    def _get_process_step_results(
        self, process_step: ProcessStep
    ) -> ProcessStepResults:
        process_step_meta_data_frame = self.post_process_simulation_data_handler.get_process_step_meta_data_by_name(
            process_step_name=process_step.name
        )
        internal_storage_meta_data_frame = (
            self.post_process_simulation_data_handler.get_storage_meta_data_by_name(
                storage_name=process_step.name
            )
        )
        list_of_input_stream_results = []
        input_stream_results = self._get_stream_results(
            stream_name=process_step.process_state_handler.process_step_data.main_mass_balance.main_input_stream_name
        )
        list_of_input_stream_results.append(input_stream_results)

        list_of_output_stream_results = []
        output_stream_result = self._get_stream_results(
            stream_name=process_step.process_state_handler.process_step_data.main_mass_balance.main_output_stream_name
        )
        list_of_output_stream_results.append(output_stream_result)
        process_step_results = ProcessStepResults(
            process_step_meta_data_frame=process_step_meta_data_frame,
            list_of_input_stream_results=list_of_input_stream_results,
            list_of_output_stream_results=list_of_output_stream_results,
            internal_storage_meta_data=internal_storage_meta_data_frame,
            load_profile_meta_data_frame=[],
        )
        return process_step_results

    def _get_sink_results(self, sink: Sink) -> SinkResults:
        storage_meta_data_frame = (
            self.post_process_simulation_data_handler.get_storage_meta_data_by_name(
                storage_name=sink.name
            )
        )
        # Get output stream result list
        list_of_input_stream_results = []
        for input_stream_name in sink.order_distributor.dict_of_stream_names.values():
            input_stream_results = self._get_stream_results(
                stream_name=input_stream_name
            )
            list_of_input_stream_results.append(input_stream_results)

        complete_order_collection_meta_data = post_process_order_collection(
            order_collection=sink.order_distributor.order_collection
        )
        dict_of_splitted_order_meta_data_by_stream_name = {}
        for (
            process_chain_identifier,
            stream_name,
        ) in sink.order_distributor.dict_of_stream_names.items():
            splitted_order = sink.order_distributor.dict_of_splitted_order[
                process_chain_identifier
            ]
            splitted_order_meta_data = post_process_order_collection(
                order_collection=splitted_order
            )
            dict_of_splitted_order_meta_data_by_stream_name[stream_name] = (
                splitted_order_meta_data
            )
        sink_results = SinkResults(
            name=sink.name,
            storage_meta_data_frame=storage_meta_data_frame,
            list_of_input_stream_results=list_of_input_stream_results,
            dict_of_splitted_order_collection=sink.order_distributor.dict_of_splitted_order,
            order_collection=sink.order_distributor.order_collection,
            total_order_collection_metadata=complete_order_collection_meta_data,
            dict_of_splitted_order_meta_data_frame=dict_of_splitted_order_meta_data_by_stream_name,
        )
        return sink_results

    def _get_process_chain_storage_results(
        self, process_chain_storage: ProcessChainStorage
    ) -> ProcessChainStorageResults:
        # Get storage meta data frame
        storage_meta_data_frame = (
            self.post_process_simulation_data_handler.get_storage_meta_data_by_name(
                storage_name=process_chain_storage.name
            )
        )
        # Get input stream result list
        list_of_input_stream_results = []
        for (
            input_stream_name
        ) in process_chain_storage.sink.order_distributor.dict_of_stream_names.values():
            input_stream_results = self._get_stream_results(
                stream_name=input_stream_name
            )
            list_of_input_stream_results.append(input_stream_results)

        # Get output stream result list
        list_of_output_stream_results = []
        for (
            output_stream_name
        ) in process_chain_storage.source.dict_of_output_stream_names.values():
            output_stream_results = self._get_stream_results(
                stream_name=output_stream_name
            )
            list_of_output_stream_results.append(output_stream_results)

        complete_order_collection_meta_data = post_process_order_collection(
            order_collection=process_chain_storage.sink.order_distributor.order_collection
        )
        dict_of_splitted_order_meta_data_by_stream_name = {}
        for (
            process_chain_identifier,
            stream_name,
        ) in process_chain_storage.sink.order_distributor.dict_of_stream_names.items():
            splitted_order = (
                process_chain_storage.sink.order_distributor.dict_of_splitted_order[
                    process_chain_identifier
                ]
            )
            splitted_order_meta_data = post_process_order_collection(
                order_collection=splitted_order
            )
            dict_of_splitted_order_meta_data_by_stream_name[stream_name] = (
                splitted_order_meta_data
            )

        process_chain_storage_results = ProcessChainStorageResults(
            name=process_chain_storage.name,
            storage_meta_data_frame=storage_meta_data_frame,
            list_of_input_stream_results=list_of_input_stream_results,
            list_of_output_stream_results=list_of_output_stream_results,
            dict_of_splitted_order_collection=process_chain_storage.sink.order_distributor.dict_of_splitted_order,
            order_collection=process_chain_storage.sink.order_distributor.order_collection,
            total_order_collection_metadata=complete_order_collection_meta_data,
            dict_of_splitted_order_meta_data_frame=dict_of_splitted_order_meta_data_by_stream_name,
        )
        return process_chain_storage_results

    def _get_source_results(self, source: Source) -> SourceResults:
        storage_meta_data_frame = (
            self.post_process_simulation_data_handler.get_storage_meta_data_by_name(
                storage_name=source.name
            )
        )
        # Get output stream result list
        list_of_output_stream_results = []
        for output_stream_name in source.dict_of_output_stream_names.values():
            output_stream_results = self._get_stream_results(
                stream_name=output_stream_name
            )
            list_of_output_stream_results.append(output_stream_results)
        source_results = SourceResults(
            name=source.name,
            storage_meta_data_frame=storage_meta_data_frame,
            list_of_output_stream_results=list_of_output_stream_results,
        )
        return source_results

    def _get_stream_results(self, stream_name: str) -> StreamResults:
        stream_meta_data_frame = (
            self.post_process_simulation_data_handler.get_stream_meta_data_by_name(
                stream_name=stream_name
            )
        )

        stream_results = StreamResults(
            stream_meta_data_frame=stream_meta_data_frame,
            list_of_load_profile_meta_data=[],
        )
        return stream_results

    # def initialize_data_frames(self):
    #     if not self.production_plan.dict_of_process_step_data_frames:
    #         self.production_plan.convert_process_state_dictionary_to_list_of_data_frames()

    #     if not self.production_plan.dict_of_stream_meta_data_data_frames:
    #         self.production_plan.convert_stream_entries_to_meta_data_data_frames()

    #     if not self.production_plan.dict_of_storage_meta_data_data_frames:
    #         self.production_plan.convert_list_of_storage_entries_to_meta_data()
