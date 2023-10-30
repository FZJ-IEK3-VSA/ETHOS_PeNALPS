# Introduction to ETHOS.PeNALPS

ETHOS.PeNALPS (Petri Net Agent based Load Profile Simulator) is a Python library for the
simulation of load profiles of industrial manufacturing processes. It is part of ETHOS (Energy Transformation Pathway Optimization Suite). Load profiles are energy demand time series. Processes that can be simulated using ETHOS.PeNALPS include, for example, steel, paper, and industrial food production. One or multiple product orders are passed to the model which starts the simulation and eventually creates the desired load profiles. The workflow of the simulation consists three main components which are described in the following and are shown in this [depiction](graphical-abstract).

1. Industrial Process Model
   - Material Flow Model
   - Process Step Communication Model
2. A Production Plan
   - Stream Activity
   - Process Step Activity
3. Output Load Profiles for each
   - Process Step
   - Stream
   - Energy Carrier

:::{figure-md} graphical-abstract
<img src="visualizations/graphical_abstract/graphical_abstract.png" >

Depiction of the model of the industrial process, production plan and the output load profiles.
:::

At the top an the industrial process model is shown which determines the material flow direction, the input request behavior and the output stream adaption behavior. Through a sequence of requests and adaptions a production plan is created that produces the requested production order.

The production plan consists of the stream activity and the activity of process steps. The stream activity is characterized by the mass transported in a certain period. Process step activity is determined by the length and sequence of process states that characterize its production behavior. 

This production plan is then converted into load profiles using mass or time specific energy demands for each energy carrier of interest. The load profiles of each process step and stream are finally aggregated for each energy carrier to represent the load profile of the whole industrial process.

# Installation


<!-- :::{figure-md} example_gantt_chart_without_load_profiles
<img src="visualizations/general_description/example_gantt_chart.png">

Gantt chart of a production plan created by the ETHOS_PENALPS. It shows the result of a single   
:::





## Load profile creation
Load profiles can be generated based on the mass that is transported in the streams or that is stored in the storage of a process step. The following graph shows an example in a load profile is associated with an input stream, an intermediate state and an output stream.



:::{figure-md} example_gantt_chart_without_load_profiles
<img src="visualizations/general_description/example_gantt_chart_with_load_profiles.png">

Gantt chart of a production plan and load profiles created by the ETHOS.PENALPS.  
:::

When multiple process steps are chained it is possible that an upstream process step can not deliver a stream as requested. This might be caused by a lower capacity of an upstream process step or a preparation time of which the downstream process step is not aware. Therefore a process step is able to communicate with its upstream and downstream process node. The priority of the process step is to deliver the output stream just in time. If that is not possible the mass is delivered earlier so that the deadline can still be met. This communication is realized using 4 different order types are implemented. 
The DownstreamValidationOrder and DownstreamAdaptionOrder can be passed to the downstream process node.The UpstreamNewProduction and UpstreamAdaptionOrder can be passed to the upstream process node.

 -->
