"""Helper and visualization functions for resampling load profiles."""

import datetime
import json
import os

import matplotlib.pyplot as plt
import numpy as np

from ethos_penalps.data_classes import LoadProfileEntry, LoadProfileMetaData, LoadProfileMetaDataResampled, LoadType
from ethos_penalps.post_processing.load_profiles.load_profile_entry_post_processor import (
    LoadProfileEntryPostProcessor,
)


def resample_load_profile(
    entries: list,
    start: datetime.datetime,
    end: datetime.datetime,
    resample_frequency: str = "1min",
) -> tuple[LoadProfileMetaData, LoadProfileMetaDataResampled]:
    """Create meta data and resample.

    Returns:
        Tuple of (meta, resampled_result).
    """
    processor = LoadProfileEntryPostProcessor()
    meta = processor.create_load_profile_meta_data(
        list_of_load_profile_entries=entries,
        start_date_time_series=start,
        end_date_time_series=end,
        object_name="TestObject",
        object_type="TestType",
    )
    result = processor.resample_load_profile_meta_data(
        load_profile_meta_data=meta,
        start_date=start,
        end_date=end,
        resample_frequency=resample_frequency,
    )
    return meta, result


def make_case_name(
    n_entries: int,
    total_duration: datetime.timedelta,
    resample_frequency: str,
) -> str:
    """Build a descriptive case folder name from the input parameters.

    Format: ``{n_entries}entries_{total_seconds}s_{resample_frequency}``

    Examples:
        ``7entries_300s_1min``
        ``200entries_172800s_5min``
    """
    total_seconds = int(total_duration.total_seconds())
    return f"{n_entries}entries_{total_seconds}s_{resample_frequency}"


def load_resampling_test_case(
    case_dir: str,
) -> tuple[LoadProfileMetaData, LoadProfileMetaDataResampled, dict]:
    """Load a resampling test case from a case directory.

    Returns:
        Tuple of (meta, resampled_result, parameters).
    """
    import pandas as pd

    with open(os.path.join(case_dir, "parameters.json")) as f:
        parameters = json.load(f)

    start = datetime.datetime.fromisoformat(parameters["start"])
    end = datetime.datetime.fromisoformat(parameters["end"])
    resample_frequency = parameters["resample_frequency"]

    # For unaligned cases, entry range differs from resample range
    entry_start = datetime.datetime.fromisoformat(parameters["entry_start"]) if "entry_start" in parameters else start
    entry_end = datetime.datetime.fromisoformat(parameters["entry_end"]) if "entry_end" in parameters else end

    input_df = pd.read_csv(os.path.join(case_dir, "input_load_profile.csv"), index_col=0)
    resampled_df = pd.read_csv(os.path.join(case_dir, "resampled.csv"), index_col=0)

    def _entries_from_df(df: pd.DataFrame) -> list:
        entries = []
        for row in df.itertuples(index=True):
            entries.append(
                LoadProfileEntry(
                    load_type=LoadType(name="Electricity", uuid="test-uuid"),
                    start_time=datetime.datetime.fromisoformat(row.start_time),
                    end_time=datetime.datetime.fromisoformat(row.end_time),
                    energy_quantity=row.energy_quantity,
                    energy_unit=row.energy_unit,
                    average_power_consumption=row.average_power_consumption,
                    power_unit=row.power_unit,
                )
            )
        return entries

    input_entries = _entries_from_df(input_df)
    resampled_entries = _entries_from_df(resampled_df)

    load_type = input_entries[0].load_type if input_entries else LoadType(name="Electricity", uuid="test-uuid")

    meta = LoadProfileMetaData(
        name="TestObject",
        object_type="TestType",
        list_of_load_profiles=input_entries,
        data_frame=input_df,
        first_start_time=entry_start,
        last_end_time=entry_end,
        load_type=load_type,
        power_unit=input_entries[0].power_unit if input_entries else "MW",
        energy_unit=input_entries[0].energy_unit if input_entries else "MJ",
        maximum_energy=max(e.energy_quantity for e in input_entries),
        maximum_power=max(e.average_power_consumption for e in input_entries),
        minimum_power=min(e.average_power_consumption for e in input_entries),
        total_energy=sum(e.energy_quantity for e in input_entries),
    )

    resample_td = datetime.datetime.fromisoformat(resampled_df["end_time"].iloc[0]) - datetime.datetime.fromisoformat(
        resampled_df["start_time"].iloc[0]
    )

    resampled_result = LoadProfileMetaDataResampled(
        name="TestObject",
        object_type="TestType",
        list_of_load_profiles=resampled_entries,
        data_frame=resampled_df,
        power_unit=resampled_entries[0].power_unit if resampled_entries else "MW",
        energy_unit=resampled_entries[0].energy_unit if resampled_entries else "MJ",
        total_energy=sum(e.energy_quantity for e in resampled_entries),
        maximum_power=max(e.average_power_consumption for e in resampled_entries),
        minimum_power=min(e.average_power_consumption for e in resampled_entries),
        load_type=load_type,
        time_step=resample_td,
        resample_frequency=resample_frequency,
        first_start_time=datetime.datetime.fromisoformat(resampled_df["start_time"].iloc[0]),
        last_end_time=datetime.datetime.fromisoformat(resampled_df["end_time"].iloc[-1]),
    )

    return meta, resampled_result, parameters


