# Tutorial Overview

This section gives an overview how to create simple models and how to create the complexity of the models.

To setup an ETHOS.PeNALPS model the following object types must be instantiated

1. Initialize Time Data
2. Setup All Commodities
3. Create Product Orders
4. Create Container Classes
5. Create Source, Sink and Process Step
6. Create Streams, Sink, Source and Process Step
7. Create Petri Net of States
8. Initialize Energy Data
9. Create Internal Storages and Mass Balances
10. Start Simulation and Post Processing

First it will be shown how to setup a [minimal cooking process simulation](ethos_penalps_in_10_minutes.md). Subsequently, [the cooking process will be modelled more rigorously ](single_cooker_process_chain.md) concerning the phases of energy demand by modifying the petri nets of states of the cooker. Afterwards it is shown how to model parallel production by [adding an additional simple cooker to a new process chain in the new level](add_more_chains.md). Then, it is shown (how to connect the inputs and outputs of two machines exclusively)[connect_two_process_steps_exclusvely.md] within a simple process chain by prepending a mixer to a cooker. Finally, it is [demonstrated how to connect the inputs and outputs of 2x2 process steps](connect_three_or_more_process_steps.md) using two network level.

The executable examples files that are built during the tutorial can be found in the tutorial folder in the [examples in the ETHOS.PeNALPS repository](https://github.com/FZJ-IEK3-VSA/ETHOS_PeNALPS).
