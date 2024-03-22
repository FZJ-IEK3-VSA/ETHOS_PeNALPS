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

The user creates the process model based on generic simulation objects. Once the user completes process model, the model receives a set of production orders to initiate the simulation. The simulation generates a production plan that tracks the activity of each node to fulfill the requested set of orders. Load profiles are then created based on the activity in the production plan. The process steps's load profiles are modeled using a Petri net with an extensible number of states that determine their activity and energy demand during production. 

![The main components of ETHOS.PeNALPS are the generic model objects, material flow simulation, production plan and load profiles.\label{fig:Main Component Overview}](main_component_overview.png){width=100%}


# Statement of Need

Energy system models are tools that provide guidance on future energy systems [@Prina.2020 p.1]. However, building long-term models with high spatial and temporal resolution and transparent input data remains a challenge [@Prina.2020 p.12].  For instance, historical load profiles for the German industrial sector in 2015 are available [@Priesmann.2021 p.5-6], while load profiles for other regions are not currently available. Furthermore, decarbonization efforts will cause changes in the industrial sector, creating a need for load profiles of future scenarios. To address the lack of sectoral load profiles for the industry, Boßmann and Stafell [-@Bomann.2015 p.1321] demonstrated the use of a bottom-up approach to create load profiles. Therefore, it is necessary to obtain load profiles of the industrial processes that are part of the industrial sector. However, these profiles are often unavailable for open research due to:

- Companies' efforts to protect commercial secrets;
- Missing measurements; 
-	Unstructured collection of energy data in companies;
-	Novelty of the industrial processes and their current lack of implementation.

ETHOS.PeNALPS can support the creation of an energy system model by providing load profiles for industrial processes. While many industrial processes and their load profiles have been previously simulated, most have not published load profiles and simulation implementation under an open-source license. This creates a research gap, despite similar work having already been done.

The suitability of load profiles simulated by ETHOS.PeNALPS for an energy system model depends on the available input data, the type of process being modeled, and the required temporal resolutions. These three aspects are interdependent, making it impossible to make a static selection of industrial processes that can be provided for all energy system models. At lower temporal resolutions, effects may occur that cannot be modeled under the assumptions of a deterministic Petri net of machine state and average energy consumption per state. Additionally, the temporal resolution of energy system models is evolving. In 2020, a temporal resolution of one hour was considered high for long-term energy system models [@Prina.2020 p.10]. Currently, studies may require load profiles with a resolution as low as one minute [@Omoyele.2024 p.12-13]. 

# Method

There are four simulation modeling paradigms as shown in \ref{fig:Simulation paradigms}. ETHOS.PeNALPS utilizes an agent-based approach for the nodes of a material flow system. Currently, the most important nodes of the material flow system, the process steps, contain a Petri net to model their activity. The part of the ETHOS.PeNALPS simulation based on the Petri net can be classified as a discrete event simulation. @Borshchev.2004 and @Thiede.2012b p.45-49 provide an introduction and comparison to these paradigms.

![Simulation paradigms for material flow simulations [@Thiede.2012b p.47] adapted from [@Borshchev.2004 p. 3]. \label{fig:Simulation paradigms}](simulation_methos.png)

The implementation as agents was chosen to improve the adaptability and extensibility of the software. Thus, more specifics of a node or even another simulation paradigm can be implemented. The [documentation of ETHOS.PeNALPS](www.ethospenalps.readthedocs.io/) contains a roadmap for the software. The process model is generated from generic objects as shown in Figure \ref{fig:Main Component Overview}. The main components are the generic nodes that create and manage material requests as agents. These nodes include

- Source
- Sink
- Process step
- Storage

Streams connect these nodes and determine the direction of material flow in the simulation. Process chains combine sequentially-dependent nodes and streams. These process chains, whether multiple or single, are integrated into a network level. A single network level model can include multiple chains to represent parallel operation of similar equipment. Multiple network levels can be used to model successive production stages of the industrial process. 

