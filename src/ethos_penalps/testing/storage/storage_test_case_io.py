"""Disk I/O for storage test cases.

Provides functions to save, load, and list storage test cases stored as
directories containing parameters.json and expected_storage_entries.csv.
"""

import datetime
import json
import os

import numpy
import pandas

from ethos_penalps.data_classes import StorageProductionPlanEntry
from ethos_penalps.testing.storage.storage_test_case import (
    StorageTestCase,
    StorageTestComponents,
    build_case_from_parameters,
)
from ethos_penalps.testing.stream.stream_test_io import (
    load_stream_test_cases,
    save_stream_test_cases,
)
from ethos_penalps.utilities.general_functions import datetime_to_seconds


def save_storage_test_case(
    case: StorageTestCase,
    cases_dir: str,
) -> str:
    """Save a storage test case to a named subdirectory.

    Writes:
      - parameters.json      — stream definitions and configuration
      - expected_storage_entries.csv  — golden reference storage entry values

    Returns:
        The path to the created case directory.
    """
    output_dir = os.path.join(cases_dir, case.name)
    os.makedirs(output_dir, exist_ok=True)

    params_to_save = case.parameters.to_dict()
    params_to_save["computed_start_storage_level"] = case.start_storage_level
    # Strip states from stream specifications — they are saved as CSV instead
    for group_key in ("input_stream_group", "output_stream_group"):
        group = params_to_save.get(group_key)
        if isinstance(group, dict):
            for spec in group.get("stream_specifications", []):
                if isinstance(spec, dict):
                    spec.pop("states", None)
    with open(os.path.join(output_dir, "parameters.json"), "w") as file_handle:
        json.dump(params_to_save, file_handle, indent=2)

    rows = []
    for entry in case.entries:
        rows.append(
            {
                "start_time": entry.start_time.isoformat(),
                "end_time": entry.end_time.isoformat(),
                "storage_level_at_start": entry.storage_level_at_start,
                "storage_level_at_end": entry.storage_level_at_end,
            }
        )
    data_frame = pandas.DataFrame(rows)
    data_frame.to_csv(os.path.join(output_dir, "expected_storage_entries.csv"), index=False)

    if case.input_group.stream_test_cases:
        save_stream_test_cases(
            case.input_group.stream_test_cases,
            os.path.join(output_dir, "input_streams.csv"),
        )
    if case.output_group.stream_test_cases:
        save_stream_test_cases(
            case.output_group.stream_test_cases,
            os.path.join(output_dir, "output_streams.csv"),
        )

    print(f"Saved case '{case.name}' to {output_dir}/")
    for fname in sorted(os.listdir(output_dir)):
        fpath = os.path.join(output_dir, fname)
        size_kb = os.path.getsize(fpath) / 1024
        print(f"  {fname:40s} {size_kb:.1f} KB")
    return output_dir


def load_storage_test_case(case_dir: str) -> StorageTestCase:
    """Load a storage test case from a case directory.

    The storage setup (stream objects, stream_handler) is rebuilt from
    parameters.json. Stream states are recomputed from the specifications.
    Storage entries are loaded from expected_storage_entries.csv so that the
    golden reference values are what tests verify.
    """
    with open(os.path.join(case_dir, "parameters.json")) as file_handle:
        parameters = json.load(file_handle)
    case = build_case_from_parameters(parameters)
    case.entries = _load_entries_from_csv(case_dir, case.storage_components)

    # Restore pre-computed start level when states were stripped from JSON
    if "computed_start_storage_level" in parameters:
        case.start_storage_level = float(parameters["computed_start_storage_level"])

    input_csv = os.path.join(case_dir, "input_streams.csv")
    if os.path.exists(input_csv):
        loaded_inputs = load_stream_test_cases(input_csv, case.storage_components.input_streams)
        if loaded_inputs:
            case.input_group.stream_test_cases = loaded_inputs

    output_csv = os.path.join(case_dir, "output_streams.csv")
    if os.path.exists(output_csv):
        loaded_outputs = load_stream_test_cases(output_csv, case.storage_components.output_streams)
        if loaded_outputs:
            case.output_group.stream_test_cases = loaded_outputs

    # Recompute duration_array from loaded stream states, applying time bounds
    if case.input_group.all_states or case.output_group.all_states:
        params = case.parameters
        boundary_time_points: list[float] = []
        if params.storage_entry_start_time is not None:
            boundary_time_points.append(datetime_to_seconds(params.storage_entry_start_time))
        if params.storage_entry_end_time is not None:
            boundary_time_points.append(datetime_to_seconds(params.storage_entry_end_time))

        duration_array = case.storage_components.base_storage._create_net_mass_duration_array(
            input_stream_state_list=case.input_group.all_states,
            output_stream_state_list=case.output_group.all_states,
            boundary_time_points=boundary_time_points or None,
        )

        if params.storage_entry_start_time is not None or params.storage_entry_end_time is not None:
            mask = numpy.ones(len(duration_array), dtype=bool)
            if params.storage_entry_start_time is not None:
                mask &= duration_array[:, 0] >= datetime_to_seconds(params.storage_entry_start_time)
            if params.storage_entry_end_time is not None:
                mask &= duration_array[:, 1] <= datetime_to_seconds(params.storage_entry_end_time)
            duration_array = duration_array[mask]

        case.duration_array = duration_array

    return case


def _load_entries_from_csv(
    case_dir: str,
    storage_components: StorageTestComponents,
) -> list[StorageProductionPlanEntry]:
    """Parse expected_storage_entries.csv into StorageProductionPlanEntry objects."""
    df = pandas.read_csv(os.path.join(case_dir, "expected_storage_entries.csv"))
    entries = []
    for _index, row in df.iterrows():
        start = datetime.datetime.fromisoformat(row["start_time"])
        end = datetime.datetime.fromisoformat(row["end_time"])
        entries.append(
            StorageProductionPlanEntry(
                process_step_name=storage_components.base_storage.process_step_name,
                start_time=start,
                end_time=end,
                duration=end - start,
                storage_level_at_start=float(row["storage_level_at_start"]),
                storage_level_at_end=float(row["storage_level_at_end"]),
                commodity=storage_components.commodity,
            )
        )
    return entries


def load_expected_entries_csv(case_dir: str) -> list[dict]:
    """Load the golden reference entries from expected_storage_entries.csv as raw dicts."""
    df = pandas.read_csv(os.path.join(case_dir, "expected_storage_entries.csv"))
    return df.to_dict(orient="records")


def list_available_cases(cases_dir: str) -> list[str]:
    """List available case names in a cases directory."""
    if not os.path.isdir(cases_dir):
        return []
    required = {"parameters.json", "expected_storage_entries.csv"}
    return sorted(
        case_name
        for case_name in os.listdir(cases_dir)
        if os.path.isdir(os.path.join(cases_dir, case_name))
        and required.issubset(set(os.listdir(os.path.join(cases_dir, case_name))))
    )
