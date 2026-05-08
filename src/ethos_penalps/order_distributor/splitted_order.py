import datetime
import math
import numbers
import warnings
from collections.abc import Iterator
from dataclasses import dataclass, field

import numpy
import pandas

from ethos_penalps.data_classes import (
    Commodity,
    OrderCollection,
    ProcessChainIdentifier,
    ProductionOrder,
)
from ethos_penalps.stream import BatchStream, ContinuousStream
from ethos_penalps.stream_handler import StreamHandler
from ethos_penalps.time_data import TimeData
from ethos_penalps.utilities.exceptions_and_warnings import MisconfigurationError
from ethos_penalps.utilities.general_functions import (
    check_if_date_1_is_before_date_2,
    check_if_date_1_is_before_or_at_date_2,
)
from ethos_penalps.utilities.type_aliases import numbers_alias


@dataclass
class SplittedOrderCollection:
    """Represents a set of orders that has been splitted
    among multiple ProcessChains
    """

    stream_name: str
    commodity: Commodity
    process_chain_identifier: ProcessChainIdentifier
    order_data_frame: pandas.DataFrame
    target_mass: numbers_alias
    current_order_number: int = 0

    def check_if_order_are_empty(self):
        """Raises an error if an order is empty.

        Raises:
            MisconfigurationError: Is raised if the order is empty.
        """
        if self.order_data_frame.empty:
            raise MisconfigurationError(
                "A splitted order of chain: "
                + self.process_chain_identifier.chain_name
                + " has no order. The corresponding sink has too few order too distribute to each chain."
            )

    def get_order_by_order_number(self, order_number: int) -> ProductionOrder:
        """Returns an order based on the order number.

        Args:
            order_number (int): Number that identifies the order.

        Returns:
            ProductionOrder: Order for a product oder intermediate product.
        """
        order_data_frame_row = self.order_data_frame.iloc[order_number]
        production_order = ProductionOrder(
            production_target=order_data_frame_row.loc["production_target"],
            production_deadline=order_data_frame_row.loc["production_deadline"],
            order_number=order_data_frame_row.loc["order_number"],
            commodity=order_data_frame_row.loc["commodity"],
            global_unique_identifier=order_data_frame_row.loc["global_unique_identifier"],
            produced_mass=order_data_frame_row.loc["produced_mass"],
            mass_unit=order_data_frame_row.loc["mass_unit"],
        )
        return production_order

    def update_order(self, produced_mass: numbers_alias):
        """Updates the mass that is already produced.

        Args:
            produced_mass (numbers_alias): The additional mass that has been
                produced and should be added to the order.
        """
        self.order_data_frame.at[self.current_order_number, "produced_mass"] = (
            self.order_data_frame.at[self.current_order_number, "produced_mass"] + produced_mass
        )
