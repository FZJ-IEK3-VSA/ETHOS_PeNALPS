# Tutorial Overview

This section gives an overview how to create simple models and how to create the complexity of the models.

To setup an ETHOS.PeNALPS model the following object types must be instantiated

1. Initialize Time Data
2. Setup Orders to be produced during the simulation
3. Create Organizational Container Objects
4. Create Process steps, sources, sinks, storages
5. Set up a petri net of states for each process step
6. Connect all objects from step 4 with Streams
7. Initialize Energy Data
8. Create Internal Storages and Mass balances
9. Setup Post Processing

First it will be shown how to setup a [minimal cooking process simulation](ethos_penalps_in_10_minutes.md). In the following it shown how to add more details to cooking process step by modifying the petri nets of states of the cooker. The next step shows how to add more process steps to increase the complexity of the production system.

