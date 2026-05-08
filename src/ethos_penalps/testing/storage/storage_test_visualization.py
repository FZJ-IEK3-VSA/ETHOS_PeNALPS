"""Visualization functions for storage entry test cases.

Provides Gantt chart and cumulative mass plots for StorageTestCase instances.
"""

import datetime

import matplotlib.pyplot as plt
import numpy
import pandas

from ethos_penalps.data_classes import (
    Commodity,
    StorageDataFrameMetaInformation,
    StorageProductionPlanEntry,
)
from ethos_penalps.energy.load_profile_calculator import LoadProfileHandlerSimulation
from ethos_penalps.post_processing.time_series_visualizations.gantt_chart import (
    GanttChartGenerator,
)
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamState,
    ContinuousStream,
    ContinuousStreamState,
    StreamDataFrameMetaInformation,
)
from ethos_penalps.testing.storage.storage_test_case import StorageTestCase
from ethos_penalps.testing.stream.stream_test_case import StreamTestCase


def _build_stream_meta(
    group: StreamTestCase,
    commodity: Commodity,
) -> StreamDataFrameMetaInformation | None:
    """Build a StreamDataFrameMetaInformation from a StreamTestCase."""
    if not group.states:
        return None

    rows = []
    if isinstance(group.stream, ContinuousStream):
        max_rate = max(
            state.current_operation_rate for state in group.states if isinstance(state, ContinuousStreamState)
        )
        for state in group.states:
            assert isinstance(state, ContinuousStreamState)
            rows.append(
                {
                    "start_time": state.start_time,
                    "end_time": state.end_time,
                    "current_operation_rate_value": state.current_operation_rate,
                    "minimum_operation_rate": 0,
                    "maximum_operation_rate": max_rate,
                }
            )
    elif isinstance(group.stream, BatchStream):
        max_mass = max(state.batch_mass_value for state in group.states if isinstance(state, BatchStreamState))
        for state in group.states:
            assert isinstance(state, BatchStreamState)
            rows.append(
                {
                    "start_time": state.start_time,
                    "end_time": state.end_time,
                    "total_mass": state.batch_mass_value,
                    "minimum_batch_mass_value": 0,
                    "maximum_batch_mass_value": max_mass,
                }
            )

    df = pandas.DataFrame(rows)
    return StreamDataFrameMetaInformation(
        data_frame=df,
        stream_name=group.name,
        first_start_time=df["start_time"].min(),
        last_end_time=df["end_time"].max(),
        stream_type=group.stream_type,
        mass_unit="t",
        commodity=commodity,
        name_to_display=group.name,
    )


def _build_storage_meta(
    entries: list[StorageProductionPlanEntry],
    commodity: Commodity,
) -> StorageDataFrameMetaInformation:
    """Build a StorageDataFrameMetaInformation from storage entries."""
    rows = []
    for entry in entries:
        rows.append(
            {
                "start_time": entry.start_time,
                "end_time": entry.end_time,
                "storage_level_at_start": entry.storage_level_at_start,
                "storage_level_at_end": entry.storage_level_at_end,
            }
        )
    df = pandas.DataFrame(rows)
    return StorageDataFrameMetaInformation(
        data_frame=df,
        process_step_name="Storage",
        commodity=commodity,
        first_start_time=df["start_time"].min(),
        last_end_time=df["end_time"].max(),
        mass_unit="t",
    )


