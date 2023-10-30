import datetime
import pathlib
import pandas
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.stream_node_distributor import OrderDistributor
from ethos_penalps.data_classes import (
    Commodity,
    OrderCollection,
    ProcessChainIdentifier,
)
from ethos_penalps.process_nodes.sink import Sink
from ethos_penalps.stream import BatchStreamStaticData, BatchStream


def test_batch_order_distribution():
    test_commodity = Commodity(name="Test Commodity")
    n_order_generator = NOrderGenerator(
        mass_per_order=7,
        production_deadline=datetime.datetime(year=2023, month=1, day=1),
        number_of_orders=11,
        commodity=test_commodity,
    )
    sink_name = "Test Sink"

    start_process_step_name_1 = "Process Step 1"
    start_process_step_name_2 = "Process Step 2"

    order_collection = n_order_generator.create_n_order_collection()
    stream_handler = StreamHandler()
    stream_1 = stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=start_process_step_name_1,
            end_process_step_name=sink_name,
            commodity=test_commodity,
            delay=datetime.timedelta(minutes=2),
            maximum_batch_mass_value=0.13,
        )
    )
    stream_2 = stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name=start_process_step_name_2,
            end_process_step_name=sink_name,
            commodity=test_commodity,
            delay=datetime.timedelta(minutes=30),
            maximum_batch_mass_value=0.13,
        )
    )
    current_directory = pathlib.Path(__file__).parent.absolute()
    file_name = "continuous_test_data.csv"
    path_to_test_data = str(pathlib.PurePath(current_directory, file_name))
    production_order_data_frame = pandas.read_csv(
        filepath_or_buffer=path_to_test_data, parse_dates=["production_deadline"]
    )

    target_mass = production_order_data_frame.loc[:, "production_target"].sum()
    order_collection = OrderCollection(
        target_mass=target_mass,
        commodity=test_commodity,
        order_data_frame=production_order_data_frame,
    )
    order_distributor = OrderDistributor(
        stream_handler=stream_handler,
        node_name="Test Sink",
        production_order_collection=OrderCollection(
            target_mass=target_mass,
            commodity=test_commodity,
            order_data_frame=None,
        ),
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
        splitted_total_mass = splitted_order.order_collection_data_frame.loc[
            :, "production_target"
        ].sum()
        print("splitted total mass", splitted_total_mass)
    print("done")

    print(
        "Original total mass is: ",
        production_order_data_frame.loc[:, "production_target"].sum(),
    )


if __name__ == "__main__":
    test_batch_order_distribution()
