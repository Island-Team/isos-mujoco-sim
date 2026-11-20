# Start by workflow

[中文](../../../docs_cn/mujoco/start/README_cn.md)

Choose the guide for the workflow you are running. The [dev guide](dev.md) covers source builds, RoboCasa smoke runs, native scene inspection, and direct simulator launch. The [IsOS package guide](isos-pkg.md) covers bundle creation, graph admission, strict readiness, governed commands, and stop. The [RoboCasa benchmark page](../core/benchmark.md) records the active task and scoring limits.

For the current schema `0.2.2` hardware candidate, `./build.sh --output ABSOLUTE_EMPTY_DIRECTORY` uses the source candidate version without an explicit `--version`. Prepare shared service configuration and retain both camera size values supplied by the preset before Apply. See the [package contract](../interfaces/package.md#current-wrapper-admission-schema-022).
