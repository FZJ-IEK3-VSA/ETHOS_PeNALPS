import datetime

import numpy as np
import pandas

from ethos_penalps.data_classes import Commodity, OrderCollection
from ethos_penalps.node_operations import ProductionOrder
from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

logger = PeNALPSLogger.get_logger_without_handler()


# def order_generator(
#     order_size: float,
#     commodity: Commodity,
#     start_date: datetime.datetime = datetime.datetime(2021, 1, 1),
#     end_date: datetime.datetime = datetime.datetime(2022, 1, 1),
#     number_of_orders: int = 52,
#     use_debugging_random_seed: bool = False,
# ) -> dict[float, ProductionOrder]:
#     """_summary_

#     :param order_size: _description_
#     :type order_size: float
#     :param commodity: _description_
#     :type commodity: Commodity
#     :param start_date: _description_, defaults to datetime.datetime(2021, 1, 1)
#     :type start_date: datetime.datetime, optional
#     :param end_date: _description_, defaults to datetime.datetime(2022, 1, 1)
#     :type end_date: datetime.datetime, optional
#     :param number_of_orders: _description_, defaults to 52
#     :type number_of_orders: int, optional
#     :param use_debugging_random_seed: _description_, defaults to False
#     :type use_debugging_random_seed: bool, optional
#     :return: _description_
#     :rtype: dict[float, ProductionOrder]
#     """
#     if use_debugging_random_seed is True:
#         np.random.seed(1111)
#     # Generate order data frame with number of orders

#     # calculate order time range
#     time_range = end_date - start_date
#     time_range_day = time_range.days
#     logger.debug(
#         "Order starts at: %s and ends at: %s which total in: %s days",
#         start_date,
#         end_date,
#         time_range_day,
#     )

#     # Create list with order sizes
#     order_mass_value_list = np.random.multinomial(
#         order_size, [1 / number_of_orders] * number_of_orders
#     )
#     logger.debug("Order mass list is %s", order_mass_value_list)

#     # Create list with daily differences between orders
#     incoming_order_day_difference_list = np.random.multinomial(
#         time_range_day, [1 / number_of_orders] * number_of_orders
#     )
#     logger.debug(
#         "Incoming order day difference list %s", incoming_order_day_difference_list
#     )

#     incoming_order_dates = []
#     date_sum = 0
#     production_order_dict = {}
#     # Sum daily differences to order dates
#     for order_number in range(number_of_orders):
#         date_sum = date_sum + incoming_order_day_difference_list[order_number]
#         incoming_order_dates.append(start_date + datetime.timedelta(days=int(date_sum)))
#         # add difference between incoming order and delivery dates
#         delivery_date = start_date + datetime.timedelta(days=int(date_sum))

#         production_order = ProductionOrder(
#             production_target=order_mass_value_list[order_number],
#             production_deadline=delivery_date,
#             commodity=commodity,
#             order_number=order_number,
#         )
#         logger.debug("Production order: %s", production_order)
#         production_order_dict[order_number] = production_order

#     return production_order_dict


# def deterministic_order_generator(
#     start_date: datetime.datetime,
#     end_date: datetime.datetime,
#     interval: datetime.timedelta,
#     total_production_amount: float,
#     commodity: Commodity,
# ) -> list[ProductionOrder]:
#     if start_date == end_date:
#         number_of_intervals = 1
#     else:
#         number_of_intervals = (end_date - start_date) / interval
#     if not number_of_intervals.is_integer():
#         raise Exception(
#             "Start date, end date and interval dont result in an integer number of intervals. Number of intervals"
#             + str(number_of_intervals)
#         )
#     next_deadline = end_date
#     production_order_dict = {}
#     single_interval_production_amount = total_production_amount / number_of_intervals
#     for interval_number in range(int(number_of_intervals)):
#         production_order_dict[interval_number] = ProductionOrder(
#             production_target=single_interval_production_amount,
#             production_deadline=next_deadline,
#             order_number=interval_number,
#             commodity=commodity,
#         )

#         next_deadline = next_deadline - interval
#     return production_order_dict


# def deterministic_order_generator_based_on_intervals(
#     end_date: datetime.datetime,
#     interval: datetime.timedelta,
#     number_of_intervals: int,
#     total_production_amount: float,
#     commodity: Commodity,
# ) -> list[ProductionOrder]:
#     next_deadline = end_date
#     production_order_dict = {}
#     single_interval_production_amount = total_production_amount / number_of_intervals

#     current_interval_number = number_of_intervals - 1
#     for interval_number in range(int(number_of_intervals)):
#         production_order_dict[current_interval_number] = ProductionOrder(
#             production_target=single_interval_production_amount,
#             production_deadline=next_deadline,
#             order_number=interval_number,
#             commodity=commodity,
#         )
#         current_interval_number = current_interval_number - 1
#         next_deadline = next_deadline - interval
#     return production_order_dict


