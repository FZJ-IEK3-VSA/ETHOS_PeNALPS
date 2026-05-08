import calendar
import datetime
import json
import numbers
import os
import uuid
from dataclasses import dataclass, fields
from pathlib import Path
from string import Template
from typing import Any

import numpy as np
import pandas

import __main__
from ethos_penalps.utilities.type_aliases import numbers_alias


def datetime_to_seconds(dt: datetime.datetime) -> float:
    """Convert a naive datetime to UTC seconds without DST adjustment.

    Uses ``calendar.timegm`` which treats the input as UTC, avoiding
    the local-timezone DST issues of ``datetime.timestamp()``.
    """
    return calendar.timegm(dt.timetuple()) + dt.microsecond / 1e6


def seconds_to_datetime(seconds: float) -> datetime.datetime:
    """Convert UTC seconds back to a naive datetime without DST adjustment.

    Converts via ``datetime.fromtimestamp`` with an explicit UTC timezone
    and then strips the tzinfo to return a naive datetime, matching the
    conversion done by ``datetime_to_seconds``.
    """
    return datetime.datetime.fromtimestamp(seconds, tz=datetime.timezone.utc).replace(tzinfo=None)


def dataframe_from_dataclasses(entries: list) -> pandas.DataFrame:
    """Create a pandas DataFrame from a list of dataclass instances
    without using dataclasses.asdict() which deep-copies every field value.
    """
    if not entries:
        return pandas.DataFrame()
    field_names = [f.name for f in fields(entries[0])]
    return pandas.DataFrame({name: [getattr(e, name) for e in entries] for name in field_names})


# def get_all_rows_with_minimum_index_from_array(
#     input_array: list[list],
# ) -> np.ndarray:
#     if isinstance(input_array, list):
#         input_array = np.array(input_array)
#     elif isinstance(input_array, np.ndarray):
#         pass
#     else:
#         raise Exception("Unexpected input datatype: " + str(type(input_array)))
#     if input_array.size == 0:
#         return input_array
#     else:
#         output_array = np.where(np.array(input_array) == min(input_array[:, 0]))
#         return input_array[output_array[0]]


# def get_all_rows_with_maximum_index_from_array(
#     input_array: list[list],
# ) -> np.ndarray:
#     if isinstance(input_array, list):
#         input_array = np.array(input_array)
#     elif isinstance(input_array, np.ndarray):
#         pass
#     else:
#         raise Exception("Unexpected input datatype: " + str(type(input_array)))
#     if input_array.size == 0:
#         return input_array
#     else:
#         output_array = np.where(np.array(input_array) == max(input_array[:, 0]))
#         return input_array[output_array[0]]


def format_timedelta(td: datetime.timedelta) -> str:
    if td < datetime.timedelta(0):
        return "-" + format_timedelta(-td)
    else:
        # Change this to format positive time deltas the way you want
        return str(td)


class ResultPathGenerator:
    """This class is used to create paths relative to the main file
    when python codes is executed.
    """

    result_time_stamp: str
    time_stamp_format: str = "%Y_%m_%d__%H_%M_%S"

    def create_path_to_file_relative_to_main_file(
        self,
        file_name: str,
        subdirectory_name: str,
        file_extension: str,
        add_time_stamp_to_filename: bool = True,
    ) -> str:
        """Creates a path to subdirectory which is located at the level of the __main__ file. Subdirectory is created if it does not exists prior to call.

        Args:
            file_name (str): Name of the file to be created. Is prepending the full file name with optional timestamp.
            subdirectory_name (str): Name of the subdirectory which is created
            file_extension (str): The file extension which is appended to the file name
            add_time_stamp_to_filename (bool, optional): Adds a current timestamp the file name between name and file extension. Defaults to True.

        Returns:
            str: Absolute path to the file relative to the main file.
        """

        results_directory = self.create_result_folder_relative_to_main_file(
            subdirectory_name=subdirectory_name, add_time_stamp_to_filename=False
        )

        if not os.path.exists(results_directory):
            os.makedirs(results_directory)

        if add_time_stamp_to_filename:
            date_appendix = datetime.datetime.now().strftime(ResultPathGenerator.time_stamp_format)
            file_name = file_name + date_appendix
        file_name_and_extension = file_name + file_extension

        full_path_to_file = os.path.join(results_directory, file_name_and_extension)
        return full_path_to_file

    def create_result_folder_relative_to_main_file(
        self, subdirectory_name: str, add_time_stamp_to_filename: bool = True
    ) -> str:
        path_to_main_module = os.path.dirname(__main__.__file__)

        if add_time_stamp_to_filename:
            ResultPathGenerator.result_time_stamp = datetime.datetime.now().strftime(
                ResultPathGenerator.time_stamp_format
            )
            date_appendix = ResultPathGenerator.result_time_stamp

            subdirectory_name = subdirectory_name + "_" + date_appendix

        results_directory = os.path.join(path_to_main_module, subdirectory_name)
        if not os.path.exists(results_directory):
            os.makedirs(results_directory)

        return results_directory

    def create_subdirectory_relative_to_parent(self, parent_directory_path: str, new_directory_name: str) -> str:
        path_to_new_subdirectory = os.path.join(parent_directory_path, new_directory_name)
        Path(path_to_new_subdirectory).mkdir(parents=True, exist_ok=True)
        return path_to_new_subdirectory


