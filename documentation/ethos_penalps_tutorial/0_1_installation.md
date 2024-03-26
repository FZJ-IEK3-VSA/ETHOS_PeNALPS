# Installation

## Requirements
The installation process uses a Conda-based Python package manager. We highly recommend using Mamba instead of Anaconda. The recommended way to use Mamba on your system is to install the Miniforge distribution. They offer installers for Windows, Linux and OS X. Have a look at the [Mamba installation guide](https://mamba.readthedocs.io/en/latest/installation/mamba-installation.html) for further details. If you prefer to stick to Anaconda you should install the [libmamba solver which is a lot faster than the classic conda solver](https://www.anaconda.com/blog/a-faster-conda-for-a-growing-community). Otherwise the installation of ETHOS.PeNALPS might take very long or does not succeed at all.  

```
conda install -n base conda-libmamba-solver
conda config --set solver libmamba
```

Please note that the installation time of the libmamba solver can be very long if you have installed a lot of other packages into you conda base environment. In the following the commands mamba and conda are exchangeable if you prefer to use conda.


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

The library can be tested locally by running pytest with the following command from the root folder.

```python
pytest
```

An automatic test pipeline is setup on the Github repository which tests both installations on a daily basis.