# ETHOS.PeNALPS

ETHOS.PeNALPS (Petri Net Agent based Load Profile Simulator) is a Python library for the simulation of load profiles of industrial manufacturing processes. It is part of [ETHOS (Energy Transformation Pathway Optimization Suite)](https://www.fz-juelich.de/de/iek/iek-3/leistungen/model-services). Load profiles are energy demand time series. Processes that can be simulated using ETHOS.PeNALPS include, for example, steel, paper, and industrial food production. One or multiple product orders are passed to the model which starts the simulation and eventually creates the desired load profiles.

# Working Principle

{numref}`main-component-overview` shows the main conceptual objects of ETHOS.PeNALPS which are:

- Generic model objects
- Material flow simulations
- Production plans
- Result load profiles

The model of the material flow simulation is created by users based on generic simulation
objects. After the material flow simulation is completed, a set of production orders is passed to the model to start the simulation. The simulation generates a production plan that tracks the activity of each node to fulfill the requested set of orders. Based on the activity in the production plan, the load profiles are created for each node in therein. 

:::{figure-md} main-component-overview
<img src="./visualizations/main_components/main_component_overview.png" >

Depiction of the main components and workflow of ETHOS.PeNALPS
:::

A further description of the model definition can be found [here](ethos_penalps_articles/model_description.md). 
Also two examples for a [toffee production process](examples/toffee_example.md) and a [b-pillar production process](examples/b_pillar_example.md) are available.


# Installation

## Requirements
The installation process uses a Conda-based Python package manager. We highly recommend using (Micro-)Mamba instead of Anaconda. The recommended way to use Mamba on your system is to install the Miniforge distribution. They offer installers for Windows, Linux and OS X. Have a look at the [Mamba installation guide](https://mamba.readthedocs.io/en/latest/mamba-installation.html#mamba-install) for further details. In the following commands mamba and conda are exchangeable if you prefer to use conda or mamba. 


## Installation via conda-forge
The simplest way ist to install FINE into a fresh environment from conda-forge with:

Create a new environment
```python
mamba create -n penalps_env 
```

Activate the environment
```python
mamba activate penalps_env
```

Install ETHOS.PeNALPS from conda forge
```python
mamba install -c conda-forge ethos_penalps
```

## Installation from Github for Development

First the repository must be cloned from Github

```python
git clone https://github.com/FZJ-IEK3-VSA/ETHOS_PeNALPS.git
```
Then change the directory to the root folder of the repository.
```python
cd ETHOS_PeNALPS
```

Create a new environment from the environment.yml file with all required dependencies.
```python
mamba env create --file=environment.yml
```

Activate the new environment.
```python
mamba activate ethos_penalps
```

Install ethos_penalps locally in editable to mode for development.
```python
pip install -e .
```

# Tests

The library can be tested by running pytest with the following command from the root folder.

```python
pytest
```

# Documentation 

A ReadTheDocs Documentation can be found [here](https://ethospenalps.readthedocs.io/en/latest/Introduction.html).