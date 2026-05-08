"""Utility functions for creating load profiles in tests and examples."""

import datetime
import random

from ethos_penalps.data_classes import LoadProfileEntry, LoadType
from ethos_penalps.utilities.units import Units


def make_random_load_profile_entries(
    start: datetime.datetime,
    end: datetime.datetime,
    n_entries: int,
    max_energy: float,
    seed: int,
    load_type: LoadType | None = None,
) -> list[LoadProfileEntry]:
    """Generate non-overlapping, contiguous load profile entries with random
    durations and energy values spanning [start, end].

    Returned in reverse chronological order.

    Args:
        start: Start of the time range.
        end: End of the time range.
        n_entries: Number of entries to generate.
        max_energy: Maximum energy per entry (uniform random in [0, max_energy]).
        seed: Random seed for reproducibility.
        load_type: Optional LoadType. Defaults to Electricity with a test UUID.

    Returns:
        List of LoadProfileEntry in reverse chronological order.
    """
    rng = random.Random(seed)
    if load_type is None:
        load_type = LoadType(name="Electricity", uuid="test-uuid")
    total_seconds = (end - start).total_seconds()
    split_points = sorted(rng.uniform(0, total_seconds) for _ in range(n_entries - 1))
    split_points = [0.0] + split_points + [total_seconds]

    energy_unit = str(Units.energy_unit)
    power_unit = str(Units.power_unit)

    entries: list[LoadProfileEntry] = []
    for i in range(len(split_points) - 1):
        entry_start = start + datetime.timedelta(seconds=split_points[i])
        entry_end = start + datetime.timedelta(seconds=split_points[i + 1])
        duration_s = (entry_end - entry_start).total_seconds()
        if duration_s <= 0:
            continue
        energy = rng.uniform(0, max_energy)
        power = energy / duration_s
        entries.append(
            LoadProfileEntry(
                load_type=load_type,
                start_time=entry_start,
                end_time=entry_end,
                energy_quantity=energy,
                energy_unit=energy_unit,
                average_power_consumption=power,
                power_unit=power_unit,
            )
        )
    entries.reverse()
    return entries


def make_load_profile_entries_from_tuples(
    start: datetime.datetime,
    energy_and_duration_tuples: list[tuple[float, datetime.timedelta]],
    load_type: LoadType | None = None,
    energy_unit: str | None = None,
    power_unit: str | None = None,
) -> list[LoadProfileEntry]:
    """Create contiguous load profile entries from a list of (energy, duration) tuples.

    Each tuple specifies the energy consumed and the duration of that consumption
    period. Entries are placed contiguously starting from ``start``.

    Returned in reverse chronological order.

    Args:
        start: Start time of the first entry.
        energy_and_duration_tuples: List of (energy_quantity, duration) tuples.
            Each energy value uses ``energy_unit`` and each duration is a timedelta.
        load_type: Optional LoadType. Defaults to Electricity with a test UUID.
        energy_unit: Energy unit string. Defaults to the project default (MJ).
        power_unit: Power unit string. Defaults to the project default (MW).

    Returns:
        List of LoadProfileEntry in reverse chronological order.
    """
    if load_type is None:
        load_type = LoadType(name="Electricity", uuid="test-uuid")
    if energy_unit is None:
        energy_unit = str(Units.energy_unit)
    if power_unit is None:
        power_unit = str(Units.power_unit)

    entries: list[LoadProfileEntry] = []
    current_start = start
    for energy, duration in energy_and_duration_tuples:
        current_end = current_start + duration
        duration_s = duration.total_seconds()
        if duration_s <= 0:
            raise ValueError(f"Duration must be positive, got {duration} for energy={energy}")
        power = energy / duration_s
        entries.append(
            LoadProfileEntry(
                load_type=load_type,
                start_time=current_start,
                end_time=current_end,
                energy_quantity=energy,
                energy_unit=energy_unit,
                average_power_consumption=power,
                power_unit=power_unit,
            )
        )
        current_start = current_end
    entries.reverse()
    return entries
