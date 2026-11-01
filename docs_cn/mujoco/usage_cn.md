# 构建与运行

**集成路径的首次使用：** 先按下文构建并测试模拟器；按 [backend_cn.md](backend_cn.md) 安装或链接精确且已验证的包；通过 IsOS 预览 `sim-hardware` 并选择场景；Validate 并 Apply 一个图修订；运行 IsOS 并等待 EOS 与模拟器的严格健康检查；查看只读相机、底盘、机械臂状态和 IsOS Logs 中当前运行的首条就绪或失败事件；最后通过 IsOS 停止部署。受管理的底盘及机械臂运动须等待 R06 证明物理停止后才可用。本文后面的独立启动器和定时评测是另一开发流程。参见[包契约](interfaces/package_cn.md)、[套接字契约](interfaces/socket_cn.md)、[设计](design_cn.md#r05-跨所有者验收)和[实现 TODO](todo_cn.md)。

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

不带 `--managed-strict-socket` 的直接启动保留旧套接字 `2.0.0` 模式：现有帧客户端可以省略或重用 `node`、`command_id`，历史 gRPC 执行器监听器仍可用。它供旧集成使用，不能使受管理的 IsOS 图合格。严格标志由 EOS 根据已验证生成配置选择，不是图设置或独立启动脚本的默认值。EOS 现已带该标志启动已验证子进程，并对每个已声明设备核对严格健康检查；限定范围的 R05 回放记录在[设计](design_cn.md#r05-跨所有者验收)。详见[套接字契约](interfaces/socket_cn.md)。

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

用 `isos build eos`、`isos version select eos <selector>`、`isos build isosui` 和 `isos version select isosui <selector>` 构建并显式选择版本。同一 EOS 提交有多个构建时，用源码指纹选择唯一收据。`isos init` 创建配置后退出。在一个终端运行 `isos serve`，用 `isos pkg preview-set` 或 IsOS API 预览 `sim-hardware` 节点集，指定场景和仅所有者可访问的套接字，再通过按修订检查的 IsOS 接口 Validate 与 Apply。IsosUI 目录编辑器属于后续 U01 工作台门禁。该预设添加 EOS 持有的模拟器进程、三个通用硬件适配器、dispatcher 绑定和有类型连接；已有图会保留至操作员显式应用新修订。

**P02 包目录与 IsOS 选择。** 构建工具现已输出 `0.1.0` 目录描述符和七节点 `@v0.1` 预设，参数为稳定的 `scene`、`camera_device`、`base_device` 和 `manipulator_device`。用 `python3 tools/build-backend-bundle.py --build-dir build-p02 --output <空目录>` 构建并检查包；`backend-v2.json` 含两个场景 ID、标签、profile 和 SHA-256，以及三台设备的描述和场景支持列表。P01 验证精确的 `island/mujoco-sim@0.1.1` 收据后，IsOS P02/P03 切片现已展示可用 ID、依当前已保存修订 Validate 与 Apply 所选场景和设备，并保留不可用的已保存 ID 供修复。修改场景生成新的已保存修订，必须 Restart 才能替换 EOS 持有的子进程。详见 [P02 包契约](interfaces/package_cn.md#p02-描述符扩展)和[负面样本](../../tests/fixtures/scene_catalog/negative-cases.json)。

另一终端运行 `isos run` 启动已应用部署。IsOS 启动前检查精确的软件包、资源、场景、MuJoCo 库、EOS 程序、套接字与端口；EOS 将模拟器作为直接子进程。R06 须证明物理停止顺序，才能启用受管理运动。`isos deployment stop` 只停止部署，`isos stop` 停止管理器、API、UI、部署和独立服务。EGIA 只通过 EOS 的正常代理接口行动，不连接私有评测套接字。模型类服务管理器独立于此硬件图。

**R05 管理模式就绪，限定范围验收通过：** Apply 后，EOS 以严格模式启动已验证子进程，对图中每台相机、底盘和机械臂设备探测 `health`，要求 `version:"2.0.0"`、回显请求 ID、`ok:true`、`accepted:true` 以及包含 `strict-socket-v1` 的 `features`。套接字文件或进程启动日志只表示进度，不表示就绪。特性缺失、设备错误、相机渲染失败或子进程退出都使后端不可用；先看当前运行的首条失败事件。固定版本跨所有者回放已验证 pick-place 和 navigation 两个场景的这一路径以及只读拍摄和观察。MuJoCo 在实时 EOS 目录中只公开 `safety.estop`；在 R06 实现物理终端停止屏障前，`base.velocity` 与 `arm.movej` 不可用。本次 R05 首次使用回放不应尝试受管理运动。详见[验收证据](design_cn.md#r05-跨所有者验收)。

直接验证模拟器所有者切片：在私有目录运行 `build/eos-mujoco-sim --managed-strict-socket --v2-socket /absolute/private/run/strict.sock --scene "$PWD/assets/scene.xml"`，再发送 `node:"base-0"` 的分帧 `health` 请求。响应必须回显 ID，并包含 `ok:true`、`accepted:true` 与 `strict-socket-v1`。受管理启动拒绝 `--socket` 和 `--benchmark-socket`；不带标志的直接启动继续支持两者。运行 `ctest --test-dir build -R 'strict-socket|strict-capacity|v2-socket' --output-on-failure` 可回放所有者检查，包括完整保留容量。

发生 P02 目录故障时，先查看场景/设备的不可用原因与第一条包或 Apply 失败事件，再修改草稿。已链接资源变化时，按 P01 收据规则显式重新链接。缺少 `MUJOCO_ROOT` 库会阻止启动就绪，场景/profile 不匹配会阻止 Apply。这些失败均保留图与运行中子进程此前的修订。

检查结果和当前运行日志后，通过 `isos deployment stop` 停止。R05 增加严格身份和传输重发保护；R06 仍需证明专用停止通道、底盘/机械臂分别确认，以及在终止和回收模拟器前完成物理停止。R06 通过前，仅凭 `accepted:true` 停止响应不能证明安全停止已确认。

**R06 首次使用目标，尚待实现：** 新包带有 `strict-stop-v1` 且通过所有者与跨所有者验收后，重复 Validate/Apply/Run。EOS 目录公开 `base.velocity` 或 `arm.movej` 前，检查每个执行器的 `health` 同时具有 `strict-socket-v1` 与 `strict-stop-v1`。EOS 在第一次有界受管理运动中传入 `stop_epoch:"0"`，之后传入当前已证明的 epoch；旧或缺失令牌返回 `stop_fenced`。通过 EOS 下发运动，在运动或拍摄进行时通过 EOS/IsOS 停止。严格 `stop` 响应须回显请求 ID，包含 `base_stop:"stopped"`、`arm_stop:"stopped"`、非空十进制字符串 `stop_epoch`、`ok:true` 及 `accepted:true`；EOS 须在终止和回收直接子进程前记录对应终态。[套接字契约](interfaces/socket_cn.md#r06-受管理停止契约设计目标)定义这些值：状态字符串是无量纲证明状态，`stop_epoch` 是子进程内次序计数，也是运动请求的前提。缺失或未知状态、超时、子进程崩溃、`stop_outcome_unknown` 均表示安全停止未确认；检查首条关联故障事件与 EOS 日志，再核对有界的子进程／套接字清理。不能仅从进程退出或 `accepted` 推断物理停止。本段是待验收的回放目标，当前 R05 程序尚未允许受管理运动。

v2 图中的模拟器节点可以在 `settings.env` 设置 `MUJOCO_GUI=1`，以同一模拟器引擎打开实时 X11 视图；独立启动脚本的 `--gui` 只是静态场景查看器。节点与套接字契约见 [backend_cn.md](backend_cn.md)。

## 定时评测与验证

这是 EOS 管理严格部署之外的独立直接启动旧版评测流程。先启动带私有 benchmark 套接字的模拟器，连接目标评测器或旧代理测试工具。R05 受管理子进程不提供 benchmark 监听器，因为 Reset 与 Step 能绕过 Dispatcher 更改引擎状态。下例以种子 42 重置，实时运行 30 秒后暂停，并输出一个 JSON 评分对象：

```sh
build/benchmark-eval --benchmark-socket /absolute/path/to/benchmark.sock --task navigation --seed 42 --duration-s 30
```

`--task pick-place` 对应 `assets/scene.xml`，`--task navigation` 对应 `assets/scenes/navigation/scene.xml`。调用者必须使任务与已选场景一致。评测器不读取场景，也不运行代理策略。时长须大于 0 且不超过 3600 秒。详细方法见[英文基准文档](../../docs/mujoco/benchmarks.md)。

场景预览可用 `tools/scene-view.sh --check --scene "$PWD/assets/scenes/navigation/scene.xml"` 验证 XML 加载；`--snapshot` 需要 MuJoCo 的 `bin/render`。运行 `ctest --test-dir build --output-on-failure` 检查引擎、套接字、评测器与场景。预览通过只能证明 XML 可加载，完整行为需由引擎和服务测试验证。
