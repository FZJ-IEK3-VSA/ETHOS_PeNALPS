import cProfile
import functools
import os
import pstats


def profile_execution(path_to_profile_results_folder: str):
    """Tracks the execution time of the input function and all subfunction calls."""

    # Must take the function that should be wrapped as argument
    def decorator_profile_execution(function_to_profile):

        # Is the actual wrapper that calls function that should be profiled
        @functools.wraps(function_to_profile)
        def profile_execution_wrapper():
            """Called from the command line.
            This function calls HiSim main and performs a profiling with cprofile.
            The results are dumped to various text files in the result directory
            and the .prof file can be visualized with for example snakeviz.
            """
            profiler = cProfile.Profile()
            profiler.enable()
            function_to_profile()
            profiler.disable()

            with open(
                os.path.join(
                    path_to_profile_results_folder,
                    r"profilingStatsAsTextSortedCumulative.txt",
                ),
                "w",
                encoding="utf-8",
            ) as f:
                stats = pstats.Stats(profiler, stream=f).sort_stats("cumulative")
                stats.print_stats()
            with open(
                os.path.join(
                    path_to_profile_results_folder,
                    r"profilingStatsAsTextSortedcalls.txt",
                ),
                "w",
                encoding="utf-8",
            ) as f:
                stats = pstats.Stats(profiler, stream=f).sort_stats("ncalls")
                stats.print_stats()
            with open(
                os.path.join(
                    path_to_profile_results_folder,
                    r"profilingStatsAsTextSortedTotalTime.txt",
                ),
                "w",
                encoding="utf-8",
            ) as f:
                stats = pstats.Stats(profiler, stream=f).sort_stats("tottime")
                stats.print_stats()
            stats.dump_stats(
                os.path.join(
                    path_to_profile_results_folder,
                    "profile-export-data.prof",
                )
            )
            # If the wrapped function returns a value it should be returned here

        return profile_execution_wrapper

    return decorator_profile_execution
