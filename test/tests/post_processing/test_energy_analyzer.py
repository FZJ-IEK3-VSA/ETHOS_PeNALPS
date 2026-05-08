import datetime
from dataclasses import dataclass

import pytest

from ethos_penalps.data_classes import (
    Commodity,
    FinalProductEnergyData,
    LoadType,
    OrderCollection,
    ProcessStateEnergyLoadData,
    ProcessStepProductEnergyLoadData,
    StreamLoadEnergyData,
    StreamProductEnergyLoadData,
)
from ethos_penalps.order_generator import NOrderGenerator
from ethos_penalps.organizational_agents.enterprise import Enterprise
from ethos_penalps.organizational_agents.network_level import NetworkLevel
from ethos_penalps.organizational_agents.process_chain import ProcessChain
from ethos_penalps.post_processing.product_energy_handler import (
    ConversionFactorHandler,
    CumulatedConversionFactorProcessChain,
    ProcessChainEnergyData,
    ProcessStateProductEnergyData,
    ProcessStepEnergyDataHandler,
    ProcessStepProductEnergyData,
    SpecificProductEnergyData,
    StreamProductEnergyData,
)
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamStaticData,
    ContinuousStream,
    ContinuousStreamStaticData,
    StreamEnergyData,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData

pytestmark = pytest.mark.energy_simulation


electricity_load_type = LoadType(name="Electricity")
natural_gas_load_type = LoadType(name="Natural Gas")


@dataclass
class SpecificEnergyTestData:
    load_type: LoadType
    specific_energy: float


@dataclass
class SpecificEnergyDataTestPair:
    input_type: SpecificEnergyTestData
    converted_type: SpecificEnergyTestData


@dataclass
class ProcessStateTestsData:
    process_state_name: str
    specific_energy_test_data_list: list[SpecificEnergyDataTestPair]


@dataclass
class StreamTestData:
    target_process_step_name: str
    start_process_step_name: str
    energy_data: list[SpecificEnergyDataTestPair]
    commodity: Commodity

    def __post_init__(self):
        batch_stream = BatchStream(
            static_data=BatchStreamStaticData(
                start_process_step_name=self.start_process_step_name,
                end_process_step_name=self.target_process_step_name,
                commodity=self.commodity,
                delay=datetime.timedelta(minutes=30),
            )
        )

        self.name: str = batch_stream.name


@dataclass
class ProcessStepTestData:
    process_step_name: str
    list_of_process_state_data: list[ProcessStateTestsData]
    conversion_factor: float
    input_stream_test_data: StreamTestData
    output_stream_test_data: StreamTestData
    commodity: Commodity


@dataclass
class SourceTestdata:
    source_name: str
    commodity: Commodity
    output_stream_name: str


@dataclass
class SinkTestdata:
    sink_name: str
    commodity: Commodity
    input_stream_name: str


@dataclass
class ProcessChainTestData:
    list_of_process_step_data: list[ProcessStepTestData]
    dict_product_energy_data: dict[str, SpecificProductEnergyData]
    sink_test_data: SinkTestdata
    source_test_data: SourceTestdata


test_process_state_1 = ProcessStateTestsData(
    process_state_name="Test State 1",
    specific_energy_test_data_list=[
        SpecificEnergyDataTestPair(
            input_type=SpecificEnergyTestData(load_type=electricity_load_type, specific_energy=100),
            converted_type=SpecificEnergyTestData(load_type=electricity_load_type, specific_energy=50),
        ),
        SpecificEnergyDataTestPair(
            input_type=SpecificEnergyTestData(load_type=natural_gas_load_type, specific_energy=150),
            converted_type=SpecificEnergyTestData(load_type=natural_gas_load_type, specific_energy=75),
        ),
    ],
)
test_process_state_2 = ProcessStateTestsData(
    process_state_name="Test State 2",
    specific_energy_test_data_list=[
        SpecificEnergyDataTestPair(
            input_type=SpecificEnergyTestData(load_type=electricity_load_type, specific_energy=300),
            converted_type=SpecificEnergyTestData(load_type=electricity_load_type, specific_energy=150),
        ),
        SpecificEnergyDataTestPair(
            input_type=SpecificEnergyTestData(load_type=natural_gas_load_type, specific_energy=2000),
            converted_type=SpecificEnergyTestData(load_type=natural_gas_load_type, specific_energy=1000),
        ),
    ],
)
test_process_state_3 = ProcessStateTestsData(
    process_state_name="Test State 3",
    specific_energy_test_data_list=[
        SpecificEnergyDataTestPair(
            input_type=SpecificEnergyTestData(load_type=electricity_load_type, specific_energy=3000),
            converted_type=SpecificEnergyTestData(load_type=electricity_load_type, specific_energy=1500),
        )
    ],
)
commodity_1 = Commodity(name="Commodity 1")
commodity_2 = Commodity(name="Commodity 2")
commodity_3 = Commodity(name="Commodity 3")

