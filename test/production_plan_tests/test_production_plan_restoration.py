from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.load_profile_calculator import LoadProfileHandlerSimulation
import pathlib


def test_load_production_plan():
    production_plan = ProductionPlan(
        load_profile_handler=LoadProfileHandlerSimulation()
    )
    parent_directory = pathlib.Path(__file__).parent.parent.absolute()
    case_folder_name = r"cases"
    case_1_name = r"case_1"
    stream_dict_file_name = r"stream_plan.db"
    process_state_dict_file_name = r"process_states.db"
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
    production_plan.restore_stream_results_from_sqlite(
        path_to_database=path_to_stream_dict_db
    )
    production_plan.restore_process_step_results_from_sqlite(
        path_to_database=path_to_process_state_dict_db
    )
