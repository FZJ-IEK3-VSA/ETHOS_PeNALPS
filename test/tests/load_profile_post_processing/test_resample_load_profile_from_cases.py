"""Test resampling against pre-generated reference cases.

Each case directory under ``aligned/cases/`` or ``unaligned/cases/`` contains:
  - input_load_profile.csv
  - resampled.csv   (golden reference)
  - parameters.json           (start, end, resample_frequency)

The test reads these files using SingleLoadProfileFromDiskLoader, runs the
resampler on the input, and asserts the output matches the golden reference.
"""

import datetime
import json
from dataclasses import dataclass
from pathlib import Path

import numpy
import pandas
import pytest

from ethos_penalps.data_classes import (
    LoadProfileMetaData,
    LoadProfileMetaDataResampled,
)
from ethos_penalps.post_processing.load_profiles.load_profile_entry_post_processor import (
    LoadProfileEntryPostProcessor,
)
from ethos_penalps.post_processing.load_profiles.load_profile_from_disk import (
    SingleLoadProfileFromDiskLoader,
)

CASES_DIR = Path(__file__).resolve().parents[2] / "generate" / "load_profile" / "aligned" / "cases"
UNALIGNED_CASES_DIR = Path(__file__).resolve().parents[2] / "generate" / "load_profile" / "unaligned" / "cases"


def _discover_cases(cases_dir: Path = CASES_DIR) -> list[str]:
    """Return case directory names that contain the expected files."""
    if not cases_dir.is_dir():
        return []
    required = {"input_load_profile.csv", "resampled.csv", "parameters.json"}
    return sorted(
        d.name for d in cases_dir.iterdir() if d.is_dir() and required.issubset({f.name for f in d.iterdir()})
    )


def _load_parameters(case_dir: Path) -> dict:
    with open(case_dir / "parameters.json") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Shared test data container
# ---------------------------------------------------------------------------


@dataclass
class ResamplingTestData:
    meta_data_original: LoadProfileMetaData
    params: dict
    result: LoadProfileMetaDataResampled
    reference_df: pandas.DataFrame
    case_dir: Path


def _build_test_data(cases_dir: Path, case_name: str, meta: LoadProfileMetaData, params: dict) -> ResamplingTestData:
    """Resample and load the reference CSV."""
    start = datetime.datetime.fromisoformat(params["start"])
    end = datetime.datetime.fromisoformat(params["end"])
    resample_frequency = params["resample_frequency"]

    processor = LoadProfileEntryPostProcessor()
    result = processor.resample_load_profile_meta_data(
        load_profile_meta_data=meta,
        start_date=start,
        end_date=end,
        resample_frequency=resample_frequency,
    )
    reference_df = pandas.read_csv(cases_dir / case_name / "resampled.csv")

    return ResamplingTestData(
        meta_data_original=meta,
        params=params,
        result=result,
        reference_df=reference_df,
        case_dir=cases_dir / case_name,
    )


# ---------------------------------------------------------------------------
# Aligned cases
# ---------------------------------------------------------------------------

case_names = _discover_cases()


@pytest.fixture(scope="class")
def load_profile_fixture(request) -> ResamplingTestData:
    """Compute resampling test data once per parametrized case_name."""
    case_name = request.param
    case_dir = CASES_DIR / case_name
    params = _load_parameters(case_dir)
    start = datetime.datetime.fromisoformat(params["start"])
    end = datetime.datetime.fromisoformat(params["end"])

    loader = SingleLoadProfileFromDiskLoader(
        path_to_data_frame=case_dir / "input_load_profile.csv",
        object_type="CaseTest",
    )
    meta = loader.create_meta_data(start_date=start, end_date=end)
    assert isinstance(meta, LoadProfileMetaData)
    return _build_test_data(CASES_DIR, case_name, meta, params)


