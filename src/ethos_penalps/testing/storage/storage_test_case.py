"""Dataclasses and builders for storage test cases.

Provides everything needed to define, parameterise, and construct a storage
test case in memory:

- ``StorageTestCaseSpecification`` — serialisable parameter set for a case.
- ``StorageTestAssembly`` — a BaseStorage with connected streams.
- ``StorageTestCase`` — the fully built case (entries, stream groups, etc.).
"""

import datetime
from dataclasses import dataclass, field
from typing import Literal

import numpy
from dataclasses_json import DataClassJsonMixin, config

from ethos_penalps.data_classes import Commodity, StorageProductionPlanEntry
from ethos_penalps.storage import BaseStorage
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamState,
    ContinuousStream,
    ContinuousStreamState,
    StreamType,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.testing.stream.stream_group_test_case import (
    StreamGroupTestCase,
    StreamGroupTestCaseSpecification,
    build_stream_group_test_case,
    create_streams_from_group,
)
from ethos_penalps.testing.stream.stream_test_case import (
    BatchStreamTestCaseSpecification,
    ContinuousStreamTestCaseSpecification,
    StreamTestCase,
    StreamTestCaseSpecification,
)
from ethos_penalps.utilities.json_coding_functions import (
    json_datetime_deserialization_function,
    json_datetime_serialization_function,
)
from ethos_penalps.utilities.type_aliases import numbers_alias

# ---------------------------------------------------------------------------
# Storage setup
# ---------------------------------------------------------------------------


@dataclass
class StorageTestComponents:
    """Container for a BaseStorage and its connected streams."""

    base_storage: BaseStorage
    stream_handler: StreamHandler
    input_streams: list[ContinuousStream | BatchStream] = field(default_factory=list)
    output_streams: list[ContinuousStream | BatchStream] = field(default_factory=list)
    commodity: Commodity = field(default_factory=lambda: Commodity(name="Test Commodity"))


# ---------------------------------------------------------------------------
# Test case parameters (serialisable definition)
# ---------------------------------------------------------------------------


@dataclass
class StorageTestCaseSpecification(DataClassJsonMixin):
    """Complete parameter set for a storage test case.

    Input and output streams can have different types (continuous vs batch).
    All input streams must be the same type, and all output streams must be
    the same type, but input and output types can differ.

    Attributes:
        name: Unique case name, used as directory name.
        description: Human-readable description of what the case tests.
        start_time: Reference start time for the simulation.
        input_stream_group: Group specification for input streams.
        output_stream_group: Group specification for output streams.
        start_storage_level: Initial storage level, or ``"auto_offset"`` to compute
            the minimum level that keeps storage non-negative throughout the simulation.
        expect_full_mass_conservation: If True, total input mass equals total output
            mass (storage level returns to its start value).
        storage_entry_start_time: If set, only duration array segments starting at
            or after this time are used for auto_offset and entry creation.
        storage_entry_end_time: If set, only duration array segments ending at or
            before this time are used for auto_offset and entry creation.
    """

    name: str
    description: str
    start_time: datetime.datetime = field(
        metadata=config(
            encoder=json_datetime_serialization_function,
            decoder=json_datetime_deserialization_function,
        )
    )
    input_stream_group: StreamGroupTestCaseSpecification = field(default_factory=StreamGroupTestCaseSpecification)
    output_stream_group: StreamGroupTestCaseSpecification = field(default_factory=StreamGroupTestCaseSpecification)
    start_storage_level: float | Literal["auto_offset"] = 0
    expect_full_mass_conservation: bool = False
    storage_entry_start_time: datetime.datetime | None = field(
        default=None,
        metadata=config(
            encoder=json_datetime_serialization_function,
            decoder=json_datetime_deserialization_function,
        ),
    )
    storage_entry_end_time: datetime.datetime | None = field(
        default=None,
        metadata=config(
            encoder=json_datetime_serialization_function,
            decoder=json_datetime_deserialization_function,
        ),
    )

    @property
    def input_stream_type(self) -> StreamType:
        return self.input_stream_group.stream_type

    @property
    def output_stream_type(self) -> StreamType:
        return self.output_stream_group.stream_type


# ---------------------------------------------------------------------------
# Test case (built result)
# ---------------------------------------------------------------------------


