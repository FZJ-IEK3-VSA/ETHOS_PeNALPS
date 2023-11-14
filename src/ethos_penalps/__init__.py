import sys

if not sys.warnoptions:
    import warnings

    warnings.filterwarnings(
        action="ignore",
        category=FutureWarning,
        append=True,
        message="pandas.Int64Index is deprecated and will be removed from pandas in a future version. Use pandas.Index with the appropriate dtype instead.",
    )