def denormalize(value: numbers_alias, minimum_value: numbers_alias, maximum_value: numbers_alias):
    denormalized_value = value * (maximum_value - minimum_value) + minimum_value
    return denormalized_value


def check_if_date_1_is_before_date_2(date_1: datetime.datetime, date_2: datetime.datetime) -> bool:
    start_is_before_end = date_1 < date_2
    return start_is_before_end


def check_if_date_1_is_before_or_at_date_2(date_1: datetime.datetime, date_2: datetime.datetime) -> bool:
    start_is_before_end = date_1 <= date_2
    return start_is_before_end


class DeltaTemplate(Template):
    delimiter = "_"


def convert_date_time_to_string(td: datetime.timedelta):
    # Get the timedelta’s sign and absolute number of seconds.
    sign = "-" if td.days < 0 else "+"
    secs = abs(td).total_seconds()

    # Break the seconds into more readable quantities.
    days, rem = divmod(secs, 86400)  # Seconds per day: 24 * 60 * 60
    hours, rem = divmod(rem, 3600)  # Seconds per hour: 60 * 60
    mins, secs = divmod(rem, 60)

    # Format (as per above answers) and return the result string.

    output_string = str(int(days)) + "_" + str(int(hours)) + "_" + str(int(mins)) + "_" + str(int(secs))
    return output_string


""">>> strfdelta(td, "%s%H:%M:%S")  # Note that %s refers to the timedelta’s sign.
'-00:00:30'
>>> strfdelta(timedelta(days=-1), "%s%D %H:%M:%S")
'-1 00:00:00'
>>> strfdelta(timedelta(days=-1, minutes=5), "%s%D %H:%M:%S")
'-0 23:55:00'
>>> strfdelta(timedelta(days=-1, minutes=-5), "%s%D %H:%M:%S")
'-1 00:05:00'
"""


def get_super(x):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-=()"
    super_s = "ᴬᴮᶜᴰᴱᶠᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾQᴿˢᵀᵁⱽᵂˣʸᶻᵃᵇᶜᵈᵉᶠᵍʰᶦʲᵏˡᵐⁿᵒᵖ۹ʳˢᵗᵘᵛʷˣʸᶻ⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾"
    res = x.maketrans("".join(normal), "".join(super_s))
    return x.translate(res)


def get_sub(x):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-=()"
    sub_s = "ₐ₈CDₑբGₕᵢⱼₖₗₘₙₒₚQᵣₛₜᵤᵥwₓᵧZₐ♭꜀ᑯₑբ₉ₕᵢⱼₖₗₘₙₒₚ૧ᵣₛₜᵤᵥwₓᵧ₂₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎"
    res = x.maketrans("".join(normal), "".join(sub_s))
    return x.translate(res)


def create_subscript_string_matplotlib(base: str, subscripted_text: str):
    base = base.replace(" ", "\ ")
    subscripted_text = subscripted_text.replace(" ", "\ ")
    output_str = "${}".format(base) + "_{" + "{}".format(subscripted_text) + "}$"
    return output_str


def get_new_uuid() -> str:
    return str(uuid.uuid4())


def create_dataclass_from_pandas_series(data: pandas.Series, factory: Any) -> Any:
    return factory(**{f.name: data[f.name] for f in fields(factory)})


# https://stackoverflow.com/questions/8906926/formatting-timedelta-objects


# class ExtendedEncoder(json.JSONEncoder):
#     def default(self, obj):
#         """Selects an encoder for custom objects

#         :param obj: _description_
#         :type obj: _type_
#         :return: _description_
#         :rtype: _type_
#         """
#         name = type(obj).__name__
#         try:
#             encoder = getattr(self, f"encode_{name}")
#         except AttributeError:
#             super().default(obj)
#         else:
#             encoded = encoder(obj)
#             encoded["__extended_json_type__"] = name
#             return encoded


def time_mod(
    time: datetime.datetime,
    delta: datetime.timedelta,
    epoch: None | datetime.datetime = None,
) -> datetime.timedelta:
    if epoch is None:
        epoch = datetime.datetime(1970, 1, 1, tzinfo=time.tzinfo)
    return (time - epoch) % delta


def time_round(
    time: datetime.datetime,
    delta: datetime.timedelta,
    epoch: None | datetime.datetime = None,
) -> datetime.datetime:
    mod = time_mod(time, delta, epoch)
    if mod < delta / 2:
        return time - mod
    return time + (delta - mod)


def time_floor(time: datetime.datetime, mod: datetime.timedelta) -> datetime.datetime:

    return time - mod


def time_ceil(time: datetime.datetime, delta: datetime.timedelta, mod: datetime.timedelta) -> datetime.datetime:

    if mod:
        return time + (delta - mod)
    return time