A network level consists of a source and a sink that define the start and end points of the material within that level. To connect two network levels, a shared storage is used to replace the source of one network level and the sink of another. Each node functions as an agent that manages material requests.

- Sources only provide materials, while sinks only request them. 
- Process steps and storages provide and request materials. 
  
The simulation is initiated by creating the first request in the sink from the production order. Requests are then passed upstream until they reach the source of the network level. If a request cannot be fulfilled in time, it can be modified within a chain to shift the request to an earlier time and ensure that the deadline is always met.

The behavior of a process step during request fulfillment is determined by a sequence of states that are stored in a Petri net, which is a state transition system consisting of places, transitions, and arcs [@Peterson.1977]. The states can be as simple as on or off switches or constitute a complex network of states during production. The main novelty of this method is the combination of these subsimulations for each process step to model a complete industrial manufacturing process. An example of toffee production is provided in the [ETHOS.PeNALPS documentation](www.ethospenalps.readthedocs.io/) to illustrate the method.


# Other Tools

There are numerous publications on the simulation of energy features of industrial processes. A collection can be found in [@Stoldt.2019 p.69-73].  However, many of these publications are limited to the presentation of concepts and selected simulation results, without implementation details. This lack of information creates a significant overhead for new research.

Stoldt et al. [-@Stoldt.2021] presents a comprehensive literature review on energy-oriented simulations in production and logistics, covering 207 publications. The article identifies the most relevant tools and simulation architectures. The most relevant simulation architectures are the discrete event simulation with integrated energy assessment, discrete event simulation with separate energy simulation, continuous simulation, agent-based simulation, one tool, different models and coupling of models.

Stoldt et al. [-@Stoldt.2021] reported the most commonly used simulation tools include PlantSimulation [-@SiemensDigitalIndustriesSoftware.15.03.2024], Anylogic [-@TheAnyLogicCompany.19.03.2024], Arena [-@RockwellAutomation.17.02.2024], Matlab [-@TheMathWorksInc.21.03.2024], Automod [-@AutoModSimulationssoftware.07.11.2019], Simio [-@LLC.19.03.2024] and Witness [-@LannerGroupLimited.19.03.2024], all of which are commercial tools. No open-source tools were found, although self-developed tools were utilized. Many publications have created extensions for commercial software. For instance, @Kohl.2014 developed an extension for the software PlantSimulation [-@SiemensDigitalIndustriesSoftware.15.03.2024] that maps measured load profiles to process states of manufacturing equipment. However, the implementation of the extension has not been published.

Additionally, Stoldt et al. [-@Stoldt.2021] identified some self-developed standalone tools, but no open-source software was found. Open-source software can prevent the need to  re-implement concepts from old research for new research. The licensing of the following software projects has been investigated.

@Wohlgemuth.2006 developed the software "Milan" which is based on a discrete event simulation. According to Wohlgemuth [-@VolkerWohlgemuth.20.03.2024], it was discontinued in 2015. Anderson et al. [-@Andersson.2012b] intended to develop the "EcoProIt tool" for conducting lifecycle assessments based on discrete event simulation. No further information could be found regarding the publication or licensing status of the tool. The "SIMTER tool" was developed in the SIMTER research project [@SallaLind.2009] for combined environmental impact calculations and discrete event simulation. However, information about licensing and distribution is not available. Rippel et al. [-@Rippel.2017] developed the "μ-ProPlAn framework", but information about the licensing and distribution is not available. @Binderbauer.2022 published "Ganymede", a software that simulates load profiles, but no information about its licensing and distribution is also not available.



# Authors Contribution 

**Julian Belina**: Software, Writing, Visualization, Methodology. **Noah Pflugradt**: Conceptualization, Methodology, Supervision, Writing - Review & Editing. **Detlef Stolten**: Conceptualization, PhD Supervision, Resources, Funding acquisition. 

# References