# Define a Process Step
A process step consists of the following components:
1. An Idle State
2. A Process State Network
    1. Either an OutputAndInputStreamProviding State
    2. Or an output stream providing state and an Input stream providing state
    3. AN arbitrary number of intermediate states  
3. A mass balance on basis of the output commodity
4. A Storage
5. An input Stream
    1. Either a Continuous Stream
    2. or a Batch Stream
6. An output Stream
    1. Either a Continuous Stream
    2. or a Batch Stream


## Process State Network in a Process Step
The purpose of process steps is to provide the output mass that is requested by a downstream process step or a sink. The output mass can be either provided from an internal storage or by a requested input stream. The chain of request can be passed until the source. In order to determine if and at what time an input stream is requested the process step shifts through process states as depicted in the following two graphs. The output stream is provided during an output stream providing state. The input stream is requested during the input providing state. If the output stream is provided directly from the storage the process step switches directly to the output state. If the not enough mass can be provided by a single input stream, it is possible to request multiple input streams.


:::{figure-md} process_states_with_separate_input_and_output_states
<img src="../visualizations/process_state_visualizations/process_state_network_separate_input_and_output.png"   >

Depiction of a process states and their connectivity with separate input and output state 
:::

:::{figure-md} process_states_with_combined_input_and_output_states
<img src="../visualizations/process_state_visualizations/process_state_network_combined_input_and_output.png"   >

Depiction of a process states and their connectivity with combined input and output state 
:::

# Process States 
1. process states must be connected in a closed loop
    1. idle state -> input stream providing state -> output stream providing state ->
2. Between each step an arbitrary number of intermediate steps can be integrated
3. Each process state must contain one process state switch selector
    1. It can contain a single state switch or select between to state switches based on a condition of the process state
4. Process state switches determine the length of the current state. They can be based on:
    1. Output stream start and end time 
    2. Input stream start and end time
    3. A fixed time_delta determined by the use

## OutputStreamProvidingState
It must provide 
1. A function to determine the maximum output that can be provided by the process step.
2. A function to determine the acceptable storage level when the production branch is fulfilled
3. A function to determine if the output stream can be supplied without issuing a new input stream request
4. A function to determine if the production branch is fulfilled

## InputStreamProvidingState
An InputStreamProvidingState must define
1. A function to determine an input stream based on an output stream
2. A function to determine further input streams if previously a single input stream could not satisfy the output stream
3. A function to create the storage entries based on the input and output streams



