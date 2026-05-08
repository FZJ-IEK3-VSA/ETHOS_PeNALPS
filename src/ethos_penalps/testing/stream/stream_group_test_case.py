"""Dataclasses and builders for stream group test cases.

A stream group bundles multiple streams of the same type (all continuous or
all batch) together with their specifications and runtime state.

Provides:
- ``StreamGroupTestCaseSpecification`` — serialisable specification for a group.
- ``StreamGroupTestCase`` — the fully built group at runtime.
- Factory and builder functions to create streams and test cases from specs.
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
from ethos_penalps.testing.stream.stream_test_case import (
    BatchStreamTestCaseSpecification,
    ContinuousStreamTestCaseSpecification,
    StreamTestCase,
    StreamTestCaseSpecification,
    _decode_stream_specs,
    _encode_stream_specs,
    build_stream_test_case,
)

# ---------------------------------------------------------------------------
# Stream group specification (serialisable parameters)
# ---------------------------------------------------------------------------


@dataclass
class StreamGroupTestCaseSpecification(DataClassJsonMixin):
    """Specification for a group of streams that share the same type.

    All stream specifications in the group must be the same type
    (all continuous or all batch).

    Attributes:
        stream_specifications: List of per-stream specifications.
    """

    stream_specifications: list[StreamTestCaseSpecification] = field(
        default_factory=list,
        metadata=config(
            encoder=_encode_stream_specs,
            decoder=_decode_stream_specs,
        ),
    )

    @property
    def stream_type(self) -> StreamType:
        """Infer the stream type from the specifications."""
        if not self.stream_specifications:
            raise ValueError("Cannot infer stream_type from empty stream_specifications")
        first_type = self.stream_specifications[0].stream_type
        if not all(s.stream_type == first_type for s in self.stream_specifications):
            raise ValueError("All stream specifications must have the same stream_type")
        return first_type

    def __len__(self) -> int:
        return len(self.stream_specifications)


# ---------------------------------------------------------------------------
# Stream group test case (runtime)
# ---------------------------------------------------------------------------


@dataclass
class StreamGroupTestCase:
    """Runtime: a group of built stream test cases sharing the same type."""

    stream_test_cases: list[StreamTestCase]

    @property
    def all_states(self) -> list[ContinuousStreamState | BatchStreamState]:
        """Flat list of all states across all streams in the group."""
        return [state for tc in self.stream_test_cases for state in tc.states]

    def __len__(self) -> int:
        return len(self.stream_test_cases)

    def __iter__(self):
        return iter(self.stream_test_cases)

    def print_group(self) -> float:
        """Print all streams in the group and return total mass."""
        total = 0.0
        for tc in self.stream_test_cases:
            total += tc.print_group()
        return total


# ---------------------------------------------------------------------------
# Factory and builder functions
# ---------------------------------------------------------------------------


def create_streams_from_group(
    group_spec: StreamGroupTestCaseSpecification,
    stream_handler: StreamHandler,
    commodity: Commodity,
    direction: str,
) -> list[ContinuousStream | BatchStream]:
    """Create live stream objects from a StreamGroupTestCaseSpecification.

    Args:
        direction: "Upstream" for input streams, "Downstream" for output streams.
    """
    is_input = direction == "Upstream"
    streams: list[ContinuousStream | BatchStream] = []
    for i, spec in enumerate(group_spec.stream_specifications):
        suffix = f" {i + 1}" if len(group_spec) > 1 else ""
        start_name = f"{direction}{suffix}" if is_input else "Storage"
        end_name = "Storage" if is_input else f"{direction}{suffix}"

        if isinstance(spec, ContinuousStreamTestCaseSpecification):
            stream = stream_handler.create_continuous_stream(
                ContinuousStreamStaticData(
                    start_process_step_name=start_name,
                    end_process_step_name=end_name,
                    commodity=commodity,
                    maximum_operation_rate=spec.get_effective_max_operation_rate(),
                    minimum_operation_rate=spec.min_operation_rate,
                )
            )
        elif isinstance(spec, BatchStreamTestCaseSpecification):
            stream = stream_handler.create_batch_stream(
                BatchStreamStaticData(
                    start_process_step_name=start_name,
                    end_process_step_name=end_name,
                    commodity=commodity,
                    maximum_batch_mass_value=spec.max_batch_mass,
                    minimum_batch_mass_value=spec.min_batch_mass,
                    delay=datetime.timedelta(seconds=spec.batch_delay_seconds),
                )
            )
        else:
            raise ValueError(f"Unknown specification type: {type(spec)}")
        streams.append(stream)
    return streams


def build_stream_group_test_case(
    group_spec: StreamGroupTestCaseSpecification,
    streams: list[ContinuousStream | BatchStream],
    start_time: datetime.datetime,
) -> StreamGroupTestCase:
    """Build a StreamGroupTestCase from a group specification and live streams."""
    test_cases = [
        build_stream_test_case(spec, stream, start_time)
        for spec, stream in zip(group_spec.stream_specifications, streams)
    ]
    return StreamGroupTestCase(stream_test_cases=test_cases)
