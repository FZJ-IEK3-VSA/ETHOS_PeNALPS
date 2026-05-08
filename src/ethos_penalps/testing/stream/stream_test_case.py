"""Dataclasses, factories, and builders for individual stream test cases.

Provides:
- Factory functions to create fully configured ContinuousStream / BatchStream
  objects with explicit static data.
- Helpers to build stream states from tuple specifications.
- Serialisable parameter dataclasses (``ContinuousStreamTestCaseSpecification``,
  ``BatchStreamTestCaseSpecification``) and their state-level counterparts.
- ``StreamTestCase`` — a stream paired with its states at runtime.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from dataclasses_json import DataClassJsonMixin, config

from ethos_penalps.data_classes import Commodity
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamState,
    BatchStreamStaticData,
    ContinuousStream,
    ContinuousStreamState,
    ContinuousStreamStaticData,
    StreamType,
)
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.utilities.type_aliases import numbers_alias

# ---------------------------------------------------------------------------
# Continuous stream factory
# ---------------------------------------------------------------------------


@dataclass
class ContinuousStreamTestComponents:
    """A fully configured ContinuousStream with its static data and handler."""

    stream: ContinuousStream
    static_data: ContinuousStreamStaticData
    stream_handler: StreamHandler
    commodity: Commodity


def make_continuous_stream(
    maximum_operation_rate: numbers_alias = 10,
    minimum_operation_rate: numbers_alias = 0,
    commodity_name: str = "Test Commodity",
    start_process_step_name: str = "Upstream",
    end_process_step_name: str = "Downstream",
    stream_handler: StreamHandler | None = None,
) -> ContinuousStreamTestComponents:
    """Create a fully configured ContinuousStream.

    Args:
        maximum_operation_rate: Maximum mass transfer rate.
        minimum_operation_rate: Minimum mass transfer rate.
        commodity_name: Name of the commodity.
        start_process_step_name: Source process step name.
        end_process_step_name: Destination process step name.
        stream_handler: Optional existing StreamHandler. A new one is created if None.

    Returns:
        ContinuousStreamTestComponents with the stream, static data, and handler.
    """
    commodity = Commodity(name=commodity_name)
    if stream_handler is None:
        stream_handler = StreamHandler()

    static_data = ContinuousStreamStaticData(
        start_process_step_name=start_process_step_name,
        end_process_step_name=end_process_step_name,
        commodity=commodity,
        maximum_operation_rate=maximum_operation_rate,
        minimum_operation_rate=minimum_operation_rate,
    )
    stream = stream_handler.create_continuous_stream(
        continuous_stream_static_data=static_data,
    )
    return ContinuousStreamTestComponents(
        stream=stream,
        static_data=static_data,
        stream_handler=stream_handler,
        commodity=commodity,
    )


def make_continuous_stream_states_from_tuples(
    stream: ContinuousStream,
    start: datetime.datetime,
    mass_rate_duration_gap_tuples: list[
        tuple[numbers_alias, numbers_alias, datetime.timedelta]
        | tuple[numbers_alias, numbers_alias, datetime.timedelta, datetime.timedelta]
    ],
) -> list[ContinuousStreamState]:
    """Create ContinuousStreamState entries from (mass, rate, duration[, gap]) tuples.

    States are placed sequentially. An optional gap after each state advances
    the time cursor without creating a stream state, allowing non-contiguous
    states within a single stream group.

    Args:
        stream: The ContinuousStream to create states for.
        start: Start time of the first entry.
        mass_rate_duration_gap_tuples: List of (commodity_amount, operation_rate,
            duration) or (commodity_amount, operation_rate, duration, gap_after) tuples.

    Returns:
        List of ContinuousStreamState in chronological order.
    """
    states: list[ContinuousStreamState] = []
    current_end = start
    for entry in mass_rate_duration_gap_tuples:
        mass, rate, duration = entry[0], entry[1], entry[2]
        gap = entry[3] if len(entry) > 3 else datetime.timedelta(0)
        current_end = current_end + duration
        state = stream.create_stream_state_for_commodity_amount(
            end_time=current_end,
            commodity_amount=mass,
            operation_rate=rate,
        )
        states.append(state)
        current_end = current_end + gap
    return states


# ---------------------------------------------------------------------------
# Batch stream factory
# ---------------------------------------------------------------------------


@dataclass
class BatchStreamTestComponents:
    """A fully configured BatchStream with its static data and handler."""

    stream: BatchStream
    static_data: BatchStreamStaticData
    stream_handler: StreamHandler
    commodity: Commodity


def make_batch_stream(
    maximum_batch_mass_value: numbers_alias = 100,
    minimum_batch_mass_value: numbers_alias = 0,
    delay: datetime.timedelta = datetime.timedelta(hours=1),
    commodity_name: str = "Test Commodity",
    start_process_step_name: str = "Upstream",
    end_process_step_name: str = "Downstream",
    stream_handler: StreamHandler | None = None,
) -> BatchStreamTestComponents:
    """Create a fully configured BatchStream.

    Args:
        maximum_batch_mass_value: Maximum batch mass.
        minimum_batch_mass_value: Minimum batch mass.
        delay: Time between start and end of each batch transfer.
        commodity_name: Name of the commodity.
        start_process_step_name: Source process step name.
        end_process_step_name: Destination process step name.
        stream_handler: Optional existing StreamHandler. A new one is created if None.

    Returns:
        BatchStreamTestComponents with the stream, static data, and handler.
    """
    commodity = Commodity(name=commodity_name)
    if stream_handler is None:
        stream_handler = StreamHandler()

    static_data = BatchStreamStaticData(
        start_process_step_name=start_process_step_name,
        end_process_step_name=end_process_step_name,
        commodity=commodity,
        maximum_batch_mass_value=maximum_batch_mass_value,
        minimum_batch_mass_value=minimum_batch_mass_value,
        delay=delay,
    )
    stream = stream_handler.create_batch_stream(
        batch_stream_static_data=static_data,
    )
    return BatchStreamTestComponents(
        stream=stream,
        static_data=static_data,
        stream_handler=stream_handler,
        commodity=commodity,
    )


def make_batch_stream_states_from_tuples(
    stream: BatchStream,
    start: datetime.datetime,
    mass_and_gap_tuples: list[tuple[numbers_alias, datetime.timedelta]],
) -> list[BatchStreamState]:
    """Create BatchStreamState entries from (mass, gap_after) tuples.

    Each batch ends at the current time, then a gap is added before the next batch.

    Args:
        stream: The BatchStream to create states for.
        start: End time of the first batch.
        mass_and_gap_tuples: List of (batch_mass, gap_after_batch) tuples.

    Returns:
        List of BatchStreamState in chronological order.
    """
    states: list[BatchStreamState] = []
    current_time = start
    for mass, gap in mass_and_gap_tuples:
        state = stream.create_batch_state(
            end_time=current_time,
            batch_mass_value=mass,
        )
        states.append(state)
        current_time: datetime.datetime = current_time + gap
    return states


# ---------------------------------------------------------------------------
# Continuous stream specification (serialisable parameters)
# ---------------------------------------------------------------------------


@dataclass
class ContinuousStreamStateParams(DataClassJsonMixin):
    """Parameters for a single continuous stream state.

    Attributes:
        mass: Total commodity mass transferred.
        rate: Operation rate in mass per hour.
        duration_seconds: Duration of the transfer in seconds.
        gap_after_seconds: Gap in seconds after this state before the next.
    """

    mass: float
    rate: float
    duration_seconds: float
    gap_after_seconds: float = 0


@dataclass
class ContinuousStreamTestCaseSpecification(DataClassJsonMixin):
    """Parameters for a group of continuous stream states from one stream.

    Attributes:
        states: List of continuous stream state parameters. May be empty when
            states are loaded separately from CSV.
        start_offset_seconds: Time offset in seconds from the case start_time
            for the first state in this group.
        max_operation_rate: Maximum operation rate for the stream. If None,
            defaults to the maximum rate across all states.
        min_operation_rate: Minimum operation rate for the stream.
    """

    states: list[ContinuousStreamStateParams] = field(default_factory=list)
    start_offset_seconds: float = 0
    max_operation_rate: float | None = None
    min_operation_rate: float = 0

    def get_effective_max_operation_rate(self) -> float:
        """Return max_operation_rate, or derive from the maximum state rate."""
        if self.max_operation_rate is not None:
            return self.max_operation_rate
        if not self.states:
            return 0
        return max(state.rate for state in self.states)

    @property
    def stream_type(self) -> StreamType:
        return StreamType.CONTINUOUS


# ---------------------------------------------------------------------------
# Batch stream specification (serialisable parameters)
# ---------------------------------------------------------------------------


@dataclass
class BatchStreamStateParams(DataClassJsonMixin):
    """Parameters for a single batch stream state.

    Attributes:
        mass: Batch mass transferred.
        gap_seconds: Gap in seconds after this batch before the next.
    """

    mass: float
    gap_seconds: float


@dataclass
class BatchStreamTestCaseSpecification(DataClassJsonMixin):
    """Parameters for a group of batch stream states from one stream.

    Attributes:
        states: List of batch stream state parameters. May be empty when
            states are loaded separately from CSV.
        start_offset_seconds: Time offset in seconds from the case start_time
            for the first state in this group.
        max_batch_mass: Maximum batch mass for this stream.
        min_batch_mass: Minimum batch mass for this stream.
        batch_delay_seconds: Delay between batch events in seconds.
    """

    states: list[BatchStreamStateParams] = field(default_factory=list)
    start_offset_seconds: float = 0
    max_batch_mass: float = 100
    min_batch_mass: float = 0
    batch_delay_seconds: float = 3600

    @property
    def stream_type(self) -> StreamType:
        return StreamType.BATCH


# ---------------------------------------------------------------------------
# Union type and serialization helpers
# ---------------------------------------------------------------------------

StreamTestCaseSpecification = ContinuousStreamTestCaseSpecification | BatchStreamTestCaseSpecification


def _encode_stream_specs(specs: list[StreamTestCaseSpecification]) -> list[dict]:
    """Serialize a list of StreamTestCaseSpecification, adding stream_type as discriminator."""
    result = []
    for s in specs:
        d = s.to_dict()
        d["stream_type"] = s.stream_type.value
        result.append(d)
    return result


def _decode_stream_specs(dicts: list[dict]) -> list[StreamTestCaseSpecification]:
    """Deserialize a list of StreamTestCaseSpecification, dispatching by stream_type."""
    result: list[StreamTestCaseSpecification] = []
    for d in dicts:
        stream_type = StreamType(d["stream_type"])
        if stream_type == StreamType.CONTINUOUS:
            result.append(ContinuousStreamTestCaseSpecification.from_dict(d))
        elif stream_type == StreamType.BATCH:
            result.append(BatchStreamTestCaseSpecification.from_dict(d))
        else:
            raise ValueError(f"Unknown stream type: {stream_type}")
    return result


# ---------------------------------------------------------------------------
# Single stream test case: a stream paired with its states
# ---------------------------------------------------------------------------


@dataclass
class StreamTestCase:
    """A stream object paired with a list of states created from it."""

    stream: ContinuousStream | BatchStream
    states: list[ContinuousStreamState | BatchStreamState]

    @property
    def name(self) -> str:
        return self.stream.name

    @property
    def stream_type(self) -> str:
        return self.stream.stream_type

    def print_group(self) -> float:
        """Print this group's stream state details and return the total mass."""
        total_mass = 0.0
        if not self.states:
            print(f"  {self.name}: (empty)")
            return total_mass
        print(f"  {self.name}:")
        print(f"    Time: {self.states[0].start_time} to {self.states[-1].end_time}")
        print(f"    States: {len(self.states)}")
        if isinstance(self.stream, ContinuousStream):
            for state in self.states:
                assert isinstance(state, ContinuousStreamState)
                duration = state.end_time - state.start_time
                print(
                    f"      mass={state.total_mass:.2f}  rate={state.current_operation_rate:.2f}/h  duration={duration}"
                )
                total_mass += state.total_mass
        elif isinstance(self.stream, BatchStream):
            for state in self.states:
                assert isinstance(state, BatchStreamState)
                print(f"      batch_mass={state.batch_mass_value:.2f}  time={state.start_time} to {state.end_time}")
                total_mass += state.batch_mass_value
        return total_mass


