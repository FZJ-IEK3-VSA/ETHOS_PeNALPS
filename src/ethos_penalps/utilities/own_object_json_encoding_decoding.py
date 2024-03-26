import datetime
import json


from ethos_penalps.data_classes import Commodity
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamStaticData,
    ContinuousStream,
    ContinuousStreamStaticData,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.utilities.units import Units

"""This module contains classes that provided encoding and decoding capabilities for various 
objects of ETHOS.PeNALPS
"""


class ExtendedEncoder(json.JSONEncoder):
    def default(self, obj):
        name = type(obj).__name__
        try:
            encoder = getattr(self, f"encode_{name}")
        except AttributeError:
            super().default(obj)
        else:
            encoded = encoder(obj)
            encoded["__extended_json_type__"] = name
            return encoded


class ExtendedDecoder(json.JSONDecoder):
    def __init__(self, **kwargs):
        kwargs["object_hook"] = self.object_hook
        super().__init__(**kwargs)

    def object_hook(self, obj):
        try:
            name = obj["__extended_json_type__"]
            decoder = getattr(self, f"decode_{name}")
        except (KeyError, AttributeError):
            return obj
        else:
            return decoder(obj)


class MyEncoder(ExtendedEncoder):
    def encode_BatchStream(self, batch_stream: BatchStream) -> dict:
        return {
            "static_data": batch_stream.static_data.to_json(),
        }

    def encode_ContinuousStream(self, continuous_stream: ContinuousStream) -> dict:
        return {
            "static_data": continuous_stream.static_data.to_json(),
        }

    def encode_StreamHandler(self, stream_handler: StreamHandler) -> dict:
        output_dict = {}
        for stream_name, stream in stream_handler.stream_dict.items():
            if isinstance(stream, ContinuousStream):
                encoded_stream = self.encode_ContinuousStream(continuous_stream=stream)
            elif isinstance(stream, BatchStream):
                encoded_stream = self.encode_BatchStream(batch_stream=stream)
            output_dict[stream_name] = encoded_stream
        return output_dict


class MyDecoder(ExtendedDecoder):
    def decode_BatchStream(self, batch_stream_dictionary: dict) -> BatchStream:
        static_data_dictionary = json.loads(batch_stream_dictionary["static_data"])
        mass_unit_dict = json.loads(static_data_dictionary["mass_unit"])
        return BatchStream(
            batch_stream_static_data=BatchStreamStaticData(
                start_process_step_name=static_data_dictionary[
                    "start_process_step_name"
                ],
                end_process_step_name=static_data_dictionary["end_process_step_name"],
                commodity=Commodity(name=static_data_dictionary["commodity"]["name"]),
                delay=datetime.timedelta(seconds=static_data_dictionary["delay"]),
                minimum_batch_mass_value=static_data_dictionary[
                    "minimum_batch_mass_value"
                ],
                maximum_batch_mass_value=static_data_dictionary[
                    "maximum_batch_mass_value"
                ],
                mass_unit=Units.get_unit(mass_unit_dict["unit"]),
                name_to_display=static_data_dictionary["name_to_display"],
            )
        )

    def decode_ContinuousStream(
        self, continuous_stream_dictionary: dict
    ) -> ContinuousStream:
        static_data_dictionary = json.loads(continuous_stream_dictionary["static_data"])
        mass_unit_dict = json.loads(static_data_dictionary["mass_unit"])

        return ContinuousStream(
            continuous_stream_static_data=ContinuousStreamStaticData(
                start_process_step_name=static_data_dictionary[
                    "start_process_step_name"
                ],
                end_process_step_name=static_data_dictionary["end_process_step_name"],
                commodity=Commodity(name=static_data_dictionary["commodity"]["name"]),
                mass_unit=Units.get_unit(mass_unit_dict["unit"]),
                name_to_display=static_data_dictionary["name_to_display"],
                minimum_operation_rate=static_data_dictionary["minimum_operation_rate"],
                maximum_operation_rate=static_data_dictionary["maximum_operation_rate"],
                time_unit=datetime.timedelta(
                    seconds=static_data_dictionary["time_unit"]
                ),
            )
        )

    def decode_StreamHandler(self, stream_handler_dict: dict) -> StreamHandler:
        output_stream_handler = StreamHandler()

        for stream_name, stream_static_data_dict_str in stream_handler_dict.items():
            if stream_name == "__extended_json_type__":
                pass
            else:
                stream_static_data_dict = json.loads(
                    stream_static_data_dict_str["static_data"]
                )

                if stream_static_data_dict["stream_type"] == "ContinuousStream":
                    static_data = ContinuousStreamStaticData.from_dict(
                        stream_static_data_dict
                    )
                    decoded_stream = ContinuousStream(static_data=static_data)
                elif stream_static_data_dict["stream_type"] == "BatchStream":
                    static_data = BatchStreamStaticData.from_dict(
                        stream_static_data_dict
                    )
                    decoded_stream = BatchStream(
                        continuous_stream_static_data=static_data
                    )

                output_stream_handler.add_stream(new_stream=decoded_stream)
        return output_stream_handler
