import datetime
import numbers
import os
import uuid
import json
from pathlib import Path
from string import Template
from typing import Any
from dataclasses import dataclass, fields


import __main__
import pandas
import numpy as np


def get_all_rows_with_minimum_index_from_array(
    input_array: list[list],
) -> np.ndarray:
    if isinstance(input_array, list):
        input_array = np.array(input_array)
    elif isinstance(input_array, np.ndarray):
        pass
    else:
        raise Exception("Unexpected input datatype: " + str(type(input_array)))
    if input_array.size == 0:
        return input_array
    else:
        output_array = np.where(np.array(input_array) == min(input_array[:, 0]))
        return input_array[output_array[0]]


def get_all_rows_with_maximum_index_from_array(
    input_array: list[list],
) -> np.ndarray:
    if isinstance(input_array, list):
        input_array = np.array(input_array)
    elif isinstance(input_array, np.ndarray):
        pass
    else:
        raise Exception("Unexpected input datatype: " + str(type(input_array)))
    if input_array.size == 0:
        return input_array
    else:
        output_array = np.where(np.array(input_array) == max(input_array[:, 0]))
        return input_array[output_array[0]]


def format_timedelta(td: datetime.timedelta) -> str:
    if td < datetime.timedelta(0):
        return "-" + format_timedelta(-td)
    else:
        # Change this to format positive time deltas the way you want
        return str(td)


class ResultPathGenerator:
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

        :param file_name: name of the file to be created. Is prepending the full file name with optional timestamp
        :type file_name: str
        :param subdirectory_name: Name of the subdirectory which is created
        :type subdirectory_name: str
        :param file_extension: The file extension which is appended to the file name
        :type file_extension: str
        :param add_time_stamp_to_filename: Adds a current timestamp the file name between name and file extension, defaults to True
        :type add_time_stamp_to_filename: bool, optional
        :param time_stamp_format: describes the format of the timestamp which is added if add_time_stamp_to_filename is set to True, defaults to "%Y_%m_%d__%H_%M_%S"
        :type time_stamp_format: str, optional
        :return: returns the path to a file in a subdirectory
        :rtype: str
        """
        results_directory = self.create_result_folder_relative_to_main_file(
            subdirectory_name=subdirectory_name, add_time_stamp_to_filename=False
        )

        if not os.path.exists(results_directory):
            os.makedirs(results_directory)

        if add_time_stamp_to_filename:
            date_appendix = datetime.datetime.now().strftime(
                ResultPathGenerator.time_stamp_format
            )
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

    def create_subdirectory_relative_to_parent(
        self, parent_directory_path: str, new_directory_name: str
    ) -> str:
        path_to_new_subdirectory = os.path.join(
            parent_directory_path, new_directory_name
        )
        Path(path_to_new_subdirectory).mkdir(parents=True, exist_ok=True)
        return path_to_new_subdirectory


def denormalize(
    value: numbers.Number, minimum_value: numbers.Number, maximum_value: numbers.Number
):
    denormalized_value = value * (maximum_value - minimum_value) + minimum_value
    return denormalized_value


def check_if_date_1_is_before_date_2(
    date_1: datetime.datetime, date_2: datetime.datetime
) -> bool:
    start_is_before_end = date_1 < date_2
    return start_is_before_end


def check_if_date_1_is_before_or_at_date_2(
    date_1: datetime.datetime, date_2: datetime.datetime
) -> bool:
    start_is_before_end = date_1 <= date_2
    return start_is_before_end


class DeltaTemplate(Template):
    delimiter = "%"


def convert_date_time_to_string(td: datetime.timedelta, fmt):
    # Get the timedelta’s sign and absolute number of seconds.
    sign = "-" if td.days < 0 else "+"
    secs = abs(td).total_seconds()

    # Break the seconds into more readable quantities.
    days, rem = divmod(secs, 86400)  # Seconds per day: 24 * 60 * 60
    hours, rem = divmod(rem, 3600)  # Seconds per hour: 60 * 60
    mins, secs = divmod(rem, 60)

    # Format (as per above answers) and return the result string.
    t = DeltaTemplate(fmt)
    return t.substitute(
        s=sign,
        D="{:d}".format(int(days)),
        H="{:02d}".format(int(hours)),
        M="{:02d}".format(int(mins)),
        S="{:02d}".format(int(secs)),
    )


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


class ExtendedEncoder(json.JSONEncoder):
    def default(self, obj):
        """Selects an encoder for custom objects

        :param obj: _description_
        :type obj: _type_
        :return: _description_
        :rtype: _type_
        """
        name = type(obj).__name__
        try:
            encoder = getattr(self, f"encode_{name}")
        except AttributeError:
            super().default(obj)
        else:
            encoded = encoder(obj)
            encoded["__extended_json_type__"] = name
            return encoded


if __name__ == "__main__":
    # start = datetime.datetime(year=2022, month=1, day=1)
    # end = datetime.datetime(year=2023, month=1, day=1)
    # a = check_if_date_1_is_before_date_2(date_1=start, date_2=end)
    # print(a)
    # b = check_if_date_1_is_before_date_2(date_1=end, date_2=start)
    # print(b)
    a = create_subscript_string_matplotlib(base="asd", subscripted_text="12354")
    print(a)
