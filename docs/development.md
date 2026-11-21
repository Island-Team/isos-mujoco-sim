# Develop and verify the package

[中文](../docs_cn/development_cn.md) · [Docs](README.md)

Use C++20 and the root CMake and formatting configuration. `src/mujoco/` owns the native scene engine; `src/isos/` owns its service; `src/plugin/` owns the EOS adapter; `robocasa_core/` and `tools/robocasa_worker.py` own the Python hardware boundary and isolated service. `tools/nodes.py` and `tools/bundle.py` declare and package both services.

## Development workflow

Create a focused `fix/`, `test/`, `docs/`, or `refactor/` branch from the confirmed integration target and preserve unrelated changes. Before changing public behavior, update its owning node, package, or core contract, implementation, fixtures, examples, and both languages together. Follow [shared publication rules](conventions.v2.0.0.md#change-and-release-workflow) for independent review, PR, testing branch, merge, and cleanup; local checks do not publish a package.

For a new device or scene, define the problem and supported capability, then update `tools/catalog.py` or `tools/nodes.py`, service handling, adapter translation, package configuration, and the owning reference. Preserve EOS Dispatcher admission and Stop proof, exact version identities, isolated native/RoboCasa devices, and evaluator privacy. Check build, installed package, runtime, and test callers before removing a component.

## Routine checks

Use the actual local MuJoCo installation and keep complete command output under ignored `data/test/<run-id>/`. The Ubuntu 22.04 profile and host requirements are described in [start](start.md#ubuntu-2204-builds).

```sh
cmake -S . -B build -DMUJOCO_ROOT=/absolute/path/to/mujoco-3.3.1
cmake --build build -j4
ctest --test-dir build --output-on-failure
python3 tests/catalogtest.py
python3 tests/nodes.py
python3 tests/release.py
python3 tests/config_modes.py
python3 tests/build_env.py
python3 tests/fixtures/strict_socket/check.py
python3 tests/fixtures/strict_stop_lane/check.py
python3 tools/check_docs.py --all
git diff --check
```

Run `clang-format --dry-run --Werror` on changed C++ files using the root formatting configuration. Python hardware changes need stubbed unit tests: `PYTHONPATH=. .local/robocasa-venv/bin/python -m unittest discover -s tests -p 'robocasahardware.py' -v`; use `robocasarecord.py` for record/replay changes and `robocasaworker.py` for the private worker. Standard payload changes also require `tests/eos_contracts.py` against the selected IsOS profile binary and built plugin. Exercise success, rejection, service failure, and Stop at the changed real boundary. The full replay procedures above require prepared simulation dependencies and establish only their stated scope.

The documentation checker validates relative files and section anchors in both trees, root guides, source READMEs, and fixture READMEs. For a docs-only change, run it, both frozen design checkers, and relevant declaration checks; a layout migration does not qualify a new runtime or release. Keep the shared conventions byte-for-byte aligned with their upstream version when moving them.

## Documentation rewrite verification 20 November 2026

The documentation checker, frozen R05/R06 checks, `tests/catalogtest.py`, `tests/nodes.py`, `tests/release.py`, `tests/config_modes.py`, `tests/build_env.py`, and `git diff --check` passed using the commands above. Link checking covered 46 Markdown files with zero broken relative links; the two language trees each contain 19 pages with matching paths, and shared conventions moved without byte changes. R05/R06 checked 31/48 frozen cases; catalog, node, release, and configuration tests passed 8/17/1/2 cases respectively, and build-environment isolation passed. `python3 -m py_compile tools/check_docs.py tests/fixtures/strict_socket/check.py tests/fixtures/strict_stop_lane/check.py` also passed. Complete commands and output are under ignored `data/test/20261120-docs-rewrite/`. This change verifies documentation and declaration boundaries; it does not rerun CTest, real Gym, or managed package qualification, or publish a package.

On 2026-11-21, the same documentation, frozen matrix, declaration, configuration, build-environment, Python compilation, and whitespace checks passed again after rebasing onto the current `master`. Complete output is under ignored `data/test/20261121-commit-merge/`. This remains documentation and declaration verification; no runtime or release qualification was rerun.

<a id="full-interface-replay"></a>
## Full interface replay

This replay checks the native simulator and the isolated RoboCasa service at their separate hardware boundaries. A copied MJCF changes the native model name while retaining the licensed mesh assets and declared benchmark profile. The native replay starts the package executable in strict mode with a live X11 GUI, checks camera, base, arm, and gripper health and observations, rejects an out-of-range movement, moves base, arm, and gripper, proves Stop on the companion socket, rejects a stale movement, and confirms child and socket cleanup. The test exits on its own.

```sh
python3 tests/full_interfaces.py build/eos-mujoco-sim assets/scene.xml \
  data/test/<run-id>/native --gui
```

RoboCasa uses the upstream Gym environment rather than the native C++ engine. Install the pinned full object assets with `./tools/robocasasetup.sh --full` before testing fixed kitchens. The three-kitchen harness records three bounded actions in each of `1:1`, `2:2`, and `3:3`, shows each live camera GUI, closes it after the final frame, then replays the exact actions without a window and compares the result. Its files stay under ignored `data/test/`.

Asset setup prints each archive's cached, download, and extraction state to the terminal. During a download it reports bytes received and, when the server supplies the length, the total and percentage about every five seconds. Interrupted `.part` downloads resume when the server supports byte ranges.

```sh
python3 tests/full_robocasa.py .local/robocasa-venv/bin/python \
  tools/robocasahrun.py data/test/<run-id>/robocasa
```

For the package boundary, run IsOS `pkg check` with a native and a RoboCasa full-preset graph pinned to the candidate version and a local package TOML. That check rebuilds and verifies exact bytes, applies each graph, exercises admitted observations and commands, rejection, service failure, Stop, and socket cleanup. `tests/package_logs.py <check-output>` then verifies that IsOS captures each package service's ready line as `package_service_output` with its package identity, instance, stream, and run ID, and that EOS records use the same run ID. IsOS owns the JSONL envelope and durable log pools; the package writes only bounded service output. Use the IsOS [log guide](https://github.com/Island-Team/isos-p/blob/master/docs/isos/core/logger.md) when that sibling checkout is available.

```sh
ISOS_AETHER_BIN_DIR=<isos-build-directory> isos pkg check \
  --source "$PWD" --version <candidate-version> --output <empty-output-directory> \
  --graph <native-graph.json> --graph <robocasa-graph.json> \
  --package-config <local-package.toml>
python3 tests/package_logs.py <check-output-directory>
```

<a id="interaction-route-todo"></a>
## Interaction route acceptance TODO

**Target design — not implemented.** This task depends on IsOS and EOS implementing versioned interaction declarations and route admission.

- [ ] Bind the exact owner-supported interaction declarations without inferring roles from socket operations.
- [ ] Extend the composed owner replay to deliver a captured frame through the admitted subscriber route and Stop while capture is pending. Use `python3 tests/full_interfaces.py build/eos-mujoco-sim assets/scene.xml data/test/<run-id>/native --gui` as the existing service-boundary baseline, then add owner-route assertions; this baseline alone does not prove the future route.
- [ ] Reject unavailable services, stale run/revision, wrong devices, malformed frames, blocked consumers, and missing routes; verify movement still requires Dispatcher admission and uncertain commands are not replayed under new IDs.
- [ ] Update both languages and save complete cross-owner evidence before describing the route as supported.
