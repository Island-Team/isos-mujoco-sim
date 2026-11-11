# Future package interfaces

- Qualify shared-library loaders for macOS and Windows after host triples, binary dependencies, ABI tests, and managed Stop replay are available. Unsupported platforms fail closed now.
- Keep Python nodes out of the IsOS/EI/EOS address space. A later Python package can use a supervised process interface with bounded I/O, interpreter isolation, and explicit Stop evidence; do not embed a Python interpreter or rely on GIL behavior in the C ABI host.
- Add Dispatcher-mediated movement to `sim-hardware` only after EOS verifies the package's strict stop companion socket and ties commands to the applied run and graph revision.
