import datetime
import numbers
from dataclasses import dataclass

from ethos_penalps.data_classes import Commodity
from ethos_penalps.simulation_data.container_simulation_data import (
    CurrentProductionStateData,
    PostProductionStateData,
    PreProductionStateData,
    ProductionProcessStateContainer,
    UninitializedCurrentStateData,
    ValidatedPostProductionStateData,
)
from ethos_penalps.storage import Storage
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamState,
    ContinuousStream,
    ContinuousStreamState,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.exceptions_and_warnings import UnexpectedDataType
from ethos_penalps.utilities.general_functions import check_if_date_1_is_before_date_2
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.units import Units

logger = PeNALPSLogger.get_logger_without_handler()


class MassBalance:
    standard_mass_unit = Units.mass_unit.__str__()
    standard_time_unit = datetime.timedelta(hours=1)

    """A mass balance provides the functionality,
        connects input and out streams of a Process Step,
        provides the necessary conversion steps between input
        and output stream and the interface to the storage
        of the ProcessStep.
    """

    def __init__(
        self,
        commodity: Commodity,
        stream_handler: StreamHandler,
        time_data: TimeData,
        input_to_output_conversion_factor: numbers.Number,
        main_output_stream: ContinuousStream | BatchStream,
        main_input_stream: ContinuousStream | BatchStream,
        optional_input_stream_list: list[ContinuousStream | BatchStream],
        state_data_container: ProductionProcessStateContainer,
        process_step_name: str,
    ) -> None:
        """

        Args:
            commodity (Commodity): The output commodity of the ProcessStep.
            stream_handler (StreamHandler): The container that contains the streams
                that are connected to the ProcessStep.
            time_data (TimeData): Store the time data that defines the state of
                the ProcessStep
            input_to_output_conversion_factor (numbers.Number): The conversion
                factor converts input mass into output mass.
            main_output_stream (ContinuousStream | BatchStream): The
                output stream of the mass balance.
            main_input_stream (ContinuousStream | BatchStream): The
                input stream of the mass balance.
            optional_input_stream_list (list[ContinuousStream  |  BatchStream]): This
                is a placeholder for further input streams. This functionality is still
                in development.
            state_data_container (ProductionProcessStateContainer): Contains the other
                simulation data that defines the state of the ProcessStep besides the
                time data.
            process_step_name (str): Name of the ProcessStep.
        """
        self.time_data: TimeData = time_data
        self.stream_handler: StreamHandler = stream_handler
        self.main_output_stream_name: str = main_output_stream.name
        self.main_input_stream_name: str = main_input_stream.name
        self.list_of_optional_input_stream_name: list[str] = []
        for optional_input_stream in optional_input_stream_list:
            self.list_of_optional_input_stream_name.append(optional_input_stream.name)
        self.commodity: Commodity = commodity
        self.storage: Storage
        self.input_to_output_conversion_factor: numbers.Number = (
            input_to_output_conversion_factor
        )
        self.state_data_container: ProductionProcessStateContainer = (
            state_data_container
        )
        self.process_step_name: str = process_step_name
        self.acceptable_error_limit_for_stream_balance = 0

        if not isinstance(main_output_stream, ContinuousStream | BatchStream):
            raise Exception(
                "Expected output stream of type ContinuousStream or BatchStream but got type: "
                + str(type(main_output_stream))
            )
        if not isinstance(main_input_stream, ContinuousStream | BatchStream):
            raise Exception(
                "Expected input stream of type ContinuousStream or BatchStream but got type: "
                + str(type(main_input_stream))
            )

    def set_continuous_operation_rate_for_parallel_input_and_output_stream_with_storage(
        self,
    ) -> ContinuousStreamState:
        """Creates input stream state that request mass parallel to the output stream
        state.

        Returns:
            ContinuousStreamState: input stream state that request mass parallel to the output stream
                state.
        """
        state_data = (
            self.state_data_container.get_validated_pre_or_post_production_state()
        )
        output_stream_state = state_data.current_output_stream_state
        output_stream_mass_output_commodity = (
            self.get_output_stream_mass_without_storage()
        )
        input_stream = self.stream_handler.get_stream(
            stream_name=self.main_input_stream_name
        )
        required_input_stream_rate = self.determine_required_input_rate(
            output_stream_state=output_stream_state,
            input_to_output_conversion_factor=self.input_to_output_conversion_factor,
        )
        required_rate_can_be_set = (
            input_stream.check_if_operation_rate_is_within_boundaries(
                operation_rate_to_check=required_input_stream_rate
            )
        )
        next_stream_end_time = self.time_data.get_next_stream_end_time()
        if isinstance(input_stream, ContinuousStream):
            if required_rate_can_be_set is True:
                logger.debug("The required input rate can be set directly")

                input_stream_state = (
                    input_stream.create_stream_state_for_commodity_amount(
                        commodity_amount=output_stream_mass_output_commodity,
                        operation_rate=required_input_stream_rate,
                        end_time=next_stream_end_time,
                    )
                )

            elif required_rate_can_be_set is False:
                logger.debug(
                    "A storage is required to provide sufficient input material"
                )
                input_stream_state = (
                    input_stream.create_stream_state_for_commodity_amount(
                        commodity_amount=output_stream_mass_output_commodity,
                        end_time=next_stream_end_time,
                    )
                )
        else:
            raise UnexpectedDataType(
                current_data_type=input_stream, expected_data_type=ContinuousStream
            )
        logger.debug("The input stream state has been set to : %s", input_stream_state)
        if input_stream_state.start_time == input_stream_state.end_time:
            raise Exception("Got infinitesimal stream")
        return input_stream_state

    def set_batch_stream_for_parallel_input_and_output_with_storage(
        self,
    ) -> BatchStreamState:
        """Tries to set the input batch stream in parallel to the output stream
        state.

        Returns:
            BatchStreamState: Input batch stream that request mass in parallel to the
                output stream.
        """
        input_stream = self.stream_handler.get_stream(
            stream_name=self.main_input_stream_name
        )
        next_stream_end_time = self.time_data.get_next_stream_end_time()

        output_stream_mass_output_commodity = (
            self.determine_missing_mass_for_output_stream()
        )
        output_stream_mass_input_commodity = self.convert_output_to_input_mass(
            output_mass=output_stream_mass_output_commodity
        )
        if isinstance(input_stream, BatchStream):
            possible_batch_mass = input_stream.consider_maximum_batch_mass(
                target_batch_mass=output_stream_mass_input_commodity
            )
            input_stream_state = input_stream.create_batch_state(
                end_time=next_stream_end_time, batch_mass_value=possible_batch_mass
            )
        else:
            raise UnexpectedDataType(
                current_data_type=input_stream, expected_data_type=BatchStream
            )
        return input_stream_state

    def get_output_stream_mass_without_storage(self) -> numbers.Number:
        """Returns the mass of the output stream state neglecting
        the mass in the storage.

        Returns:
            numbers.Number: Mass of the output stream state.
        """
        state_data = (
            self.state_data_container.get_validated_pre_or_post_production_state()
        )
        output_stream_state = state_data.current_output_stream_state
        output_stream = self.stream_handler.get_stream(
            stream_name=self.main_output_stream_name
        )
        output_mass_output_commodity = output_stream.get_produced_amount(
            state=output_stream_state
        )
        return output_mass_output_commodity

    def set_continuous_input_stream_according_to_output_stream_with_storage(
        self,
        operation_rate: numbers.Number = float("inf"),
    ) -> ContinuousStreamState:
        """Creates an input stream state based on the provided operation rate
        that provides the mass for the requested input stream state.

        Args:
            operation_rate (numbers.Number, optional): The mass
                transfer rate of the output stream state. If set to infinity
                the input stream will operate in parallel to the
                output stream. Defaults to float("inf").

        Returns:
            ContinuousStreamState: Output stream state that operates at
                the operation rate provided. Tries to start at the start time
                of the input stream state.
        """
        # validated_input_stream_list_is_shorter_than_one = (
        #     self.state_data_container.check_if_validated_input_stream_list_is_shorter_than_1()
        # )
        output_mass_output_commodity = self.determine_missing_mass_for_output_stream(
            # include_output_stream_mass_in_balance=validated_input_stream_list_is_shorter_than_one
        )
        output_mass_input_commodity = self.convert_output_to_input_mass(
            output_mass=output_mass_output_commodity
        )
        input_stream = self.stream_handler.get_stream(
            stream_name=self.main_input_stream_name
        )
        stream_end_time = self.time_data.get_next_stream_end_time()
        if isinstance(input_stream, ContinuousStream):
            input_stream_state = input_stream.create_stream_state_for_commodity_amount(
                commodity_amount=output_mass_input_commodity,
                end_time=stream_end_time,
                operation_rate=operation_rate,
            )
        else:
            raise UnexpectedDataType(
                current_data_type=input_stream, expected_data_type=ContinuousStream
            )
        return input_stream_state

    def set_batch_input_stream_according_to_output_stream_with_storage(
        self,
    ) -> BatchStreamState:
        """Creates an input batch stream state that provides mass
        for the output stream state.

        Returns:
            BatchStreamState: Input batch stream state.
        """
        # output_stream_mass_is_neglected = (
        #     self.state_data_container.check_if_validated_input_stream_list_is_shorter_than_1()
        # )
        output_mass_output_commodity = self.determine_missing_mass_for_output_stream(
            # validated_input_stream_list_is_shorter_than_one=output_stream_mass_is_neglected
        )
        output_mass_input_commodity = self.convert_output_to_input_mass(
            output_mass=output_mass_output_commodity
        )
        input_stream: BatchStream = self.stream_handler.get_stream(
            stream_name=self.main_input_stream_name
        )
        next_stream_end_time = self.time_data.get_next_stream_end_time()
        if isinstance(input_stream, BatchStream):
            possible_batch_mass = input_stream.consider_maximum_batch_mass(
                target_batch_mass=output_mass_input_commodity
            )
            input_stream_state = input_stream.create_batch_state(
                end_time=next_stream_end_time,
                batch_mass_value=possible_batch_mass,
            )
        else:
            raise UnexpectedDataType(
                current_data_type=input_stream, expected_data_type=BatchStream
            )
        return input_stream_state

    def determine_next_stream_end_time_from_previous_input_streams(
        self,
    ) -> datetime.datetime:
        """Returns the the next stream end time based on the previous
        input stream state. This method is required when multiple
        input stream states are required.

        Returns:
            datetime.datetime: Next stream end time.
        """
        state_data = (
            self.state_data_container.get_validated_pre_or_post_production_state()
        )

        if type(state_data) is PostProductionStateData:
            input_stream_end_time = state_data.current_input_stream_state.end_time
        elif type(state_data) is ValidatedPostProductionStateData:
            last_input_stream_state = state_data.validated_input_stream_list[-1]
            input_stream_end_time = last_input_stream_state.end_time
        elif type(state_data) is PreProductionStateData:
            raise Exception(
                "Tried to get the stream start time from an input stream which does not exist"
            )
        else:
            raise Exception("Unexpected datatype")

        return input_stream_end_time

    def determine_next_stream_start_time_from_previous_input_streams(
        self,
    ) -> datetime.datetime:
        """Returns the the next stream start time based on the previous
        input stream state. This method is required when multiple
        input stream states are required.

        Returns:
            datetime.datetime: Next stream start time.
        """
        state_data = (
            self.state_data_container.get_validated_pre_or_post_production_state()
        )

        if type(state_data) is PostProductionStateData:
            input_stream_start_time = state_data.current_input_stream_state.start_time
        elif type(state_data) is ValidatedPostProductionStateData:
            last_input_stream_state = state_data.validated_input_stream_list[-1]
            input_stream_start_time = last_input_stream_state.start_time
        elif type(state_data) is PreProductionStateData:
            raise Exception(
                "Tried to get the stream start time from an input stream which does not exist"
            )
        else:
            raise Exception("Unexpected datatype")

        return input_stream_start_time

    def determine_required_batch_end_time_to_fulfill_storage(
        self,
    ) -> datetime.datetime:
        """Determines the required end time for a batch stream so that the
        output mass is available in time.

        Returns:
            datetime.datetime: Required end time of the input stream.
        """
        target_output_mass = self.get_output_stream_mass_without_storage()
        missing_output_mass_output_commodity = (
            self.storage.determine_missing_input_mass(
                target_output_mass=target_output_mass
            )
        )
        missing_output_mass_input_commodity = self.convert_output_to_input_mass(
            output_mass=missing_output_mass_output_commodity
        )
        input_stream = self.stream_handler.get_stream(
            stream_name=self.main_input_stream_name
        )
        output_stream = self.stream_handler.get_stream(
            stream_name=self.main_output_stream_name
        )
        if type(input_stream) is BatchStream:
            possible_batch_mass_input_commodity = (
                input_stream.consider_maximum_batch_mass(
                    target_batch_mass=missing_output_mass_input_commodity
                )
            )
        if type(output_stream) is ContinuousStream:
            state_data = (
                self.state_data_container.get_validated_pre_or_post_production_state()
            )
            if type(state_data) is PreProductionStateData:
                last_input_stream_end_time = (
                    state_data.current_output_stream_state.end_time
                )
            elif type(state_data) in (
                PostProductionStateData,
                ValidatedPostProductionStateData,
            ):
                last_input_stream_end_time = (
                    self.determine_next_stream_end_time_from_previous_input_streams()
                )
                last_input_stream_start_time = (
                    self.determine_next_stream_start_time_from_previous_input_streams()
                )
            else:
                raise UnexpectedDataType(
                    current_data_type=state_data,
                    expected_data_type=(
                        PreProductionStateData,
                        PostProductionStateData,
                        ValidatedPostProductionStateData,
                    ),
                )

            possible_batch_mass_output_commodity = self.convert_input_to_output_mass(
                input_mass=possible_batch_mass_input_commodity
            )
            last_part_of_output_stream_state = (
                output_stream.create_stream_state_for_commodity_amount(
                    end_time=last_input_stream_end_time,
                    commodity_amount=possible_batch_mass_output_commodity,
                )
            )
            if type(state_data) in (
                PostProductionStateData,
                ValidatedPostProductionStateData,
            ):
                # If a previous input stream exists check if the required input stream end time starts
                # before the last input stream ends.
                if check_if_date_1_is_before_date_2(
                    date_1=last_input_stream_start_time,
                    date_2=last_part_of_output_stream_state.start_time,
                ):
                    # If earlier input is required, set seamless new input stream
                    next_stream_end_time = last_input_stream_start_time
                else:
                    next_stream_end_time = last_part_of_output_stream_state.start_time
            else:
                next_stream_end_time = last_part_of_output_stream_state.start_time
        elif type(output_stream) is BatchStream:
            state_data = (
                self.state_data_container.get_validated_pre_or_post_production_state()
            )
            if type(state_data) is PreProductionStateData:
                last_stream_start_time = (
                    state_data.current_output_stream_state.start_time
                )
            elif type(state_data) in (
                PostProductionStateData,
                ValidatedPostProductionStateData,
            ):
                last_stream_start_time = (
                    self.determine_next_stream_end_time_from_previous_input_streams()
                )
            next_stream_end_time = last_stream_start_time
        else:
            raise Exception("Unexpected output stream type")

        return next_stream_end_time

    def convert_output_to_input_mass(
        self, output_mass: numbers.Number
    ) -> numbers.Number:
        """Converts output mass to input mass.

        Args:
            output_mass (numbers.Number): Output mass that should be converted.

        Returns:
            numbers.Number: Input mass value.
        """
        input_mass = output_mass / self.input_to_output_conversion_factor
        return input_mass

    def convert_input_to_output_mass(
        self, input_mass: numbers.Number
    ) -> numbers.Number:
        """Converts input to output mass.

        Args:
            input_mass (numbers.Number): Input mass that should be converted.

        Returns:
            numbers.Number: Output mass value.
        """
        output_mass = input_mass * self.input_to_output_conversion_factor
        return output_mass

    def determine_required_input_rate(
        self,
        output_stream_state: ContinuousStreamState,
        input_to_output_conversion_factor: numbers.Number,
    ) -> float:
        """Returns the required mass transfer rate for the input
        stream state based on the output stream state.

        Args:
            output_stream_state (ContinuousStreamState): The output stream
                state whose mass transfer rate should be matched.
            input_to_output_conversion_factor (numbers.Number): The conversion
                factor form input to output mass.

        Returns:
            float: The new operation rate for input stream.
        """

        input_stream_operation_rate = (
            output_stream_state.current_operation_rate
            / input_to_output_conversion_factor
        )
        return input_stream_operation_rate

    def reevaluate_storage_level_according_to_adapted_input_stream(
        self,
    ) -> BatchStreamState | ContinuousStreamState:
        """Adapts the storage level according to a changes stream state.

        Returns:
            BatchStreamState | ContinuousStreamState: Returns the input stream
                state that was used to adapt the storage level.
        """
        state_data = (
            self.state_data_container.get_validated_or_post_production_state_data()
        )
        adapted_input_stream_state = state_data.current_input_stream_state
        return adapted_input_stream_state

    def create_storage(
        self,
        current_storage_level: numbers.Number = 0,
        minimum_storage_level_at_start_time_of_production_branch: numbers.Number = 0,
        maximum_storage_level_at_start_time_of_production_branch: (
            numbers.Number | None
        ) = None,
    ) -> Storage:
        """The storage is used to track the required mass of the output stream state. Each Process Step
        requires a storage.

        Args:
            current_storage_level (numbers.Number, optional): The storage level at the start of the simulation
                . Defaults to 0.
            minimum_storage_level_at_start_time_of_production_branch (numbers.Number, optional): This is an
                experimental attribute that requires further development. It should provide the capability
                to change the request behavior so that a minimum storage level will always be available in the storage
                . Defaults to 0.
            maximum_storage_level_at_start_time_of_production_branch (numbers.Number  |  None, optional): This is an
                experimental attribute that requires further development. It should provide the capability
                to change the request behavior so that a maximum storage level will always be available in the storage
                . Defaults to 0. Defaults to None.

        Returns:
            Storage: The new created storage of the ProcessStep.
        """
        storage_name = self.commodity.name + " Storage"
        new_storage = Storage(
            name=storage_name,
            commodity=self.commodity,
            stream_handler=self.stream_handler,
            input_stream_name=self.main_input_stream_name,
            output_stream_name=self.main_output_stream_name,
            input_to_output_conversion_factor=self.input_to_output_conversion_factor,
            time_data=self.time_data,
            state_data_container=self.state_data_container,
            process_step_name=self.process_step_name,
            minimum_storage_level_at_start_time_of_production_branch=minimum_storage_level_at_start_time_of_production_branch,
            maximum_storage_level_at_start_time_of_production_branch=maximum_storage_level_at_start_time_of_production_branch,
        )

        self.state_data_container.initialization_data_collector.add_current_storage_level(
            current_storage_level=current_storage_level
        )
        self.storage = new_storage
        return new_storage

    def add_main_input_stream_name(self, input_stream_name: str):
        """Adds the input stream to the mass balance. This is required for
        the simulation to work.

        Args:
            input_stream_name (str): Name of the input stream of the ProcessStep.
        """
        self.main_input_stream_name = input_stream_name

    def add_main_output_stream_name(self, output_stream_name: str):
        """Adds the output stream to the mass balance. This is required for
        the simulation to work.

        Args:
            output_stream_name (str): Name of the output stream of the ProcessStep.
        """
        self.main_output_stream_name = output_stream_name

    def get_input_stream_name(self) -> str:
        """Returns the name of the input stream.

        Returns:
            str: Name of the input stream.
        """
        return self.main_input_stream_name

    def get_output_stream_name(self) -> str:
        """Returns the name of the output stream.

        Returns:
            str: Name of the output stream.
        """
        return self.main_output_stream_name

    def check_input_and_output_stream_mass_balance(self):
        """Checks if enough input stream mass has been provided
        to fulfill the output stream state.
        """
        logger.debug("Check if stream inputs and outputs fit the mass balance")

        missing_net_stream_mass = self.determine_missing_mass_for_output_stream()
        if (
            missing_net_stream_mass < self.acceptable_error_limit_for_stream_balance
            and missing_net_stream_mass
            > -self.acceptable_error_limit_for_stream_balance
        ):
            pass
        else:
            raise Exception(
                "Something went wrong with the current production branch. Missing mass is: "
                + str(missing_net_stream_mass)
            )

    def determine_missing_mass_for_output_stream(self) -> float:
        """Returns the missing input mass that is required
        to provide the output stream mass.

        Returns:
            float: Missing input mass that must be requested.
        """
        state_data = (
            self.state_data_container.get_validated_pre_or_post_production_state()
        )
        output_stream = self.stream_handler.get_stream(
            stream_name=state_data.current_output_stream_state.name
        )
        output_mass = output_stream.get_produced_amount(
            state=state_data.current_output_stream_state
        )

        if type(state_data) is (PreProductionStateData):
            validated_input_mass = 0
        else:
            input_stream = self.stream_handler.get_stream(
                stream_name=state_data.validated_input_stream_list[0].name
            )
            validated_input_mass = 0
            for input_stream_state in state_data.validated_input_stream_list:
                validated_input_mass = (
                    validated_input_mass
                    + input_stream.get_produced_amount(input_stream_state)
                )
        missing_net_stream_mass = output_mass - validated_input_mass
        logger.debug(
            "%s input mass misses to satisfy the mass balance",
            missing_net_stream_mass,
        )
        return missing_net_stream_mass

    def check_if_production_branch_is_fulfilled(self) -> bool:
        """Determines if further input stream states must be requested.

        Returns:
            bool: Returns True if no further input stream states must be requested.
        """
        self.determine_missing_mass_for_output_stream()
        missing_mass = self.determine_missing_mass_for_output_stream()
        error_limit = 0
        if missing_mass > 0:
            is_fulfilled = False
            logger.debug(
                "Further input streams are required to satisfy the output stream"
            )
        # elif missing_mass < error_limit and missing_mass > -error_limit:
        #     is_fulfilled = True
        #     logger.debug("The following stream satisfies the output stream")
        elif missing_mass == 0:
            is_fulfilled = True
            logger.debug("The following stream satisfies the output stream")
        else:
            raise Exception("Unexpected missing mass: " + str(missing_mass))
        return is_fulfilled

    def check_if_production_branch_is_fulfilled_with_over_production(
        self,
    ) -> bool:
        """Determines if further input stream states must be requested But allows
        that more input mass is available than required but the output stream state.

        Returns:
            bool: Returns True if no further input stream states must be requested.
        """
        maximum_storage_level_at_start_time_of_production_branch = (
            self.storage.maximum_storage_level_at_start_time_of_production_branch
        )
        if (
            self.storage.maximum_storage_level_at_start_time_of_production_branch
            is None
        ):
            raise Exception(
                "It is checked if the storage level can be supplied without requesting an input stream but no maximum storage level has been set in process step: "
                + self.process_step_name
            )
        state_data = self.state_data_container.get_validated_production_state_data()
        current_storage_level = state_data.current_storage_level
        available_mass_in_storage = (
            current_storage_level
            - self.storage.minimum_storage_level_at_start_time_of_production_branch
        )
        threshold_to_maximum_storage_level = (
            maximum_storage_level_at_start_time_of_production_branch
            - current_storage_level
        )
        if 0 >= threshold_to_maximum_storage_level:
            input_is_bigger_than_output = (
                self.determine_if_input_stream_is_bigger_than_output()
            )
            # if input_is_bigger_than_output is True:
            #     raise Exception("Storage level will increase endlessly")
            # The storage level decreases with further input streams due to back calculation. Thus it is required
            is_fulfilled = False
            logger.debug(
                "The current storage level is too high. Further input stream is required: %s",
                current_storage_level,
            )

        elif 0 >= available_mass_in_storage:
            input_is_bigger_than_output = (
                self.determine_if_input_stream_is_bigger_than_output()
            )
            # if input_is_bigger_than_output is False:
            #     raise Exception("Storage level will decrease endlessly")
            is_fulfilled = False
        elif (
            0 <= available_mass_in_storage
            and 0 <= threshold_to_maximum_storage_level
            # and current_storage_level
            # > -error_limit + minimum_storage_level_at_start_time_of_production_branch
        ):
            is_fulfilled = True
            logger.debug("The following stream satisfies the output stream")
        else:
            raise Exception(
                "Storage level has an Unexpected case: " + str(current_storage_level)
            )
        return is_fulfilled

    def check_if_output_stream_can_be_supplied_directly_from_storage(self) -> bool:
        """Returns True if the output stream state can be supplied directly from
        the internal storage without requesting further input mass.

        Returns:
            bool: Returns True if the output stream state can be supplied directly from
                the internal storage
        """

        # maximum_storage_level_at_start_time_of_production_branch - minimum_storage_level_at_start_time_of_production_branch
        # Difference must be at least as big as the output stream batch size
        state_data = (
            self.state_data_container.get_validated_pre_or_post_production_state()
        )
        state_data.current_storage_level
        output_stream_mass = self.get_output_stream_mass_without_storage()
        available_mass_in_storage_for_provision = (
            state_data.current_storage_level
            - self.storage.minimum_storage_level_at_start_time_of_production_branch
        )

        if available_mass_in_storage_for_provision >= output_stream_mass:
            output_mass_can_be_supplied_directly = True
        else:
            output_mass_can_be_supplied_directly = False
        return output_mass_can_be_supplied_directly

    def determine_if_input_stream_is_bigger_than_output(self) -> bool:
        """Determines if the input stream is bigger than the output.


        Returns:
            bool: Returns True if the input stream is bigger than the output
        """
        input_stream = self.stream_handler.get_stream(
            stream_name=self.main_input_stream_name
        )
        output_stream = self.stream_handler.get_stream(
            stream_name=self.main_output_stream_name
        )
        if type(input_stream) is BatchStream:
            input_max_batch_mass = input_stream.static_data.maximum_batch_mass_value
        else:
            raise Exception("Case not implemented")
        if isinstance(output_stream, BatchStream):
            output_max_batch_mass = output_stream.static_data.maximum_batch_mass_value
        else:
            raise Exception("Case not implemented")
        if input_max_batch_mass > output_max_batch_mass:
            input_is_bigger_than_output = True
        elif input_max_batch_mass < output_max_batch_mass:
            input_is_bigger_than_output = False
        else:
            raise Exception(
                "Request full batch size has been used on symmetric batch size"
            )
        return input_is_bigger_than_output
        # state_data=self.state_data_container.get_validated_pre_or_post_production_state()
        # output_stream=self.stream_handler.get_stream(stream_name=self.main_output_stream_name)
        # output_stream.get_produced_amount(state=state_data.current_output_stream_state)
