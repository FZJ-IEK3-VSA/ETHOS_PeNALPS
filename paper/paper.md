---
title: 'ETHOS.PeNALPS: A Tool for the Load Profile Simulation of Industrial Processes Based on a Material Flow Simulation'
tags:
  - Python
  - Load Profile
  - Industry
  - Manufacturing
  - Energy Simulation
  - Industrial Production
  - Materials Processing
authors:
  - name: Julian Belina
    orcid: 0000-0002-5878-2936
    affiliation: "1, 2"
  - name: Noah Pflugradt
    orcid: 0000-0002-1982-8794
    affiliation: "1, 2"
  - name: Detlef Stolten
    orcid: 0000-0002-1671-3262
    affiliation: "1, 2, 3"
affiliations:
 - name: Jülich Aachen Research Alliance, JARA-Energy, Jülich, Aachen, Germany
   index: 1
 - name: Forschungszentrum Jülich GmbH, Institute of Energy and Climate Research – Techno-economic Systems Analysis (IEK-3), 52425 Jülich, Germany
   index: 2
 - name: RWTH Aachen University, Chair for Fuel Cells, Faculty of Mechanical Engineering, 52062 Aachen, Germany
   index: 3
date: 30 September 2023
bibliography: citavi.bib
---

# Summary 

