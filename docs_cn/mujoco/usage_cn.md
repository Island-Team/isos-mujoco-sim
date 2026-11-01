# 构建与运行

**集成路径的首次使用：** 先按下文构建并测试模拟器；按 [backend_cn.md](backend_cn.md) 安装或链接精确且已验证的包；在 IsosUI 预览 `sim-hardware` 并选择场景；验证并 Apply 一个图修订；运行 IsOS 并等待 EOS 与模拟器健康；只使用 EOS 声明的控制和观察；随后在 IsOS Logs 先找当前运行的首条就绪或失败事件，再按节点/关联 ID 筛选；最后通过 IsOS 停止部署。本文后面的独立启动器和定时评测是可选开发流程。参见[包契约](interfaces/package_cn.md)、[套接字契约](interfaces/socket_cn.md)、[目标算法](design_cn.md)和[实现 TODO](todo_cn.md)。选择器元数据、共享关联日志和完整停止协调属于目标行为，不是当前保证。

[English](../../docs/mujoco/usage.md) · [v2 后端](backend_cn.md)

MuJoCo 模拟器由此仓库构建，EOS 通过私有套接字连接它；可信评测器使用另一个私有套接字进行重置与评分。安装 MuJoCo 3.16.0 后，将 `.env.example` 复制为忽略的 `.env`，把 `MUJOCO_ROOT` 设为实际安装目录。该目录需要 `include/mujoco/mujoco.h`、`lib/libmujoco.so`、`bin/compile` 和 `bin/simulate`。构建还需要 C++20、CMake、protobuf、gRPC 与 libjpeg。

```sh
. ./.env
: "${MUJOCO_ROOT:?Set MUJOCO_ROOT}"
cmake -S . -B build -DMUJOCO_ROOT="$MUJOCO_ROOT"
cmake --build build -j
ctest --test-dir build --output-on-failure
```

## 独立运行

根目录的 `launch.sh` 将模拟器放到后台，并读取本地 `.env` 与可选的 `launch.conf`。默认运行目录 `.run/mujoco/` 保存仅所有者可访问的套接字、日志和进程记录。`kill.sh` 只停止此启动脚本记录的进程，不停止 EOS 持有的模拟器子进程。

```sh
./launch.sh --scene pick-place --no-gui
./kill.sh
./launch.sh --scene navigation --gui
./kill.sh
```

`--gui` 启动独立的 MuJoCo `simulate` 查看器，显示 XML 的初始场景，不显示运行中模拟器的实时状态或带种子的重置变化。`--no-gui` 是默认值。可用 `--manual-step`、`--run-dir PATH` 和 `--executable PATH` 覆盖默认值；自定义运行目录也要传给 `kill.sh`。启动失败时查看 `.run/mujoco/simulator.log` 或 `viewer.log`。

直接运行需要绝对路径的机器人套接字、评测套接字和场景。测试当前 EOS v2 适配器协议时，另传互不相同的绝对 `--v2-socket` 路径。`--manual-step` 初始暂停；否则模拟器按 2 毫秒物理步长实时推进。评测 `Reset` 也会暂停，以便确定性步进。

```sh
build/eos-mujoco-sim \
  --socket /tmp/eos-simulator.sock \
  --benchmark-socket /tmp/eos-benchmark.sock \
  --v2-socket /tmp/eos-v2.sock \
  --scene "$PWD/assets/scenes/navigation/scene.xml" \
  --manual-step
```

套接字权限为 `0600`。评测时使用私有运行目录，仅向评测器开放 benchmark 套接字。SIGINT 或 SIGTERM 正常停止进程并移除套接字。

## IsOS 与 EOS 部署

当前 IsOS/EOS 路径使用本地 `island/mujoco-sim@0.1.1` 包和共享部署图。已发布的 v1.0.1 包属于旧图形态；其[发布文档](package-release_cn.md)仅供旧安装参考。按照 [后端指南](backend_cn.md)构建包，并设置真实的 `MUJOCO_ROOT`。

```sh
python3 tools/build-backend-bundle.py --output /absolute/path/to/mujoco-v2-bundle
isos init --mode dev
isos pkg link island/mujoco-sim 0.1.1 /absolute/path/to/mujoco-v2-bundle --manifest /absolute/path/to/mujoco-v2-bundle/release.json
isos pkg node-sets
```

