import datetime
import os
import pathlib
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

import __main__
from ethos_penalps.data_classes import (
    Commodity,
    EmptyMetaDataInformation,
    LoadProfileMetaData,
    ProcessStepDataFrameMetaInformation,
    ProcessStepProductionPlanEntry,
    StorageDataFrameMetaInformation,
    StorageProductionPlanEntry,
)
from ethos_penalps.load_profile_calculator import LoadProfileHandlerSimulation
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamProductionPlanEntry,
    ContinuousStream,
    ContinuousStreamProductionPlanEntry,
    StreamDataFrameMetaInformation,
)
from ethos_penalps.utilities.data_base_interactions import DataBaseInteractions
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.utilities.to_dataclass_conversions import (
    create_batch_stream_production_plan_entry,
    create_continuous_stream_production_plan_entry,
    create_process_step_production_plan_entry,
    create_process_step_production_plan_entry_with_stream_state,
    create_storage_production_plan_entry,
)

logger = PeNALPSLogger.get_logger_without_handler()


@dataclass(kw_only=True)
class ResultBaseClass:
    """Provides the capabilities to dump and load simulation
    data of streams, process steps and storages.
    """

    process_step_states_dict: dict[str, list[ProcessStepProductionPlanEntry]] = field(
        default_factory=dict
    )
    stream_state_dict: dict[
        str,
        list[ContinuousStreamProductionPlanEntry]
        | list[BatchStreamProductionPlanEntry],
    ] = field(default_factory=dict)
    storage_state_dict: dict[str, dict[Commodity, list[StorageProductionPlanEntry]]] = (
        field(default_factory=dict)
    )

    def save_all_simulation_results_to_sqlite(
        self,
        full_path_to_stream_data_base: str | None = None,
        full_path_to_process_step_data_base: str | None = None,
    ) -> list[str]:
        """Stores all stream and process step results to an sqlite database respectively.

        Args:
            full_path_to_stream_data_base (str | None, optional): Path to the stream
                sqlite database.. Defaults to None.
            full_path_to_process_step_data_base (str | None, optional): Path to the
                process step sqlite database. Defaults to None.

        Returns:
            list[str]: List of paths to the data bases.
        """
        list_of_output_file_paths = []
        path_to_stream_db = self.save_stream_plan_to_sqlite_db(
            full_path_to_data_base=full_path_to_stream_data_base,
        )
        path_to_process_state_db = self.save_process_state_plan_to_sqlite_db(
            full_path_to_data_base=full_path_to_process_step_data_base,
        )
        list_of_output_file_paths.append(path_to_stream_db)
        list_of_output_file_paths.append(path_to_process_state_db)
        return list_of_output_file_paths

    def save_stream_plan_to_sqlite_db(
        self,
        full_path_to_data_base: str | None = None,
    ) -> str:
        """Stores the stream simulation results to a database.

        Args:
            full_path_to_data_base (str | None, optional): Path to the stream
                database. Defaults to None.

        Returns:
            str: Path to the stream database.
        """
        if full_path_to_data_base is None:
            path_to_main_module = os.path.dirname(__main__.__file__)
            results_directory = os.path.join(path_to_main_module, "results")

            if not os.path.exists(results_directory):
                os.makedirs(results_directory)

            date_appendix = datetime.datetime.now().strftime("%Y_%m_%d__%H_%M_%S")
            file_name = "stream_plan_" + date_appendix + ".db"

            full_path_to_data_base = os.path.join(results_directory, file_name)
        else:
            pass
        if isinstance(full_path_to_data_base, str):
            if not os.path.exists(pathlib.Path(full_path_to_data_base).parent):
                os.makedirs(pathlib.Path(full_path_to_data_base).parent)

        data_base_handler = DataBaseInteractions(
            path_to_database=full_path_to_data_base
        )
        for stream_name, stream_entries in self.stream_state_dict.items():
            stream_df = pd.DataFrame(stream_entries)
            data_base_handler.write_to_database(
                data_frame=stream_df, table_name=stream_name
            )
        return full_path_to_data_base

    def save_process_state_plan_to_sqlite_db(
        self,
        full_path_to_data_base: str | None = None,
    ) -> str:
        """Creates a sqlite database from the process state plan.

        Args:
            full_path_to_data_base (str | None, optional): Path to the
                process state sqlite database. Defaults to None.

        Returns:
            str: Path to the sqlite database.
        """
        if full_path_to_data_base is None:
            path_to_main_module = os.path.dirname(__main__.__file__)
            results_directory = os.path.join(path_to_main_module, "results")

            if not os.path.exists(results_directory):
                os.makedirs(results_directory)

            date_appendix = datetime.datetime.now().strftime("%Y_%m_%d__%H_%M_%S")
            file_name = "process_states" + date_appendix + ".db"

            full_path_to_data_base = os.path.join(results_directory, file_name)
        else:
            pass
        data_base_handler = DataBaseInteractions(
            path_to_database=full_path_to_data_base
        )
        for (
            process_step_name,
            process_step_entries,
        ) in self.process_step_states_dict.items():
            stream_df = pd.DataFrame(process_step_entries)
            data_base_handler.write_to_database(
                data_frame=stream_df, table_name=process_step_name
            )
        return full_path_to_data_base

    def restore_stream_results_from_sqlite(self, path_to_database: str):
        """Read the results from the stream database to
        the current object.

        Args:
            path_to_database (str): Path to the stream sqlite database.
        """
        data_base_interactions = DataBaseInteractions(path_to_database=path_to_database)
        list_of_all_table_names = data_base_interactions.get_all_table_names()

        for table_name in list_of_all_table_names:
            data_frame = data_base_interactions.read_database(table_name=table_name)
            stream_type = data_frame.loc[0, "stream_type"]
            if stream_type == "BatchStream":
                entry_list = create_batch_stream_production_plan_entry(data=data_frame)
            elif stream_type == "ContinuousStream":
                entry_list = create_continuous_stream_production_plan_entry(
                    data=data_frame
                )

            self.stream_state_dict[table_name] = entry_list

    def restore_process_step_results_from_sqlite(self, path_to_database: str):
        """Restores the process process step results from an sqlite database.

        Args:
            path_to_database (str): Path to the sqlite database.
        """
        data_base_interactions = DataBaseInteractions(path_to_database=path_to_database)
        list_of_all_table_names = data_base_interactions.get_all_table_names()

        for table_name in list_of_all_table_names:
            data_frame = data_base_interactions.read_database(table_name=table_name)
            if "total_stream_mass" in data_frame.columns:
                entry_list = (
                    create_process_step_production_plan_entry_with_stream_state(
                        data=data_frame
                    )
                )
            else:
                entry_list = create_process_step_production_plan_entry(data=data_frame)

            self.process_step_states_dict[table_name] = entry_list

    def save_list_stream_frames_to_xlsx(
        self,
        full_path_to_xlsx_file: str | None = None,
        file_name: str | None = None,
        print_file_save_path=True,
    ):
        """Stores the stream simulation results to an xlsx file.

        Args:
            full_path_to_xlsx_file (str | None, optional): Path to the xlsx file. Defaults to None.
            file_name (str | None, optional): Name of the output file. Defaults to None.
            print_file_save_path (bool, optional): Prints the path to the xlsx file
                if set to True. Defaults to True.
        """
        logger.info("Save stream plan to xlsx starts")

        iterator = 0

        if full_path_to_xlsx_file is None:
            if file_name is None:
                file_name = "stream_plan_"
                subdirectory_name = "results"
                file_extension = ".xlsx"
                results_generator = ResultPathGenerator()
                full_path_to_xlsx_file = (
                    results_generator.create_path_to_file_relative_to_main_file(
                        file_name=file_name,
                        subdirectory_name=subdirectory_name,
                        file_extension=file_extension,
                    )
                )
            else:
                pass

        else:
            pass
        writer = pd.ExcelWriter(full_path_to_xlsx_file, engine="xlsxwriter")

        for stream_entries in self.stream_state_dict.values():
            stream_df = pd.DataFrame(stream_entries)
            sheet_name = "stream_" + str(iterator)
            stream_df.to_excel(writer, sheet_name=sheet_name)
            iterator = iterator + 1
        writer.close()
        self.path_to_stream_xlsx_file = full_path_to_xlsx_file
        if print_file_save_path is True:
            print("The stream plan has been saved to:\n" + full_path_to_xlsx_file)