ETHOS.PeNALPS (Petri Net Agent-based Load Profile Simulator) is a Python library designed to simulate the load profiles of industrial manufacturing processes for arbitrary energy carriers. It is part of the [ETHOS (Energy Transformation Pathway Optimization Suite)](https://go.fzj.de/ethos_suite). Load profiles
are time series of energy demand. The library models the material flow of industrial processes and the activity of individual machines during production. ETHOS.PeNALPS is capable of simulating processes such as steel, paper, and industrial food production. ETHOS.PeNALPS is able to model non-cyclic industrial production networks. 

Figure \ref{fig:Main Component Overview} shows the main conceptual objects of ETHOS.PeNALPS, which are: 

- Generic model objects
- Material flow simulations 
- Production plans
- Result load profiles

The user creates the process model based on generic simulation objects. Once the user completes process model, the model receives a set of production orders to initiate the simulation. The simulation generates a production plan that tracks the activity of each node to fulfill the requested set of orders. Load profiles are then created based on the activity in the production plan. The process steps's load profiles are modeled using a Petri Net with an extensible number of states that determine their activity and energy demand during production. 

![The main components of ETHOS.PeNALPS are the generic model objects, material flow simulation, production plan and load profiles.\label{fig:Main Component Overview}](main_component_overview.png){width=100%}


# Statement of Need

Energy system models are tools that provide guidance on future energy systems [@Prina.2020 p.1]. However, building long-term models with high spatial and temporal resolution and transparent input data remains a challenge [@Prina.2020 p.12].  For instance, historical load profiles for the German industrial sector in 2015 are available [@Priesmann.2021 p.5-6], while load profiles for other regions are not currently available. Furthermore, decarbonization efforts will cause changes in the industrial sector, creating a need for load profiles of future scenarios. To address the lack of sectoral load profiles for the industry, Boßmann and Stafell [-@Bomann.2015 p.1321] demonstrated the use of a bottom-up approach to create load profiles. Therefore, it is necessary to obtain load profiles of the industrial processes that are part of the industrial sector. However, these profiles are often unavailable for open research due to:

- Companies' efforts to protect commercial secrets;
- Missing measurements; 
-	Unstructured collection of energy data in companies;
-	Novelty of the industrial processes and their current lack of implementation.

ETHOS.PeNALPS can support the creation of an energy system model by providing load profiles for industrial processes. While many industrial processes and their load profiles have been previously simulated, most have not published load profiles and simulation implementation under an open source license. This creates a research gap, despite similar work having already been done.

The suitability of load profiles simulated by ETHOS.PeNALPS for an energy system model depends on the available input data, the type of process being modeled, and the required temporal resolution. These three aspects are interdependent, making it impossible to make a static selection of industrial processes that can be provided for all energy system models. At lower temporal resolutions, effects may occur that cannot be modeled under the assumptions of a deterministic Petri Net of machine state and average energy consumption per state. Additionally, the temporal resolution of energy system models is evolving. In 2020, a temporal resolution of one hour was considered high for long-term energy system models [@Prina.2020 p.10]. Currently, studies may require load profiles with a resolution as low as one minute [xxx]. 

# Method
The simulation is generated from generic objects, as shown in Figure \ref{fig:Main Component Overview}. The main components are the generic nodes that create and manage material requests as agents. These nodes include: 

- Source
- Sink
- Process step
- Storage

Streams connect these nodes and determine the direction of the material flow in the simulation. Process chains combine sequentially-dependent nodes and streams. These process chains, whether multiple or single, are integrated into a network level. A single network level model can include multiple chains to represent the parallel operation of similar equipment. Multiple network levels can be used to model successive production stages of the industrial process. 

A network level consists of a source and a sink, which determine the start and end points of the material within that level. To connect two network levels, a shared storage is used to replace the source of one network level and the sink of another. 

Each node functions as an agent that manages material requests.

- Sources only provide materials, while sinks only request them. 
- Process steps and storages provide and request materials. 
  
The simulation is initiated by creating the first request in the sink from the production order. Requests are then passed upstream until they reach the source of the network level. If a request cannot be fulfilled in time, it can be modified within a chain to shift the request to an earlier time and ensure that the deadline is always met.

The behavior of a process step during request fulfillment is determined by a sequence of states that are stored in a Petri Net, which is a state transition system consisting of places, transitions, and arcs [@Peterson.1977]. The states can be as simple as on or off switches or constitute a complex network of states during production. The main method novelty is the combination of these subsimulations for each process step to model a complete industrial manufacturing process.

The [documentation of ETHOS.PeNALPS](www.ethospenalps.readthedocs.io/) provides an example of a toffee production process to illustrate the method.

<!-- # Example: Toffee Production
The ETHOS.PeNALPS workflow is demonstrated based on the example of a simplified toffee production process, which is described by Korovessi and Linninger [-@Korovessi.2005 p. 31-32]. During the process, the raw toffee materials are mixed, cooked, and cooled in a toffee machine. The cooled toffee is then cut and packaged in two-subsequential machines. The corresponding model is depicted in Figure \ref{fig:Graphical Abstract}. The energy values are taken from similar machines from [@Wojdalski.2015] and should be interpreted as an non validated showcase example. The nodes in the material flow simulation are (a) first named by their generic name and its specific name in the example in brackets. It is assumed that the process consists of two toffee machines that operate in parallel. The toffee produced is cut and packaged by two sequentially-ordered machines. 
The activity of the machines and streams is tracked in the production plan (b), which is partially shown in the figure. Based on the states of the process steps and streams, load profiles (c) are calculated using specific energy demands.

![Demonstration of the functional principle of ETHOS.PeNALPS using the example of toffee production. It contains the main components (a) material flow simulation the production plan (b) and the load profiles (c) \label{fig:Graphical Abstract}](Graphical_Abstract.png){width=100%}

The simulation is begun by passing a set of orders for packed toffee to the packaged toffee sink. It then generates requests for the upstream node, which is the packaging machine. This in turn triggers a chain of upstream requests until it reaches the source. 

While fulfilling the request, a process node switches a cycle through its Petri Net. Figure \ref{fig:Process State network} displays an example Petri Net for the toffee machine. The places of the Petri Net are the machine states of the modeled machine. There are four different kinds of states:

- Idle state (yellow), which is the start and end point
- Input state (green), determines the activity of the input stream
- Output state (red), determines the activity of the output stream
- Intermediate state (gray), resembles a specific task or phase of the production

They are ordered by temporal occurrence during production. To fulfill a request for an output stream, the process step switches over a full cycle from idle state to idle state. Each active state during the switch cycle is tracked in the production plan, which simulates the machine’s activity. Even though the states are stored in the correct forward temporal order, the internal switches occur in the opposite temporal direction. This is useful because the output request that is passed to the process step only provides the required time frame for the output state.

![This figure shows the Petri Net of the example toffee machine and how it determines the activity of the machine in the production plan.\label{fig:Process State network}](process_state_network_activity.png){width=100%}

The packaging and cutting machine only have one state apart from their idle state, which are termed "Cutting" and "Packaging", respectively. Each state can be associated with a specific energy demand that causes an energy demand during the activity of the respective state. Thus the sequential activity of the states can be used to model the energy demand fluctuations in the load profile. Furthermore, an energy demand can also be attributed to a stream to model a conveyor belt or pump, for instance. -->


# Other Tools and Methods

A lot of previous work has been done to simulate the energy features of industrial processes. But none of the work distributed an implementation oft their work. 

Jain et. al {-@Jain.2013 p.412} provides an overview about the different modelling paradigms that are use to model supply chains. These different paradigms are System Dynamics, Discrete Event Simulation, Agent-based simulation and physical- science based simulations.

Stoldt et al. [-@Stoldt.2021] conducted a scoping literature review about energy-oriented simulations in production and logistics which considered 207 publications. There he identified the most relevant tools, simulation architectures. The us architectures are discrete event simulation with integrated energy assessment,  discrete event simulation with separate energy simulation, continuous simulation, agent based simulation, one tool, different models and coupling of models.

The most used tools are PlantSimulation [-@SiemensDigitalIndustriesSoftware.15.03.2024], Anylogic[-@TheAnyLogicCompany.19.03.2024], Arena, Matlab, Automod, Simeo and Witness, which are all commercial tools. Self developed tools were also used but no Tool could be identified which has been published under an open source license.

@Wohlgemuth.2006 developed the software "Milan" which is based on a discrete event. According to Wohlgemuth it has been discontinued in 2015 @VolkerWohlgemuth.20.03.2024. Anderson et al. [-@Andersson.2012b] intended to develop EcoProItTool should be able to used to conduct lifecycle assemssments based on discrete event simulation. No further information could be found about the publish and licesene status of the tool.

Stold[-@Stoldt.2019 p.69] identified at least 15 dissertations or similar publications which conducted material flow simulations with integrated energy consideration. Furthermore Stoldt et al. identified  8 reviews which analyze these types of simulations with different foci [@Stoldt.2019 p.69].

[-@Simul8SimulationSoftware.19.03.2024]
Due to the amount of publications mostly reviews willBut none of implementation is open source. [@Garwood.2018 p.909] investigates which tools can be used for manufacturing process simulation, for Building Energy Models and a holistic simulation of both domains. Garwood et al. identified the following commercial tools which can be used to model manufacturing processes DELMIA [-@DassaultSystemes.2023], FlexSim [-@FlexSim.21.12.2023], Plant Simulation , Simio [-@LLC.19.03.2024], SIMUL8  and WITNESS [-@LannerGroupLimited.19.03.2024]. Still it is noted that the software does not model energy usage directly be default or does so only with limitations[@Garwood.2018 p.903]. Still a lot of the simulations that use the aforementioned software model the load profiles of the manufacturing process. 

One example is @Kohl.2014 who has created an extension for the software [-@SiemensDigitalIndustriesSoftware.15.03.2024] which maps measured load profiles to process states of the manufacturing equipment. So load profiles of the whole process can be obtained. The software Modelica Buildings Library 
[-@ModelicaAssociationInternationalBuildingPerformanceSimulationAssociation.15.03.2024] models buildings and machines. But the machines modelling focus lays on fluid systems and controllers rather than actual production processes. 



One example for another standalone software is 
@Binderbauer.2022 published a study on the “Ganymede” software, which also uses a material flow simulation to simulate load profiles. The material flow simulation is based on a discrete event simulation. Ganymede only distinguishes between continuous and batch process steps. In order to implement more detailed load profiles of machines, external load profiles are required for the respective machines. These are difficult to obtain for many machines, especially as machine-readable data.

@Li.2022 implemented a Petri Net to forecast the energy demand of individual machines in real time. This approach lacks a method to coordinate the activity of multiple machines that are connected in a network.

@Dock.2021 created a discrete event based on a material flow simulation for an electric arc furnace plant. It uses a parameterized Markov Chain load profile model to generate load profiles for the electric arc furnace. Neither the Markov Chain parameters nor the load profile used for parametrization have been published. Moreover, maintenance activity and interdependent activity are implemented for some of the process steps. The applicability of the model to other industrial processes cannot be verified, because the source code of the model has not been published.

@Sandhaas.2022 use a different approach to generate load profiles which is not based on a material flow simulation. Rather, their approach is based on the recombination of eight standard load profiles of appliances, which are used to model the load profile of an industry. For a specific industry the share of each appliance of the standard load profiles is determined. These shares are then used as weights in th recombination of the standard load profiles. Furthermore, some stochastic fluctuation is applied to the recombined load profile. This approach requires less input data, but cannot model any features that are not contained in the standard load profiles. It has been published as an open-source code.

The software eLOAD employs an approach similar to that from Sandhaas. Instead of applying it to individual industries, @Bomann.2015 applies it at a national level. They also assume demand response flexibility for some appliances. The source code and appliance load profiles used have also not been published. 

# Summary and Conclusion
ETHOS.PeNALPS is a tool which can be used to model load profiles of industrial manufacturing processes. Therefore it models the material flow o

# Authors Contribution 

**Julian Belina**: Software, Writing, Visualization, Methodology. **Noah Pflugradt**: Conceptualization, Methodology, Supervision, Writing - Review & Editing. **Detlef Stolten**: Conceptualization, PhD Supervision, Resources, Funding acquisition. 

# References