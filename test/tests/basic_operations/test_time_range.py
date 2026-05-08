import datetime

import datetimerange
import pandas

from ethos_penalps.data_classes import Commodity
from ethos_penalps.simulation_data.container_simulation_data import (
    ProductionProcessStateContainer,
)
from ethos_penalps.storage import Storage, TimeRangesHandler
from ethos_penalps.stream import (
    BatchStreamState,
)
from ethos_penalps.testing.stream.stream_test_case import (
    make_batch_stream,
    make_continuous_stream,
)
from ethos_penalps.time_data import TimeData


def test_time_range():
    start_time = datetime.datetime(year=2022, month=2, day=1)
    end_time = datetime.datetime(year=2022, month=2, day=2)
    batch_stream_state_1 = BatchStreamState(
        name="Test name",
        start_time=start_time,
        end_time=end_time,
        date_time_range=datetimerange.DateTimeRange(start_datetime=start_time, end_datetime=end_time),
        batch_mass_value=200,
    )

    start_time = datetime.datetime(year=2022, month=2, day=2)
    end_time = datetime.datetime(year=2022, month=2, day=3)
    batch_stream_state_2 = BatchStreamState(
        name="Test name",
        start_time=start_time,
        end_time=end_time,
        date_time_range=datetimerange.DateTimeRange(start_datetime=start_time, end_datetime=end_time),
        batch_mass_value=200,
    )
    time_ranges_handler = TimeRangesHandler()
    time_ranges_handler.add_continuous_time_point(time_point=10)
    time_ranges_handler.add_continuous_time_point(time_point=20)
    time_ranges_handler.add_batch_input_state(batch_state=batch_stream_state_1)
    time_ranges_handler.add_batch_output_state(batch_state=batch_stream_state_2)
    time_ranges_list = time_ranges_handler.get_time_ranges_list_from_start_to_end()
    print(time_ranges_list)


def test_time_range_2():
    cont_setup = make_continuous_stream(
        maximum_operation_rate=float("inf"),
        start_process_step_name="Process Step Name 1",
        end_process_step_name="Process Step Name 2",
    )
    continuous_stream = cont_setup.stream
    commodity = cont_setup.commodity

    batch_setup = make_batch_stream(
        maximum_batch_mass_value=300,
        delay=datetime.timedelta(days=0.5),
        start_process_step_name="Process Step Name 2",
        end_process_step_name="Process Step Name 3",
        commodity_name=commodity.name,
        stream_handler=cont_setup.stream_handler,
    )
    batch_stream = batch_setup.stream
    stream_handler = cont_setup.stream_handler

    list_input_stream_states = [
        continuous_stream.create_stream_state_for_commodity_amount(
            end_time=datetime.datetime(year=2022, month=1, day=28, hour=0),
            commodity_amount=300,
            operation_rate=15,
        )
    ]
    list_input_stream_states.append(
        continuous_stream.create_stream_state_for_commodity_amount(
            end_time=datetime.datetime(year=2022, month=1, day=29, hour=0),
            commodity_amount=300,
            operation_rate=15,
        )
    )
    print(pandas.DataFrame(list_input_stream_states).loc[:, ["start_time", "end_time"]])

    list_of_output_stream_states = [
        batch_stream.create_batch_state(
            end_time=datetime.datetime(year=2022, month=2, day=2, hour=0),
            batch_mass_value=200,
        )
    ]
    list_of_output_stream_states.append(
        batch_stream.create_batch_state(
            end_time=datetime.datetime(year=2022, month=2, day=4, hour=0),
            batch_mass_value=200,
        )
    )
    print(pandas.DataFrame(list_of_output_stream_states).loc[:, ["start_time", "end_time"]])
    storage = Storage(
        process_step_name="Process Step Name 2",
        name="Test Storage",
        commodity=commodity,
        stream_handler=stream_handler,
        input_stream_name=continuous_stream.name,
        output_stream_name=batch_stream.name,
        time_data=TimeData(),
        input_to_output_conversion_factor=1,
        state_data_container=ProductionProcessStateContainer(),
    )
    time_ranges_handler = storage.create_time_ranges_handler(
        input_stream_state_list=list_input_stream_states,
        output_stream_state_list=list_of_output_stream_states,
    )
    list_of_time_ranges = time_ranges_handler.get_time_ranges_list_from_start_to_end_datetime()
    print(pandas.DataFrame(list_of_time_ranges))


if __name__ == "__main__":
    test_time_range_2()
