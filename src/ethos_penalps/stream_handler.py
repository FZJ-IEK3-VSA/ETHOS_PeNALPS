import json
from pprint import pprint

from ethos_penalps.stream import (
    BatchStream,
    BatchStreamState,
    BatchStreamStaticData,
    ContinuousStream,
    ContinuousStreamState,
    ContinuousStreamStaticData,
)
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.type_aliases import numbers_alias

logger = PeNALPSLogger.get_logger_without_handler()


class StreamHandler:
    # -- Initialization --

    def __init__(self):
        self.stream_dict: dict[str, ContinuousStream | BatchStream] = {}

    # -- Stream creation & registration --

    def create_continuous_stream(
        self,
        continuous_stream_static_data: ContinuousStreamStaticData,
    ) -> ContinuousStream:
        """Creates a continuous stream that connects two nodes in the material flow
        model. A continuous streams moves the mass continuously from the start node
        to the target node at its operation rate. These nodes can be either a
        ProcessStep, Sink, Source or a ProcessChainStorage. It is important to
        note that Process steps require states that compatible to continuous streams.

        Args:
            continuous_stream_static_data (ContinuousStreamStaticData):
                An object that contains all stream data that does not change
                during the simulation.

        Returns:
            ContinuousStream: New stream Object.
        """
        stream = ContinuousStream(
            static_data=continuous_stream_static_data,
        )
        if stream.name in self.stream_dict:
            raise Exception("Stream with name " + str(stream.name) + " is already in stream dict of the stream handler")
        self.stream_dict[stream.name] = stream
        return stream

    def create_batch_stream(self, batch_stream_static_data: BatchStreamStaticData) -> BatchStream:
        """Creates a batch stream that connects two nodes in the material flow
        model. A batch stream transports the mass between two nodes in a discrete manner.
        At the start time of the stream all mass removed from the start node. At the end
        time all mass is added to the target node. These nodes can be either a ProcessStep,
        Sink, Source or a ProcessChainStorage. It is important to note that Process steps
        require states that compatible to batch streams.

        Args:
            batch_stream_static_data (BatchStreamStaticData): _description_

        Raises:
            Exception: _description_

        Returns:
            BatchStream: _description_
        """
        batch_stream = BatchStream(static_data=batch_stream_static_data)
        if batch_stream.name in self.stream_dict:
            raise Exception(
                "Stream with name " + str(batch_stream.name) + " is already in stream dict of the stream handler"
            )
        self.stream_dict[batch_stream.name] = batch_stream
        return batch_stream

    def add_stream(self, new_stream: ContinuousStream | BatchStream, overwrite_stream: bool = False):
        """Adds a stream directly to the StreamHandler.

        Args:
            new_stream (ContinuousStream | BatchStream): _description_
            overwrite_stream (bool, optional): _description_. Defaults to False.

        Raises:
            Exception: _description_
        """
        if new_stream.name in self.stream_dict and overwrite_stream is False:
            raise Exception(
                "Stream with name " + str(new_stream.name) + " is already in stream dict of the stream handler"
            )
        self.stream_dict[new_stream.name] = new_stream

    # -- Stream access --

    def get_stream(self, stream_name: str) -> ContinuousStream | BatchStream:
        """Returns a stream based on the name as a key.

        Args:
            stream_name (str): Name of stream to be returned.


        Returns:
            ContinuousStream | BatchStream: Returns the stream with the
                input key.
        """
        if not isinstance(stream_name, str):
            raise Exception("Expected string as a stream name but got type : " + str(type(stream_name)) + " instead")

        try:
            stream = self.stream_dict[stream_name]
        except KeyError as exc:
            all_stream_name_list = self.get_list_of_all_stream_names_in_stream_handler()
            raise Exception(
                "Stream: "
                + str(stream_name)
                + " could no be found in the stream handler. Stream Handler contains the following streams:\n"
                + str(all_stream_name_list)
            ) from exc
        except Exception:
            print(" Exception: " + str(Exception.__class__) + " occurred")

        return stream

    def get_list_of_all_stream_names_in_stream_handler(self) -> list[str]:
        """Gets the names of all streams stored in the StreamHandler instance. Includes inactive streams.

        Returns:
            list[str]: List of all stream names in the StreamHandler.
        """
        stream_name_list = []
        for stream_name in self.stream_dict:
            stream_name_list.append(stream_name)
        return stream_name_list

    # -- Serialization: streams --

    def json_dumps_streams(self) -> str:
        """Dumps all streams to json files.

        Returns:
            str: Json string of the streams.
        """
        continuous_stream_json_dict = {}
        batch_stream_json_dict = {}
        for stream_name, stream in self.stream_dict.items():
            if isinstance(stream, ContinuousStream):
                continuous_stream_json_dict[stream_name] = stream.to_json()
            elif isinstance(stream, BatchStream):
                batch_stream_json_dict[stream_name] = stream.to_json()
        json_stream_dict = {
            "continuous": continuous_stream_json_dict,
            "batch": batch_stream_json_dict,
        }
        stream_handler_json_dump = json.dumps(json_stream_dict)
        return stream_handler_json_dump

    def json_dump_streams(self, path: str | None = None):
        """Dumps streams to json file.

        Args:
            path (str | None, optional): Path to the json file. Defaults to None.
        """
        if path is None:
            result_path_generator = ResultPathGenerator()
            path = result_path_generator.create_path_to_file_relative_to_main_file(
                file_name="combined_stream_handler",
                subdirectory_name="results",
                file_extension=".json",
                add_time_stamp_to_filename=False,
            )
        json_string = self.json_dumps_streams()
        with open(file=path, mode="w", encoding="utf8") as out_file:
            out_file.write(json_string)

    def json_loads_streams(self, json_string: str):
        """Loads the streams from a json string.

        Args:
            json_string (str): Json string which contains
            the stream data.
        """
        container_json = json.loads(json_string)
        batch_stream_dict = {}
        for stream_name, stream_json_dict in container_json["batch"].items():
            batch_stream_dict[stream_name] = BatchStream.from_json(stream_json_dict)
        continuous_stream_dict = {}
        for stream_name, stream_json_dict in container_json["continuous"].items():
            continuous_stream_dict[stream_name] = ContinuousStream.from_json(stream_json_dict)
        self.stream_dict.update(batch_stream_dict)
        self.stream_dict.update(continuous_stream_dict)

    def json_load_streams(self, path: str):
        """Loads streams from json file.

        Args:
            path (str): Path to json file.
        """
        with open(file=path) as input_file:
            json_string = input_file.read()
        self.json_loads_streams(json_string=json_string)

    # -- Serialization: stream states --

    def json_dumps_stream_states(
        self,
        stream_states: list[ContinuousStreamState | BatchStreamState],
    ) -> str:
        """Serializes a list of stream states to a JSON string.

        Each state is stored with its stream_type so that the correct
        class can be used for deserialization.

        Args:
            stream_states: List of stream states to serialize.

        Returns:
            str: JSON string of the serialized states.
        """
        serialized = []
        for state in stream_states:
            if isinstance(state, ContinuousStreamState):
                stream_type = ContinuousStream.stream_type
            elif isinstance(state, BatchStreamState):
                stream_type = BatchStream.stream_type
            else:
                raise ValueError(f"Unknown stream state type: {type(state)}")
            serialized.append(
                {
                    "stream_type": stream_type,
                    "state": state.to_dict(),
                }
            )
        return json.dumps(serialized)

    def json_dump_stream_states(
        self,
        stream_states: list[ContinuousStreamState | BatchStreamState],
        path: str,
    ) -> None:
        """Serializes a list of stream states to a JSON file.

        Args:
            stream_states: List of stream states to serialize.
            path: Path to the output JSON file.
        """
        json_string = self.json_dumps_stream_states(stream_states)
        with open(file=path, mode="w", encoding="utf-8") as out_file:
            out_file.write(json_string)

    @staticmethod
    def json_loads_stream_states(
        json_string: str,
    ) -> list[ContinuousStreamState | BatchStreamState]:
        """Deserializes a list of stream states from a JSON string.

        Args:
            json_string: JSON string produced by json_dumps_stream_states.

        Returns:
            List of deserialized stream state objects.
        """
        serialized = json.loads(json_string)
        states: list[ContinuousStreamState | BatchStreamState] = []
        for entry in serialized:
            stream_type = entry["stream_type"]
            state_dict = entry["state"]
            if stream_type == ContinuousStream.stream_type:
                states.append(ContinuousStreamState.from_dict(state_dict))
            elif stream_type == BatchStream.stream_type:
                states.append(BatchStreamState.from_dict(state_dict))
            else:
                raise ValueError(f"Unknown stream type: {stream_type}")
        return states

    @staticmethod
    def json_load_stream_states(
        path: str,
    ) -> list[ContinuousStreamState | BatchStreamState]:
        """Deserializes a list of stream states from a JSON file.

        Args:
            path: Path to the JSON file.

        Returns:
            List of deserialized stream state objects.
        """
        with open(file=path, encoding="utf-8") as input_file:
            json_string = input_file.read()
        return StreamHandler.json_loads_stream_states(json_string)

    # -- Debug / display --

    def print_all_streams_with_parameters(self) -> None:
        """Prints all attributes of all streams that are stored in the stream_dict. Is only used for debugging purposes."""
        for stream in self.stream_dict.values():
            pprint(vars(stream))
