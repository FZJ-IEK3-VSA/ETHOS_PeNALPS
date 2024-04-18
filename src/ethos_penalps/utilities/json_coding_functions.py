import datetime
import json

import datetimerange
import pint

from ethos_penalps.utilities.units import Units


def json_datetime_serialization_function(date_time_object):
    if isinstance(date_time_object, datetime.datetime):
        return date_time_object.isoformat()


def json_datetime_deserialization_function(date_time_string):
    return datetime.datetime.fromisoformat(date_time_string)


def json_timedelta_serialization_function(date_time_object):
    if isinstance(date_time_object, datetime.timedelta):
        return date_time_object.total_seconds()


def json_timedelta_deserialization_function(date_time_string):
    return datetime.timedelta(seconds=date_time_string)


def json_datetime_range_serialization_function(date_time_range_object):
    if isinstance(date_time_range_object, datetimerange.DateTimeRange):
        start_and_end_dictionary = {
            "start_datetime": date_time_range_object.start_datetime.isoformat(),
            "end_datetime": date_time_range_object.end_datetime.isoformat(),
        }
        start_and_end_json = json.dumps(obj=start_and_end_dictionary)
        return start_and_end_json


def json_datetime_range_deserialization_function(
    date_time_range_object,
) -> datetimerange.DateTimeRange:
    start_and_end_dictionary = json.loads(date_time_range_object)
    start_datetime = datetime.datetime.fromisoformat(
        start_and_end_dictionary["start_datetime"]
    )
    end_datetime = datetime.datetime.fromisoformat(
        start_and_end_dictionary["start_datetime"]
    )
    return datetimerange.DateTimeRange(
        start_datetime=start_datetime,
        end_datetime=end_datetime,
    )


def json_pint_unit_serialization_function(pint_unit):
    if isinstance(pint_unit, pint.Unit):
        astropy_dictionary = {
            "unit": str(pint_unit),
        }
        start_and_end_json = json.dumps(obj=astropy_dictionary)
        return start_and_end_json


def json_pint_unit_deserialization_function(astropy_unit_dict_str) -> pint.Unit:
    astropy_unit_dict = json.load(astropy_unit_dict_str)
    astropy_unit = Units.get_unit(astropy_unit_dict["unit"])
    return astropy_unit


# def json_astropy_unit_serialization_function(astropy_unit):
#     if isinstance(astropy_unit, astropy.units.core.Unit):
#         astropy_dictionary = {
#             "unit": astropy_unit.name,
#         }
#         start_and_end_json = json.dumps(obj=astropy_dictionary)
#         return start_and_end_json


# def json_astropy_unit_deserialization_function(astropy_unit_dict_str) -> astropy.units:
#     astropy_unit_dict = json.loads(astropy_unit_dict_str)
#     astropy_unit = setattr(astropy.units, astropy_unit_dict["unit"])
#     return astropy_unit
