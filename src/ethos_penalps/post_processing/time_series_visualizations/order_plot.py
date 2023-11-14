import datetime
import numbers
from dataclasses import dataclass

import matplotlib
import matplotlib.figure
import matplotlib.dates
import numpy
import pandas
import proplot

from ethos_penalps.data_classes import (
    Commodity,
    OrderCollection,
    ProductionOrder,
    ProductionOrderMetadata,
)
from ethos_penalps.stream_node_distributor import SplittedOrderCollection


def create_order_gantt_plot(
    fig: matplotlib.figure.Figure,
    current_axs: proplot.gridspec.SubplotGrid,
    order_meta_data: ProductionOrderMetadata,
    subplot_number: float,
    bar_width: float = 1,
):
    ax = current_axs[subplot_number]

    obj = ax.vlines(
        x=order_meta_data.list_of_unique_deadlines,
        y2=order_meta_data.list_of_aggregated_production_order,
        color="dark gray",
        linestyles="solid",
        linewidths=3,
    )
    ax.format(
        ytickminor=False,
        xtickminor=False,
        grid=False,
    )
    # fig.show()


def post_process_order_collection(
    order_collection: OrderCollection | SplittedOrderCollection,
) -> ProductionOrderMetadata:
    list_of_all_unique_deadlines = list(
        order_collection.order_data_frame.loc[:, "production_deadline"].unique()
    )
    list_of_aggregated_order_targets = []
    for unique_dead_line in list_of_all_unique_deadlines:
        all_rows_with_deadline = order_collection.order_data_frame.loc[
            order_collection.order_data_frame["production_deadline"] == unique_dead_line
        ]
        aggregated_target = all_rows_with_deadline.loc[:, "production_target"].sum()
        list_of_aggregated_order_targets.append(aggregated_target)

    latest_deadline = order_collection.order_data_frame["production_deadline"].max()
    earliest_deadline = order_collection.order_data_frame["production_deadline"].min()
    production_order_meta_data = ProductionOrderMetadata(
        data_frame=order_collection.order_data_frame,
        list_of_aggregated_production_order=list_of_aggregated_order_targets,
        list_of_unique_deadlines=list_of_all_unique_deadlines,
        commodity=order_collection.commodity,
        total_order_mass=order_collection.target_mass,
        earliest_deadline=earliest_deadline,
        latest_deadline=latest_deadline,
    )
    return production_order_meta_data
