import datetime

from ethos_penalps.data_classes import Commodity
from ethos_penalps.load_profile_calculator import LoadProfileHandlerSimulation
from ethos_penalps.mass_balance import MassBalance
from ethos_penalps.simulation_data.container_simulation_data import (
    CurrentProductionStateData,
    PostProductionStateData,
    PreProductionStateData,
    ProductionProcessStateContainer,
    UninitializedCurrentStateData,
)
from ethos_penalps.storage import Storage
from ethos_penalps.stream import BatchStreamState, ContinuousStreamState
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData


class ProcessStepData:
    def __init__(
        self,
        process_step_name: str,
        stream_handler: StreamHandler,
        time_data: TimeData,
        load_profile_handler: LoadProfileHandlerSimulation,
    ) -> None:
        self.process_step_name: str = process_step_name
        self.stream_handler: StreamHandler = stream_handler
        self.time_data: TimeData = time_data
        self.state_data_container: ProductionProcessStateContainer = (
            ProductionProcessStateContainer()
        )
        self.main_mass_balance: MassBalance
        self.load_profile_handler: LoadProfileHandlerSimulation = load_profile_handler

    def restore_time_data(self, new_time_data: TimeData):
        self.time_data.last_idle_time = new_time_data.last_idle_time
        self.time_data.last_process_state_switch_time = (
            new_time_data.last_process_state_switch_time
        )
        self.time_data.next_process_state_switch_time = (
            new_time_data.next_process_state_switch_time
        )
        if hasattr(new_time_data, "next_stream_end_time"):
            self.time_data.next_stream_end_time = new_time_data.next_stream_end_time
        else:
            if hasattr(self.time_data, "next_stream_end_time"):
                del self.time_data.next_stream_end_time

        self.time_data.storage_last_update_time = new_time_data.storage_last_update_time

    def validate_input_stream(self):
        # # Input stream must be added to storage level before it is shifted to validated stream list
        # self.main_mass_balance.storage.add_validated_input_stream_to_storage_level()
        # Shift input stream to validated stream list
        self.state_data_container.validate_input_stream()
