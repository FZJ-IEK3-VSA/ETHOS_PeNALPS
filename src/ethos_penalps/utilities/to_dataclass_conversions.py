import datetime
import json
from dataclasses import dataclass, fields
from typing import Any

import pandas

from ethos_penalps.data_classes import (
    LoadProfileEntry,
    LoadType,
    ProcessStepProductionPlanEntry,
    StorageProductionPlanEntry,
)
from ethos_penalps.stream import (
    BatchStreamProductionPlanEntry,
    ContinuousStreamProductionPlanEntry,
    ProcessStepProductionPlanEntryWithMass,
)


def create_dataclass(data: pandas.Series, factory: Any) -> Any:
    """Creates a dataclass based on a pandas series.

    Args:
        data (pandas.Series): Series that should be converted into
            a dataclass
        factory (Any): Constructor of the dataclass.

    Returns:
        Any: Instance of the dataclass.
    """
    return factory(**{f.name: data[f.name] for f in fields(factory)})


def _create_dataclass_list_from_dataframe(data: pandas.DataFrame, factory: Any) -> list:
    """Creates a list of dataclass instances from a DataFrame using itertuples.

    This is significantly faster than using iterrows() because itertuples()
    avoids creating a new Series object per row.

    Args:
        data (pandas.DataFrame): DataFrame to convert.
        factory (Any): Dataclass constructor.

    Returns:
        list: List of dataclass instances.
    """
    field_names = [f.name for f in fields(factory)]
    return [factory(**{name: getattr(row, name) for name in field_names}) for row in data.itertuples(index=False)]


def create_batch_stream_production_plan_entry(
    data: pandas.DataFrame,
) -> list[BatchStreamProductionPlanEntry]:
    """Creates a list of BatchStreamProductionPlanEntry based
    on a data frame that was created from a list of
    BatchStreamProductionPlanEntry.

    Args:
        data (pandas.DataFrame): Data frame that was created from a list of
    BatchStreamProductionPlanEntry.

    Returns:
        list[BatchStreamProductionPlanEntry]: List of BatchStreamProductionPlanEntry
            that was stored in a data frame.
    """
    return _create_dataclass_list_from_dataframe(data, BatchStreamProductionPlanEntry)


def create_continuous_stream_production_plan_entry(
    data: pandas.DataFrame,
) -> list[ContinuousStreamProductionPlanEntry]:
    """Creates a list of ContinuousStreamProductionPlanEntry based
    on a data frame that was created from a list of
    ContinuousStreamProductionPlanEntry.

    Args:
        data (pandas.DataFrame): Data frame that was created from a list of
    ContinuousStreamProductionPlanEntry.

    Returns:
        list[ContinuousStreamProductionPlanEntry]: List of ContinuousStreamProductionPlanEntry
            that was stored in a data frame.
    """
    return _create_dataclass_list_from_dataframe(data, ContinuousStreamProductionPlanEntry)


def create_process_step_production_plan_entry(
    data: pandas.DataFrame,
) -> list[ProcessStepProductionPlanEntry]:
    """Creates a list of ProcessStepProductionPlanEntry based
    on a data frame that was created from a list of
    ProcessStepProductionPlanEntry.

    Args:
        data (pandas.DataFrame): Data frame that was created from a list of
    ProcessStepProductionPlanEntry.

    Returns:
        list[ProcessStepProductionPlanEntry]: List of ProcessStepProductionPlanEntry
            that was stored in a data frame.
    """
    return _create_dataclass_list_from_dataframe(data, ProcessStepProductionPlanEntry)


def create_storage_production_plan_entry(
    data: pandas.DataFrame,
) -> list[StorageProductionPlanEntry]:
    """Creates a list of StorageProductionPlanEntry based
    on a data frame that was created from a list of
    StorageProductionPlanEntry.

    Args:
        data (pandas.DataFrame): Data frame that was created from a list of
    StorageProductionPlanEntry.


    Returns:
        list[StorageProductionPlanEntry]: List of StorageProductionPlanEntry
            that was stored in a data frame.
    """
    return _create_dataclass_list_from_dataframe(data, StorageProductionPlanEntry)


def create_process_step_production_plan_entry_with_stream_state(
    data: pandas.DataFrame,
) -> list[ProcessStepProductionPlanEntryWithMass]:
    """Creates a list of StorageProductionPlanEntry based
    on a data frame that was created from a list of
    ProcessStepProductionPlanEntryWithInputStreamState.

    Args:
        data (pandas.DataFrame): Data frame that was created from a list of
    ProcessStepProductionPlanEntryWithInputStreamState.

    Returns:
        list[ProcessStepProductionPlanEntryWithInputStreamState]: List of ProcessStepProductionPlanEntryWithInputStreamState
            that was stored in a data frame.
    """
    return _create_dataclass_list_from_dataframe(data, ProcessStepProductionPlanEntryWithMass)


def create_load_profile_entry(
    data: pandas.DataFrame,
) -> list[LoadProfileEntry]:
    """Creates a list of LoadProfileEntry based
    on a data frame that was created from a list of
    LoadProfileEntry.

    Args:
        data (pandas.DataFrame): Data frame that was created from a list of
    LoadProfileEntry.


    Returns:
        list[LoadProfileEntry]: List of LoadProfileEntry
            that was stored in a data frame.
    """
    return _create_dataclass_list_from_dataframe(data, LoadProfileEntry)


def create_load_type_from_string(input_string: str) -> LoadType:
    input_string = input_string.replace("'", '"')
    load_type_dict = json.loads(s=input_string)
    load_type = LoadType(name=load_type_dict["name"], uuid=load_type_dict["uuid"])
    return load_type
