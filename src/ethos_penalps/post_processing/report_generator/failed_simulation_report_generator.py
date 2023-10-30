import os
import pathlib
import traceback
import webbrowser

import datapane

from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

from ethos_penalps.debugging_information import (
    DebuggingInformationLogger,
    NodeOperationViewer,
)
from ethos_penalps.utilities.general_functions import ResultPathGenerator
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger
from ethos_penalps.process_nodes.process_step import ProcessStep
from ethos_penalps.process_nodes.process_node import ProcessNode
from ethos_penalps.stream_handler import StreamHandler


class FailedRunReportGenerator:
    def __init__(
        self,
        debugging_information_logger: DebuggingInformationLogger,
        process_node_dict: dict[str, ProcessNode],
        stream_handler: StreamHandler,
        report_directory: str | None = None,
    ) -> None:
        self.debugging_information_logger: DebuggingInformationLogger = (
            debugging_information_logger
        )
        self.process_node_dict: dict[str, ProcessNode] = process_node_dict
        self.stream_handler: StreamHandler = stream_handler
        self.group_list: list[datapane.Group] = []
        self.report_directory = report_directory
        self.open_report_after_creation: bool = True

    def add_output_directory(self, output_directory: str | None):
        if isinstance(output_directory, str):
            pathlib.Path(output_directory).mkdir(exist_ok=True)
            self.report_directory = output_directory

    def generate_report(self):
        if self.report_directory is None:
            if hasattr(PeNALPSLogger, "directory_to_log"):
                self.report_directory = PeNALPSLogger.directory_to_log
            else:
                result_path_generator = ResultPathGenerator()
                self.report_directory: str = (
                    result_path_generator.create_result_folder_relative_to_main_file(
                        subdirectory_name="report"
                    )
                )
        if hasattr(PeNALPSLogger, "directory_to_log"):
            log_data_frame = PeNALPSLogger.read_log_to_data_frame()

            # row_counter = log_data_frame.shape[0]
            # if row_counter >= 4999:
            #     output_data_frame = log_data_frame[0:4998]
            # else:
            #     output_data_frame = log_data_frame
            output_data_frame = log_data_frame
            self.group_list.append(
                datapane.Group(
                    label="Debug Log",
                    blocks=[
                        # datapane.Text(text=self.error_message, label="Error Message"),
                        datapane.HTML(
                            html=traceback.format_exc().replace("\n", "<br>"),
                            label="Error Message",
                        ),
                        # datapane.DataTable(output_data_frame),
                        datapane.DataTable(output_data_frame),
                    ],
                ),
            )
        else:
            print("No path to a log file has been saved")
        if isinstance(self.debugging_information_logger, DebuggingInformationLogger):
            node_operation_viewer = NodeOperationViewer(
                debugging_information_logger=self.debugging_information_logger,
                process_node_dict=self.process_node_dict,
                stream_handler=self.stream_handler,
                graph_directory=self.report_directory,
            )
            node_operation_viewer.create_all_node_visualizations()
            block_list = []
            for path_to_file_svg in node_operation_viewer.list_of_paths_to_images:
                # drawing = svg2rlg(path_to_file_svg)
                # path_to_enterprise_structure_graph_png = path_to_file_svg[:-4] + ".png"
                # renderPM.drawToFile(
                #     drawing, path_to_enterprise_structure_graph_png, fmt="PNG"
                # )

                block_list.append(datapane.Media(path_to_file_svg))
            print("block_list\n", block_list)
            if block_list:
                self.group_list.append(
                    datapane.Group(
                        label="Node Operation Graphs",
                        blocks=block_list,
                    )
                )
        file_name = "report_of_failed_run"
        if self.report_directory == None:
            result_path_generator = ResultPathGenerator()
            path_to_main_file = (
                result_path_generator.create_path_to_file_relative_to_main_file(
                    file_name=file_name,
                    subdirectory_name="results",
                    file_extension=".html",
                )
            )
        else:
            path_to_main_file = os.path.join(self.report_directory, file_name + ".html")

        if len(self.group_list) > 1:
            view = datapane.Select(*self.group_list)

        else:
            view = self.group_list[0]
        # https://github.com/datapane/datapane-docs/tree/v2/reports/blocks#report-types

        datapane.save_report(
            blocks=view,
            path=path_to_main_file,
            open=self.open_report_after_creation,
            formatting=datapane.Formatting(
                width=datapane.Width.FULL,
            ),
        )