def list_available_cases(cases_dir: str) -> list[str]:
    """List available case names in a cases directory.

    Returns:
        Sorted list of case directory names.
    """
    if not os.path.isdir(cases_dir):
        return []
    return sorted(d for d in os.listdir(cases_dir) if os.path.isdir(os.path.join(cases_dir, d)))


def save_resampling_test_case(
    meta: LoadProfileMetaData,
    result: LoadProfileMetaDataResampled,
    cases_dir: str,
    parameters: dict,
    case_name: str | None = None,
) -> str:
    """Save a resampling test case to a named subdirectory.

    If *case_name* is not given it is derived from the input data via
    :func:`make_case_name`.

    Returns:
        The path to the created case directory.
    """
    if case_name is None:
        n_entries = len(meta.list_of_load_profiles)
        total_duration = meta.last_end_time - meta.first_start_time
        resample_frequency = parameters.get("resample_frequency", "1min")
        case_name = make_case_name(n_entries, total_duration, resample_frequency)

    output_dir = os.path.join(cases_dir, case_name)
    os.makedirs(output_dir, exist_ok=True)
    meta.data_frame.to_csv(os.path.join(output_dir, "input_load_profile.csv"), index=True)
    result.data_frame.to_csv(os.path.join(output_dir, "resampled.csv"), index=True)
    with open(os.path.join(output_dir, "parameters.json"), "w") as f:
        json.dump(parameters, f, indent=2)

    print(f"Saved case '{case_name}' to {output_dir}/")
    for fname in sorted(os.listdir(output_dir)):
        fpath = os.path.join(output_dir, fname)
        size_kb = os.path.getsize(fpath) / 1024
        print(f"  {fname:40s} {size_kb:.1f} KB")
    return output_dir


