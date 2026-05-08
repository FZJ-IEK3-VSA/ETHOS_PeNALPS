"""Tests for BaseStorage.create_net_mass_duration_array and
_create_storage_entries_from_duration_array.

Test cases are loaded from disk:
  - test/generate/storage/01_single_continuous_stream/cases/
  - test/generate/storage/02_single_batch_stream/cases/
  - test/generate/storage/03_balanced_timing/cases/
  - test/generate/storage/04_multiple_streams/cases/
  - test/generate/storage/05_mixed_stream_types/cases/
  - test/generate/storage/06_time_bounds/cases/
Generate them by running the generate.ipynb notebook in each subdirectory.

Each case is validated for:
    - Contiguous time segments
    - Continuous storage levels (no jumps between entries)
    - Non-negative storage levels (when storage_level_at_start="auto_offset")
    - Mass conservation
    - Match against golden reference values
"""

import datetime
from pathlib import Path

import numpy
import pytest

from ethos_penalps.stream import BatchStreamState, ContinuousStreamState
from ethos_penalps.testing.storage.storage_sanity_checks import (
    assert_entries_contiguous,
    assert_entries_match_expected,
    assert_mass_conservation,
    assert_non_negative,
)
from ethos_penalps.testing.storage.storage_test_case import (
    StorageTestCaseSpecification,
    build_case_from_parameters,
)
from ethos_penalps.testing.storage.storage_test_case_io import (
    list_available_cases,
    load_expected_entries_csv,
    load_storage_test_case,
)
from ethos_penalps.testing.stream.stream_group_test_case import (
    StreamGroupTestCaseSpecification,
)
from ethos_penalps.testing.stream.stream_test_case import (
    ContinuousStreamStateParams,
    ContinuousStreamTestCaseSpecification,
)

_GENERATE_DIR = Path(__file__).resolve().parents[2] / "generate" / "storage"

_CASE_DIRS = [
    _GENERATE_DIR / "01_single_continuous_stream" / "cases",
    _GENERATE_DIR / "02_single_batch_stream" / "cases",
    _GENERATE_DIR / "03_balanced_timing" / "cases",
    _GENERATE_DIR / "04_multiple_streams" / "cases",
    _GENERATE_DIR / "05_mixed_stream_types" / "cases",
    _GENERATE_DIR / "06_time_bounds" / "cases",
    _GENERATE_DIR / "07_regression_random" / "cases",
]


def _discover_all_cases() -> list[tuple[Path, str]]:
    """Return (cases_dir, case_name) pairs from all directories."""
    cases: list[tuple[Path, str]] = []
    for cases_dir in _CASE_DIRS:
        for name in list_available_cases(str(cases_dir)):
            cases.append((cases_dir, name))
    return cases


_ALL_CASES = _discover_all_cases()


@pytest.fixture(params=_ALL_CASES, ids=lambda t: t[1])
def case_name_and_dir(request):
    return request.param


@pytest.fixture
def case(case_name_and_dir):
    cases_dir, case_name = case_name_and_dir
    case_dir = str(cases_dir / case_name)
    return load_storage_test_case(case_dir)


@pytest.fixture
def expected(case_name_and_dir):
    cases_dir, case_name = case_name_and_dir
    case_dir = str(cases_dir / case_name)
    return load_expected_entries_csv(case_dir)


def _sum_stream_mass(states: list[ContinuousStreamState | BatchStreamState]) -> float:
    """Sum mass across continuous and batch stream states."""
    total = 0.0
    for state in states:
        if isinstance(state, ContinuousStreamState):
            total += state.total_mass
        elif isinstance(state, BatchStreamState):
            total += state.batch_mass_value
    return total