@pytest.mark.parametrize("load_profile_fixture", case_names, ids=case_names, indirect=True)
class TestResampleFromCases:
    """Run the resampler on each saved case and verify correctness."""

    # --- Energy ---

    def test_energy_conservation(self, load_profile_fixture: ResamplingTestData):
        """Total energy must be conserved through resampling."""
        input_energy = sum(e.energy_quantity for e in load_profile_fixture.meta_data_original.list_of_load_profiles)
        numpy.testing.assert_allclose(load_profile_fixture.result.total_energy, input_energy, rtol=1e-9)

    def test_expected_total_energy(self, load_profile_fixture: ResamplingTestData):
        """Total energy must match the hand-calculated expected value."""
        expected = load_profile_fixture.params.get("expected_total_energy")
        if expected is None:
            pytest.skip("No expected_total_energy in parameters.json")
        numpy.testing.assert_allclose(load_profile_fixture.result.total_energy, expected, rtol=1e-9)

    # --- Power ---

    def test_power_consistency(self, load_profile_fixture: ResamplingTestData):
        """Power must equal energy / duration for each bin."""
        dt_seconds = load_profile_fixture.result.time_step.total_seconds()
        for entry in load_profile_fixture.result.list_of_load_profiles:
            expected_power = entry.energy_quantity / dt_seconds
            numpy.testing.assert_allclose(entry.average_power_consumption, expected_power, rtol=1e-12)

    # --- Time series comparison ---

    def test_resampled_values_match_reference(self, load_profile_fixture: ResamplingTestData):
        """Entry list, DataFrame, and reference CSV on disk must all agree."""
        result = load_profile_fixture.result

        # Entry list vs reference CSV (golden reference)
        entry_energies = numpy.array([e.energy_quantity for e in result.list_of_load_profiles])
        entry_power = numpy.array([e.average_power_consumption for e in result.list_of_load_profiles])
        ref_energies = load_profile_fixture.reference_df["energy_quantity"].values
        numpy.testing.assert_allclose(entry_energies, ref_energies, rtol=1e-9, atol=1e-12)
        assert len(result.list_of_load_profiles) == len(load_profile_fixture.reference_df)

        # DataFrame vs entry list (internal consistency)
        numpy.testing.assert_allclose(result.data_frame["energy_quantity"].values, entry_energies, rtol=1e-12)
        numpy.testing.assert_allclose(result.data_frame["average_power_consumption"].values, entry_power, rtol=1e-12)

        # DataFrame vs reference CSV on disk
        reference_vec_df = pandas.read_csv(load_profile_fixture.case_dir / "resampled.csv")
        numpy.testing.assert_allclose(
            result.data_frame["energy_quantity"].values,
            reference_vec_df["energy_quantity"].values,
            rtol=1e-9,
            atol=1e-12,
        )


# ---------------------------------------------------------------------------
# Unaligned start/end date cases — energy is NOT conserved
# ---------------------------------------------------------------------------

unaligned_case_names = _discover_cases(UNALIGNED_CASES_DIR)


@pytest.fixture(scope="class")
def utd(request) -> ResamplingTestData:
    """Compute unaligned resampling test data once per parametrized case_name."""
    case_name = request.param
    case_dir = UNALIGNED_CASES_DIR / case_name
    params = _load_parameters(case_dir)
    entry_start = datetime.datetime.fromisoformat(params["entry_start"])
    entry_end = datetime.datetime.fromisoformat(params["entry_end"])

    loader = SingleLoadProfileFromDiskLoader(
        path_to_data_frame=case_dir / "input_load_profile.csv",
        object_type="CaseTest",
    )
    meta = loader.create_meta_data(start_date=entry_start, end_date=entry_end)
    assert isinstance(meta, LoadProfileMetaData)
    return _build_test_data(UNALIGNED_CASES_DIR, case_name, meta, params)


@pytest.mark.parametrize("utd", unaligned_case_names, ids=unaligned_case_names, indirect=True)
class TestUnalignedResampleFromCases:
    """Resample with a window that doesn't cover all input entries."""

    # --- Energy ---

    def test_energy_within_input_bounds(self, utd: ResamplingTestData):
        """Total resampled energy must be <= input energy."""
        input_energy = sum(e.energy_quantity for e in utd.meta_data_original.list_of_load_profiles)
        assert utd.result.total_energy <= input_energy + 1e-9, (
            f"Resampled energy {utd.result.total_energy:.6f} exceeds input {input_energy:.6f}"
        )

    def test_expected_total_energy(self, utd: ResamplingTestData):
        """Total energy must match the hand-calculated expected value."""
        expected = utd.params.get("expected_total_energy")
        if expected is None:
            pytest.skip("No expected_total_energy in parameters.json")
        numpy.testing.assert_allclose(utd.result.total_energy, expected, rtol=1e-9)

    # --- Power ---

    def test_power_consistency(self, utd: ResamplingTestData):
        """Power must equal energy / duration for each bin."""
        dt_seconds = utd.result.time_step.total_seconds()
        for entry in utd.result.list_of_load_profiles:
            expected_power = entry.energy_quantity / dt_seconds
            numpy.testing.assert_allclose(entry.average_power_consumption, expected_power, rtol=1e-12)

    # --- Time series comparison ---

    def test_resampled_values_match_reference(self, utd: ResamplingTestData):
        """Entry list, DataFrame, and reference CSV must all agree."""
        result = utd.result
        entry_energies = numpy.array([e.energy_quantity for e in result.list_of_load_profiles])
        ref_energies = utd.reference_df["energy_quantity"].values
        numpy.testing.assert_allclose(entry_energies, ref_energies, rtol=1e-9, atol=1e-12)
        assert len(result.list_of_load_profiles) == len(utd.reference_df)
        numpy.testing.assert_allclose(result.data_frame["energy_quantity"].values, entry_energies, rtol=1e-12)
