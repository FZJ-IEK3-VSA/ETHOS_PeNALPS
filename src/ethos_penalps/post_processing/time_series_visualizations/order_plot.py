import datetime
import numbers
from dataclasses import dataclass

import matplotlib
import matplotlib.dates
import matplotlib.figure
import numpy
import pandas
import proplot

from ethos_penalps.data_classes import (
    Commodity,
    OrderCollection,
    ProductionOrder,
    ProductionOrderMetadata,
)
from ethos_penalps.order_distributor.base_node_distributor import (
    SplittedOrderCollection,
)


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
    ax.format(ytickminor=False, xtickminor=False, grid=False, title=order_meta_data.order_name)

    # fig.show()


def post_process_order_collection(
    order_collection: OrderCollection | SplittedOrderCollection,
) -> ProductionOrderMetadata:
    grouped = order_collection.order_data_frame.groupby("production_deadline")["production_target"].sum()
    list_of_all_unique_deadlines = list(grouped.index)
    list_of_aggregated_order_targets = list(grouped.values)

    latest_deadline = order_collection.order_data_frame["production_deadline"].max()
    earliest_deadline = order_collection.order_data_frame["production_deadline"].min()

    if isinstance(order_collection, OrderCollection):
        order_name = order_collection.commodity.name
    elif isinstance(order_collection, SplittedOrderCollection):
        order_name = order_collection.process_chain_identifier.chain_name
    else:
        order_name = "No Order Name"
    production_order_meta_data = ProductionOrderMetadata(
        order_name=order_name,
        data_frame=order_collection.order_data_frame,
        list_of_aggregated_production_order=list_of_aggregated_order_targets,
        list_of_unique_deadlines=list_of_all_unique_deadlines,
        commodity=order_collection.commodity,
        total_order_mass=order_collection.target_mass,
        earliest_deadline=earliest_deadline,
        latest_deadline=latest_deadline,
    )
    pass
    return production_order_meta_data
