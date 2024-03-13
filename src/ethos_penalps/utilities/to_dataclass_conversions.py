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
    return factory(**{f.name: data[f.name] for f in fields(factory)})


def create_batch_stream_production_plan_entry(
    data: pandas.DataFrame,
) -> list[BatchStreamProductionPlanEntry]:
    return [
        create_dataclass(row, BatchStreamProductionPlanEntry)
        for ind, row in data.iterrows()
    ]


def create_continuous_stream_production_plan_entry(
    data: pandas.DataFrame,
) -> list[ContinuousStreamProductionPlanEntry]:
    return [
        create_dataclass(row, ContinuousStreamProductionPlanEntry)
        for ind, row in data.iterrows()
    ]


def create_process_step_production_plan_entry(
    data: pandas.DataFrame,
) -> list[ProcessStepProductionPlanEntry]:
    return [
        create_dataclass(row, ProcessStepProductionPlanEntry)
        for ind, row in data.iterrows()
    ]


def create_storage_production_plan_entry(
    data: pandas.DataFrame,
) -> list[StorageProductionPlanEntry]:
    return [
        create_dataclass(row, StorageProductionPlanEntry)
        for ind, row in data.iterrows()
    ]


def create_process_step_production_plan_entry_with_stream_state(
    data: pandas.DataFrame,
) -> list[ProcessStepProductionPlanEntryWithInputStreamState]:
    return [
        create_dataclass(row, ProcessStepProductionPlanEntryWithInputStreamState)
        for ind, row in data.iterrows()
    ]
