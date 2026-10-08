# Motivation & object
Knill type qec has some good property, the broad goal is to construct FTQC architecture using Knill QEC. 

The positioning of this research extends beyond the mere optimization of the Knill error correction (EC) supply system. Instead, it is more accurately defined as the construction of an architecture framework that formulates a fault-tolerant quantum computing (FTQC) architecture using Knill EC as a primitive, structured as a set of interchangeable modular components where each component and its interconnections can be indepeldently designed and optimized. 

The analogy with the "Extractors" framework is fundamental of this research. 
The Extractors paper extends quantum low-density parity-check (QLDPC) memory into computational units called EAC (Extractor-augmented computational) blocks and abstructs inter-block connections as a block map $M = (V, E)$. 
Furthermore, it treats the relationship between circuit partition and the block map as acompiler-side constraint. Rather than detailing specific physical devices, it defines architecture hierarchically. 

$$\text{computational primitive} \rightarrow \text{module} \rightarrow \text{module interconnection} \rightarrow \text{compilation}$$

Crucially, regarding magic-state supply, the Extractors framework explicitly distinguishes between attaching a local factory to each EAC block, sharing a factory among a small number of adjacent blocks, and distributing from a global factory. This is nearly isomorphic to the design space currently under consideration in this research:

However, the structural differences must be clearly delineated. In the Extractors framework, the central primitive is the fault-tolerant logical Pauli measurement, which is connected via bridges and adapters to construct a Pauli-Based Computation (PBC) architecture. In contrast, the central primitive in the proposed architecture is Knill error-correcting teleportation, and the primary constituents of a module are:

$$\text{online data block} + \text{auxiliary-state preparation} + \text{postselection} + \text{buffer} + \text{local transversal coupling}$$

Therefore, while stating that this research replaces the Extractors framework with transversal-gate logic captures the general direction, a more precise positioning is that whereas the Extractors framework constructed a modular FTQC architecture based on the logical-Pauli-measurement primitive, this study constructs a similar modular architecture abstraction utilizing Knill error-correcting teleportation and transversal logical operations as foundational primitives.

The structural progression of the Extractors paper serves as a highly relevant reference for organizing this research. Its bottom-up approach—defining the primitive first, followed by single-module design, multi-module interconnection, architecture graph formulation, compilation, and resource trade-offs—is directly applicable to the proposed framework. While prior work such as Hirano et al.(magic pool) is closely related when evaluating the stochastic behavior of the supply subsystem, the Extractors framework provides the more appropriate foundational precedent for constructing the overall architecture abstraction.

[Extractors](https://arxiv.org/abs/2503.10390)
