"""Reusable assertion helpers for storage entry tests."""

import numpy

from ethos_penalps.data_classes import StorageProductionPlanEntry


def assert_entries_contiguous(entries: list[StorageProductionPlanEntry]):
    """Assert that entries are contiguous: each end_time == next start_time."""
    for a, b in zip(entries[:-1], entries[1:]):
        assert a.end_time == b.start_time, f"Gap between entries: {a.end_time} != {b.start_time}"


def assert_mass_conservation(
    entries: list[StorageProductionPlanEntry],
    total_input: float,
    total_output: float,
    start_level: float,
):
    """Assert that final_level == start_level + total_input - total_output."""
    final_level = entries[-1].storage_level_at_end
    expected = start_level + total_input - total_output
    assert numpy.isclose(final_level, expected, atol=1e-9), (
        f"Mass not conserved: final={final_level}, expected={expected}"
    )


def assert_non_negative(entries: list[StorageProductionPlanEntry]):
    """Assert all storage levels are >= 0."""
    for entry in entries:
        assert entry.storage_level_at_start >= -1e-9, f"Negative start level: {entry.storage_level_at_start}"
        assert entry.storage_level_at_end >= -1e-9, f"Negative end level: {entry.storage_level_at_end}"


def assert_entries_match_expected(
    entries: list[StorageProductionPlanEntry],
    expected: list[dict],
    atol: float = 1e-6,
):
    """Assert that storage entries match the golden reference values.

    Args:
        entries: Computed storage entries.
        expected: List of dicts from expected_storage_entries.csv with keys
            start_time, end_time, storage_level_at_start, storage_level_at_end.
        atol: Absolute tolerance for level comparisons.
    """
    assert len(entries) == len(expected), f"Entry count mismatch: got {len(entries)}, expected {len(expected)}"
    for i, (entry, exp) in enumerate(zip(entries, expected)):
        assert numpy.isclose(entry.storage_level_at_start, exp["storage_level_at_start"], atol=atol), (
            f"Entry {i} start level: {entry.storage_level_at_start} != {exp['storage_level_at_start']}"
        )
        assert numpy.isclose(entry.storage_level_at_end, exp["storage_level_at_end"], atol=atol), (
            f"Entry {i} end level: {entry.storage_level_at_end} != {exp['storage_level_at_end']}"
        )
