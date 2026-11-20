# Repository agent guide

Follow the [IslandTeam conventions](docs/conventions.v1.4.0.md) and the [MuJoCo documentation index](docs/README.md). This file is a short map of the current repository, not a second source for product contracts. Before changing behavior, read `docs/start.md`, `docs/package.md`, the owning `docs/node/<core>/<layer>/<group>.md`, and relevant `docs/core/` pages. The owning interface defines public behavior. Keep English `docs/` and Chinese `docs_cn/` pages, examples, and links aligned.

## Current source map

`src/mujoco/` owns scene loading, deterministic reset, physics, rendering, and private benchmark scoring. `src/isos/` owns the native service and strict socket. `src/plugin/` builds the C++20 `isos_node_v2` adapter loaded by EOS. `robocasa_core/` is the Python user hardware API; `tools/robocasa_worker.py` runs it in a separate IsOS-owned service. `tools/nodes.py` and `tools/bundle.py` declare and package both services. Source, package, node type, graph, ABI, and socket versions are independent.

IsOS owns verified package selection, service configuration, graph Apply, and child supervision. EOS owns Dispatcher admission, the robot-facing hardware boundary, health, and Stop proof. EGIA acts through EOS. The [architecture overview](docs/architecture.md) explains the current data flow and explicitly labeled targets. Preserve the EOS graph port and payload contracts when changing an adapter; camera `frame` is also consumed by the EOS Vision route. The native `cam-0` device renders JPEG from the selected scene, while RoboCasa cameras return RGB8. Keep service and device behavior isolated. Do not expose benchmark ground truth or `proto/benchmark.proto` to EOS or EGIA. If changing the retained simulator RPC, keep `proto/simulator.proto` aligned with its EOS-owned counterpart when that source is available.

## Change workflow

Create a focused `<change-type>/<topic>` branch from the confirmed integration target. Use `fix`, `test`, `docs`, or `refactor` as the change type; this local naming rule supersedes the shared `refactor(v2)` prefix for future branches. Preserve unrelated changes. For a public change, update the owning contract, implementation, fixtures, tests, and first-use guidance together. Check build, installation, runtime, and test callers before removing a component. Keep scene metadata, provenance, task rules, interface examples, and verification instructions under [docs/](docs/README.md) in sync. A new scene needs deterministic reset, a defined success condition, source attribution and license review, load and replay tests, and usable EOS-visible capabilities.

Run checks relevant to the changed boundary using the repository's CMake and C++20 patterns, root formatting rules, Python boundary tests, CTest, and selected-service IsOS package checks. Test success, rejection, service failure, and Stop at the real boundary where applicable. Save complete output under ignored `data/test/<run-id>/` and record reproducible commands and outcomes in the owning guide.

Follow the [shared publication workflow](docs/conventions.v1.4.0.md#change-and-release-workflow) for review, testing branch, PR, merge, and cleanup. Confirm the integration target before publishing. A local build or package check is evidence for a candidate, not publication of a release; the [package contract](docs/package.md) owns qualification and release rules.

## Documentation boundaries

Current guides describe implemented behavior in present tense. Put future behavior in `docs/architecture.md` or the owning `core/` page as a labeled target and link to its executable TODO. Keep shared conventions separate from repository-specific layout changes. Do not duplicate wire fields or payload definitions outside the owning interface. Keep private hardware identities, credentials, calibration, endpoints, and field evidence out of public source and docs.

## Documentation layout

`docs/README.md` is the documentation entry point; root README files contain a quick start and `docs/start.md` owns the detailed local and managed workflows. `docs/architecture.md` owns package responsibilities and data flow. Keep `docs/core/` flat and specific to this package: native runtime and retained RPC, RoboCasa hardware and record/replay, EOS adapter and private service control, and benchmark method and evaluator RPC. `docs/package.md` owns package declarations and qualification rules, `docs/development.md` owns contribution and verification procedures, and `docs/changelog.md` preserves historical releases and dated evidence. Shared conventions live at the docs root.

Node references use `docs/node/<core>/<layer>/<group>.md`, matching IsOS. Each group owns its exact node types, ports, payloads, carriers, rates, settings/defaults, availability, rejection, and Stop. These are package-contributed nodes, not IsOS built-ins. The flat package and core contract pages supersede the shared convention's `interfaces/` directory rule for this repository; do not add `api/`, `interfaces/`, `start/`, or a redundant product directory. Mirror this reading path in `docs_cn/` with `_cn` filenames. Run `python3 tools/check_docs.py --all` after changing navigation.
