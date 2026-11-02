# Original model inspection diagrams

The tensor workflow is copied byte-for-byte from the original decoded parameter
inspector. Each heatmap cell is a scalar, not a bit or byte; normalization is per
tensor, all four expert banks are shown, and only two execute per inference.
It is not reconstructable model data or an activation trace.

The dark connection graph is a color-only presentation of the original native
Netron 9.3.4 export: labels, tensor dimensions, residual branches and graph
geometry are unchanged. Its PNG is browser-rendered with Chromium, not represented as
a fresh native Netron capture. The exact original light PNG/SVG are preserved.
These are inspection views, not the C64 packet or new hardware acceptance.

- [Tensor workflow PNG](tensor-workflow.png) / [SVG](tensor-workflow.svg).
- [Dark graph PNG](netron-dark.png) / [SVG](netron-dark.svg).
- [Original graph PNG](netron-original.png) / [SVG](netron-original.svg).
- [Source and derivative hashes](provenance.json).
