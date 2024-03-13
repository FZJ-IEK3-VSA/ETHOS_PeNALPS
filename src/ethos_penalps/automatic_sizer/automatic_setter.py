from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.stream import ContinuousStream, BatchStream


class ProcessStepSetter:
    def __init__(
        self, process_step: ProcessStep, stream_handler: StreamHandler
    ) -> None:
        self.process_step: ProcessStep = process_step
        self.stream_handler: StreamHandler = stream_handler

    def set_continuous_output_stream_max_rate(self, maximum_operation_rate):
        output_stream_name = self.process_step.get_output_stream_name()
        output_stream = self.stream_handler.get_stream(stream_name=output_stream_name)
        if isinstance(output_stream, ContinuousStream):
            output_stream.static_data.maximum_operation_rate = maximum_operation_rate
        else:
            raise Exception("Output stream is not continuous")

    def set_continuous_input_stream_max_rate(self, maximum_operation_rate):
        input_stream_name = self.process_step.get_input_stream_name()
        input_stream = self.stream_handler.get_stream(stream_name=input_stream_name)
        if isinstance(input_stream, ContinuousStream):
            input_stream.static_data.maximum_operation_rate = maximum_operation_rate
        else:
            raise Exception("Output stream is not continuous")

    def set_batch_output_stream_value(self, batch_mass):
        output_stream_name = self.process_step.get_output_stream_name()
        output_stream = self.stream_handler.get_stream(stream_name=output_stream_name)
        if isinstance(output_stream, BatchStream):
            output_stream.static_data.maximum_batch_mass_value = batch_mass
        else:
            raise Exception("Output stream is not batch")

    def set_batch_input_stream_value(self, batch_mass):
        input_stream_name = self.process_step.get_input_stream_name()
        input_stream = self.stream_handler.get_stream(stream_name=input_stream_name)
        if isinstance(input_stream, BatchStream):
            input_stream.static_data.maximum_batch_mass_value = batch_mass
        else:
            raise Exception("Output stream is not batch")
