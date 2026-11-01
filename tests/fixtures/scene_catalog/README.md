# P02 frozen design fixtures

These files pin the intended `island/mujoco-sim@0.1.1` scene/device catalog before implementation. `target-descriptor.json` is the additive `backend-v2.json` schema-`2.0.0` target; its scene hashes match the two repository XML files at design review. `expected-contribution.json` records the new process type and the seven type IDs in the `0.1.0` `sim-hardware` template. It is an expected projection, not a current release payload. `negative-cases.json` records failures for package, semantic catalog and revision boundaries; implementation tests should use these cases or equivalent assertions.

P01 verifies the exact receipt, payload tree, sidecar and safe paths first. P02 may derive options only from that verified handle. P03 defines the generic node-options response. R05 later validates device IDs and commands on the private socket. No fixture grants actuator authority or changes legacy graph bytes.