sink_name = "Test Sink"
source_name = "Test Source"

stream_test_data_downstream_to_sink = StreamTestData(
    target_process_step_name="Process Step Name Downstream",
    start_process_step_name=sink_name,
    energy_data=[
        SpecificEnergyDataTestPair(
            input_type=SpecificEnergyTestData(load_type=electricity_load_type, specific_energy=400),
            converted_type=SpecificEnergyTestData(load_type=electricity_load_type, specific_energy=400),
        )
    ],
    commodity=commodity_1,
)
stream_test_data_upstream_to_downstream = StreamTestData(
    target_process_step_name="Process Step Name Downstream",
    start_process_step_name="Process Step Name Upstream",
    energy_data=[
        SpecificEnergyDataTestPair(
            input_type=SpecificEnergyTestData(load_type=electricity_load_type, specific_energy=600),
            converted_type=SpecificEnergyTestData(load_type=electricity_load_type, specific_energy=300),
        )
    ],
    commodity=commodity_2,
)


@pytest.fixture
def process_step_test_data_downstream_fixture() -> ProcessStepTestData:
    process_step_test_data = ProcessStepTestData(
        process_step_name="Process Step Name Downstream",
        list_of_process_state_data=[
            test_process_state_1,
            test_process_state_2,
            test_process_state_3,
        ],
        conversion_factor=2,
        input_stream_test_data=stream_test_data_upstream_to_downstream,
        output_stream_test_data=stream_test_data_downstream_to_sink,
        commodity=commodity_1,
    )
    return process_step_test_data


test_process_state_4 = ProcessStateTestsData(
    process_state_name="Test State 4",
    specific_energy_test_data_list=[
        SpecificEnergyDataTestPair(
            input_type=SpecificEnergyTestData(load_type=electricity_load_type, specific_energy=3000),
            converted_type=SpecificEnergyTestData(load_type=electricity_load_type, specific_energy=750),
        )
    ],
)


stream_test_data_source_to_upstream = StreamTestData(
    target_process_step_name=source_name,
    start_process_step_name="Process Step Name Downstream",
    energy_data=[
        SpecificEnergyDataTestPair(
            input_type=SpecificEnergyTestData(load_type=electricity_load_type, specific_energy=800),
            converted_type=SpecificEnergyTestData(load_type=electricity_load_type, specific_energy=200),
        )
    ],
    commodity=commodity_3,
)


@pytest.fixture
def process_step_test_data_upstream_fixture() -> ProcessStepTestData:
    process_step_test_data = ProcessStepTestData(
        process_step_name="Process Step Name Upstream",
        list_of_process_state_data=[
            test_process_state_4,
        ],
        conversion_factor=2,
        input_stream_test_data=stream_test_data_source_to_upstream,
        output_stream_test_data=stream_test_data_upstream_to_downstream,
        commodity=commodity_2,
    )
    return process_step_test_data


@pytest.fixture
def process_chain_test_data_fixture(
    process_step_test_data_upstream_fixture, process_step_test_data_downstream_fixture
) -> ProcessChainTestData:
    process_chain_test_data = ProcessChainTestData(
        list_of_process_step_data=[
            process_step_test_data_downstream_fixture,
            process_step_test_data_upstream_fixture,
        ],
        dict_product_energy_data={
            electricity_load_type.uuid: SpecificProductEnergyData(
                load_type=electricity_load_type,
                specific_energy_data_demand=50 + 150 + 1500 + 400 + 300 + 750 + 200,
                raw_material_commodity=commodity_3,
                product_commodity=commodity_1,
                unit="MJ/metric_ton",
            ),
            natural_gas_load_type.uuid: SpecificProductEnergyData(
                load_type=natural_gas_load_type,
                specific_energy_data_demand=75 + 1000,
                raw_material_commodity=commodity_3,
                product_commodity=commodity_1,
                unit="MJ/metric_ton",
            ),
        },
        sink_test_data=SinkTestdata(
            sink_name=sink_name,
            commodity=commodity_1,
            input_stream_name=stream_test_data_downstream_to_sink.name,
        ),
        source_test_data=SourceTestdata(
            source_name=source_name,
            commodity=commodity_3,
            output_stream_name=stream_test_data_source_to_upstream.name,
        ),
    )

    return process_chain_test_data