class TestStorageEntriesFromCases:
    """Run structural and golden-reference checks on all generated cases."""

    def test_entries_contiguous(self, case):
        assert_entries_contiguous(case.entries)

    def test_non_negative_when_auto_offset(self, case):
        if case.parameters.start_storage_level == "auto_offset":
            assert_non_negative(case.entries)

    def test_mass_conservation_duration_array(self, case):
        """Net mass from duration array equals change in storage level."""
        total_net_mass = float(case.duration_array[:, 3].sum())
        expected_end = case.start_storage_level + total_net_mass
        actual_end = case.entries[-1].storage_level_at_end
        assert numpy.isclose(actual_end, expected_end, atol=1e-9), (
            f"Mass not conserved: end={actual_end}, expected={expected_end}"
        )

    def test_mass_conservation_streams(self, case):
        """Total input mass minus total output mass equals storage level change.

        Skipped for cases with time bounds because stream states contain
        the full (uncut) mass while entries only cover the cut window.
        """
        has_time_bounds = (
            case.parameters.storage_entry_start_time is not None or case.parameters.storage_entry_end_time is not None
        )
        if has_time_bounds:
            return
        total_input = _sum_stream_mass(case.input_group.all_states)
        total_output = _sum_stream_mass(case.output_group.all_states)
        expected_end = case.start_storage_level + total_input - total_output
        actual_end = case.entries[-1].storage_level_at_end
        assert numpy.isclose(actual_end, expected_end, atol=1e-9), (
            f"Stream mass not conserved: input={total_input}, output={total_output}, "
            f"start={case.start_storage_level}, expected_end={expected_end}, actual_end={actual_end}"
        )

    def test_matches_golden_reference(self, case, expected):
        assert_entries_match_expected(case.entries, expected)


# ---------------------------------------------------------------------------
# Duration array structural tests (not case-dependent)
# ---------------------------------------------------------------------------


class TestNetMassDurationArray:
    """Verify the structure of create_net_mass_duration_array output."""

    def test_array_shape(self, case):
        """Array has 4 columns: start_seconds, end_seconds, duration, net_mass."""
        assert case.duration_array.ndim == 2
        assert case.duration_array.shape[1] == 4

    def test_durations_are_non_negative(self, case):
        """Durations >= 0. Batch streams may have zero-duration (instantaneous) segments."""
        assert numpy.all(case.duration_array[:, 2] >= 0)

    def test_time_segments_contiguous(self, case):
        end_times = case.duration_array[:-1, 1]
        start_times = case.duration_array[1:, 0]
        assert numpy.allclose(end_times, start_times, atol=1e-6)


# ---------------------------------------------------------------------------
# Time-bound cutting tests (inline, no golden references)
# ---------------------------------------------------------------------------

_T0 = datetime.datetime(2022, 1, 1)

# Input: T0-1h → T0+5h (300 kg at 50/h), Output: T0+1h → T0+7h (300 kg at 50/h).
# Storage profile (full range, auto_offset=0):
#   T0-1h → T0+1h : input only  → rises  0 → 100
#   T0+1h → T0+5h : both active → flat at 100
#   T0+5h → T0+7h : output only → drops  100 → 0
_OVERLAPPING_STREAMS_SPEC = StorageTestCaseSpecification(
    name="overlapping_streams",
    description="Overlapping continuous streams for time-bound cutting tests.",
    start_time=_T0,
    input_stream_group=StreamGroupTestCaseSpecification(
        stream_specifications=[
            ContinuousStreamTestCaseSpecification(
                states=[ContinuousStreamStateParams(mass=300, rate=50, duration_seconds=21600)],
                start_offset_seconds=-3600,
            )
        ]
    ),
    output_stream_group=StreamGroupTestCaseSpecification(
        stream_specifications=[
            ContinuousStreamTestCaseSpecification(
                states=[ContinuousStreamStateParams(mass=300, rate=50, duration_seconds=21600)],
                start_offset_seconds=3600,
            )
        ]
    ),
    start_storage_level="auto_offset",
)


