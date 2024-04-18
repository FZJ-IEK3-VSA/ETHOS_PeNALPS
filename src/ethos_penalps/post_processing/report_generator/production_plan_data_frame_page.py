import datapane
import pandas

from ethos_penalps.data_classes import EmptyMetaDataInformation
from ethos_penalps.post_processing.post_processed_data_handler import (
    PostProcessSimulationDataHandler,
)
from ethos_penalps.post_processing.report_generator.report_options import (
    ReportGeneratorOptions,
)
from ethos_penalps.production_plan import ProductionPlan
from ethos_penalps.stream import (
    BatchStream,
    BatchStreamProductionPlanEntry,
    ContinuousStream,
    ContinuousStreamProductionPlanEntry,
)
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


class DataFramePageGenerator:
    """Creates a page which contains the production plan data frames."""

    def __init__(
        self,
        production_plan: ProductionPlan,
        post_process_simulation_data_handler: PostProcessSimulationDataHandler,
    ) -> None:
        """

        Args:
            production_plan (ProductionPlan): Contains the unprocessed
                simulation results.
            post_process_simulation_data_handler (PostProcessSimulationDataHandler): Contains
            the processed simulation results.
        """
        self.production_plan: ProductionPlan = production_plan
        self.post_process_simulation_data_handler: PostProcessSimulationDataHandler = (
            post_process_simulation_data_handler
        )

    def create_stream_state_data_frame_selector(
        self, report_generator_options: ReportGeneratorOptions
    ) -> datapane.Select | None:
        """

        Args:
            report_generator_options (ReportGeneratorOptions): Is an object
                that contains the parameters to adjust the report
                appearance.

        Returns:
            datapane.Select | None: DataPane object of the stream data frames
            in the production plan.
        """
        stream_state_block_list = []
        if (
            report_generator_options.production_plan_data_frame.include_stream_data_frames
            is True
        ):
            logger.info("Start generation of page with stream data frames")
            stream_data_frame_list = list(
                (
                    self.post_process_simulation_data_handler.dict_of_stream_meta_data_data_frames.values()
                )
            )
            for stream_data_frame_meta_information in stream_data_frame_list:
                if isinstance(
                    stream_data_frame_meta_information, EmptyMetaDataInformation
                ):
                    stream_data_frame_and_summary_group.append(
                        datapane.HTML(
                            "No results are stored for: "
                            + str(stream_data_frame_meta_information.name)
                        )
                    )
                elif stream_data_frame_meta_information.data_frame.empty:
                    stream_data_frame_and_summary_group.append(
                        datapane.HTML(
                            "No results are stored for: "
                            + str(stream_data_frame_meta_information.stream_name)
                        )
                    )
                else:
                    stream_data_frame_and_summary_group = []
                    stream_data_frame_and_summary_group.append(
                        datapane.DataTable(
                            stream_data_frame_meta_information.data_frame,
                            label=stream_data_frame_meta_information.name_to_display,
                        )
                    )

                    if (
                        stream_data_frame_meta_information.stream_type
                        == BatchStream.stream_type
                    ):
                        total_stream_mass = (
                            stream_data_frame_meta_information.data_frame.loc[
                                :, "batch_mass_value"
                            ]
                        ).sum()
                    elif (
                        stream_data_frame_meta_information.stream_type
                        == ContinuousStream.stream_type
                    ):
                        total_stream_mass = (
                            stream_data_frame_meta_information.data_frame.loc[
                                :, "total_mass"
                            ]
                        ).sum()
                    else:
                        raise Exception("Unexpected stream data type")
                    stream_data_frame_and_summary_group.append(
                        datapane.HTML(
                            "The total mass of all streams is: "
                            + str(total_stream_mass)
                        )
                    )
                    stream_state_block_list.append(
                        datapane.Group(
                            blocks=stream_data_frame_and_summary_group,
                            label=stream_data_frame_meta_information.name_to_display,
                        )
                    )
        if stream_state_block_list:
            stream_state_data_frame_selector = datapane.Select(
                blocks=stream_state_block_list, label="Stream States"
            )
        else:
            stream_state_data_frame_selector = None

        return stream_state_data_frame_selector

    def create_process_state_data_frame_selector(
        self, report_generator_options: ReportGeneratorOptions
    ) -> datapane.Select | datapane.Group | None:
        """

        Args:
            report_generator_options (ReportGeneratorOptions): Is an object
                that contains the parameters to adjust the report
                appearance.

        Returns:
            datapane.Select | None: DataPane object of the process state data frames
            in the production plan.
        """
        process_state_block_list = []
        if (
            report_generator_options.production_plan_data_frame.include_process_step_data_frames
            is True
        ):
            logger.info("Start generation of page with process state data frames")

            process_state_data_frame_list = list(
                self.post_process_simulation_data_handler.dict_of_process_step_data_frames.values()
            )
            for (
                process_state_data_frame_meta_information
            ) in process_state_data_frame_list:
                if process_state_data_frame_meta_information.data_frame.empty:
                    pass
                else:
                    process_state_block_list.append(
                        datapane.DataTable(
                            process_state_data_frame_meta_information.data_frame,
                            label=process_state_data_frame_meta_information.process_step_name,
                        )
                    )
        if len(process_state_block_list) > 1:
            process_state_data_frame_selector = datapane.Select(
                blocks=process_state_block_list, label="Process States"
            )
        elif len(process_state_block_list) == 1:
            process_state_data_frame_selector = datapane.Group(
                blocks=process_state_block_list, label="Process States"
            )
        else:
            process_state_data_frame_selector = None

        return process_state_data_frame_selector

    def create_storage_state_data_frame_page(
        self, report_generator_options: ReportGeneratorOptions
    ) -> datapane.Select | datapane.Group | None:
        """

        Args:
            report_generator_options (ReportGeneratorOptions): Is an object
                that contains the parameters to adjust the report
                appearance.

        Returns:
            datapane.Select | None: DataPane object of the storage frames
            in the production plan.
        """
        logger.info("Start generation storage state data frame page")
        storage_state_block_list = []
        if (
            report_generator_options.production_plan_data_frame.include_storage_data_frames
            is True
        ):
            # storage_block_list = []
            storage_state_dictionary = self.production_plan.storage_state_dict
            for process_step_name in storage_state_dictionary:
                for commodity in storage_state_dictionary[process_step_name]:
                    storage_data_frame = pandas.DataFrame(
                        storage_state_dictionary[process_step_name][commodity]
                    )
                    storage_state_block_list.append(
                        datapane.DataTable(
                            storage_data_frame,
                            caption=process_step_name,
                            label=process_step_name,
                        )
                    )

        if len(storage_state_block_list) > 1:
            process_state_data_frame_selector = datapane.Select(
                blocks=storage_state_block_list,
                label="Storage States",
            )
        elif len(storage_state_block_list) == 1:
            process_state_data_frame_selector = datapane.Group(
                blocks=storage_state_block_list, label="Storage States"
            )
        else:
            process_state_data_frame_selector = None

        return process_state_data_frame_selector

    def create_data_frame_page(
        self, report_generator_options: ReportGeneratorOptions
    ) -> datapane.Group:
        """_summary_

        Args:
            report_generator_options (ReportGeneratorOptions): Is an object
                that contains the parameters to adjust the report
                appearance.

        Returns:
            datapane.Select | None: Creates the production plan data frame page
                of the report.
        """
        logger.info("Create generate production plan data page")
        data_frame_block_list = []
        process_state_data_frame_selector = (
            self.create_process_state_data_frame_selector(
                report_generator_options=report_generator_options
            )
        )
        if isinstance(process_state_data_frame_selector, datapane.Select):
            data_frame_block_list.append("# Process step data frames")
            data_frame_block_list.append(process_state_data_frame_selector)
        else:
            data_frame_block_list.append(
                "# No process step  data frames have been created"
            )
        stream_state_data_frame_selector = self.create_stream_state_data_frame_selector(
            report_generator_options=report_generator_options
        )
        if isinstance(stream_state_data_frame_selector, datapane.Select):
            data_frame_block_list.append("# Stream data frames")
            data_frame_block_list.append(stream_state_data_frame_selector)
        else:
            data_frame_block_list.append("# No stream data frames have been created")

        storage_data_frame_selector = self.create_storage_state_data_frame_page(
            report_generator_options=report_generator_options
        )
        if isinstance(storage_data_frame_selector, datapane.Select):
            data_frame_block_list.append("# Storage data frames")
            data_frame_block_list.append(storage_data_frame_selector)
        else:
            data_frame_block_list.append("# No storage data frames have been created")

        data_frame_page = datapane.Group(
            label="Production Plan Data Frames",
            blocks=[
                *data_frame_block_list,
            ],
        )
        return data_frame_page