class WorkTimeConfigurator:
    def __init__(
        self,
        include_national_holidays: bool,
        shift_length: datetime.timedelta,
        number_of_shifts_per_working_day: int,
        weekend_work: bool,
        first_shift_start_time: datetime.time,
    ) -> None:
        self.include_national_holidays: bool = include_national_holidays
        self.shift_length: datetime.timedelta = shift_length
        self.number_of_shifts_per_working_day: int = number_of_shifts_per_working_day
        self.weekend_work: bool = weekend_work
        self.first_shift_start_time: datetime.time = first_shift_start_time

    def determine_required_frequency(self):
        if self.weekend_work is True and self.include_national_holidays is False:
            self.pandas_frequency = "D"
        elif self.weekend_work is False and self.include_national_holidays is False:
            self.pandas_frequency = "B"
        elif self.weekend_work is False and self.include_national_holidays is True:
            self.pandas_frequency = "C"
        elif self.weekend_work is True and self.include_national_holidays is True:
            raise Exception("Date combination is not implemented yet")
        else:
            raise Exception("Date combination is not implemented yet")


no_weekends_two_shift_generator = WorkTimeConfigurator(
    include_national_holidays=True,
    shift_length=datetime.timedelta(hours=8),
    number_of_shifts_per_working_day=2,
    weekend_work=False,
    first_shift_start_time=datetime.time(hour=6),
)
no_weekends_one_shift_generator = WorkTimeConfigurator(
    include_national_holidays=True,
    shift_length=datetime.timedelta(hours=8),
    number_of_shifts_per_working_day=1,
    weekend_work=False,
    first_shift_start_time=datetime.time(hour=6),
)
all_day_3_shift_operation = WorkTimeConfigurator(
    include_national_holidays=False,
    shift_length=datetime.timedelta(hours=8),
    number_of_shifts_per_working_day=3,
    weekend_work=True,
    first_shift_start_time=datetime.time(hour=0),
)
one_shift_24_hours = WorkTimeConfigurator(
    include_national_holidays=False,
    shift_length=datetime.timedelta(hours=24),
    number_of_shifts_per_working_day=1,
    weekend_work=True,
    first_shift_start_time=datetime.time(hour=0),
)


class OrderGenerator:
    def __init__(self, target_mass: float, commodity: Commodity) -> None:
        self.target_mass: float = target_mass
        self.commodity: Commodity = commodity

    # def create_number_of_shifts_for_day(
    #     self,
    #     day: datetime.date,
    #     first_shift_start_time: datetime.time,
    #     shift_length: datetime.timedelta,
    #     mass_produced_per_shift: float,
    #     number_of_shifts_per_day: int,
    #     order_number: int,
    # ) -> tuple[dict[int, ProductionOrder], int]:
    #     output_order_dict: dict[int, ProductionOrder] = {}
    #     current_shift_start_date = datetime.datetime.combine(
    #         day - datetime.timedelta(days=1), first_shift_start_time
    #     )
    #     for shift_number in range(number_of_shifts_per_day):
    #         production_deadline = current_shift_start_date + shift_length
    #         output_order_dict[order_number] = ProductionOrder(
    #             production_target=mass_produced_per_shift,
    #             production_deadline=production_deadline,
    #             commodity=self.commodity,
    #             order_number=order_number,
    #         )

    #         order_number = order_number + 1

    #         current_shift_start_date = production_deadline
    #     return output_order_dict, order_number

    # def create_production_order_for_total_mass(
    #     self,
    #     start_date: datetime.datetime,
    #     total_mass: float,
    #     end_date: datetime.datetime,
    #     work_time_configurator: WorkTimeConfigurator,
    # ):
    #     work_time_configurator.determine_required_frequency()
    #     pandas_frequency = work_time_configurator.pandas_frequency
    #     date_range = pandas.date_range(
    #         start=start_date, end=end_date, freq=pandas_frequency
    #     )
    #     number_of_working_days = len(date_range)
    #     number_of_shifts = (
    #         number_of_working_days
    #         * work_time_configurator.number_of_shifts_per_working_day
    #     )
    #     mass_produced_per_day = total_mass / number_of_working_days
    #     mass_produced_per_shift = (
    #         mass_produced_per_day
    #         / work_time_configurator.number_of_shifts_per_working_day
    #     )
    #     output_order_dict: dict[int, ProductionOrder] = {}
    #     current_order_number = 0
    #     for current_date in date_range:
    #         (
    #             daily_order_output_dict,
    #             current_order_number,
    #         ) = self.create_number_of_shifts_for_day(
    #             day=current_date.date(),
    #             shift_length=work_time_configurator.shift_length,
    #             first_shift_start_time=work_time_configurator.first_shift_start_time,
    #             mass_produced_per_shift=mass_produced_per_shift,
    #             number_of_shifts_per_day=work_time_configurator.number_of_shifts_per_working_day,
    #             order_number=current_order_number,
    #         )

    #         output_order_dict.update(daily_order_output_dict)
    #     logger.info(
    #         """A total of: %s shifts have been created to produce a mass of: %s .\nThey start between: %s and: %s.\nPer shift a mass of: %s
    #         is produced of commodity: %s""",
    #         number_of_shifts,
    #         total_mass,
    #         start_date,
    #         end_date,
    #         mass_produced_per_shift,
    #         self.commodity,
    #     )
    #     return output_order_dict

    # def create_production_order_mass_per_shift(
    #     self,
    #     deadline_start_date: datetime.datetime,
    #     shift_per_mass_total_mass: float,
    #     deadline_end_date: datetime.datetime,
    #     work_time_configurator: WorkTimeConfigurator,
    # ):
    #     work_time_configurator.determine_required_frequency()
    #     pandas_frequency = work_time_configurator.pandas_frequency

    #     date_range = pandas.date_range(
    #         start=deadline_start_date, end=deadline_end_date, freq=pandas_frequency
    #     )
    #     number_of_working_days = len(date_range)
    #     number_of_shifts = (
    #         number_of_working_days
    #         * work_time_configurator.number_of_shifts_per_working_day
    #     )
    #     output_order_dict: dict[int, ProductionOrder] = {}
    #     # current_order_number = number_of_shifts - 1
    #     current_order_number = 0
    #     for current_date in date_range:
    #         (
    #             daily_order_output_dict,
    #             current_order_number,
    #         ) = self.create_number_of_shifts_for_day(
    #             day=current_date.date(),
    #             shift_length=work_time_configurator.shift_length,
    #             first_shift_start_time=work_time_configurator.first_shift_start_time,
    #             mass_produced_per_shift=shift_per_mass_total_mass,
    #             number_of_shifts_per_day=work_time_configurator.number_of_shifts_per_working_day,
    #             order_number=current_order_number,
    #         )

    #         output_order_dict.update(daily_order_output_dict)
    #     total_mass = number_of_shifts * shift_per_mass_total_mass
    #     logger.info(
    #         "A total of: %s shifts have been created to produce a mass of: %s",
    #         number_of_shifts,
    #         total_mass,
    #     )
    #     logger.info(
    #         "They start between: %s and: %s.",
    #         deadline_start_date,
    #         deadline_end_date,
    #     )
    #     logger.info(
    #         "Per shift a mass of: %s is produced of commodity: %s.",
    #         shift_per_mass_total_mass,
    #         self.commodity,
    #     )

    #     return output_order_dict

    # def create_single_order(
    #     self, production_target: float, production_deadline: datetime.datetime
    # ) -> dict[int, ProductionOrder]:
    #     output_order_dict = {
    #         0: ProductionOrder(
    #             production_target=production_target,
    #             production_deadline=production_deadline,
    #             order_number=1,
    #             commodity=self.commodity,
    #         ),
    #     }
    #     return output_order_dict


