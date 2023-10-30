import datetime
import scipy.optimize
from ethos_penalps.automatic_sizer.automatic_setter import ProcessStepSetter
from simulation_starter_for_automatic_sizing import run_simulation
import datapane


def size_enterprise(x):
    print("Simulation run start with parameters: " + str(x))
    start_time = datetime.datetime.now()
    objective_function_results = run_simulation(x)
    end_time = datetime.datetime.now()

    duration = end_time - start_time
    print("The simulation ran: " + str(duration))
    print("Input parameters was: " + str(x))
    print("The objective function has value: " + str(objective_function_results))
    return objective_function_results


if __name__ == "__main__":
    # print("Optimization starts")
    # results = scipy.optimize.differential_evolution(
    #     func=size_enterprise,
    #     x0=[1, 150],
    #     bounds=[(0.1, 2), (100, 200)],
    #     # constraints=[constraint_1, constraint_2],
    #     workers=7,
    #     disp=True,
    #     updating="deferred",
    # )
    # print("The optimization results are: " + str(results))
    # print("Optimization is terminated")
    from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger

    logger = PeNALPSLogger.get_logger_to_create_table()

    size_enterprise(x=[0.39 * 2, 0.13])