def build_stream_test_case(
    stream_case_specification: StreamTestCaseSpecification,
    stream: ContinuousStream | BatchStream,
    start_time: datetime.datetime,
) -> StreamTestCase:
    """Build a single StreamTestCase from a specification and stream."""
    group_start = start_time + datetime.timedelta(seconds=stream_case_specification.start_offset_seconds)

    states: list[ContinuousStreamState | BatchStreamState] = []
    if isinstance(stream_case_specification, ContinuousStreamTestCaseSpecification):
        assert isinstance(stream, ContinuousStream)
        tuples_c = [
            (
                sp.mass,
                sp.rate,
                datetime.timedelta(seconds=sp.duration_seconds),
                datetime.timedelta(seconds=sp.gap_after_seconds),
            )
            for sp in stream_case_specification.states
        ]
        if tuples_c:
            states = list(
                make_continuous_stream_states_from_tuples(
                    stream=stream, start=group_start, mass_rate_duration_gap_tuples=tuples_c
                )
            )
    elif isinstance(stream_case_specification, BatchStreamTestCaseSpecification):
        assert isinstance(stream, BatchStream)
        tuples_b = [(sp.mass, datetime.timedelta(seconds=sp.gap_seconds)) for sp in stream_case_specification.states]
        if tuples_b:
            states = list(
                make_batch_stream_states_from_tuples(stream=stream, start=group_start, mass_and_gap_tuples=tuples_b)
            )
    return StreamTestCase(stream=stream, states=states)
