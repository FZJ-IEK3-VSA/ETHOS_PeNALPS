# Structure of the ETHOS.PENALPS
In order to understand how the ETHOS.PENALPS works its modules are separated into three layers:
- First layer
  - Is responsible for the communication between process steps.
- Second layer
  - Determines the required input stream state from the output stream state. It keeps track if the required input and output stream can be provided coherently
- Third layer 
  - Is an intermediate storage for the state between to requests


<!-- :::{figure-md} first-layer-fig
<img src="../visualizations/data_structure_diagrams_ethos_PENALPS/packages_first_layer.svg" alt="fishy" class="bg-primary mb-1"> -->

This is the first layer of the packages in ETHOS.PENALPS
:::

1. EnterpriseStructure is the main container for process steps. 
2. ProcessSteps model the structure of an industry process. 
3. NodeOperations are used to
   1. Request streams from upstream process steps
   2. Request changes in streams from upstream and downstream process steps
   3. Validate that stream can be supplied as requested
4. A ProductionBranch is created for each request that is made to a process step. It keeps track how many inputs are required to fulfill the request of the production branch. 
5. A TemporalBranch is created for each required input
6. ProcessStateHandler is the interface to the next layer. It conducts all process state switches that are necessary to convert an input stream into an output stream.


<!-- :::{figure-md} second-layer-fig
<img src="../visualizations/data_structure_diagrams_ethos_PENALPS/packages_second_layer.svg" alt="fishy" class="bg-primary mb-1"> -->

This is the second layer of the packages in ETHOS.PENALPS
:::
- The Process state handler contains all process states of the respective process step. Process state handler of different process steps are not connected.
- The process state switch

<!-- :::{figure-md} markdown-fig
<img src="../visualizations/data_structure_diagrams_ethos_PENALPS/packages_third_layer.svg" alt="fishy" class="bg-primary mb-1">

This is the third layer of the packages in ETHOS.PENALPS
::: -->

testete4st asdf

<!-- :::{figure-md} third_layer-fig
<img src="../visualizations/data_structure_diagrams_ethos_PENALPS/packages_whole_library.svg" alt="fishy" class="bg-primary mb-1"> -->

These are all packages in the ETHOS.PENALPS in a single diagram
:::

testete4st asdf