def _build_overlapping_case(
    start_time: datetime.datetime | None = None,
    end_time: datetime.datetime | None = None,
) -> "StorageTestCaseSpecification":
    """Return a copy of _OVERLAPPING_STREAMS_SPEC with optional time bounds."""
    import dataclasses

    return build_case_from_parameters(
        dataclasses.replace(
            _OVERLAPPING_STREAMS_SPEC,
            storage_entry_start_time=start_time,
            storage_entry_end_time=end_time,
        )
    )


class TestCreateStorageEntriesWithStartEndTime:
    """Verify that start_time/end_time parameters on
    create_storage_entries_from_streams correctly cut streams at the
    boundaries and influence the auto_offset calculation.

    Fixture layout:
        Input:  T0-1h ──────────────── T0+5h   (6 h, 300 kg, 50 kg/h)
        Output:         T0+1h ──────────────── T0+7h   (6 h, 300 kg, 50 kg/h)
    """

    def test_start_time_cuts_input_startup(self):
        """start_time=T0 cuts 1h of input startup (1/6 of 300 kg = 50 kg lost).
        Net mass in window: 250 - 300 = -50."""
        case = _build_overlapping_case(start_time=_T0)

        net_mass = float(case.duration_array[:, 3].sum())
        assert net_mass == pytest.approx(-50.0, abs=1e-9)
        assert case.entries[0].start_time >= _T0
        assert max(e.storage_level_at_end for e in case.entries) > 0

    def test_end_time_cuts_output_cooldown(self):
        """end_time=T0+6h cuts 1h of output cooldown (1/6 of 300 kg = 50 kg saved).
        Net mass in window: 300 - 250 = 50."""
        case = _build_overlapping_case(end_time=_T0 + datetime.timedelta(hours=6))

        net_mass = float(case.duration_array[:, 3].sum())
        assert net_mass == pytest.approx(50.0, abs=1e-9)
        assert case.entries[-1].end_time <= _T0 + datetime.timedelta(hours=6)
        assert max(e.storage_level_at_end for e in case.entries) > 0

    def test_both_bounds_cut_startup_and_cooldown(self):
        """Both streams lose 50 kg symmetrically → net mass = 0.
        Storage rises to 50, plateaus, then drops back to 0."""
        case = _build_overlapping_case(
            start_time=_T0,
            end_time=_T0 + datetime.timedelta(hours=6),
        )

        net_mass = float(case.duration_array[:, 3].sum())
        assert net_mass == pytest.approx(0.0, abs=1e-9)
        assert case.entries[0].start_time >= _T0
        assert case.entries[-1].end_time <= _T0 + datetime.timedelta(hours=6)
        assert max(e.storage_level_at_end for e in case.entries) == pytest.approx(50.0, abs=1e-9)

    def test_auto_offset_changes_with_cut(self):
        """Full range has auto_offset=0. Cutting startup removes 50 kg of input,
        making output exceed input. Auto_offset must increase to compensate."""
        full = _build_overlapping_case()
        assert full.start_storage_level == pytest.approx(0.0, abs=1e-9)

        cut = _build_overlapping_case(start_time=_T0)
        assert cut.start_storage_level == pytest.approx(50.0, abs=1e-9)

    def test_non_negative_levels_with_cut_auto_offset(self):
        """Storage levels are non-negative when auto_offset is used with
        cutting bounds on both sides."""
        case = _build_overlapping_case(
            start_time=_T0,
            end_time=_T0 + datetime.timedelta(hours=6),
        )
        for entry in case.entries:
            assert entry.storage_level_at_start >= -1e-9
            assert entry.storage_level_at_end >= -1e-9

    def test_mass_conservation_with_cut_bounds(self):
        """Mass conservation holds for the cut subset."""
        case = _build_overlapping_case(
            start_time=_T0,
            end_time=_T0 + datetime.timedelta(hours=6),
        )
        total_net_mass = float(case.duration_array[:, 3].sum())
        expected_end = case.start_storage_level + total_net_mass
        actual_end = case.entries[-1].storage_level_at_end
        assert actual_end == pytest.approx(expected_end, abs=1e-9)
