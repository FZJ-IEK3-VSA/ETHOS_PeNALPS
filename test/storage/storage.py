import pathlib
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.load_profile_calculator import LoadProfileHandler
from ethos_penalps.storage import Storage
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.simulation_data.container_simulation_data import (
    ProductionProcessStateContainer,
    ValidatedPostProductionStateData,
)

production_plan = ProductionPlan(load_profile_handler=LoadProfileHandler())

current_working_directory = pathlib.Path(__file__).parent.absolute()

path_to_stream_handler_json = str(
    pathlib.PurePath(
        current_working_directory, "results", "combined_stream_handler.json"
    )
)
stream_handler = StreamHandler()
stream_handler.json_load_streams(path=path_to_stream_handler_json)
path_to_stream_data = str(
    pathlib.PurePath(current_working_directory, "results", "stream_plan.db")
)
path_to_process_states = str(
    pathlib.PurePath(current_working_directory, "results", "process_states.db")
)
storage_output_stream = stream_handler.stream_dict[
    "Open Hearth Furnace_Hot Part Sink_Hot Blank"
]
storage_commodity = storage_output_stream.static_data.commodity
production_plan.restore_stream_results_from_sqlite(path_to_database=path_to_stream_data)
production_plan.restore_process_step_results_from_sqlite(
    path_to_database=path_to_process_states
)
ValidatedPostProductionStateData(current_process_state_name="",current_output_stream_state=production_plan.stream_state_dict[])
time_data = TimeData()
storage = Storage(
    name="TestStorage",
    commodity=storage_commodity,
    stream_handler=stream_handler,
    output_stream_name="Open Hearth Furnace_Hot Part Sink_Hot Blank",
    input_stream_name="Coil Cutter_Open Hearth Furnace_Cold Blank",
    time_data=time_data,
    input_to_output_conversion_factor=1,
    state_data_container=ProductionProcessStateContainer(),
)
storage.create_all_storage_production_plan_entry()
print("")