用 `isos build eos`、`isos version select eos <selector>`、`isos build isosui` 和 `isos version select isosui <selector>` 构建并显式选择版本。同一 EOS 提交有多个构建时，用源码指纹选择唯一收据。`isos init` 创建配置后退出。在一个终端运行 `isos serve`，于 Graph 工作台预览 `sim-hardware` 节点集，指定场景和仅所有者可访问的套接字，再 Validate 与 Apply。该预设添加 EOS 持有的模拟器进程、三个通用硬件适配器、dispatcher 绑定和有类型连接；已有图会保留至操作员显式应用新修订。

**P02 首次使用目标——尚未实现。** P01 验证精确的 `island/mujoco-sim@0.1.1` 收据后，查看包的场景与设备目录。按稳定 ID 选择 `pick-place` 或 `navigation`，仅在该场景声明支持时选择 `cam-0`、`base-0` 和 `arm-0`；界面的标签与描述解释各选项。针对初始图已有的 dispatcher control 预览七节点 `0.1.0` 预设，再用当前已保存修订 Validate 与 Apply。发布图前，IsOS 检查所选 XML profile 与 SHA-256、整个包收据、设备映射和 MuJoCo 库。P03 会保留缺失或不可用的已保存 ID 以便修复，但禁止 Apply。修改场景生成新的已保存修订，必须 Restart 才能替换 EOS 持有的子进程。当前构建工具仍输出固定设备 ID、`@v1.0` 类型的 `1.0.0` 预设，因此不能把现有预览当作 P02 合格证据。详见 [P02 包契约](interfaces/package_cn.md#p02-描述符扩展目标设计尚未实现)和[负面样本](../../tests/fixtures/scene_catalog/negative-cases.json)。

另一终端运行 `isos run` 启动已应用部署。IsOS 启动前检查精确的软件包、资源、场景、MuJoCo 库、EOS 程序、套接字与端口；EOS 将模拟器作为直接子进程，并在终止前停止已准入执行器。`isos deployment stop` 只停止部署，`isos stop` 停止管理器、API、UI、部署和独立服务。EGIA 只通过 EOS 的正常代理接口行动，不连接私有评测套接字。模型类服务管理器独立于此硬件图。

发生 P02 目录故障时，先查看场景/设备的不可用原因与第一条包或 Apply 失败事件，再修改草稿。已链接资源变化时，按 P01 收据规则显式重新链接。缺少 `MUJOCO_ROOT` 库会阻止启动就绪，场景/profile 不匹配会阻止 Apply。这些失败均保留图与运行中子进程此前的修订。

v2 图中的模拟器节点可以在 `settings.env` 设置 `MUJOCO_GUI=1`，以同一模拟器引擎打开实时 X11 视图；独立启动脚本的 `--gui` 只是静态场景查看器。节点与套接字契约见 [backend_cn.md](backend_cn.md)。

## 定时评测与验证

先启动模拟器和 EOS/EGIA 代理，再由可信评测器连接私有 benchmark 套接字。下例以种子 42 重置，实时运行 30 秒后暂停，并输出一个 JSON 评分对象：

```sh
build/benchmark-eval --benchmark-socket /absolute/path/to/benchmark.sock --task navigation --seed 42 --duration-s 30
```

`--task pick-place` 对应 `assets/scene.xml`，`--task navigation` 对应 `assets/scenes/navigation/scene.xml`。调用者必须使任务与已选场景一致。评测器不读取场景，也不运行代理策略。时长须大于 0 且不超过 3600 秒。详细方法见[英文基准文档](../../docs/mujoco/benchmarks.md)。

场景预览可用 `tools/scene-view.sh --check --scene "$PWD/assets/scenes/navigation/scene.xml"` 验证 XML 加载；`--snapshot` 需要 MuJoCo 的 `bin/render`。运行 `ctest --test-dir build --output-on-failure` 检查引擎、套接字、评测器与场景。预览通过只能证明 XML 可加载，完整行为需由引擎和服务测试验证。
