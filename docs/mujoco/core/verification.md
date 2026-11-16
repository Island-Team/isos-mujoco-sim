# Full interface replay

[中文](../../../docs_cn/mujoco/core/verification_cn.md) · [Core index](README.md) · [Package contract](../interfaces/package.md)

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

## Local verification, 2026-11-16

The native custom-scene GUI replay passed and exited automatically. IsOS `pkg check` passed for native and RoboCasa full graphs at candidate version `0.2.6` with 256 × 192 camera settings; `tests/package_logs.py` found matching service output and EOS run IDs. The three-kitchen GUI record and headless replay completed for `1:1`, `2:2`, and `3:3`, with three actions and matching summaries per kitchen. The bounded actions did not complete the `CloseFridge` task; this replay verifies launch, action delivery, deterministic replay, GUI exit, and cleanup. Complete local output is under ignored `data/test/20261116-full-interfaces/`, including `robocasa-three-final/summary.json`.
