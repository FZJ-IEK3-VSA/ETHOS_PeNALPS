from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.stream import BatchStream, ContinuousStream
from ethos_penalps.stream_handler import StreamHandler


class ProcessStepSetter:
    """This class is used to set capacity related parameters of the ProcessStep
    in an automated way using a sensitivity analysis or an optimization e.g.
    """

    def __init__(
        self, process_step: ProcessStep, stream_handler: StreamHandler
    ) -> None:
        """

        Args:
            process_step (ProcessStep): The ProcessStep whose parameters should
                be adjusted.
            stream_handler (StreamHandler): The StreamHandler that contains the
                input and output stream of the ProcessStep.
        """
        self.process_step: ProcessStep = process_step
        self.stream_handler: StreamHandler = stream_handler

    def set_continuous_input_stream_max_rate(self, maximum_operation_rate):
        """Sets the operation rate of the continuous input stream.

        Args:
            maximum_operation_rate (_type_): New value for the maximum operation
                rate of the input stream.

        Raises:
            Exception: Raises an error if the input stream is not continuous.
        """
        input_stream_name = self.process_step.get_input_stream_name()
        input_stream = self.stream_handler.get_stream(stream_name=input_stream_name)
        if isinstance(input_stream, ContinuousStream):
            input_stream.static_data.maximum_operation_rate = maximum_operation_rate
        else:
            raise Exception("Output stream is not continuous")

    def set_continuous_output_stream_max_rate(self, maximum_operation_rate: float):
        """Sets the operation rate of the continuous output stream.

        Args:
            maximum_operation_rate (float): New value for the maximum operation
                rate of the output stream.

        Raises:
            Exception: Raises an error if the output stream is not continuous.
        """
        output_stream_name = self.process_step.get_output_stream_name()
        output_stream = self.stream_handler.get_stream(stream_name=output_stream_name)
        if isinstance(output_stream, ContinuousStream):
            output_stream.static_data.maximum_operation_rate = maximum_operation_rate
        else:
            raise Exception("Output stream is not continuous")

    def set_batch_input_stream_value(self, batch_mass: float):
        """Sets the maximum batch mass of the input stream of the ProcessStep.

        Args:
            batch_mass (float): Value for the new maximum batch size for the
                input stream of the ProcessStep.

        Raises:
            Exception: Raises an error if the input stream is not a BatchStream.
        """
        input_stream_name = self.process_step.get_input_stream_name()
        input_stream = self.stream_handler.get_stream(stream_name=input_stream_name)
        if isinstance(input_stream, BatchStream):
            input_stream.static_data.maximum_batch_mass_value = batch_mass
        else:
            raise Exception("Output stream is not batch")

    def set_batch_output_stream_value(self, batch_mass: float):
        """Sets the maximum batch mass of the output stream of the ProcessStep.

        Args:
            batch_mass (float): Value for the new maximum batch size for the
                output stream of the ProcessStep.

        Raises:
            Exception: Raises an error if the output stream is not a BatchStream.
        """
        output_stream_name = self.process_step.get_output_stream_name()
        output_stream = self.stream_handler.get_stream(stream_name=output_stream_name)
        if isinstance(output_stream, BatchStream):
            output_stream.static_data.maximum_batch_mass_value = batch_mass
        else:
            raise Exception("Output stream is not batch")
