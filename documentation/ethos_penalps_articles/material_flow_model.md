# Material Flow Model
The process model is must be a single stranded process chain. It modelled based on written or verbal descriptions of an industrial process. A measured load profile is not required to create the profile even though it can be helpful to identify relevant features of the process. A chain consists of one source, one sink, at least one generic process step and streams that connect the aforementioned elements. Source and sink determine the end and start point of the chain respectively. A process step converts an output stream into an input stream. The required input mass, temporal distance to the output stream and possible split into multiple input streams is determined by a network of process states of the respective process step.
:::{figure-md} process_step_chain
<img src="../visualizations/single_strand_visualization/single_strand_visualization.png" >

Depiction of a process step chain that can be modelled using the ETHOS.PENALPS
:::