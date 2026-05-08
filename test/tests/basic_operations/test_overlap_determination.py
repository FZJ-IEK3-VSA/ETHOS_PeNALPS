import datetime

from ethos_penalps.time_overlap_analyzer import (
    TimeOverLapAnalyzer,
    TimeRange,
    TimeRangeDatetime,
)


def test_time_overlap_analyzer():
    time_overlap_analyzer = TimeOverLapAnalyzer()
    # Case 1

    contribution_time_range = TimeRange(
        start_time=datetime.datetime(year=2022, month=1, day=15, hour=5).timestamp(),
        end_time=datetime.datetime(year=2022, month=1, day=15, hour=15).timestamp(),
    )
    target_time_range = TimeRange(
        start_time=datetime.datetime(year=2022, month=1, day=15, hour=0).timestamp(),
        end_time=datetime.datetime(year=2022, month=1, day=15, hour=10).timestamp(),
    )

    overlap_share = time_overlap_analyzer.get_overlap_share(
        contribution_time_range=contribution_time_range,
        target_time_range=target_time_range,
    )
    assert overlap_share == 0.5

    # Case 2

    contribution_time_range = TimeRange(
        start_time=datetime.datetime(year=2022, month=1, day=15, hour=5).timestamp(),
        end_time=datetime.datetime(year=2022, month=1, day=15, hour=15).timestamp(),
    )
    target_time_range = TimeRange(
        start_time=datetime.datetime(year=2022, month=1, day=15, hour=10).timestamp(),
        end_time=datetime.datetime(year=2022, month=1, day=15, hour=20).timestamp(),
    )

    overlap_share = time_overlap_analyzer.get_overlap_share(
        contribution_time_range=contribution_time_range,
        target_time_range=target_time_range,
    )
    assert overlap_share == 0.5

    # Case 3
    contribution_time_range = TimeRange(
        start_time=datetime.datetime(
            year=2022,
            month=1,
            day=15,
            hour=0,
        ).timestamp(),
        end_time=datetime.datetime(year=2022, month=1, day=15, hour=10).timestamp(),
    )
    target_time_range = TimeRange(
        start_time=datetime.datetime(year=2022, month=1, day=15, hour=2, minute=30).timestamp(),
        end_time=datetime.datetime(year=2022, month=1, day=15, hour=5).timestamp(),
    )

    overlap_share = time_overlap_analyzer.get_overlap_share(
        contribution_time_range=contribution_time_range,
        target_time_range=target_time_range,
    )

    assert overlap_share == 0.25

    # Case 4
    contribution_time_range = TimeRange(
        start_time=datetime.datetime(
            year=2022,
            month=1,
            day=15,
            hour=0,
        ).timestamp(),
        end_time=datetime.datetime(year=2022, month=1, day=15, hour=10).timestamp(),
    )
    target_time_range = TimeRange(
        start_time=datetime.datetime(
            year=2022,
            month=1,
            day=15,
            hour=0,
        ).timestamp(),
        end_time=datetime.datetime(year=2022, month=1, day=15, hour=10).timestamp(),
    )

    overlap_share = time_overlap_analyzer.get_overlap_share(
        contribution_time_range=contribution_time_range,
        target_time_range=target_time_range,
    )

    assert overlap_share == 1
    # Case 5
    contribution_time_range = TimeRange(
        start_time=datetime.datetime(year=2022, month=1, day=15, hour=2, minute=30).timestamp(),
        end_time=datetime.datetime(
            year=2022,
            month=1,
            day=15,
            hour=5,
        ).timestamp(),
    )
    target_time_range = TimeRange(
        start_time=datetime.datetime(
            year=2022,
            month=1,
            day=15,
            hour=0,
        ).timestamp(),
        end_time=datetime.datetime(year=2022, month=1, day=15, hour=10).timestamp(),
    )

    overlap_share = time_overlap_analyzer.get_overlap_share(
        contribution_time_range=contribution_time_range,
        target_time_range=target_time_range,
    )

    assert overlap_share == 1

    # Case 6
    contribution_time_range = TimeRange(
        start_time=datetime.datetime(
            year=2022,
            month=1,
            day=15,
            hour=0,
        ).timestamp(),
        end_time=datetime.datetime(
            year=2022,
            month=1,
            day=16,
        ).timestamp(),
    )
    target_time_range = TimeRange(
        start_time=datetime.datetime(
            year=2022,
            month=1,
            day=13,
        ).timestamp(),
        end_time=datetime.datetime(year=2022, month=1, day=14).timestamp(),
    )

    overlap_share = time_overlap_analyzer.get_overlap_share(
        contribution_time_range=contribution_time_range,
        target_time_range=target_time_range,
    )

    assert overlap_share == 0
    # Case 7
    contribution_time_range = TimeRange(
        start_time=datetime.datetime(
            year=2022,
            month=1,
            day=13,
        ).timestamp(),
        end_time=datetime.datetime(year=2022, month=1, day=14).timestamp(),
    )
    target_time_range = TimeRange(
        start_time=datetime.datetime(
            year=2022,
            month=1,
            day=15,
            hour=0,
        ).timestamp(),
        end_time=datetime.datetime(
            year=2022,
            month=1,
            day=16,
        ).timestamp(),
    )

    overlap_share = time_overlap_analyzer.get_overlap_share(
        contribution_time_range=contribution_time_range,
        target_time_range=target_time_range,
    )

    assert overlap_share == 0


if __name__ == "__main__":
    test_time_overlap_analyzer()
