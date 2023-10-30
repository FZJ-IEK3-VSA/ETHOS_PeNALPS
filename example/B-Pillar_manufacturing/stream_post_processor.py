import pathlib
import json
from dataclasses import make_dataclass
import pandas
import jsonpickle
from ethos_penalps.post_processing.production_plan_post_processor import (
    StreamPostProcessor,
)
from ethos_penalps.stream import (
    BatchStreamProductionPlanEntry,
    BatchStream,
    BatchStreamStaticData,
)
from ethos_penalps.data_classes import Commodity
from ethos_penalps.utilities.general_functions import (
    create_dataclass_from_pandas_series,
)

path_to_current_file = pathlib.Path(__file__).absolute()
path_to_current_directory = path_to_current_file.parents[0]

STREAM_EXCEL_FILE = r"stream_data_frame.xlsx"
excel_file = pathlib.Path.joinpath(path_to_current_directory, STREAM_EXCEL_FILE)
stream_data_frame = pandas.read_excel(io=excel_file)


def create_batch_stream_state(
    data: pandas.DataFrame,
) -> list[BatchStreamProductionPlanEntry]:
    return [
        create_dataclass_from_pandas_series(row, BatchStreamProductionPlanEntry)
        for index, row in data.iterrows()
    ]


with open(
    r"C:\Programming\ethos_elpsi\example\B-Pillar_manufacturing\stream_handler.json"
) as data_file:
    data_loaded = json.load(data_file)


stream_handler = jsonpickle.decode(data_loaded)
asd = list_of_data_stream_entries = create_batch_stream_state(data=stream_data_frame)
print(list_of_data_stream_entries)
batch_stream_static_data = BatchStreamStaticData(
    start_process_step_name="Forming Quenching",
    end_process_step_name="Trimming",
    commodity=Commodity("Formed and quenched part"),
)
batch_stream = BatchStream(batch_stream_static_data=batch_stream_static_data)
stream_post_processor = StreamPostProcessor(
    stream=batch_stream, list_of_stream_states=list_of_data_stream_entries
)
