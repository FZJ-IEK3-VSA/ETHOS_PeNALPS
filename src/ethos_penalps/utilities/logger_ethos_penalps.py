import logging
import os
import sys
from typing import ClassVar

import pandas as pd

from ethos_penalps.data_classes import CurrentProcessNode, LoopCounter
from ethos_penalps.utilities.general_functions import ResultPathGenerator

logging.basicConfig(
    level=logging.CRITICAL,
)


class ContextFilter(logging.Filter):
    """
    This is a filter which injects contextual information into the log.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        loop_counter = LoopCounter.loop_number
        current_node_name = CurrentProcessNode.node_name
        record.loop_counter = loop_counter
        record.current_node_name = current_node_name
        return True


class PeNALPSLogger:
    """This class summarizes the configuration of the logging
    capabilities of ETHOS.PeNALPS.
    """

    logger_name: ClassVar[str] = "ethos_penalps"
    table_delimiter: ClassVar[str] = "DELIMITER"
    prepend_loop_counter: ClassVar[bool] = True
    has_been_called: ClassVar[bool] = False
    logger: ClassVar[logging.Logger] = logging.getLogger(logger_name)
    directory_to_log: ClassVar[str | None] = None
    path_to_log: ClassVar[str | None] = None

    @staticmethod
    def initialize_logger() -> logging.Logger:
        """Initializes the logger"""
        root = logging.getLogger()
        root.removeHandler(root.handlers[0])
        table_logger: logging.Logger = PeNALPSLogger.logger
        table_logger.propagate = False
        table_logger.addFilter(ContextFilter())
        table_logger.setLevel(logging.INFO)
        # table_logger.addHandler(logging.NullHandler())
        return table_logger

    @staticmethod
    def get_logger_without_handler() -> logging.Logger:
        """Returns a logger without handler. This logger
        is used in the modules of ETHOS.PeNALPS.
        Adding the handler later allows to easily silence
        the logger
        """
        # https://docs.python.org/3/library/logging.html#logrecord-attributes
        # create logger
        if not PeNALPSLogger.has_been_called:
            PeNALPSLogger.has_been_called = True
            PeNALPSLogger.initialize_logger()

        table_logger: logging.Logger = PeNALPSLogger.logger
        return table_logger

    @staticmethod
    def get_human_readable_logger(logging_level: int = logging.INFO) -> logging.Logger:
        """Returns a logger configuration that can easily be read by humans."""
        # create logger
        logger: logging.Logger = PeNALPSLogger.logger

        # create console handler and set level to debug
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging_level)
        # create formatter
        # More attributes:
        # https://docs.python.org/3/library/logging.html#logrecord-attributes
        formatter = logging.Formatter("%(filename)s %(funcName)s line:%(lineno)d :%(message)s ")

        # add formatter to console handler
        console_handler.setFormatter(formatter)
        # add ch to logger
        logger.addHandler(console_handler)

        # https://docs.python.org/3/howto/logging-cookbook.html#context-info

        return logger

    @staticmethod
    def get_logger_to_create_table(logging_level: int = logging.INFO) -> logging.Logger:
        """Returns a logger configuration that can easily be converted to a table."""
        logger: logging.Logger = PeNALPSLogger.logger
        logger.setLevel(logging_level)
        result_path_generator = ResultPathGenerator()
        directory_to_log = result_path_generator.create_result_folder_relative_to_main_file(
            subdirectory_name="results", add_time_stamp_to_filename=True
        )
        PeNALPSLogger.directory_to_log = directory_to_log
        path_to_log_file = os.path.join(directory_to_log, "table.log")
        PeNALPSLogger.path_to_log = path_to_log_file

        table_delimiter = PeNALPSLogger.table_delimiter
        # create formatter
        # More attributes:
        # https://docs.python.org/3/library/logging.html#logrecord-attributes

        log_file_formatter = logging.Formatter(
            "%(current_node_name)s"
            + table_delimiter
            + "%(loop_counter)s"
            + table_delimiter
            + "%(filename)s"
            + table_delimiter
            + "%(funcName)s "
            + table_delimiter
            + "%(lineno)d"
            + table_delimiter
            + "%(message)s "
        )

        file_handler = logging.FileHandler(path_to_log_file)

        file_handler.setFormatter(log_file_formatter)

        # https://docs.python.org/3/howto/logging-cookbook.html#context-info
        # add formatter to ch
        file_handler.setLevel(logging_level)
        logger.addHandler(file_handler)
        return logger

    @staticmethod
    def read_log_to_data_frame(path_to_log_file: str | None = None) -> pd.DataFrame:
        """Reads the logger entries to a table."""
        log_path: str = path_to_log_file if path_to_log_file is not None else PeNALPSLogger.path_to_log  # type: ignore[assignment]
        data_frame = pd.read_csv(
            filepath_or_buffer=log_path,
            delimiter=PeNALPSLogger.table_delimiter,
            engine="python",
        )
        if PeNALPSLogger.prepend_loop_counter:
            data_frame.columns = [
                "Current node name",
                "Main Loop Iteration",
                "Module",
                "Method",
                "Module line",
                "Log Message",
            ]
        elif PeNALPSLogger.prepend_loop_counter is False:
            data_frame.columns = [
                "Module",
                "Method",
                "Module line",
                "Log Message",
            ]
        return data_frame
