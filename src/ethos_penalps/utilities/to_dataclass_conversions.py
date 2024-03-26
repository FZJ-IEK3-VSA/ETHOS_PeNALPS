from dataclasses import dataclass, fields
from typing import Any

import pandas

from ethos_penalps.data_classes import (
    ProcessStepProductionPlanEntry,
    StorageProductionPlanEntry,
)
from ethos_penalps.stream import (
    BatchStreamProductionPlanEntry,
    ContinuousStreamProductionPlanEntry,
    ProcessStepProductionPlanEntryWithInputStreamState,
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
    return [
        create_dataclass(row, BatchStreamProductionPlanEntry)
        for ind, row in data.iterrows()
    ]


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
    return [
        create_dataclass(row, ContinuousStreamProductionPlanEntry)
        for ind, row in data.iterrows()
    ]


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
    return [
        create_dataclass(row, ProcessStepProductionPlanEntry)
        for ind, row in data.iterrows()
    ]


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
    return [
        create_dataclass(row, StorageProductionPlanEntry)
        for ind, row in data.iterrows()
    ]


def create_process_step_production_plan_entry_with_stream_state(
    data: pandas.DataFrame,
) -> list[ProcessStepProductionPlanEntryWithInputStreamState]:
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
    return [
        create_dataclass(row, ProcessStepProductionPlanEntryWithInputStreamState)
        for ind, row in data.iterrows()
    ]