@dataclass
class OutputBranchProductionPlan(ResultBaseClass):
    """Production Plan for the results of a single output stream request."""

    def add_stream_state_entry(
        self,
        stream_state_entry: (
            ContinuousStreamProductionPlanEntry | BatchStreamProductionPlanEntry
        ),
    ):
        """Adds a single stream entry to the production plan

        Args:
            stream_state_entry (ContinuousStreamProductionPlanEntry  |  BatchStreamProductionPlanEntry):
            StreamEntry that is added to the production plan.
        """
        if stream_state_entry.name in self.stream_state_dict:
            self.stream_state_dict[stream_state_entry.name].append(stream_state_entry)
        else:
            self.stream_state_dict[stream_state_entry.name] = [stream_state_entry]

    def add_storage_entry(
        self, process_step_name: str, storage_entry: StorageProductionPlanEntry
    ):
        """Adds a storage entry to the production plan

        Args:
            process_step_name (str): Name of the process step that
                owns the storage.
            storage_entry (StorageProductionPlanEntry): Entry that should
                be added to the production plan.
        """
        if process_step_name not in self.storage_state_dict:
            self.storage_state_dict[process_step_name] = {}
        if storage_entry.commodity not in self.storage_state_dict[process_step_name]:
            self.storage_state_dict[process_step_name][storage_entry.commodity] = []

        self.storage_state_dict[process_step_name][storage_entry.commodity].append(
            storage_entry
        )

    def create_self_copy(self) -> "OutputBranchProductionPlan":
        """Creates a copy of the current OutputBranchProductionPlan

        Returns:
            OutputBranchProductionPlan: Copy of the current OutputBranchProductionPlan.
        """
        copy_of_process_step_state_dictionary = self._copy_process_step_states()
        copy_of_stream_state_dictionary = self._copy_stream_states()
        copy_of_storage_state_dictionary = self._copy_storage_state_dictionaries()
        production_branch_production_plan = OutputBranchProductionPlan(
            process_step_states_dict=copy_of_process_step_state_dictionary,
            stream_state_dict=copy_of_stream_state_dictionary,
            storage_state_dict=copy_of_storage_state_dictionary,
        )

        return production_branch_production_plan

    def _copy_process_step_states(
        self,
    ) -> dict[str, list[ProcessStepProductionPlanEntry]]:
        """Copies all ProcessStepProductionPlan entries

        Returns:
            dict[str, list[ProcessStepProductionPlanEntry]]: dictionary of all
                ProcessStepProductionPlanEntry. The keys are the names of the respective
                ProcessSteps.

        """
        copy_of_process_step_state_dictionary = {}
        for name, process_step_state_list in self.process_step_states_dict.items():
            copy_of_process_step_state_dictionary[name] = list(process_step_state_list)
        return copy_of_process_step_state_dictionary

    def _copy_stream_states(
        self,
    ) -> dict[
        str,
        list[ContinuousStreamProductionPlanEntry]
        | list[BatchStreamProductionPlanEntry],
    ]:
        """Copies all stream states.

        Returns:
            dict[ str, list[ContinuousStreamProductionPlanEntry] | list[BatchStreamProductionPlanEntry], ]: A dictionary
                that contains all stream states. The keys are the names of the respective streams.
        """
        copy_of_stream_state_dictionary = {}
        for stream_name, stream_state_list in self.stream_state_dict.items():
            copy_of_stream_state_dictionary[stream_name] = list(stream_state_list)
        return copy_of_stream_state_dictionary

    def _copy_storage_state_dictionaries(
        self,
    ) -> dict[str, dict[Commodity, list[StorageProductionPlanEntry]]]:
        """Copies all storage entries.

        Returns:
            dict[str, dict[Commodity, list[StorageProductionPlanEntry]]]:  A dictionary
                that contains all storage states. The keys are the names of the respective process steps.
        """
        copy_of_storage_state_dictionary = {}
        for (
            process_step_name,
            commodity_storage_state_dictionary,
        ) in self.storage_state_dict.items():
            for (
                commodity,
                storage_state_list,
            ) in commodity_storage_state_dictionary.items():
                copy_of_storage_state_dictionary[process_step_name] = {
                    commodity: list(storage_state_list)
                }
        return copy_of_storage_state_dictionary

    def __get_list_of_all_start_and_end_times(self) -> list[datetime.datetime]:
        """Returns a list of start and end times of all process step states
        and all stream states.

        Returns:
            list[datetime.datetime]: A list of start and end times of all process step states
        and all stream states.
        """
        list_of_start_and_times = []
        if self.process_step_states_dict:
            for process_step_name in self.process_step_states_dict:
                for process_state_entry in self.process_step_states_dict[
                    process_step_name
                ]:
                    list_of_start_and_times.append(process_state_entry.start_time)
                    list_of_start_and_times.append(process_state_entry.end_time)
        if self.stream_state_dict:
            for stream_name in self.stream_state_dict:
                for stream_state in self.stream_state_dict[stream_name]:
                    list_of_start_and_times.append(stream_state.start_time)
                    list_of_start_and_times.append(stream_state.end_time)
        return list_of_start_and_times

    def determine_start_time(self) -> datetime.datetime:
        """Get the earliest start time of all entries.

        Returns:
            datetime.datetime: Earliest start time of all entries.
        """
        list_of_all_start_and_end_times = self.__get_list_of_all_start_and_end_times()
        return min(list_of_all_start_and_end_times)

    def determine_end_time(self) -> datetime.datetime:
        """Get the latest end time of all entries.

        Returns:
            datetime.datetime: Latest end time of all entries.
        """
        list_of_all_start_and_end_times = self.__get_list_of_all_start_and_end_times()
        return max(list_of_all_start_and_end_times)