def plot_input_vs_resampled(
    meta: LoadProfileMetaData,
    vectorized_result: LoadProfileMetaDataResampled,
) -> None:
    """Plot input power profile vs resampled power profile."""
    input_entries = meta.list_of_load_profiles
    vec_entries = vectorized_result.list_of_load_profiles

    number_of_segments_vectorized = len(vec_entries)
    line_width = max(0.3, min(2.0, 500 / number_of_segments_vectorized))

    input_colors = ["steelblue", "navy"]

    fig, ax = plt.subplots(1, 1, figsize=(14, 4), sharex=True)

    for i, entry in enumerate(input_entries):
        ax.plot(
            [entry.start_time, entry.end_time],
            [entry.average_power_consumption, entry.average_power_consumption],
            color=input_colors[i % 2],
            linestyle="-",
            linewidth=line_width * 2.5,
            alpha=1,
            label=f"Input ({len(input_entries)} entries, irregular)" if i == 0 else None,
        )
        ax.axvline(entry.start_time, color="gray", linewidth=0.8, alpha=0.5, linestyle=":")

    vec_times = []
    vec_powers = []
    for current_vectorized_entry in vec_entries:
        vec_times.extend([current_vectorized_entry.start_time, current_vectorized_entry.end_time])
        vec_powers.extend(
            [current_vectorized_entry.average_power_consumption, current_vectorized_entry.average_power_consumption]
        )

    ax.step(
        vec_times,
        vec_powers,
        color="darkorange",
        linestyle="--",
        linewidth=line_width * 1.2,
        alpha=0.7,
        label=f"Resampled ({number_of_segments_vectorized} segments, {vectorized_result.resample_frequency} grid)",
    )
    ax.set_ylabel(f"Power [{vectorized_result.power_unit}]")
    ax.set_title("Input vs. Resampled Power Profile")
    ax.set_xlim(meta.first_start_time, meta.last_end_time)
    ax.legend()
    ax.grid(True, alpha=0.8)

    fig.autofmt_xdate()
    plt.tight_layout()
    plt.show()


def plot_compare_energy(
    meta: LoadProfileMetaData,
    vectorized_result: LoadProfileMetaDataResampled,
) -> None:
    """Plot input entries vs resampled bins as horizontal energy bars."""
    input_entries = meta.list_of_load_profiles
    vec_entries = vectorized_result.list_of_load_profiles
    resample_time_step = vectorized_result.time_step
    profile_start = meta.first_start_time
    total_minutes = (meta.last_end_time - profile_start).total_seconds() / 60
    bin_width_min = resample_time_step.total_seconds() / 60

    fig, ax = plt.subplots(figsize=(14, 5))

    for i, e in enumerate(input_entries):
        ax.barh(
            y=1.2,
            width=(e.end_time - e.start_time).total_seconds() / 60,
            left=(e.start_time - profile_start).total_seconds() / 60,
            height=0.3,
            color=plt.cm.tab10(i % 10),
            edgecolor="black",
            linewidth=0.5,
            alpha=0.7,
            label=f"Input ({len(input_entries)} segments)" if i == 0 else None,
        )
        duration_s = (e.end_time - e.start_time).total_seconds()
        mid_x = (e.start_time - profile_start).total_seconds() / 60 + duration_s / 120
        ax.text(mid_x, 1.25, f"{e.energy_quantity:.2f} {e.energy_unit}", ha="center", va="bottom", fontsize=6)
        ax.text(mid_x, 1.15, f"{duration_s:.0f}s", ha="center", va="top", fontsize=6)

    for i, e in enumerate(vec_entries):
        ax.barh(
            y=0.5,
            width=bin_width_min,
            left=(e.start_time - profile_start).total_seconds() / 60,
            height=0.3,
            color="darkorange",
            edgecolor="black",
            linewidth=0.5,
            alpha=0.7,
            label=f"Resampled ({len(vec_entries)} segments)" if i == 0 else None,
        )
        duration_s = (e.end_time - e.start_time).total_seconds()
        mid_x = (e.start_time - profile_start).total_seconds() / 60 + bin_width_min / 2
        ax.text(mid_x, 0.55, f"{e.energy_quantity:.2f} {e.energy_unit}", ha="center", va="bottom", fontsize=6)
        ax.text(mid_x, 0.45, f"{duration_s:.0f}s", ha="center", va="top", fontsize=6)

    for m in np.arange(0, total_minutes + bin_width_min, bin_width_min):
        ax.axvline(m, color="gray", linewidth=0.3, linestyle="--")

    ax.set_yticks([0.5, 1.2])
    ax.set_yticklabels([f"Resampled ({vectorized_result.resample_frequency})", "Input (irregular)"])
    ax.set_xlabel("Minutes")
    ax.legend(loc="upper right")
    ax.set_title("Energy Comparison: Input vs. Resampled")
    ax.set_xlim(0, total_minutes)
    plt.tight_layout()
    plt.show()


