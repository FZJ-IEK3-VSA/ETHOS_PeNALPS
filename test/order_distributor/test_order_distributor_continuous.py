import datetime
import pathlib

import pandas
from ethos_penalps.data_classes import (
    Commodity,
    OrderCollection,
    ProcessChainIdentifier,
)
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamStaticData,
    ContinuousStreamStaticData,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.stream_node_distributor import OrderDistributor

test_commodity = Commodity(name="Test Commodity")
n_order_generator = NOrderGenerator(
    mass_per_order=50,
    production_deadline=datetime.datetime(year=2023, month=1, day=1),
    number_of_orders=5,
    commodity=test_commodity,
    time_span_between_order=datetime.timedelta(minutes=60),
)
sink_name = "Test Sink"


start_process_step_name_1 = "Process Step 1"
start_process_step_name_2 = "Process Step 2"

order_collection = n_order_generator.create_n_order_collection()
stream_handler = StreamHandler()
stream_1 = stream_handler.create_continuous_stream(
    continuous_stream_static_data=ContinuousStreamStaticData(
        start_process_step_name=start_process_step_name_1,
        end_process_step_name=sink_name,
        commodity=test_commodity,
        maximum_operation_rate=50,
    )
)
stream_2 = stream_handler.create_continuous_stream(
    continuous_stream_static_data=ContinuousStreamStaticData(
        start_process_step_name=start_process_step_name_2,
        end_process_step_name=sink_name,
        commodity=test_commodity,
        maximum_operation_rate=50,
    )
)

current_directory = pathlib.Path(__file__).parent.absolute()
file_name = "continuous_test_data.csv"
path_to_test_data = str(pathlib.PurePath(current_directory, file_name))
production_order_data_frame = pandas.read_csv(
    filepath_or_buffer=path_to_test_data, parse_dates=["production_deadline"]
)
print(production_order_data_frame)
target_mass = production_order_data_frame.loc[:, "production_target"].sum()
order_collection = OrderCollection(
    target_mass=target_mass,
    commodity=test_commodity,
    order_data_frame=production_order_data_frame,
)
# order_collection = OrderCollection(target_mass=0, commodity=test_commodity)
order_distributor = OrderDistributor(
    stream_handler=stream_handler,
    node_name="Test Sink",
    production_order_collection=order_collection,
)
process_chain_identifier_1 = ProcessChainIdentifier(
    chain_number=1, chain_name="Chain 1"
)
process_chain_identifier_2 = ProcessChainIdentifier(
    chain_number=2, chain_name="Chain 2"
)
order_distributor.add_stream_name(
    stream_name=stream_1.name, process_chain_identifier=process_chain_identifier_1
)
order_distributor.add_stream_name(
    stream_name=stream_2.name, process_chain_identifier=process_chain_identifier_2
)
order_distributor.update_order_collection(new_order_collection=order_collection)
for splitted_order in order_distributor.dict_of_splitted_order.values():
    print(splitted_order)
print("done")