@pytest.mark.parametrize(
    (
        "energy_value_1",
        "energy_value_2",
        "energy_product_value_1",
        "energy_product_value_2",
        "conversion_factor",
    ),
    [
        (50, 30, 25, 15, 2),
        (30, 75, 10, 25, 3),
    ],
)
def test_product_stream_energy_data(
    energy_value_1: float,
    energy_value_2: float,
    energy_product_value_1: float,
    energy_product_value_2: float,
    conversion_factor: float,
):
    time_data = TimeData()

    enterprise = Enterprise(time_data=time_data)
    network_level = enterprise.create_network_level()
    process_chain = network_level.create_process_chain(process_chain_name="Test Chain")

    output_stream_commodity = Commodity(name="Output Commodity")
    input_stream_commodity = Commodity(name="Input Commodity")
    stream = process_chain.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name="Start step",
            end_process_step_name="End process step",
            commodity=input_stream_commodity,
            delay=datetime.timedelta(minutes=39),
        )
    )

    load_type_1 = LoadType(name="Electricity")
    load_type_2 = LoadType(name="Natural Gas")
    stream.create_stream_energy_data(specific_energy_demand=energy_value_1, load_type=load_type_1)
    stream.create_stream_energy_data(specific_energy_demand=energy_value_2, load_type=load_type_2)

    cumulated_conversion_factor_process_chain = CumulatedConversionFactorProcessChain(
        chain_name=process_chain.process_chain_identifier.chain_name,
        product_commodity=output_stream_commodity,
        input_to_product_conversion_factor=conversion_factor,
        raw_material_commodity=input_stream_commodity,
    )
    stream_product_energy_data = StreamProductEnergyData(
        stream_energy_data=stream.stream_energy_data,
        cumulated_conversion_factor_process_chain=cumulated_conversion_factor_process_chain,
    )
    assert (
        stream_product_energy_data.dict_of_product_load_energy_data[load_type_1.uuid].specific_energy_demand
        == energy_product_value_1
    )
    assert (
        stream_product_energy_data.dict_of_product_load_energy_data[load_type_2.uuid].specific_energy_demand
        == energy_product_value_2
    )


def test_process_step_energy_data(
    process_step_test_data_downstream_fixture: ProcessStepTestData,
):
    time_data = TimeData()

    enterprise = Enterprise(time_data=time_data)
    network_level = enterprise.create_network_level()
    process_chain = network_level.create_process_chain(process_chain_name="Test Chain")

    process_step = process_chain.create_process_step(name="Process Step")

    output_stream_commodity = Commodity(name="Output Commodity")
    input_stream_commodity = Commodity(name="Input Commodity")
    stream = process_chain.stream_handler.create_batch_stream(
        batch_stream_static_data=BatchStreamStaticData(
            start_process_step_name="Start step",
            end_process_step_name="End process step",
            commodity=input_stream_commodity,
            delay=datetime.timedelta(minutes=39),
        )
    )

    process_step_energy_data_handler = ProcessStepEnergyDataHandler(
        process_step_name=process_step.name,
    )

    for current_process_state_test_data in process_step_test_data_downstream_fixture.list_of_process_state_data:
        process_state_inter = process_step.process_state_handler.create_intermediate_process_state(
            process_state_name=current_process_state_test_data.process_state_name
        )
        for current_energy_data in current_process_state_test_data.specific_energy_test_data_list:
            process_state_inter.create_process_state_energy_data_based_on_stream_mass(
                specific_energy_demand=current_energy_data.input_type.specific_energy,
                load_type=current_energy_data.input_type.load_type,
                stream=stream,
            )
        process_step_energy_data_handler.add_process_state_energy_data(
            process_state_name=process_state_inter.process_state_name,
            process_state_energy_data=process_state_inter.process_state_energy_data,
        )

    cumulated_conversion_factor_process_chain = CumulatedConversionFactorProcessChain(
        chain_name=process_chain.process_chain_identifier.chain_name,
        product_commodity=process_step_test_data_downstream_fixture.commodity,
        raw_material_commodity=input_stream_commodity,
        input_to_product_conversion_factor=1,
    )
    cumulated_conversion_factor_process_chain_updated = (
        cumulated_conversion_factor_process_chain.add_new_conversion_factor_from_process_step(
            process_step_name=process_step.name,
            conversion_factor=process_step_test_data_downstream_fixture.conversion_factor,
            new_raw_material_commodity=stream.static_data.commodity,
        )
    )

    process_step_product_energy_data = ProcessStepProductEnergyData(
        process_step_energy_data=process_step_energy_data_handler,
        cumulated_conversion_factor_process_chain=cumulated_conversion_factor_process_chain_updated,
    )
    for current_process_state_test_data in process_step_test_data_downstream_fixture.list_of_process_state_data:
        c = current_process_state_test_data.process_state_name
        for current_energy_test_data in current_process_state_test_data.specific_energy_test_data_list:
            current_load_type = current_energy_test_data.converted_type.load_type

            assert (
                process_step_product_energy_data.process_state_energy_load_data_dict[
                    current_process_state_test_data.process_state_name
                ]
                .dict_of_load_energy_data[current_load_type.uuid]
                .specific_energy_demand
                == current_energy_test_data.converted_type.specific_energy
            )