@dataclass
class StorageTestCase:
    """Container for a loaded storage test case."""

    name: str
    parameters: StorageTestCaseSpecification
    storage_components: StorageTestComponents
    input_group: StreamGroupTestCase
    output_group: StreamGroupTestCase
    duration_array: numpy.ndarray
    start_storage_level: float
    entries: list[StorageProductionPlanEntry]

    @property
    def input_stream_states(self) -> list[ContinuousStreamState | BatchStreamState]:
        """Flat list of all input stream states."""
        return self.input_group.all_states

    @property
    def output_stream_states(self) -> list[ContinuousStreamState | BatchStreamState]:
        """Flat list of all output stream states."""
        return self.output_group.all_states

    def print_overview(self) -> None:
        """Print a concise one-line overview of the test case for quick validation."""
        params = self.parameters
        parts = [f"'{self.name}'"]
        parts.append(f"Entries: {len(self.entries)}")
        if params.input_stream_group.stream_specifications:
            parts.append(f"In: {len(self.input_group)} {params.input_stream_type.value}")
        else:
            parts.append("In: none")
        if params.output_stream_group.stream_specifications:
            parts.append(f"Out: {len(self.output_group)} {params.output_stream_type.value}")
        else:
            parts.append("Out: none")
        parts.append(f"Start level: {self.start_storage_level}")
        if self.entries:
            parts.append(f"Min level: {min(e.storage_level_at_start for e in self.entries)}")
            parts.append(f"End level: {self.entries[-1].storage_level_at_end}")
        print(", ".join(parts))

    def print_detailed_summary(self) -> None:
        """Print detailed metadata about the test case including stream properties and mass balance."""
        params = self.parameters
        print(f"Case:        {self.name}")
        print(f"Description: {params.description}")
        if params.input_stream_group.stream_specifications:
            print(f"Input stream type:  {params.input_stream_type.value}")
        else:
            print("Input stream type:  none")
        if params.output_stream_group.stream_specifications:
            print(f"Output stream type: {params.output_stream_type.value}")
        else:
            print("Output stream type: none")
        for direction, group_spec in [
            ("Input", params.input_stream_group),
            ("Output", params.output_stream_group),
        ]:
            for i, spec in enumerate(group_spec.stream_specifications):
                label = f"{direction} stream {i + 1}" if len(group_spec) > 1 else f"{direction} stream"
                if isinstance(spec, ContinuousStreamTestCaseSpecification):
                    print(
                        f"{label}: max_rate={spec.get_effective_max_operation_rate()} (min: {spec.min_operation_rate})"
                    )
                elif isinstance(spec, BatchStreamTestCaseSpecification):
                    print(
                        f"{label}: batch_mass=[{spec.min_batch_mass}, {spec.max_batch_mass}], "
                        f"delay={spec.batch_delay_seconds}s"
                    )
        print(f"Start storage level: {self.start_storage_level:.4f}")
        if params.start_storage_level == "auto_offset":
            print("  (computed via auto_offset)")
        if self.entries:
            print(f"Final storage level: {self.entries[-1].storage_level_at_end:.4f}")
            print(f"Time range:  {self.entries[0].start_time} to {self.entries[-1].end_time}")
            if params.storage_entry_start_time or params.storage_entry_end_time:
                print(f"Time bounds: start={params.storage_entry_start_time}, end={params.storage_entry_end_time}")
        print(f"Segments:    {len(self.entries)}")
        print(f"Mass conservation expected: {params.expect_full_mass_conservation}")
        print()

        total_input_mass = 0.0
        if self.input_group.stream_test_cases:
            print(f"Input streams ({len(self.input_group)}):")
            total_input_mass = self.input_group.print_group()
            print(f"  Total input mass: {total_input_mass:.4f}")
            print()

        total_output_mass = 0.0
        if self.output_group.stream_test_cases:
            print(f"Output streams ({len(self.output_group)}):")
            total_output_mass = self.output_group.print_group()
            print(f"  Total output mass: {total_output_mass:.4f}")
            print()

        net_mass = total_input_mass - total_output_mass
        print(f"Mass balance: input={total_input_mass:.4f} - output={total_output_mass:.4f} = net={net_mass:.4f}")
        print(
            f"Storage:      start={self.start_storage_level:.4f} + net={net_mass:.4f} = end={self.start_storage_level + net_mass:.4f}"
        )


# ---------------------------------------------------------------------------
# Build a test case from parameters
# ---------------------------------------------------------------------------


def build_case_from_parameters(
    parameters: StorageTestCaseSpecification | dict,
) -> StorageTestCase:
    """Build a StorageTestCase from StorageTestCaseSpecification or a dict.

    Args:
        parameters: Either a StorageTestCaseSpecification dataclass or a raw dict
            (for backward compatibility / loading from JSON).
    """
    if isinstance(parameters, dict):
        parameters = StorageTestCaseSpecification.from_dict(parameters)

    params = parameters

    # Create storage infrastructure
    commodity = Commodity(name="Test Commodity")
    stream_handler = StreamHandler()

    input_streams = create_streams_from_group(params.input_stream_group, stream_handler, commodity, "Upstream")
    output_streams = create_streams_from_group(params.output_stream_group, stream_handler, commodity, "Downstream")

    storage = BaseStorage(
        stream_handler=stream_handler,
        input_to_output_conversion_factor=1,
        commodity=commodity,
        process_step_name="Storage",
    )
    storage_components = StorageTestComponents(
        base_storage=storage,
        stream_handler=stream_handler,
        input_streams=input_streams,
        output_streams=output_streams,
        commodity=commodity,
    )

    # Build stream test cases
    input_group = build_stream_group_test_case(params.input_stream_group, input_streams, params.start_time)
    output_group = build_stream_group_test_case(params.output_stream_group, output_streams, params.start_time)

    # Create storage entries (skipped when states are empty, e.g. loaded from CSV)
    has_states = input_group.all_states or output_group.all_states
    if has_states:
        entries, duration_array, start_level = storage.create_storage_entries_from_streams(
            input_stream_state_list=input_group.all_states,
            output_stream_state_list=output_group.all_states,
            storage_level_at_start=params.start_storage_level,
            check_mass_conservation=True,
            start_time=params.storage_entry_start_time,
            end_time=params.storage_entry_end_time,
        )
    else:
        entries = []
        duration_array = numpy.array([])
        start_level = params.start_storage_level if isinstance(params.start_storage_level, float) else 0.0

    return StorageTestCase(
        name=params.name,
        parameters=params,
        storage_components=storage_components,
        input_group=input_group,
        output_group=output_group,
        duration_array=duration_array,
        start_storage_level=float(start_level),
        entries=entries,
    )
