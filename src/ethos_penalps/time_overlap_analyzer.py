import datetime
from dataclasses import dataclass, field
from typing import cast

from ethos_penalps.stream import BatchStreamState
from ethos_penalps.utilities.type_aliases import numbers_alias


@dataclass(slots=True)
class TimeRangeDatetime:
    start_time: datetime.datetime
    end_time: datetime.datetime


@dataclass(slots=True)
class TimeRange:
    start_time: numbers_alias
    end_time: numbers_alias

    def create_time_range_datetime(self) -> TimeRangeDatetime:
        from ethos_penalps.utilities.general_functions import seconds_to_datetime

        return TimeRangeDatetime(
            start_time=seconds_to_datetime(float(self.start_time)),
            end_time=seconds_to_datetime(float(self.end_time)),
        )


@dataclass
class TimeRangesHandler:
    list_of_number_time_points: list[numbers_alias] = field(default_factory=list)
    list_of_continuous_time_points: list[numbers_alias] = field(default_factory=list)
    list_of_batch_mass_points: list[numbers_alias] = field(default_factory=list)

    def add_continuous_time_point(self, time_point: numbers_alias):
        self.list_of_number_time_points.append(time_point)
        self.list_of_continuous_time_points.append(time_point)

    def add_batch_input_state(self, batch_state: BatchStreamState):
        self.list_of_batch_mass_points.append(batch_state.end_time_seconds)
        self.list_of_number_time_points.append(batch_state.end_time_seconds)
        self.list_of_number_time_points.append(batch_state.start_time_seconds)

    def add_batch_output_state(self, batch_state: BatchStreamState):
        self.list_of_batch_mass_points.append(batch_state.start_time_seconds)
        self.list_of_number_time_points.append(batch_state.start_time_seconds)
        self.list_of_number_time_points.append(batch_state.end_time_seconds)

    def get_batch_point_dict(self) -> dict[numbers_alias, int]:
        batch_point_list = sorted(list(set(self.list_of_batch_mass_points)))
        return dict.fromkeys(batch_point_list, 0)

    def get_continuous_dict_and_storage_mass_flow_list(
        self,
    ) -> tuple[dict[numbers_alias, int], list[numbers_alias], list[numbers_alias]]:
        continuous_point_list = sorted(list(set(self.list_of_continuous_time_points)))
        net_mass_flow_list: list[numbers_alias] = cast(list[numbers_alias], [0] * len(continuous_point_list))

        continuous_time_point_index_dict = {}
        continuous_time_point_index = 0

        for current_continuous_point in continuous_point_list:
            continuous_time_point_index_dict[current_continuous_point] = continuous_time_point_index
            continuous_time_point_index = continuous_time_point_index + 1
        return (
            continuous_time_point_index_dict,
            net_mass_flow_list,
            continuous_point_list,
        )

    def get_duration_list_list_and_time_point_dictionaries(
        self,
    ) -> tuple[
        list[list[numbers_alias]],
        dict[numbers_alias, int],
        dict[numbers_alias, int],
        dict[numbers_alias, int],
    ]:
        """_summary_

        Args:
            list_of_duration_lists (str): Contains a list of the length 4, which represents a period of storages levels.
            The first entry is the start point of the period, the second ist the end point, the third point is the duration and the last

        Returns:
            tuple[ list[list[numbers_alias]], dict[numbers_alias, int], dict[numbers_alias, int], dict[numbers_alias, int], ]: _description_
        """

        all_point_list = sorted(list(set(self.list_of_number_time_points)))
        list_of_duration_lists = []
        previous_point = all_point_list[0]
        index_iterator = 0
        batch_time_point_to_index_dict = {}
        continuous_start_point_to_index_dict = {}
        continuous_end_point_to_index_dict = {}
        batch_mass_points_set = set(self.list_of_batch_mass_points)

        if previous_point in batch_mass_points_set:
            duration = 0
            batch_period_tuple = [previous_point, previous_point, duration, 0]
            batch_time_point_to_index_dict[previous_point] = index_iterator
            list_of_duration_lists.append(batch_period_tuple)
            index_iterator = index_iterator + 1
        for current_point in all_point_list[1:]:
            duration = current_point - previous_point
            continuous_period_tuple = [previous_point, current_point, duration, 0]
            continuous_start_point_to_index_dict[previous_point] = index_iterator
            continuous_end_point_to_index_dict[current_point] = index_iterator

            list_of_duration_lists.append(continuous_period_tuple)
            if current_point in batch_mass_points_set:
                duration = 0
                batch_period_tuple = [current_point, current_point, duration, 0]
                index_iterator = index_iterator + 1
                batch_time_point_to_index_dict[current_point] = index_iterator
                list_of_duration_lists.append(batch_period_tuple)

            index_iterator = index_iterator + 1
            previous_point = current_point

        # duration_tuple_list[0][3] = storage_level_at_start
        return (
            list_of_duration_lists,
            batch_time_point_to_index_dict,
            continuous_start_point_to_index_dict,
            continuous_end_point_to_index_dict,
        )

    def get_time_ranges_list_from_start_to_end(self) -> list[TimeRange]:
        set_of_time_points = set(self.list_of_number_time_points)
        sorted_list_of_time_points = list(set_of_time_points)
        sorted_list_of_time_points.sort(reverse=False)
        last_point = None
        batch_mass_points_set = set(self.list_of_batch_mass_points)

        list_of_time_ranges: list[TimeRange] = []
        for time_point in sorted_list_of_time_points:
            if last_point is not None:
                list_of_time_ranges.append(TimeRange(start_time=last_point, end_time=time_point))
            last_point = time_point
            if time_point in batch_mass_points_set:
                list_of_time_ranges.append(TimeRange(start_time=time_point, end_time=time_point))

        return list_of_time_ranges

    def get_time_ranges_list_from_start_to_end_datetime(
        self,
    ) -> list[TimeRangeDatetime]:
        list_of_time_ranges = self.get_time_ranges_list_from_start_to_end()
        output_list = []
        for datetime_range in list_of_time_ranges:
            output_list.append(datetime_range.create_time_range_datetime())
        return output_list


