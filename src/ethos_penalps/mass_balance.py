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

    """A mass balance realizes three functions.
    - Connection of input and output streams.
    - Integration of storage for mass
    - Conversion of commodities
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
        input_mass = output_mass / self.input_to_output_conversion_factor
        return input_mass

    def convert_input_to_output_mass(
        self, input_mass: numbers.Number
    ) -> numbers.Number:
        output_mass = input_mass * self.input_to_output_conversion_factor
        return output_mass

    def determine_required_input_rate(
        self,
        output_stream_state: ContinuousStreamState,
        input_to_output_conversion_factor: numbers.Number,
    ):
        input_stream_operation_rate = (
            output_stream_state.current_operation_rate
            / input_to_output_conversion_factor
        )
        return input_stream_operation_rate

    def reevaluate_storage_level_according_to_adapted_input_stream(
        self,
    ) -> BatchStreamState | ContinuousStreamState:
        state_data = (
            self.state_data_container.get_validated_or_post_production_state_data()
        )
        adapted_input_stream_state = state_data.current_input_stream_state
        return adapted_input_stream_state

    def create_storage(
        self,
        current_storage_level: numbers.Number = 0,
        minimum_storage_level_at_start_time_of_production_branch: numbers.Number = 0,
        maximum_storage_level_at_start_time_of_production_branch: numbers.Number
        | None = None,
    ) -> Storage:
        """Each process step requires a storage currently.
        Currently storage level must be 0 at start

        :return: _description_
        :rtype: _type_
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
        self.main_input_stream_name = input_stream_name

    def add_main_output_stream_name(self, output_stream_name: str):
        self.main_output_stream_name = output_stream_name

    def get_input_stream_name(self) -> str:
        return self.main_input_stream_name

    def get_output_stream_name(self) -> str:
        return self.main_output_stream_name

    def check_input_and_output_stream_mass_balance(self):
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

    def determine_missing_mass_for_output_stream(self):
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

    def check_if_production_branch_is_fulfilled(self):
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

    def check_if_output_stream_can_be_supplied_directly_from_storage(self):
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
