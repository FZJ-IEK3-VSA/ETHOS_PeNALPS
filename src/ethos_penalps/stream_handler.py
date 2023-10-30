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
        with open(file=path) as input_file:
            json_string = input_file.read()
        self.json_loads_streams(json_string=json_string)

    def create_continuous_stream(
        self,
        continuous_stream_static_data: ContinuousStreamStaticData,
    ) -> ContinuousStream:
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
        if new_stream.name in self.stream_dict and overwrite_stream is False:
            raise Exception(
                "Stream with name "
                + str(new_stream.name)
                + " is already in stream dict of the stream handler"
            )
        self.stream_dict[new_stream.name] = new_stream

    def get_list_of_all_stream_names_in_stream_handler(self) -> list[str]:
        """Gets the names of all streams stored in the StreamHandler instance. Includes inactive streams.

        :return: _description_
        :rtype: list[str]
        """
        stream_name_list = []
        for stream_name in self.stream_dict:
            stream_name_list.append(stream_name)
        return stream_name_list

    def get_stream(self, stream_name: str) -> ContinuousStream | BatchStream:
        """returns a stream based on the name as a key

        :param stream_name: [description]
        :type stream_name: str
        :return: [description]
        :rtype: Stream
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
        batch_stream = BatchStream(static_data=batch_stream_static_data)
        if batch_stream.name in self.stream_dict:
            raise Exception(
                "Stream with name "
                + str(batch_stream.name)
                + " is already in stream dict of the stream handler"
            )
        self.stream_dict[batch_stream.name] = batch_stream
        return batch_stream
