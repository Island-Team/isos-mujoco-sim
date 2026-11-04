# 旧实现调用者核查（2026-11-04）

[English](../../../docs/mujoco/maintenance/legacy-caller-audit.md)

IsOS 受管理路径使用严格模式的 v2 帧套接字。以下旧路径仍有调用者，因此保留。

| 候选项 | 构建、运行时或测试调用者 | 结论 |
|---|---|---|
| `src/service.cpp`、`src/service.h`、`proto/simulator.proto` | `src/main.cpp` 调用 `Serve`；直接启动的 `launch.sh` 传入 `--socket` 与 `--benchmark-socket`；`tests/smoke.sh`、`tests/eval.py` 和 `smoke-rpc` 检查 gRPC 路径。EOS 也保存 simulator proto。 | 保留直接运行兼容性及已发布 proto。受管理严格模式禁止两个旧监听器。 |
| `proto/benchmark.proto`、`benchmark-eval` | 可信的直接运行评测器调用 Reset、Step 和评分 RPC；`tests/eval.py` 覆盖此路径。 | 保留，仅供评测器使用。 |
| `benchmark-reset` | `tests/q03_socket_bench.py` 使用此私有工具进行确定性种子重置；Q03 验证命令也指定该目标。 | 在基准工具有替代实现前保留。 |
| 直接模式的 `--v2-socket` | `tests/v2.py` 与 Q03 工具覆盖该路径；直接运行时可与历史监听器共存。 | 保留。README 和英文用法示例现列出三个不同的套接字。 |

上述候选项均非无调用者实现。IsOS 受管理子进程仍通过 `--managed-strict-socket` 启动，仅使用所有者可访问的 v2 与伴随停止套接字。

## 当前基线

- 命令：`eos-mujoco-sim --help` 列出直接运行的 `--socket`、`--benchmark-socket`、可选 `--v2-socket` 与 `--managed-strict-socket`；`launch.sh`/`kill.sh` 持有独立进程；`benchmark-eval` 仅供评测器使用。
- 安装：`CMakeLists.txt` 只将 `eos-mujoco-sim` 安装到 `bin`。`tools/build-backend-bundle.py` 生成独立的 IsOS 包；CMake 不安装测试及基准工具。
- 接口：直接运行的历史 gRPC simulator 与 benchmark 套接字仍为私有路径；受管理路径仅开放 v2 帧套接字和派生的 `.stop` 伴随套接字。精确请求与响应契约见 `docs/mujoco/interfaces/socket.md`。
- 图版本：`tools/node_contributions.py` 输出七个 `@v0.1` 注册类型；`tools/scene_catalog.py` 输出 catalog `0.1.0`。IsOS 持有编写图的版本与持久化；模拟器不修改已应用图。
