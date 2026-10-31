# Repository guidance

Follow [Island coding conventions 1.2.0](docs/island/conventions.v1.3.0.md) and the existing C++20, CMake, formatting, and test patterns in this repository. The copied conventions contain EOS-wide workflow and publication guidance; that guidance describes the EOS repositories, not a publishing mechanism for this standalone simulator package.

The simulator owns MuJoCo scene loading, deterministic reset, physics, rendering, and benchmark scoring. EOS owns its simulator contract and robot-facing HAL and gateway; EGIA connects to EOS as an agent. Keep `proto/simulator.proto` aligned with `../Island-eos/share/contracts/eos/external/simulator/simulator.proto` when changing that interface. Do not expose benchmark ground truth or `proto/benchmark.proto` through EOS or EGIA.

Keep scene metadata, provenance, task rules, interface examples, and verification instructions under [docs/mujoco/](docs/mujoco/README.md) in sync with behavior. A new scene must have deterministic reset and a defined success condition, an academic/source attribution and license review, load and replay tests, and EOS-visible capabilities that the agent can actually use. Document current behavior in present tense and plans as future work.
