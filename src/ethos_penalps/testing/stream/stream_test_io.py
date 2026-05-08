"""CSV I/O helpers for stream test case state lists.

Provides functions for saving/loading StreamTestCase lists as CSV files.
Each row is one stream state; a ``stream_name`` column distinguishes
streams within the same group.
"""

from __future__ import annotations

import os

import pandas

from ethos_penalps.stream import (
    BatchStream,
    BatchStreamState,
    ContinuousStream,
    ContinuousStreamState,
)
from ethos_penalps.testing.stream.stream_test_case import (
    StreamTestCase,
)

# ---------------------------------------------------------------------------
# CSV serialization for StreamTestCase lists
# ---------------------------------------------------------------------------


def save_stream_test_cases(groups: list[StreamTestCase], path: str) -> None:
    """Serialize a list of StreamTestCase to a CSV file.

    Columns vary by stream type:
      - Continuous: stream_name, start_time, end_time, total_mass, current_operation_rate
      - Batch:      stream_name, start_time, end_time, batch_mass_value

    All streams in a single file must be the same type.
    """
    rows: list[dict] = []
    for group in groups:
        for state in group.states:
            row: dict = {
                "stream_name": group.name,
                "start_time": state.start_time.isoformat(),
                "end_time": state.end_time.isoformat(),
            }
            if isinstance(state, ContinuousStreamState):
                row["total_mass"] = state.total_mass
                row["current_operation_rate"] = state.current_operation_rate
            elif isinstance(state, BatchStreamState):
                row["batch_mass_value"] = state.batch_mass_value
            rows.append(row)

    pandas.DataFrame(rows).to_csv(path, index=False)


def load_stream_test_cases(
    path: str,
    streams: list[ContinuousStream | BatchStream],
) -> list[StreamTestCase]:
    """Load stream states from a CSV file into StreamTestCase objects.

    Dispatches by column presence: ``total_mass`` → continuous,
    ``batch_mass_value`` → batch.

    Args:
        path: Path to the CSV file.
        streams: The stream objects to pair with the loaded states (one per
            unique stream_name, in order of first appearance).

    Returns an empty list if the file does not exist.
    """
    if not os.path.exists(path):
        return []

    df = pandas.read_csv(path)
    if df.empty:
        return []

    is_continuous = "total_mass" in df.columns

    # Group rows by stream_name, preserving order of first appearance
    stream_names: list[str] = list(dict.fromkeys(df["stream_name"]))

    groups: list[StreamTestCase] = []
    for stream_index, stream_name in enumerate(stream_names):
        stream = streams[stream_index]
        sub = df[df["stream_name"] == stream_name]

        states: list[ContinuousStreamState | BatchStreamState] = []
        for _, row in sub.iterrows():
            import datetime

            import datetimerange

            start_time = datetime.datetime.fromisoformat(row["start_time"])
            end_time = datetime.datetime.fromisoformat(row["end_time"])
            date_time_range = datetimerange.DateTimeRange(start_time, end_time)

            if is_continuous:
                states.append(
                    ContinuousStreamState(
                        name=stream_name,
                        start_time=start_time,
                        end_time=end_time,
                        date_time_range=date_time_range,
                        total_mass=float(row["total_mass"]),
                        current_operation_rate=float(row["current_operation_rate"]),
                    )
                )
            else:
                states.append(
                    BatchStreamState(
                        name=stream_name,
                        start_time=start_time,
                        end_time=end_time,
                        date_time_range=date_time_range,
                        batch_mass_value=float(row["batch_mass_value"]),
                    )
                )
        groups.append(StreamTestCase(stream=stream, states=states))

    return groups
