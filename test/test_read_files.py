import datetime
import json
import pathlib

from ethos_penalps.data_classes import Commodity, LoadType
from ethos_penalps.load_profile_calculator import LoadProfileHandlerSimulation
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamStaticData,
    ContinuousStream,
    ContinuousStreamStaticData,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.own_object_json_encoding_decoding import (
    MyDecoder,
    MyEncoder,
)


def test_read_files():
    production_plan = ProductionPlan(
        load_profile_handler=LoadProfileHandlerSimulation()
    )
    parent_directory = pathlib.Path(__file__).parent.absolute()
    case_folder_name = r"cases"
    case_1_name = r"case_1"
    stream_dict_file_name = r"stream_plan.db"
    process_state_dict_file_name = r"process_states.db"
    stream_handler_json_file_name = r"combined_stream_handler.json"
    path_to_stream_dict_db = str(
        pathlib.PurePath(
            parent_directory, case_folder_name, case_1_name, stream_dict_file_name
        )
    )
    path_to_process_state_dict_db = str(
        pathlib.PurePath(
            parent_directory,
            case_folder_name,
            case_1_name,
            process_state_dict_file_name,
        )
    )
    path_to_stream_handler_json = str(
        pathlib.PurePath(
            parent_directory,
            case_folder_name,
            case_1_name,
            stream_handler_json_file_name,
        )
    )
    production_plan.restore_stream_results_from_sqlite(
        path_to_database=path_to_stream_dict_db
    )
    production_plan.restore_process_step_results_from_sqlite(
        path_to_database=path_to_process_state_dict_db
    )

    stream_handler = StreamHandler()
    time_data = TimeData()
    stream_handler.json_load_streams(path=path_to_stream_handler_json)