@dataclass
class ProductionPlan(ResultBaseClass):
    """Collects all final simulation results of the streams, process steps
    and storages.
    """

    load_profile_handler: LoadProfileHandlerSimulation
    path_to_stream_xlsx_file: Optional[str] = ""
    path_to_process_state_xlsx_file: Optional[str] = ""

    def convert_temporary_production_plan_to_load_profile(
        self, temporary_production_plan: OutputBranchProductionPlan
    ):
        """Converts all stream and process step entries into load profiles.

        Args:
            temporary_production_plan (OutputBranchProductionPlan): Contains all
                entries that should be considered for conversion to load profiles.
        """

        for stream_entry_list in temporary_production_plan.stream_state_dict.values():
            for stream_entry in stream_entry_list:
                self.load_profile_handler.create_all_load_profiles_entries_from_stream_entry(
                    stream_entry=stream_entry
                )

        for (
            process_state_entry_list
        ) in temporary_production_plan.process_step_states_dict.values():
            for process_state_entry in process_state_entry_list:
                self.load_profile_handler.create_all_load_profiles_from_process_state_entry(
                    process_state_entry=process_state_entry,
                )

    def check_process_state_consistency(self):
        """Check if all process states align in the correct temporal
        order without gaps.

        Raises:
            Exception: Raises an exception if a gap or inconsistency was found.
        """
        for process_step_state_list in self.process_step_states_dict.values():
            last_entry = None
            for process_step_entry in process_step_state_list:
                if last_entry is not None:
                    if process_step_entry.end_time != last_entry.start_time:
                        raise Exception("Process step states do no align")
                last_entry = process_step_entry

    def add_list_of_storage_entries(
        self,
        storage_name: str,
        commodity: Commodity,
        list_of_storage_entries: list[StorageProductionPlanEntry],
    ):
        """Adds a list of storage entries to the production plan.

        Args:
            storage_name (str): Name of the storage that created
                the new entries.
            commodity (Commodity): Commodity of the storage that created
                the entries.
            list_of_storage_entries (list[StorageProductionPlanEntry]): List of storage
                entries that should be added to the production plan.
        """
        self.storage_state_dict[storage_name] = {commodity: list_of_storage_entries}

    def add_temporary_production_plan(
        self, temporary_production_plan: OutputBranchProductionPlan
    ):
        """Adds all entries from a temporary production plan to the final production plan.

        Args:
            temporary_production_plan (OutputBranchProductionPlan): Temporary production plan
                that should be added to the final production plan.
        """
        for stream_name in temporary_production_plan.stream_state_dict:
            if stream_name in self.stream_state_dict:
                self.stream_state_dict[stream_name].extend(
                    temporary_production_plan.stream_state_dict[stream_name]
                )
            else:
                self.stream_state_dict[stream_name] = (
                    temporary_production_plan.stream_state_dict[stream_name]
                )
        for process_step_name in temporary_production_plan.process_step_states_dict:
            if process_step_name in self.process_step_states_dict:
                self.process_step_states_dict[process_step_name].extend(
                    temporary_production_plan.process_step_states_dict[
                        process_step_name
                    ]
                )
            else:
                self.process_step_states_dict[process_step_name] = (
                    temporary_production_plan.process_step_states_dict[
                        process_step_name
                    ]
                )

        for process_step_name in temporary_production_plan.storage_state_dict:
            if process_step_name not in self.storage_state_dict:
                self.storage_state_dict[process_step_name] = {}
            for commodity in temporary_production_plan.storage_state_dict[
                process_step_name
            ]:
                if commodity not in self.storage_state_dict[process_step_name]:
                    self.storage_state_dict[process_step_name][commodity] = []
                self.storage_state_dict[process_step_name][commodity].extend(
                    temporary_production_plan.storage_state_dict[process_step_name][
                        commodity
                    ]
                )
        self.check_process_state_consistency()

    # def read_xlsx_to_list_of_data_frames(
    #     self, path_to_xlsx_file: str
    # ) -> list[pd.DataFrame]:
    #     dict_of_stream_dfs = pd.read_excel(path_to_xlsx_file, sheet_name=None)
    #     list_of_stream_dfs = dict_of_stream_dfs.values()
    #     self.dict_of_stream_meta_data_data_frames = list_of_stream_dfs

    #     return list_of_stream_dfs

    def initialize_process_step_production_plan_entry(self, process_step_name: str):
        """Creates lists for each to process step that are used to store
        the simulation results.

        Args:
            process_step_name (str): Name of the process step that should
                requires an initial list.
        """
        self.process_step_states_dict[process_step_name] = []

    def initialize_stream_production_plan_entry(self, stream_name: str):
        """Creates an empty list for each stream to store the simulation results.

        Args:
            stream_name (str): Name of the stream that should be initialized.
        """
        self.stream_state_dict[stream_name] = []

    # def save_list_of_process_states_to_xlsx(
    #     self,
    #     full_path_to_xlsx_file: str,
    #     print_file_save_path: bool = True,
    # ):
    #     logger.debug("Store process states to xlsx has been called")

    #     writer = pd.ExcelWriter(path=full_path_to_xlsx_file, engine="xlsxwriter")
    #     iterator = 0
    #     for process_state_entries in self.process_step_states.values():
    #         process_state_df = pd.DataFrame(process_state_entries)
    #         self.dict_of_process_step_data_frames.append(process_state_df)
    #         sheet_name = "process_state_" + str(iterator)
    #         process_state_df.to_excel(writer, sheet_name=sheet_name)
    #         iterator = iterator + 1
    #     writer.save()
    #     self.path_to_stream_xlsx_file = full_path_to_xlsx_file
    #     if print_file_save_path:
    #         print("The stream plan has been saved to:\n" + full_path_to_xlsx_file)