class TimeOverLapAnalyzer:
    def get_overlap_share(self, contribution_time_range: TimeRange, target_time_range: TimeRange) -> numbers_alias:
        contribution_time_range_seconds = contribution_time_range.end_time - contribution_time_range.start_time

        # Case 1
        if (
            contribution_time_range.start_time >= target_time_range.start_time
            and contribution_time_range.start_time <= target_time_range.end_time
            and contribution_time_range.end_time >= target_time_range.start_time
            and contribution_time_range.end_time >= target_time_range.end_time
        ):
            overlap_time_range = target_time_range.end_time - contribution_time_range.start_time

        # Case 2
        elif (
            contribution_time_range.start_time <= target_time_range.start_time
            and contribution_time_range.start_time <= target_time_range.end_time
            and contribution_time_range.end_time >= target_time_range.start_time
            and contribution_time_range.end_time <= target_time_range.end_time
        ):
            overlap_time_range = contribution_time_range.end_time - target_time_range.start_time

        # Case 3
        elif (
            contribution_time_range.start_time <= target_time_range.start_time
            and contribution_time_range.start_time <= target_time_range.end_time
            and contribution_time_range.end_time >= target_time_range.start_time
            and contribution_time_range.end_time >= target_time_range.end_time
        ):
            overlap_time_range = target_time_range.end_time - target_time_range.start_time

        # Case 4
        elif (
            contribution_time_range.start_time == target_time_range.start_time
            and contribution_time_range.end_time == target_time_range.end_time
        ):
            overlap_time_range = contribution_time_range_seconds

        # Case 5
        elif (
            contribution_time_range.start_time >= target_time_range.start_time
            and contribution_time_range.start_time <= target_time_range.end_time
            and contribution_time_range.end_time >= target_time_range.start_time
            and contribution_time_range.end_time <= target_time_range.end_time
        ):
            overlap_time_range = contribution_time_range.end_time - contribution_time_range.start_time

        # Case 6
        elif (
            contribution_time_range.start_time >= target_time_range.start_time
            and contribution_time_range.start_time >= target_time_range.end_time
            and contribution_time_range.end_time >= target_time_range.start_time
            and contribution_time_range.end_time >= target_time_range.end_time
        ):
            overlap_time_range = 0

        # Case 7
        elif (
            contribution_time_range.start_time <= target_time_range.start_time
            and contribution_time_range.start_time <= target_time_range.end_time
            and contribution_time_range.end_time <= target_time_range.start_time
            and contribution_time_range.end_time <= target_time_range.end_time
        ):
            overlap_time_range = 0
        overlap_share = overlap_time_range / contribution_time_range_seconds
        return overlap_share