def plot_input_vs_resampled_energy(
    meta: LoadProfileMetaData,
    vectorized_result: LoadProfileMetaDataResampled,
) -> None:
    """Plot cumulative energy of input entries vs resampled bins.

    For aligned cases the curves converge to the same total.
    For unaligned cases the resampled curve will be lower, showing the energy loss.
    """
    input_entries = meta.list_of_load_profiles
    vec_entries = vectorized_result.list_of_load_profiles

    input_energies = np.array([e.energy_quantity for e in input_entries])
    vec_energies = np.array([e.energy_quantity for e in vec_entries])

    input_end_times = [e.end_time for e in input_entries]
    vec_end_times = [e.end_time for e in vec_entries]

    xlim_start = min(meta.first_start_time, vectorized_result.first_start_time)
    xlim_end = max(meta.last_end_time, vectorized_result.last_end_time)
    margin = (xlim_end - xlim_start) * 0.02

    cum_input_times = [input_entries[0].start_time] + input_end_times
    cum_input = np.concatenate([[0], np.cumsum(input_energies)])

    cum_vec_times = [vec_entries[0].start_time] + vec_end_times
    cum_vec = np.concatenate([[0], np.cumsum(vec_energies)])

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(
        cum_input_times,
        cum_input,
        "o-",
        label=f"Input ({len(input_entries)} entries)",
        linewidth=1.0,
        markersize=4,
        color="steelblue",
    )
    ax.plot(
        cum_vec_times,
        cum_vec,
        "s--",
        label=f"Resampled ({len(vec_entries)} bins)",
        linewidth=1.0,
        markersize=4,
        color="darkorange",
    )

    input_total = float(input_energies.sum())
    vec_total = float(vec_energies.sum())
    energy_lost = input_total - vec_total
    ax.set_ylabel(f"Cumulative Energy [{meta.energy_unit}]")
    ax.set_title(f"Cumulative Energy: Input vs. Resampled (lost: {energy_lost:.2f} {meta.energy_unit})")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim(xlim_start - margin, xlim_end + margin)

    fig.autofmt_xdate()
    plt.tight_layout()
    plt.show()


def plot_duration_distribution(
    meta: LoadProfileMetaData,
    vectorized_result: LoadProfileMetaDataResampled,
) -> None:
    """Plot histogram of input entry durations vs resample bin width."""
    resample_td = vectorized_result.time_step
    bin_width_min = resample_td.total_seconds() / 60

    input_durations_min = [(e.end_time - e.start_time).total_seconds() / 60 for e in meta.list_of_load_profiles]
    resampled_durations_min = [
        (e.end_time - e.start_time).total_seconds() / 60 for e in vectorized_result.list_of_load_profiles
    ]

    fig, ax = plt.subplots(figsize=(10, 4))

    input_unique, input_counts = np.unique(input_durations_min, return_counts=True)
    resampled_unique, resampled_counts = np.unique(resampled_durations_min, return_counts=True)

    ax.vlines(
        input_unique,
        0,
        input_counts,
        color="steelblue",
        linewidth=2,
        label=f"Input ({len(input_durations_min)} entries)",
    )
    ax.vlines(
        resampled_unique,
        0,
        resampled_counts,
        color="darkorange",
        linewidth=2,
        linestyle="--",
        label=f"Resampled ({len(resampled_durations_min)} entries, {vectorized_result.resample_frequency})",
    )
    ax.plot(input_unique, input_counts, "o", color="steelblue", markersize=5)
    ax.plot(resampled_unique, resampled_counts, "s", color="darkorange", markersize=5)
    ax.set_xlabel("Entry Duration (minutes)")
    ax.set_ylabel("Count")
    ax.set_title("Distribution of Entry Durations")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
