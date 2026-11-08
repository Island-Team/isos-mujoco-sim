# 构建与运行

**集成路径的首次使用：** 先按下文构建并测试模拟器；按 [backend_cn.md](isos-pkg_cn.md) 安装或链接精确且已验证的包；通过 IsOS 预览 `sim-hardware` 并选择场景；Validate 并 Apply 一个图修订；运行 IsOS 并等待 EOS 与模拟器的严格健康检查；查看只读相机、底盘、机械臂状态和 IsOS Logs 中当前运行的首条就绪或失败事件；最后通过 IsOS 停止部署。已合并的 R06 所有者通道及限定范围跨所有者回放已执行受治理的底盘/机械臂运动与停止；更完整的 R06 验收仍待完成。本文后面的独立启动器与 RoboCasa 冒烟回合属于本地开发流程。参见[包契约](../interfaces/package_cn.md)、[套接字契约](../interfaces/socket_cn.md)、[设计](../architecture_cn.md#r05-跨所有者验收)和[实现 TODO](../todo_cn.md)。

[English](../../../docs/mujoco/usage/README.md) · [首次运行](dev_cn.md) · [v2 后端](isos-pkg_cn.md)

[Q03 验证设计](../q03-qualification_cn.md) 固定发布前的选定版本安装重放与初始套接字基准。

MuJoCo 模拟器由此仓库构建，EOS 通过私有套接字连接它。`SIM_PROFILE=dev` 时，`./build.sh` 构建原生目标并检查 RoboCasa；缺少源码、运行环境或资源时在下载前询问。仓库默认的 `isos-pkg` 仅构建原生目标。`./build.sh --output <空的绝对路径目录>` 只构建 IsOS 软件包资源。可信评测器使用另一个私有套接字进行重置与评分。安装 MuJoCo 3.3.1 后，将 `.env.example` 复制为忽略的 `.env`，把 `MUJOCO_ROOT` 设为实际安装目录。该目录需要 `include/mujoco/mujoco.h`、`lib/libmujoco.so`、`bin/compile` 和 `bin/simulate`。构建还需要 C++20、CMake、protobuf、gRPC 与 libjpeg。

`src/mujoco/` 拥有原生仿真引擎及直接开发入口，`src/isos/` 拥有软件包进程和 EOS 套接字适配器。构建后运行 `build/mujoco-core --scene "$PWD/assets/scene.xml" --seed 42 --steps 20`，无需启动套接字即可加载场景、重置并推进物理步。使用 `build/eos-mujoco-sim` 或下面的独立启动脚本验证包装层。

```sh
cp .env.example .env
# 编辑 .env：将 MUJOCO_ROOT 设为 MuJoCo 3.3.1 安装目录的绝对路径。
./build.sh
ctest --test-dir build --output-on-failure
```

## 独立运行

使用 `--scene` 时，根目录的 `launch.sh` 将历史 C++ 模拟器放到后台，先读取根目录的 [config.toml](../../../config.toml)，再读取可选的本地 `.env`；后者覆盖同名默认值。支持 `MUJOCO_ROOT`、`SIM_EXECUTABLE`、`SIM_SCENE`、`SIM_RUN_DIR`、`SIM_GUI` 和 `SIM_MANUAL_STEP`，后两项为布尔值。默认运行目录 `.run/mujoco/` 保存仅所有者可访问的套接字、日志和进程记录。`kill.sh` 只停止此启动脚本记录的进程，不停止 EOS 持有的模拟器子进程。

```sh
./launch.sh --scene pick-place --no-gui
./kill.sh
./launch.sh --scene navigation --gui
./kill.sh
```

`--gui` 启动独立的 MuJoCo `simulate` 查看器，显示 XML 的初始场景，不显示运行中模拟器的实时状态或带种子的重置变化。dev 模式默认开启 GUI，`--no-gui` 可关闭；isos-pkg 模式默认无界面。可用 `--manual-step`、`--run-dir PATH` 和 `--executable PATH` 覆盖默认值；自定义运行目录也要传给 `kill.sh`。启动失败时查看 `logs/dev/native/latest.log` 或对应的 `*-viewer.log`。

直接运行需要绝对路径的机器人套接字、评测套接字和场景。测试当前 EOS v2 适配器协议时，另传互不相同的绝对 `--v2-socket` 路径。`--manual-step` 初始暂停；否则模拟器按 2 毫秒物理步长实时推进。评测 `Reset` 也会暂停，以便确定性步进。

不带 `--managed-strict-socket` 的直接启动保留旧套接字 `2.0.0` 模式：现有帧客户端可以省略或重用 `node`、`command_id`，历史 gRPC 执行器监听器仍可用。它供旧集成使用，不能使受管理的 IsOS 图合格。严格标志由 EOS 根据已验证生成配置选择，不是图设置或独立启动脚本的默认值。EOS 现已带该标志启动已验证子进程，并对每个已声明设备核对严格健康检查；限定范围的 R05 回放记录在[设计](../architecture_cn.md#r05-跨所有者验收)。详见[套接字契约](../interfaces/socket_cn.md)。

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

当前 IsOS/EOS 路径使用本地 `island/mujoco-sim@0.1.2` 包和共享部署图。已发布的 v1.0.1 包属于旧图形态；其[发布文档](../package-release_cn.md)仅供旧安装参考。按照 [后端指南](isos-pkg_cn.md)构建包，并设置真实的 `MUJOCO_ROOT`。

```sh
source .env
python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output /absolute/path/to/mujoco-v2-bundle
isos init --mode dev
isos pkg link island/mujoco-sim 0.1.2 /absolute/path/to/mujoco-v2-bundle --manifest /absolute/path/to/mujoco-v2-bundle/release.json
isos pkg node-sets
```

用 `isos build eos`、`isos version select eos <selector>`、`isos build isosui` 和 `isos version select isosui <selector>` 构建并显式选择版本。同一 EOS 提交有多个构建时，用源码指纹选择唯一收据。`isos init` 创建配置后退出。在一个终端运行 `isos serve`，用 `isos pkg preview-set` 或 IsOS API 预览 `sim-hardware` 节点集，指定场景和仅所有者可访问的套接字，再通过按修订检查的 IsOS 接口 Validate 与 Apply。IsosUI 目录编辑器属于后续 U01 工作台门禁。该预设添加 EOS 持有的模拟器进程、三个通用硬件适配器、dispatcher 绑定和有类型连接；已有图会保留至操作员显式应用新修订。

**P02 包目录与 IsOS 选择。** 构建工具现已输出 `0.1.0` 目录描述符和七节点 `@v0.1` 预设，参数为稳定的 `scene`、`camera_device`、`base_device` 和 `manipulator_device`。用 `python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output <空目录>` 构建并检查包；`backend-v2.json` 含两个场景 ID、标签、profile 和 SHA-256，以及三台设备的描述和场景支持列表。P01 验证精确的 `island/mujoco-sim@0.1.2` 收据后，IsOS P02/P03 切片现已展示可用 ID、依当前已保存修订 Validate 与 Apply 所选场景和设备，并保留不可用的已保存 ID 供修复。修改场景生成新的已保存修订，必须 Restart 才能替换 EOS 持有的子进程。详见 [P02 包契约](../interfaces/package_cn.md#p02-描述符扩展)和[负面样本](../../../tests/fixtures/scene_catalog/negative-cases.json)。

另一终端运行 `isos run` 启动已应用部署。IsOS 启动前检查精确的软件包、资源、场景、MuJoCo 库、EOS 程序、套接字与端口；EOS 将模拟器作为直接子进程。限定范围的 R06 回放已证明 pick-place 和 navigation 的物理停止顺序；更完整的故障验收仍待完成。`isos deployment stop` 只停止部署，`isos stop` 停止管理器、API、UI、部署和独立服务。EGIA 只通过 EOS 的正常代理接口行动，不连接私有评测套接字。模型类服务管理器独立于此硬件图。

**R05 管理模式就绪，限定范围验收通过：** Apply 后，EOS 以严格模式启动已验证子进程，对图中每台相机、底盘和机械臂设备探测 `health`，要求 `version:"2.0.0"`、回显请求 ID、`ok:true`、`accepted:true` 以及包含 `strict-socket-v1` 的 `features`。套接字文件或进程启动日志只表示进度，不表示就绪。特性缺失、设备错误、相机渲染失败或子进程退出都使后端不可用；先看当前运行的首条失败事件。固定版本跨所有者回放已验证 pick-place 和 navigation 两个场景的这一路径以及只读拍摄和观察。当时的 R05 EOS 目录只公开 `safety.estop`，未公开 `base.velocity` 与 `arm.movej`；下文 R06 回放随后执行了受治理的运动与停止。R05 回放本身没有下发受管理运动。详见[验收证据](../architecture_cn.md#r05-跨所有者验收)。

直接验证模拟器所有者切片：在私有目录运行 `build/eos-mujoco-sim --managed-strict-socket --v2-socket /absolute/private/run/strict.sock --scene "$PWD/assets/scene.xml"`，再发送 `node:"base-0"` 的分帧 `health` 请求。响应必须回显 ID，并包含 `ok:true`、`accepted:true` 与 `strict-socket-v1`。受管理启动拒绝 `--socket` 和 `--benchmark-socket`；不带标志的直接启动继续支持两者。运行 `ctest --test-dir build -R 'strict-socket|strict-capacity|v2-socket' --output-on-failure` 可回放所有者检查，包括完整保留容量。

发生 P02 目录故障时，先查看场景/设备的不可用原因与第一条包或 Apply 失败事件，再修改草稿。已链接资源变化时，按 P01 收据规则显式重新链接。缺少 `MUJOCO_ROOT` 库会阻止启动就绪，场景/profile 不匹配会阻止 Apply。这些失败均保留图与运行中子进程此前的修订。

检查结果和当前运行日志后，通过 `isos deployment stop` 停止。R05 增加严格身份和传输重发保护；已合并的 R06 伴随通道及限定范围回放证明两个场景在模拟器终止并回收前分别确认底盘/机械臂。仅凭 `accepted:true` 响应始终不能证明安全停止已确认；须核对 EOS 选定的终态回执与 IsOS 的最终结果。

**R06 限定范围首次使用行为：** 经审查的 `strict-stop-v1` 所有者实现已在 [PR #21](https://github.com/Island-Team/isos-mujoco-sim/pull/21) 合并；真实 pick-place/navigation 的 IsOS → EOS → MuJoCo 回放执行了受治理的运动与停止。使用精确且已验证的所有者构建，重复 Validate/Apply/Run。受管理子进程在主套接字路径追加 `.stop`，得到仅所有者可访问的伴随套接字；图不增加字段。EOS 目录公开 `base.velocity` 或 `arm.movej` 前，检查每个执行器的 `health` 同时具有 `strict-socket-v1` 与 `strict-stop-v1`，且 EOS 已探测伴随停止套接字。EOS 在第一次有界受管理运动中传入两个健康路径匹配的 32 字符 `generation_id` 和 `stop_epoch:"0"`，之后传入当前已证明的 epoch；旧令牌的**新**命令返回 `stop_fenced`，相同旧命令 ID 仍返回 R05 已存储结果。通过 EOS 下发运动，在运动或拍摄进行时通过 EOS/IsOS 停止；EOS 将带代际 ID 的受管停止送到伴随套接字。上代延迟请求返回 `stale_generation`。严格 `stop` 响应须回显请求 ID，包含 `base_stop:"stopped"`、`arm_stop:"stopped"`、匹配的 `generation_id`、非空十进制字符串 `stop_epoch`、`ok:true` 及 `accepted:true`；EOS 须在终止和回收直接子进程前校验该证明，清理后才发布选定的终态回执。[套接字契约](../interfaces/socket_cn.md#r06-受管理停止契约)定义这些值：状态字符串是无量纲证明状态，`stop_epoch` 是子进程内次序计数，也是运动请求的前提。缺失或未知状态、超时、子进程崩溃、`stop_outcome_unknown` 均表示安全停止未确认；检查首条关联故障事件与 EOS 日志，再核对有界的子进程及两个套接字路径清理。不能仅从进程退出或 `accepted` 推断物理停止。限定范围回放确认了两部分停止、匹配的代际与 epoch `1`，且没有残留子进程、进程组或套接字；停止套接字丢失与子进程崩溃仍判为未知。详见 [R06 证据](../architecture_cn.md#r06-所有者合并与限定范围跨所有者回放)。强制超时/KILL、GUI 不可用、过期或错误管道及崩溃恢复仍需更完整的 R06 验收，才能宣称 M3 控制全部完成。

v2 图中的模拟器节点可以在 `settings.env` 设置 `MUJOCO_GUI=1`，以同一模拟器引擎打开实时 X11 视图；独立启动脚本的 `--gui` 只是静态场景查看器。节点与套接字契约见 [backend_cn.md](isos-pkg_cn.md)。

## RoboCasa 基准与验证

默认运行 `./launch.sh` 启动已配置的上游 RoboCasa 冒烟回合。用 `./launch.sh --list-benchmarks --filter Fridge` 列任务，用 `./launch.sh --list-kitchens` 列厨房场景；`./launch.sh --benchmark CloseFridge --seed 42 --steps 20` 选择任务。可在 `config/benchmarks/robocasa.toml` 设置任务和相机默认值（根目录 `BENCHMARK_CONFIG` 指向该文件），或用 `.env` 中的 `BENCHMARK_*` 变量覆盖，再用 `./launch.sh --show-config` 检查。`ROBOCASA_ROOT` 指定其他源码目录；空值使用忽略的 `.local/robocasa`。缺少源码、私有 Python 环境或资源时，脚本先询问再下载；其他任务或固定厨房场景需要更大的资源集。详见[基准说明](../benchmarks/Robocasa/README_cn.md)。

场景预览可用 `tools/view.sh --check --scene "$PWD/assets/scenes/navigation/scene.xml"` 验证历史兼容场景的 XML 加载；`--snapshot` 需要 MuJoCo 的 `bin/render`。运行 `ctest --test-dir build --output-on-failure` 检查 C++ 引擎与套接字兼容性。