def plot_streams_and_storage(case: StorageTestCase):
    """Plot input streams, storage level, and output streams using the
    ethos_penalps GanttChartGenerator.

    Layout: one row per input stream, storage in the middle, one row per output stream.
    Empty stream directions are omitted.

    Returns:
        The proplot Figure.
    """
    commodity = case.storage_components.commodity
    storage_meta = _build_storage_meta(case.entries, commodity)
    start_date = storage_meta.first_start_time
    end_date = storage_meta.last_end_time

    meta_data_list = []

    for group in case.input_group:
        meta = _build_stream_meta(group, commodity)
        if meta is not None:
            start_date = min(start_date, meta.first_start_time)
            end_date = max(end_date, meta.last_end_time)
            meta_data_list.append(meta)

    meta_data_list.append(storage_meta)

    for group in case.output_group:
        meta = _build_stream_meta(group, commodity)
        if meta is not None:
            start_date = min(start_date, meta.first_start_time)
            end_date = max(end_date, meta.last_end_time)
            meta_data_list.append(meta)

    margin = (end_date - start_date) * 0.02
    load_profile_handler = LoadProfileHandlerSimulation()
    production_plan = ProductionPlan(load_profile_handler=load_profile_handler)
    generator = GanttChartGenerator(
        production_plan=production_plan,
        process_node_dict={},
        stream_handler=case.storage_components.stream_handler,
    )
    figure = generator.create_gantt_chart_from_list_of_meta_data(
        list_of_meta_data=meta_data_list,
        start_date=start_date - margin,
        end_date=end_date + margin,
        gantt_chart_title=case.name,
    )

    # Resize: the gantt chart uses refheight=0.5cm per row which is tiny.
    n_rows = len(meta_data_list)
    figure.set_size_inches(14, max(3, n_rows * 1.5))

    # Mark time bounds (start_time / end_time) if set in the case parameters.
    # Only draw on the first n_rows axes (subplot axes), not any auxiliary axes
    # that proplot may create.
    entry_start = case.parameters.storage_entry_start_time
    entry_end = case.parameters.storage_entry_end_time
    if entry_start is not None or entry_end is not None:
        for ax in figure.axes[:n_rows]:
            if entry_start is not None:
                ax.axvline(entry_start, color="red", linewidth=1.5, linestyle="--", alpha=0.8)
            if entry_end is not None:
                ax.axvline(entry_end, color="red", linewidth=1.5, linestyle="--", alpha=0.8)

    return figure


def plot_cumulative_mass(case: StorageTestCase) -> None:
    """Plot cumulative net mass and storage level with offset."""
    duration_array = case.duration_array
    net_masses = duration_array[:, 3]
    cumulative = numpy.cumsum(net_masses)

    from ethos_penalps.utilities.general_functions import seconds_to_datetime

    start_times = [seconds_to_datetime(float(timestamp)) for timestamp in duration_array[:, 0]]
    end_times = [seconds_to_datetime(float(timestamp)) for timestamp in duration_array[:, 1]]

    cum_times = [start_times[0]]
    cum_values_raw = [0.0]
    cum_values_offset = [case.start_storage_level]
    for _step, (end_time, cum_value) in enumerate(zip(end_times, cumulative)):
        cum_times.append(end_time)
        cum_values_raw.append(float(cum_value))
        cum_values_offset.append(case.start_storage_level + float(cum_value))

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(cum_times, cum_values_raw, "o--", color="gray", markersize=3, label="Cumulative (no offset)")
    ax.plot(
        cum_times,
        cum_values_offset,
        "o-",
        color="steelblue",
        markersize=3,
        label=f"With offset ({case.start_storage_level:.1f})",
    )
    ax.axhline(0, color="red", linewidth=0.8, linestyle="--", alpha=0.5)

    # Mark time bounds (start_time / end_time) if set in the case parameters
    entry_start = case.parameters.storage_entry_start_time
    entry_end = case.parameters.storage_entry_end_time
    if entry_start is not None:
        ax.axvline(entry_start, color="red", linewidth=1.5, linestyle="--", alpha=0.8, label="Time bound")
    if entry_end is not None:
        ax.axvline(
            entry_end,
            color="red",
            linewidth=1.5,
            linestyle="--",
            alpha=0.8,
            label="Time bound" if entry_start is None else None,
        )

    ax.set_ylabel("Mass")
    ax.set_xlabel("Time")
    ax.set_title(f"Cumulative Mass — {case.name}")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.show()
