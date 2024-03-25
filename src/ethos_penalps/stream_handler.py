import json
from dataclasses import dataclass, field
from pprint import pprint

from dataclasses_json import DataClassJsonMixin, config, dataclass_json

from ethos_penalps.stream import (
    BatchStream,
    BatchStreamStaticData,
    ContinuousStream,
    ContinuousStreamStaticData,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.general_functions import ResultPathGenerator

logger = PeNALPSLogger.get_logger_without_handler()


class StreamHandler:
    def __init__(self):
        self.stream_dict: dict[str, ContinuousStream | BatchStream] = {}

    def print_all_streams_with_parameters(self) -> None:
        """Prints all attributes of all streams that are stored in the stream_dict. Is only used for debugging purposes."""
        for stream in self.stream_dict.values():
            pprint(vars(stream))

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
        with open(file=path, mode="w") as out_file:
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
            continuous_stream_dict[stream_name] = ContinuousStream.from_json(
                stream_json_dict
            )
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
            raise Exception(
                "Stream with name "
                + str(stream.name)
                + " is already in stream dict of the stream handler"
            )
        self.stream_dict[stream.name] = stream
        return stream

    def add_stream(
        self, new_stream: ContinuousStream | BatchStream, overwrite_stream: bool = False
    ):
        """Adds a stream directly to the StreamHandler.

        Args:
            new_stream (ContinuousStream | BatchStream): _description_
            overwrite_stream (bool, optional): _description_. Defaults to False.

        Raises:
            Exception: _description_
        """
        if new_stream.name in self.stream_dict and overwrite_stream is False:
            raise Exception(
                "Stream with name "
                + str(new_stream.name)
                + " is already in stream dict of the stream handler"
            )
        self.stream_dict[new_stream.name] = new_stream

    def get_list_of_all_stream_names_in_stream_handler(self) -> list[str]:
        """Gets the names of all streams stored in the StreamHandler instance. Includes inactive streams.

        Returns:
            list[str]: List of all stream names in the StreamHandler.
        """
        stream_name_list = []
        for stream_name in self.stream_dict:
            stream_name_list.append(stream_name)
        return stream_name_list

    def get_stream(self, stream_name: str) -> ContinuousStream | BatchStream:
        """Returns a stream based on the name as a key.

        Args:
            stream_name (str): Name of stream to be returned.


        Returns:
            ContinuousStream | BatchStream: Returns the stream with the
                input key.
        """
        if not isinstance(stream_name, str):
            raise Exception(
                "Expected string as a stream name but got type : "
                + str(type(stream_name))
                + " instead"
            )

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

    def create_batch_stream(
        self, batch_stream_static_data: BatchStreamStaticData
    ) -> BatchStream:
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
                "Stream with name "
                + str(batch_stream.name)
                + " is already in stream dict of the stream handler"
            )
        self.stream_dict[batch_stream.name] = batch_stream
        return batch_stream
