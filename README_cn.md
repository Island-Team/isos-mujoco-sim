# EOS MuJoCo 基准模拟器

0.x 集成设计从[首次使用](docs_cn/mujoco/usage_cn.md)开始，依次阅读[包契约](docs_cn/mujoco/interfaces/package_cn.md)、[套接字契约](docs_cn/mujoco/interfaces/socket_cn.md)、[算法](docs_cn/mujoco/design_cn.md)与 [TODO](docs_cn/mujoco/todo_cn.md)。目标行为与当前模拟器明确区分。

[English](README.md) · [文档导航](docs_cn/mujoco/doc_index_cn.md)

此独立 C++ 软件包在 MuJoCo 中运行机器人基准场景。EOS 通过模拟器套接字取得普通设备发现、观察与 primitive，并交给 EGIA 等代理。只有可信评测器连接独立的 benchmark 套接字，用于带种子的重置、手动步进、真实状态和评分。场景包括[抓取放置](assets/scene.xml)与[导航](assets/scenes/navigation/scene.xml)。直接运行通过 `--scene` 选场景；IsOS/EOS v2 管理运行通过共享图选场景。

当前 IsOS/EOS 路径构建并链接本地 `island/mujoco-sim@0.1.1` 包，预览 `sim-hardware` 节点集后应用共享图。IsOS 检查软件包与场景，EOS 将模拟器作为直接子进程启动。详见 [v2 后端](docs_cn/mujoco/backend_cn.md)与[使用指南](docs_cn/mujoco/usage_cn.md)。MuJoCo 3.16.0 由操作员通过 `MUJOCO_ROOT` 提供。已发布的 v1.0.1 版本是另一个旧包，见[发布历史](docs_cn/mujoco/package-release_cn.md)。

独立源码构建需要 C++20、CMake 3.22+、MuJoCo 3.16.0、protobuf、gRPC 与 libjpeg。将 `.env.example` 复制为忽略的 `.env` 并设置 `MUJOCO_ROOT`；目录需有 `include/mujoco/mujoco.h`、`lib/libmujoco.so`、`bin/compile` 和 `bin/simulate`。

```sh
. ./.env
cmake -S . -B build -DMUJOCO_ROOT="$MUJOCO_ROOT"
cmake --build build -j
ctest --test-dir build --output-on-failure
```

独立后台运行用 `./launch.sh --scene pick-place --no-gui` 启动，用 `./kill.sh` 停止。`--scene navigation` 选择导航；`--gui` 打开独立的静态场景查看器，不显示运行中模拟器的实时状态。直接运行需为 `--socket`、`--benchmark-socket` 与 `--scene` 提供绝对路径；当前 v2 适配器还需要独立的 `--v2-socket`。详见[使用指南](docs_cn/mujoco/usage_cn.md)。