class NOrderGenerator:
    def __init__(
        self,
        mass_per_order: float,
        production_deadline: datetime.datetime,
        number_of_orders: int,
        commodity: Commodity,
        time_span_between_order: datetime.timedelta = datetime.timedelta(minutes=0),
    ) -> None:
        self.mass_per_order: float = mass_per_order
        self.production_deadline: datetime.datetime = production_deadline
        self.number_of_orders: int = number_of_orders
        self.commodity: Commodity = commodity
        self.target_mass: float = self.mass_per_order * number_of_orders
        self.time_span_between_order: datetime.timedelta = time_span_between_order

    def create_n_order_collection(
        self,
    ) -> OrderCollection:
        output_order_dict = {}
        number_of_orders = self.number_of_orders
        mass_per_order = self.mass_per_order

        current_deadline = self.production_deadline
        for order_number in range(number_of_orders):
            output_order_dict[order_number] = ProductionOrder(
                production_target=mass_per_order,
                production_deadline=current_deadline,
                order_number=order_number,
                commodity=self.commodity,
            )
            current_deadline = current_deadline - self.time_span_between_order
        order_data_frame = pandas.DataFrame(data=list(output_order_dict.values()))
        order_collection = OrderCollection(
            target_mass=self.target_mass,
            commodity=self.commodity,
            order_data_frame=order_data_frame,
        )

        return order_collection


if __name__ == "__main__":
    start_date = datetime.datetime(year=2023, month=1, day=1)
    end_date = datetime.datetime(year=2023, month=1, day=3)
    date_range = pandas.date_range(start=start_date, end=end_date, freq="B")

    day = datetime.date(year=2022, month=1, day=1)
    first_shift_start_time = datetime.time(hour=2)
    asd = datetime.datetime.combine(day, first_shift_start_time)
    print(asd)
    test_commodity = Commodity(name="test_commodity")

    start_date = datetime.datetime(year=2023, month=1, day=1)
    end_date = datetime.datetime(year=2023, month=2, day=2)
    n_order_generator = NOrderGenerator(
        mass_per_order=300,
        production_deadline=end_date,
        number_of_orders=10,
        commodity=test_commodity,
    )
    output_order_collection = n_order_generator.create_n_order_collection()
    print(output_order_collection.order_data_frame)
    print("asd")
    order_collec = OrderCollection(target_mass=350, commodity=test_commodity)
    print(order_collec.order_data_frame)
