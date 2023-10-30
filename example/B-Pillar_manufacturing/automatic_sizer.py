import datetime
import scipy.optimize
from ethos_penalps.automatic_sizer.automatic_setter import ProcessStepSetter
from simulation_starter_for_automatic_sizing import run_simulation


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
    print("Optimization starts")
    # results = scipy.optimize.differential_evolution(
    #     func=size_enterprise,
    #     x0=[
    #         0.3,
    #     ],
    #     bounds=[
    #         (0.1, 2),
    #     ],
    #     # constraints=[constraint_1, constraint_2],
    #     workers=6,
    #     disp=True,
    #     updating="deferred",
    # )
    results = size_enterprise(x=[0.5267])
    print("The optimization results are: " + str(results))
    print("Optimization is terminated")
