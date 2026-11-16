# IsOS MuJoCo 模拟器

本仓库提供面向 IsOS 和 EOS 的 MuJoCo 模拟器包，以及本地 RoboCasa 基准流程。

[English](README.md) · [开始使用](docs_cn/mujoco/start/README_cn.md) · [接口](docs_cn/mujoco/interfaces/README_cn.md) · [设计](docs_cn/mujoco/core/README_cn.md)

| 路径 | 运行内容 | 当前范围 |
| --- | --- | --- |
| RoboCasa | 私有 Python 环境中的上游 `CloseFridge` | 本地冒烟运行及可重放的 PandaOmron 硬件记录 |
| 原生模拟器 | C++ MuJoCo 场景引擎和 IsOS 软件包包装层 | `pick-place` 与 `navigation` 兼容场景、面向 EOS 的设备及私有评测 RPC |

EOS 管理机器人侧准入和模拟器子进程。基准评分仅供可信评测器使用，不通过 EOS 或代理暴露。RoboCasa 冒烟运行不等同于 EOS 代理评测。

## 快速开始

Linux 上需要 MuJoCo **3.3.1**、C++20 编译器、CMake 3.22+、protobuf、gRPC、libjpeg、Python 3.11、`git`、`wget` 和 `uv`。`MUJOCO_ROOT` 指向包含 `include/mujoco/mujoco.h`、`lib/libmujoco.so.3.3.1`、`bin/compile` 和 `bin/simulate` 的安装目录。

```sh
cp .env.example .env
# 编辑 .env：export MUJOCO_ROOT=/absolute/path/to/mujoco-3.3.1
./build.sh
ctest --test-dir build --output-on-failure
./launch.sh --benchmark CloseFridge --seed 42 --steps 20 --no-gui
```

`./build.sh` 构建原生目标并准备本地开发所需的 RoboCasa 源码、资源和 Python 环境；`./build.sh --output 绝对空目录 --version 0.2.x` 使用 `config/package.toml` 构建包候选。缺少资源时会先询问。基准输出包含任务、场景、相机、种子、动作数、指令和成功状态的 JSON。运行器使用有界随机动作，`success: false` 仍是有效冒烟结果。依赖、配置、GUI 和故障排查见[首次运行指南](docs_cn/mujoco/start/dev_cn.md)。

## 选择和检查

```sh
./launch.sh --show-config
./launch.sh --list-benchmarks --filter Fridge
./launch.sh --list-kitchens
./launch.sh --list-scenes
./launch.sh --scene pick-place --no-gui
./kill.sh
```

`config/dev.toml` 选择 `config/benchmarks/robocasa.toml`；`.env` 覆盖相同配置，命令参数再次覆盖。原生包装层在后台启动并打印仅所有者可访问的套接字和日志路径。`./kill.sh` 停止启动器记录的进程。详见[任务选择](docs_cn/mujoco/core/benchmark_cn.md)和[原生运行指南](docs_cn/mujoco/start/dev_cn.md)。

## 记录硬件控制

在 `config/benchmarks/robocasa.toml` 中设置 `[record].enabled = true` 和 `[record].path`，或在 `.env` 中导出 `BENCHMARK_RECORD_ENABLED=true` 与 `BENCHMARK_RECORD_PATH`。默认关闭记录。硬件演示写入有版本的本地 JSON，重放时逐步检查机器人状态；记录不含基准奖励、成功信息或图像。

```sh
./launch.sh --record-demo
./launch.sh --replay-record .run/hardware-record.json
```

相对路径以仓库根目录为基准；`--record-demo FILE` 可覆盖本次路径。格式和限制见[记录契约](docs_cn/mujoco/interfaces/record_cn.md)。

## 接入 IsOS

执行 `./build.sh --output ABSOLUTE_EMPTY_DIRECTORY` 构建资源包，再在 IsOS 中验证并安装精确版本。EOS 加载软件包适配器并管理模拟器子进程；IsOS 负责包校验和图准入。命令和停止流程见[软件包指南](docs_cn/mujoco/start/isos-pkg_cn.md)。[文档概览](docs_cn/mujoco/README_cn.md)汇总源码归属、接口、设计、出处和验证。

[GitHub 仓库](https://github.com/Island-Team/isos-mujoco-sim)
