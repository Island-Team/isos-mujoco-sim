# IsOS MuJoCo 模拟器

[English](README.md) · [首次运行指南](docs_cn/mujoco/usage/dev_cn.md) · [文档概览](docs_cn/mujoco/README_cn.md)

本仓库有两条可运行路径。当前基准是上游 RoboCasa365 `CloseFridge`，通过其 Python 环境在本地启动。C++ MuJoCo 模拟器提供直接开发用的核心和 IsOS/EOS 软件包包装层；抓取放置与导航场景保留为兼容性测试场景。EOS 连接包装层，向代理提供机器人设备与 primitive；只有可信评测器使用独立的私有 benchmark 套接字。RoboCasa 目前尚无 EOS 适配器。

## 构建全部内容

在 Linux 上安装 MuJoCo **3.3.1**、C++20 编译器、CMake 3.22 或更新版本、protobuf、gRPC、libjpeg、Python 3、`git`、`wget` 和 `uv`。复制环境示例文件，将 `MUJOCO_ROOT` 设为 MuJoCo 安装目录的绝对路径。目录下需包含 `include/mujoco/mujoco.h`、`lib/libmujoco.so.3.3.1`、`bin/compile` 和 `bin/simulate`。

Protobuf 要求 3.12 或更新版本；低于 3.15 的版本会自动启用 proto3 optional 实验参数。在 Ubuntu 22.04 上，gRPC 依赖安装 `libgrpc++-dev`、`protobuf-compiler-grpc` 和 `pkg-config`。构建优先使用 gRPC 的 CMake 配置；若软件包未提供该配置，则通过 pkg-config 查找 `grpc++`，并单独查找 `grpc_cpp_plugin`。

```sh
cp .env.example .env
# 编辑 .env：export MUJOCO_ROOT=/absolute/path/to/mujoco-3.3.1
./build.sh
ctest --test-dir build --output-on-failure
build/mujoco-core --scene "$PWD/assets/scene.xml" --seed 42 --steps 20
```

`config.toml` 提供仓库级默认值，并指向基准配置文件 `config/benchmarks/robocasa.toml`；被忽略的 `.env` 覆盖同名配置。`./build.sh` 将全部 C++ 目标构建到 `build/`，包括 `mujoco-core` 和 `eos-mujoco-sim`。dev 模式还会检查 RoboCasa 源码、私有 Python 环境和资源，并在下载前询问。本地启动包装层并随后停止：

仓库的 `SIM_PROFILE = "isos-pkg"` 默认选择 IsOS 包构建。本机开发时，在 `.env` 增加 `export SIM_PROFILE=dev`；此时 `./build.sh` 也准备 RoboCasa，`./launch.sh` 默认打开实时相机 GUI。使用 `--no-gui` 可关闭窗口。`isos-pkg` 下的 `./build.sh` 构建原生目标；`./build.sh --output 绝对路径空目录` 创建软件包资源。

```sh
./launch.sh --scene pick-place --no-gui
./kill.sh
```

包装层在后台运行，报告套接字路径，并将日志写到 `logs/dev/native/latest.log`。另一个兼容性场景用 `--scene navigation`。dev 模式默认打开独立静态查看器，需要桌面显示环境；启动器仅在确认套接字没有进程占用后清理遗留套接字。配置项、预期结果和故障排查见[首次运行指南](docs_cn/mujoco/usage/dev_cn.md#构建和运行原生模拟器)。

## 查找并选择任务

```sh
./launch.sh --show-config
./launch.sh --list-benchmarks --filter Fridge
./launch.sh --list-kitchens
./launch.sh --benchmark CloseFridge --split target --seed 42 --steps 20
./launch.sh --list-scenes
./launch.sh --scene navigation --no-gui
```

`--list-benchmarks` 从 RoboCasa 注册表列出指定划分的任务；固定版本的默认 `target` 划分有 50 个任务。`--filter` 缩小列表。`CloseFridge` 已通过本地冒烟验证。选择其他任务或以 `--kitchen-scene 1:1` 固定厨房场景时，启动器或默认构建会先询问是否下载约 8 GB 的额外压缩物体资源；默认的带种子场景只需要首个任务资源。`--list-scenes` 列出两个原生兼容性场景。在 `config/benchmarks/robocasa.toml` 保存默认任务、划分、厨房场景、种子和步数，或在 `.env` 中覆盖；`./launch.sh` 使用这些默认值。详见[选择指南](docs_cn/mujoco/benchmarks/Robocasa/README_cn.md#列出并选择任务)。

## 运行 RoboCasa

`./build.sh` 完成后，从仓库根目录运行基准：

```sh
./launch.sh --robocasa --seed 42 --steps 20
```

若仍缺少 RoboCasa，`./launch.sh` 也会在下载固定版本的源码、robosuite 和任务资源前先询问。默认存放在忽略的 `.local/` 下；可在 [config.toml](config.toml) 或 `.env` 设置 `ROBOCASA_ROOT`，使用其他源码目录。脚本安装私有 Python 3.11 环境，并输出包含任务、指令、种子、动作数与成功标志的 JSON。运行器使用有界随机动作，所以 `success: false` 仍是有效的冒烟结果。详见[首次运行指南](docs_cn/mujoco/usage/dev_cn.md#运行首个-robocasa-任务)与[基准方法](docs_cn/mujoco/benchmarks/Robocasa/README_cn.md)。

dev 模式运行 RoboCasa 时显示实时相机画面，并保留最终画面，直至在图像窗口按键。`./launch.sh --benchmark CloseFridge --no-gui` 可仅使用终端。输出保存在 `logs/dev/robocasa/latest.log`，每次运行另有带时间戳的日志。可选 robosuite 模型、IK、mimicgen 提示以及 Gymnasium observation-space 警告来自上游环境，不妨碍本次冒烟运行。

GUI 默认宽 768 像素。可在 `config/benchmarks/robocasa.toml` 设置 `[gui].width`，或在 `.env` 设置 `BENCHMARK_GUI_WIDTH`，或传入 `--gui-width 960`，只放大窗口而不改变基准观测。使用 `--camera robot0_agentview_right` 或 `--camera robot0_eye_in_hand` 切换视角。`--camera-width` 和 `--camera-height` 则修改实际渲染的观测分辨率；详见[相机配置](docs_cn/mujoco/benchmarks/Robocasa/README_cn.md#相机和显示配置)。

## 与 IsOS 和 EOS 一起使用

本地 `island/mujoco-sim@0.1.2` 候选包将 C++ 包装层接入 IsOS 图。构建资源包、验证清单、在 IsOS 中链接或安装，然后 Validate、Apply 并 Run 图。EOS 管理模拟器子进程，向代理公开普通设备能力。精确的包与图命令、就绪检查、日志和停止流程见[受管理后端指南](docs_cn/mujoco/usage/isos-pkg_cn.md)。已发布的 `0.1.1` 版本使用 MuJoCo 3.16.0；此处的源码说明针对 3.3.1。

[文档概览](docs_cn/mujoco/README_cn.md)提供接口、源码职责、基准来源、设计及验证记录。[GitHub 仓库](https://github.com/Island-Team/isos-mujoco-sim)。
