# IsOS 管理的 MuJoCo 后端


## v0.2.x 外部适配器候选（当前源码）

当前源码默认构建 `island/mujoco-sim@0.2.0`。`./build.sh --output <绝对路径空目录> --version 0.2.x` 选择尚未发布的补丁候选；每次已发布版本的修复使用新的补丁号。发布清单使用 `isos.package@v1`、schema `0.2.0`，通过 `lib/libmujoco-eos-node.so` 贡献 `mujoco-v2` 适配器系列。清单在 `adapters` 和 `node_contributions.libraries` 中记录同一 SHA-256；归档固定相同字节。输出目录保留清单中的资产文件名，例如 `mujoco-sim-v0.2.0-linux-x86_64.tar.gz`。归档按路径排序，文件所有者与时间戳归零，gzip 时间戳为零；固定载荷字节的重复归档摘要应一致。`python3 tests/archive.py` 验证此边界。`bin/eos-mujoco-sim` 仍是经过验证、受监督的子进程。动态库导出 `isos_node_v1` 的 create/start/input/health/stop/destroy，读取已准入节点的 `adapter.settings`，探测 `strict-socket-v1`，并将相机、底盘和机械臂观测转换成通用 `@v0.2` 载荷。它只接受 `{"op":"observe"}` 输入，拒绝直接运动命令。当前 `sim-hardware` 节点集只含模拟器进程与 JPEG 相机（观测 JSON 上限 12 MiB），能力标记为 `jpeg`；底盘和机械臂仍在资源目录中，但在执行器 Stop 证明完成前不纳入托管图。发布命令节点集前，EOS 必须负责 Dispatcher 准入和物理停止证明。

运行 `isos pkg check --source` 前，导出 `MUJOCO_ROOT` 指向本地 3.3.1 安装；显式环境值优先于 `config.toml` 和 `.env`。`python3 tests/build_env.py` 在不下载内容的情况下验证此构建输入边界。清单将 IsOS 兼容范围限定为 `[0.2.3,0.3.0)`，并要求 IsOS `package-process-v1` 与 EOS `native-plugin-v1`；发布检查仍记录实际验证的 IsOS 构建。`.so` 是 Linux C++/protobuf 二进制文件，需要 IsOS 主机的 ABI 表和匹配的运行库。仅构建文件不足以证明兼容：IsOS 检查清单和摘要，EOS 检查 ABI 与回调，托管资格检查模拟器子进程、数据 schema、就绪和 Stop。其他平台及进程内 Python 是未来工作；Python 可使用受监督进程接口。`python3 tests/plugin.py <已构建动态库>` 使用桩验证严格健康、观测、运动拒绝和 Stop。下面旧的 `0.1.2` 记录属于历史候选证据，不是当前源码的操作说明。

在 2026-11-11 的 Linux x86_64 验证主机上，使用实际 MuJoCo 3.3.1 构建后，29 项 CTest 全部通过，包括原生适配器、包目录、严格套接字、相机故障、Stop 和场景查看检查。构建和包进程主机输入均设置 `MUJOCO_ROOT=<MuJoCo 3.3.1 绝对根目录>`。启动 IsOS 时还须设置 `LD_LIBRARY_PATH="$MUJOCO_ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"`，使 EOS 管理的模拟器子进程能加载 `libmujoco.so.3.3.1`；包归档不包含该库。已检查的 `0.2.0` 源码候选通过 `isos pkg check --source ... --version 0.2.0 --graph ...`，覆盖托管 Run、相机观测、日志和 Stop。本地完整构建与 CTest 输出位于被 Git 忽略的 `data/test/20261111-real-mujoco/`；IsOS 资格检查的证据由其检查输出保存。这是源码资格验证记录，不表示 GitHub 发布已完成。

## 历史 0.1.2 候选说明

下述 `0.1.2` 软件包是使用 MuJoCo 3.3.1 的本地开发候选，尚未发布；本页后面的历史 `0.1.1` 证据仍对应 MuJoCo 3.16.0。

**当前实现：** 本页记录现有包与集成路径。[包描述符与声明](../interfaces/package_cn.md)和[模拟器套接字](../interfaces/socket_cn.md)是本包拥有的字段契约；[架构](../architecture_cn.md)说明集成方式，[后续验证](../architecture_cn.md#后续验证)记录尚未完成的检查。协议或已生成描述符文件名中的 `v2` 为兼容而保留；本主题页文件名不带版本后缀。

[English](../../../docs/mujoco/usage/isos-pkg.md)

从本地源码全新安装时，先设置 `MUJOCO_ROOT`，再运行 `isos pkg install --source /absolute/path/to/isos-mujoco-sim --allow-source-build`。IsOS 调用本仓库可执行的 `build.sh --output <空暂存目录>`，验证 `release.json` 和清单指定名称的归档后安装包。包声明进程入口及通用场景和设备目录，IsOS 无需 MuJoCo 专用启动路径。随后验证并应用节点集，再明确运行或重启部署；仅安装包不会改变当前运行实例。

先构建模拟器，再生成本地 `island/mujoco-sim@0.1.2` 包：

```sh
export MUJOCO_ROOT=/absolute/path/to/mujoco-3.3.1
mkdir -p "$HOME/tmp"
export TMPDIR="$HOME/tmp"
cmake -S . -B build -DMUJOCO_ROOT="$MUJOCO_ROOT"
cmake --build build -j
ctest --test-dir build --output-on-failure
python3 tests/nodes.py
python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output /absolute/path/to/mujoco-v2-bundle
isos pkg link island/mujoco-sim 0.1.2 /absolute/path/to/mujoco-v2-bundle --manifest /absolute/path/to/mujoco-v2-bundle/release.json
```

构建目录与临时目录应放在空间充足的文件系统上，例如设置 `TMPDIR=/home/you/tmp` 和 `--build-dir /home/you/build-mujoco`。构建工具通过 CMake 安装程序，检查安装后的 ELF 依赖，并将原生 Ubuntu、glibc 和已解析库要求写入 `release.json`。在 Ubuntu 24.04 上，资源声明 `glibc>=2.39`、`tested_ubuntu:["24.04"]`，归档中没有构建主机的 RUNPATH。若构建工具未继承环境变量，用 `--mujoco-root "$MUJOCO_ROOT"` 显式指定根目录。链接或发布前检查 `readelf -d bin/eos-mujoco-sim` 以及清单中的资源要求。

包中包含 `bin/eos-mujoco-sim`、两个场景及其资源、`backend-v2.json` 和本地 schema v4 `release.json`。构建工具还会在包目录旁生成带 SHA-256 校验值的发布归档。后端描述文件声明 `mujoco-v2` 协议、`cam-0`、`base-0`、`arm-0` 设备 ID，以及外部 MuJoCo 3.3.1 库依赖。IsOS 在运行前验证可执行文件、场景、资源和库；安装包本身不会启用部署图。

发布清单中的 `node_contributions` 声明 `sim-hardware` 节点集、`mujoco-v2` 适配器系列，以及包拥有的 `eos.process.mujoco.simulator@v0.2` 进程类型。`0.2.1` 节点集添加该进程及 EOS 通用相机、底盘、机械臂 `device@v0.2` 实例。每个硬件节点在 `node.adapter.package` 中固定 `island/mujoco-sim@0.1.2`，并选择稳定的设备 ID。此首版节点集仅供观测：不声明 Dispatcher 命令绑定或相机门。IsOS 先验证发布包，再于预览和 Apply 验证组合图；EOS 就绪和 Stop 仍需另行测试所有者运行时。详见[包贡献契约](../interfaces/package_cn.md#p02-声明与图边界)。

后端节点的 `settings.env` 可设置 `MUJOCO_GUI=1` 或 `MUJOCO_GUI=true`，在支持 X11 的主机上打开 `IsOS MuJoCo — live simulation` 窗口。窗口渲染来自同一个 `SimEngine` 的相机画面；默认不显示 GUI。若请求 GUI 但显示服务不可用，模拟器启动失败。`tools/view.sh` 仍用于独立的静态场景预览。

v2 Unix 套接字帧以八字节小端长度头开头，后接 JSON 元数据和可选 JPEG 负载。元数据上限为 64 KiB，负载上限为 8 MiB。请求包含 `version: "2.0.0"`、字符串 `id`、`node` 和 `op`；响应回显 ID 与版本，并返回 `ok` 或 `error.message`。

**R05 限定范围验收：** EOS 管理的严格子进程只接受帧格式 v2 套接字，拒绝历史 gRPC 机器人套接字与 benchmark 套接字。独立直接启动仍为旧客户端与可信评测保留这些套接字。固定版本的 IsOS → EOS → MuJoCo 回放验证了两个场景中相机、底盘和机械臂的严格健康检查、只读图像及状态、子进程和套接字清理。R06 所有者停止屏障已合并，限定范围跨所有者运动与停止回放通过；更完整的 R06 故障验收仍待完成。详见[所有者套接字契约](../interfaces/socket_cn.md)和 [R05 证据](../architecture_cn.md#r05-跨所有者验收)。

| 操作 | 请求字段 | 响应字段 |
| --- | --- | --- |
| `health` | 通用字段 | `accepted: bool` |
| `camera_capture` | 通用字段 | `format: "jpeg"`、`rgb_length: u32` 字节、`depth_available: false`、`width_px: u32`、`height_px: u32` 和 JPEG 负载 |
| `base_observe` | 通用字段 | `position_m: [f64; 2]`、`linear_velocity_m_s: [f64; 2]`、`yaw_rad: f64`、`angular_velocity_rad_s: f64` |
| `base_move` | `linear_x_m_s`、`linear_y_m_s`、`angular_z_rad_s: f64`，`valid_for_ms`，`command_id: string` | `accepted: bool`；租期结束后底盘停止 |
| `manipulator_observe` | 通用字段 | 六个关节位置、速度，以及末端位置和四元数 |
| `manipulator_move` | 六个关节目标和 `command_id: string` | `accepted: bool` |
| `stop` | `command_id: string` | `accepted: bool`；停止底盘和机械臂 |

`timestamp_ns` 是以纳秒为单位的模拟时间，`sequence` 是引擎步数。浮点数必须有限，运动边界由引擎强制执行。套接字权限为 `0600`，正常停止时会被移除。IsOS 验证包并把可执行文件及场景传给 EOS；EOS 将模拟器作为直接子进程启动，并使用硬件适配器连接套接字。限定范围的 R06 回放已证明两个场景在终止和回收前完成物理停止；R05 清理结果本身不能证明这一点。

## 验证

2026-10-30 的现有基线在 Ubuntu 和 MuJoCo 3.3.1 上通过了十个 CTest 用例。`tests/v2.py` 覆盖 JPEG 捕获、底盘运动、六关节命令、安全停止和套接字清理。GUI 检查还验证了可见窗口、运动后像素变化，以及显示服务不可用时的启动失败。完整日志保存在本地 `logs/test/2026-10-30-v2-live/`。新增节点声明可用 `python3 tests/nodes.py` 检查，并需通过 IsOS 与 EOS 的完整图准入及运行集成测试。

2026-10-30，旧版六节点预设及端口元数据通过 `python3 tests/nodes.py` 的四个测试。`python3 tools/bundle.py --build-dir build --output logs/test/20261030-general-interfaces/bundle-r3` 成功生成当时的发布候选包，`ctest --test-dir build --output-on-failure` 的十个模拟器测试全部通过。完整本地输出保存在 `logs/test/20261030-general-interfaces/`。当时的八节点预设也用相同的 Python 命令检查；2026-10-31 的模拟器基线十个测试通过，日志在 `logs/test/20261031-generic-device-preset/`。

随后，独立的 IsOS 目录链接旧版 `bundle-r3`，使用场景和套接字参数预览 `sim-hardware`，并通过 EOS `aether-profile` 验证生成的图。该预览添加六个节点，只在当时四个 MuJoCo 类型上保留包引用，并报告三个由 IsOS 管理的进程。复现细节见 `logs/test/20261030-general-interfaces/graph-preview.log`。这属于历史回放证据；当前两节点 `0.2.1` 相机节点集仍需新的跨所有者回放。

## 软件包 0.1.2 检查（2026-10-31）

`python3 tests/nodes.py`、`python3 tests/release.py` 和 `ctest --test-dir build --output-on-failure` 通过（10 项模拟器测试）。`python3 tools/bundle.py --build-dir build --output logs/test/20261031-version-alignment/bundle` 暂存的软件包在发行清单与描述文件中均报告 `0.1.2`。描述文件 schema 和套接字协议保持 `2.0.0`。输出位于忽略 Git 的 `logs/test/20261031-version-alignment/`。

## IsOS 与 EOS 部署

当前 IsOS/EOS 路径使用本地 `island/mujoco-sim@0.1.2` 包和共享部署图。已发布的 v1.0.1 包属于旧图形态；其[发布文档](isos-pkg_cn.md#软件包发布记录)仅供旧安装参考。按照 [后端指南](isos-pkg_cn.md)构建包，并设置真实的 `MUJOCO_ROOT`。

```sh
source .env
python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output /absolute/path/to/mujoco-v2-bundle
isos init --mode dev
isos pkg link island/mujoco-sim 0.1.2 /absolute/path/to/mujoco-v2-bundle --manifest /absolute/path/to/mujoco-v2-bundle/release.json
isos pkg node-sets
```

用 `isos build eos`、`isos version select eos <selector>`、`isos build isosui` 和 `isos version select isosui <selector>` 构建并显式选择版本。同一 EOS 提交有多个构建时，用源码指纹选择唯一收据。`isos init` 创建配置后退出。在一个终端运行 `isos serve`，用 `isos pkg preview-set` 或 IsOS API 预览 `sim-hardware` 节点集，指定场景和仅所有者可访问的套接字，再通过按修订检查的 IsOS 接口 Validate 与 Apply。IsosUI 目录编辑器属于后续 U01 工作台门禁。该节点集声明 EOS 持有的模拟器进程和三个通用硬件适配器；本候选包没有 Dispatcher 命令绑定。已有图会保留至操作员显式应用新修订。

**P02 包目录与 IsOS 选择。** 构建工具现已输出 `0.1.0` 目录描述符和四节点 `0.2.1` 节点集，参数为稳定的 `scene`、`camera_device`、`base_device` 和 `manipulator_device`。用 `python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output <空目录>` 构建并检查包；`backend-v2.json` 含两个场景 ID、标签、profile 和 SHA-256，以及三台设备的描述和场景支持列表。P01 验证精确的 `island/mujoco-sim@0.1.2` 收据后，IsOS P02/P03 切片现已展示可用 ID、依当前已保存修订 Validate 与 Apply 所选场景和设备，并保留不可用的已保存 ID 供修复。修改场景生成新的已保存修订，必须 Restart 才能替换 EOS 持有的子进程。详见 [P02 包契约](../interfaces/package_cn.md#p02-描述符扩展)和[负面样本](../../../tests/fixtures/scene_catalog/negative-cases.json)。

另一终端运行 `isos run` 启动已应用部署。IsOS 启动前检查精确的软件包、资源、场景、MuJoCo 库、EOS 程序、套接字与端口；EOS 将模拟器作为直接子进程。限定范围的 R06 回放已证明 pick-place 和 navigation 的物理停止顺序；更完整的故障验收仍待完成。`isos deployment stop` 只停止部署，`isos stop` 停止管理器、API、UI、部署和独立服务。EGIA 只通过 EOS 的正常代理接口行动，不连接私有评测套接字。模型类服务管理器独立于此硬件图。

**R05 管理模式就绪，限定范围验收通过：** Apply 后，EOS 以严格模式启动已验证子进程，对图中每台相机、底盘和机械臂设备探测 `health`，要求 `version:"2.0.0"`、回显请求 ID、`ok:true`、`accepted:true` 以及包含 `strict-socket-v1` 的 `features`。套接字文件或进程启动日志只表示进度，不表示就绪。特性缺失、设备错误、相机渲染失败或子进程退出都使后端不可用；先看当前运行的首条失败事件。固定版本跨所有者回放已验证 pick-place 和 navigation 两个场景的这一路径以及只读拍摄和观察。当时的 R05 EOS 目录只公开 `safety.estop`，未公开 `base.velocity` 与 `arm.movej`；下文 R06 回放随后执行了受治理的运动与停止。R05 回放本身没有下发受管理运动。详见[验收证据](../architecture_cn.md#r05-跨所有者验收)。

直接验证模拟器所有者切片：在私有目录运行 `build/eos-mujoco-sim --managed-strict-socket --v2-socket /absolute/private/run/strict.sock --scene "$PWD/assets/scene.xml"`，再发送 `node:"base-0"` 的分帧 `health` 请求。响应必须回显 ID，并包含 `ok:true`、`accepted:true` 与 `strict-socket-v1`。受管理启动拒绝 `--socket` 和 `--benchmark-socket`；不带标志的直接启动继续支持两者。运行 `ctest --test-dir build -R 'strict-socket|strict-capacity|v2-socket' --output-on-failure` 可回放所有者检查，包括完整保留容量。

发生 P02 目录故障时，先查看场景/设备的不可用原因与第一条包或 Apply 失败事件，再修改草稿。已链接资源变化时，按 P01 收据规则显式重新链接。缺少 `MUJOCO_ROOT` 库会阻止启动就绪，场景/profile 不匹配会阻止 Apply。这些失败均保留图与运行中子进程此前的修订。

检查结果和当前运行日志后，通过 `isos deployment stop` 停止。R05 增加严格身份和传输重发保护；已合并的 R06 伴随通道及限定范围回放证明两个场景在模拟器终止并回收前分别确认底盘/机械臂。仅凭 `accepted:true` 响应始终不能证明安全停止已确认；须核对 EOS 选定的终态回执与 IsOS 的最终结果。

**R06 限定范围首次使用行为：** 经审查的 `strict-stop-v1` 所有者实现已在 [PR #21](https://github.com/Island-Team/isos-mujoco-sim/pull/21) 合并；真实 pick-place/navigation 的 IsOS → EOS → MuJoCo 回放执行了受治理的运动与停止。使用精确且已验证的所有者构建，重复 Validate/Apply/Run。受管理子进程在主套接字路径追加 `.stop`，得到仅所有者可访问的伴随套接字；图不增加字段。EOS 目录公开 `base.velocity` 或 `arm.movej` 前，检查每个执行器的 `health` 同时具有 `strict-socket-v1` 与 `strict-stop-v1`，且 EOS 已探测伴随停止套接字。EOS 在第一次有界受管理运动中传入两个健康路径匹配的 32 字符 `generation_id` 和 `stop_epoch:"0"`，之后传入当前已证明的 epoch；旧令牌的**新**命令返回 `stop_fenced`，相同旧命令 ID 仍返回 R05 已存储结果。通过 EOS 下发运动，在运动或拍摄进行时通过 EOS/IsOS 停止；EOS 将带代际 ID 的受管停止送到伴随套接字。上代延迟请求返回 `stale_generation`。严格 `stop` 响应须回显请求 ID，包含 `base_stop:"stopped"`、`arm_stop:"stopped"`、匹配的 `generation_id`、非空十进制字符串 `stop_epoch`、`ok:true` 及 `accepted:true`；EOS 须在终止和回收直接子进程前校验该证明，清理后才发布选定的终态回执。[套接字契约](../interfaces/socket_cn.md#r06-受管理停止契约)定义这些值：状态字符串是无量纲证明状态，`stop_epoch` 是子进程内次序计数，也是运动请求的前提。缺失或未知状态、超时、子进程崩溃、`stop_outcome_unknown` 均表示安全停止未确认；检查首条关联故障事件与 EOS 日志，再核对有界的子进程及两个套接字路径清理。不能仅从进程退出或 `accepted` 推断物理停止。限定范围回放确认了两部分停止、匹配的代际与 epoch `1`，且没有残留子进程、进程组或套接字；停止套接字丢失与子进程崩溃仍判为未知。详见 [R06 证据](../architecture_cn.md#r06-所有者合并与限定范围跨所有者回放)。强制超时/KILL、GUI 不可用、过期或错误管道及崩溃恢复仍需更完整的 R06 验收，才能宣称 M3 控制全部完成。

v2 图中的模拟器节点可以在 `settings.env` 设置 `MUJOCO_GUI=1`，以同一模拟器引擎打开实时 X11 视图；独立启动脚本的 `--gui` 只是静态场景查看器。节点与套接字契约见 [backend_cn.md](isos-pkg_cn.md)。

## 软件包发布记录

## Island 包发布

[English](../../../docs/mujoco/usage/isos-pkg.md#package-release-record)

## `0.1.1` 发布版本 — 2026-11-04

**状态：**`v0.1.1` 已从准确的二进制构建源码 `04b65882cd11b0aff8ce56473164691dbd662196` 发布。重新下载的公开清单与归档摘要均与下文选定值一致。独立的干净 IsOS 主目录测试已验证并安装公开软件包、选择场景和设备、应用图、将 EOS 启动至就绪，并确认 Stop 与子进程回收。后续五方发布资产重放通过了既定 Q04/M5 关卡；具体范围与限制见下文。从较新的文档提交重新构建会产生新候选包，必须重新验证。

**操作员可见变化。** IsOS 可以验证并安装 `island/mujoco-sim@0.1.1`，列出两个场景及可用的相机、底盘、机械臂设备，预览 `sim-hardware` 节点集，并对选定图执行 Validate/Apply。EOS 将已验证仿真器作为直接子进程启动，读取真实相机帧，经 Dispatcher 准入运动，并在终止和回收子进程前确认物理 Stop。选定的干净主目录运行还覆盖子进程故障、受治理重启、软件包与边拒绝，以及显式图迁移。[Q03 验证记录](../architecture_cn.md)及 [EOS Q04 重放记录](https://github.com/Island-Team/Island-eos/blob/master/docs_cn/island/q04-merged-qualification_cn.md)说明范围和原始证据。

**兼容与迁移。** 此包采用 IsOS schema v4，节点集面向 `0.2.1` 图和已注册的 `@v0.2` 类型。先前已验证发布包中的 `eos.process.mujoco@v1.0` 仍由旧读取器处理；本候选包不贡献该类型。迁移须显式执行并检查修订。已发布的 `v1.0.1` 包使用退役图形态，属于另一版本。当前 `0.1.2` 候选包要求操作员提供 MuJoCo 3.3.1 库。已发布 `v0.1.1` 资产使用 MuJoCo 3.16.0，并记录 Ubuntu 24.04、`glibc>=2.39` 和 x86_64。原生依赖规则见[软件包契约](../interfaces/package_cn.md)。

**发布后的安装或升级。** 将 `MUJOCO_ROOT` 指向已安装的 MuJoCo 3.16.0 目录，按下文验证已发布清单和归档，再按[后端指南](isos-pkg_cn.md)安装或链接精确的 `0.1.1` 软件包，选择场景和设备，执行 Validate/Apply，启动 EOS。已保存的旧图在操作员请求迁移前保持原字节。

**已知范围。** 此次验证使用本地模拟托管 Origin 和 Ubuntu 24.04 原生资产；不证明公网 HTTPS 部署、其他架构或发行版、物理机器人切换或高频执行器通道。MuJoCo 仍是外部运行时依赖。软件包不向 EOS 或 EGIA 暴露基准真实状态。

### 已发布的精确字节与候选包检查

冻结的 Q04 final-5 候选包由源码提交 `04b65882cd11b0aff8ce56473164691dbd662196` 构建。选定**输入** `release.json` 的 SHA-256 为 `c421039753c24ffc74658d6b1dfe5c9de6a1ed77b64df8fbaee77063da837096`；归档为 8,797,162 字节，SHA-256 为 `bb2862b01c3ccab8b68570e766a0ad26c8c5783b3c87cf99225eb0edb7a260f4`。IsOS 安装后的清单是另一份字节流，不是发布输入。当前远端 `master` 之后仅增加文档；依照 IsOS 软件包来源校验要求，`v0.1.1` 必须解析到准确的构建源码。新标签首次发布时曾指向文档后代提交，随后立即修正；清单与归档字节未变。任何非文档改动都须重新构建、生成清单与摘要并重放干净主目录。

将封存的 Q04 `live/package-input/` 候选文件复制到 `/home` 下由操作员管理的目录后，运行并保留以下输出：

```sh
candidate=/home/ashex/release-candidates/mujoco-0.1.1
test "$(sha256sum "$candidate/release.json" | cut -d' ' -f1)" = c421039753c24ffc74658d6b1dfe5c9de6a1ed77b64df8fbaee77063da837096
test "$(sha256sum "$candidate/asset.tar.gz" | cut -d' ' -f1)" = bb2862b01c3ccab8b68570e766a0ad26c8c5783b3c87cf99225eb0edb7a260f4
test "$(stat -c %s "$candidate/asset.tar.gz")" = 8797162
python3 - "$candidate/release.json" <<'PY'
import json, sys
release = json.load(open(sys.argv[1], encoding="utf-8"))
asset = release["assets"][0]
assert (release["id"], release["version"], release["source_commit"]) == ("island/mujoco-sim", "0.1.1", "04b65882cd11b0aff8ce56473164691dbd662196")
assert (asset["sha256"], asset["size_bytes"], asset["libc"], asset["tested_ubuntu"]) == ("bb2862b01c3ccab8b68570e766a0ad26c8c5783b3c87cf99225eb0edb7a260f4", 8797162, "glibc>=2.39", ["24.04"])
assert "libmujoco.so.3.16.0" in asset["required_libraries"]
PY
mkdir -p "$candidate/inspect"
tar -xzf "$candidate/asset.tar.gz" -C "$candidate/inspect"
readelf -d "$candidate/inspect/bin/eos-mujoco-sim"
test -z "$(readelf -d "$candidate/inspect/bin/eos-mujoco-sim" | rg 'RPATH|RUNPATH')"
git diff --quiet 04b65882cd11b0aff8ce56473164691dbd662196 HEAD -- . ':(exclude)docs/**' ':(exclude)docs_cn/**'
```

最后一条命令比较已审查构建源码与当前的纯文档后代提交；已发布标签本身解析到构建源码。应对照目标主机检查 `readelf` 以及清单中的完整排序 `required_libraries` 列表，并在发布记录中保留选定 EOS [完整离线验证器命令](https://github.com/Island-Team/Island-eos/blob/master/docs/island/q04-merged-qualification.md)及其 `Q01_FULL_VERIFIED` 输出。该记录还包含 CMake/CTest（26/26）与 3,630 个文件的归档审查。选定 Q04 资产须原字节上传；从较新提交重新构建并写入新的 `source_commit`，即使测试通过，也属于新候选包。

此次文档审查在已审查的 master 基础提交上重新运行 `git ls-files -z '*.cc' '*.cpp' '*.h' '*.hpp' | xargs -0 -r clang-format --dry-run --Werror`、`cmake -S . -B logs/test/20261104-q04-release-notes/build -DMUJOCO_ROOT=<MuJoCo 3.16.0 根目录>`、`cmake --build logs/test/20261104-q04-release-notes/build -j4` 和 `ctest --test-dir logs/test/20261104-q04-release-notes/build --output-on-failure`：格式检查通过，CTest 为 26/26。R05/R06 静态用例矩阵分别通过 31/48 项，五项节点贡献测试、文档本地链接以及所复制选定清单／归档／ELF 检查均通过。完整本机输出位于 Git 忽略的 `logs/test/20261104-q04-release-notes/`；此次重跑检查当前源码，冻结的 Q04 归档仍是精确发布候选包。

### 发布后检查

首次公开下载检查已通过：`sha256sum` 返回选定清单摘要 `c421039…` 和归档摘要 `bb2862…`；归档有 56 个安全成员，远端 `v0.1.1^{}` 解析到 `04b65882cd11b0aff8ce56473164691dbd662196`。独立的干净主目录测试使用重新下载的字节、IsOS `c45011f`、公开 EOS 候选源码 `a4b66d3` 与 MuJoCo 3.16.0；软件包验证／安装、`pick-place` 预览、Validate/Apply、受管就绪和确认 Stop／回收均通过。完整本机输出位于 `/home/ashex/q04t/mujoco-public-smoke/`。这是首次使用已发布字节的初步测试。后续[五方发布资产重放](https://github.com/Island-Team/Island-eos/blob/master/docs_cn/island/q04-merged-qualification_cn.md)在干净 IsOS 主目录中使用已发布的 MuJoCo 归档，通过了发布资产的主路径、重启、迁移及 Stop 验证；另有单独封存的合并后提交六案例重放作为补充。发布关卡在其既定范围内已完成；发布资产重放没有呈现界面 Vision 帧，也没有测试公网 HTTPS Origin。

已发布的 `v0.1.1` 包包含精确的 `release.json` 清单和 `mujoco-sim-v0.1.1-linux-x86_64.tar.gz` 归档。将两份资源下载到 `/home` 下的新目录，对照上文核对 SHA-256 和归档大小，并检查公开标签目标、清单 `source_commit`、许可证、归档布局、ELF 依赖与发布 URL。上述安装／就绪／Stop 初步测试与后续 Q04/M5 发布资产重放，均已在各自记录的范围内通过。封存的 EOS `logs/test/20261104-public-five-assets-7/` 记录已发布资产字节、来源、现场观察、重启、迁移、Stop、独立评审及校验和清单。新的候选包或部署环境须使用新的运行 ID 重新验证。

```sh
download=/home/ashex/release-candidates/mujoco-0.1.1-public
mkdir -p "$download"
gh release download v0.1.1 --repo Island-Team/isos-mujoco-sim --dir "$download" --pattern release.json --pattern mujoco-sim-v0.1.1-linux-x86_64.tar.gz
sha256sum "$download/release.json" "$download/mujoco-sim-v0.1.1-linux-x86_64.tar.gz"
stat -c '%s %n' "$download/mujoco-sim-v0.1.1-linux-x86_64.tar.gz"
git ls-remote --tags origin refs/tags/v0.1.1
```

## Aether v2 节点候选包详情

`tools/bundle.py` 生成本地 `island/mujoco-sim@0.1.2` 后端包、schema v4 `release.json` 和带校验值的归档。`node_contributions` 声明一个由包提供的模拟器进程类型、`mujoco-v2` 适配器系列，以及 `sim-hardware` 节点集。节点集使用通用 EOS 相机、底盘、机械臂、门和 primitive 绑定类型。每个硬件节点在设置中选择并固定 MuJoCo 适配器；通用类型不归该包所有。IsOS 在安装或链接时验证发布信息并展示节点；图预览与应用仍需操作员明确执行。`backend-v2.json` 继续单独描述可执行文件、场景、设备和 MuJoCo 库依赖。构建与验证步骤见 [后端指南](isos-pkg_cn.md)。

原生 `0.1.2` 候选包先运行 CMake/CTest 门，再执行 `tools/bundle.py --build-dir <构建目录> --mujoco-root "$MUJOCO_ROOT" --output <空目录>`。构建工具暂存 CMake 安装后的程序，并在归档前检查它。审核 `assets[0].libc`、`tested_ubuntu`、`required_libraries`、归档摘要以及解压后 `readelf -d bin/eos-mujoco-sim` 的输出。当前 Ubuntu 24.04 主机记录 `glibc>=2.39` 和精确的 MuJoCo 3.3.1 SONAME。归档程序通过 IsOS 受管理启动时的 `LD_LIBRARY_PATH` 使用外部 MuJoCo 库。干净的 IsOS 管理式重定位与停止回放通过之前，不发布候选包。

## 先前发布版本

版本 1.0.1 已通过 GitHub Release 和 Island 包目录发布为 `island/mujoco-sim`。旧版 v0.1.0 使用旧目录模式；v1.0.1 使用 IsOS schema v4 清单。

`tools/release.py` 构建经过测试的 C++ 模拟器、场景资源、许可证和旧 EOS 配置模板，并生成供审核的归档及清单草稿。示例：

```sh
python3.12 tools/release.py --build-dir build --output dist
```

发布前需审核源代码、归档字节、许可证、SHA-256、依赖和 EOS 行为。候选清单记录 `ldd` 报告的 SONAME；`isos packages doctor` 检查运行时依赖。旧版激活包中的 `module.toml`、`eos.toml` 和 `binding.toml` 属于原 EOS 布局。MuJoCo 3.16.0 仍由操作员提供；可在 IsOS 管理的 EOS 节点 `launch.env` 中设置 `MUJOCO_ROOT`。变更二进制文件必须发布新版本。

## 当前 `0.1.2` 候选包验证（2026-11-11）

在本源码检出中，`python3 tests/nodes.py` 和 `ctest --test-dir build -R '^(scene-catalog|bundle-catalog|strict-socket|strict-stop-lane|strict-stop-lane-navigation)$' --output-on-failure` 通过。先用 `python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output <空目录>` 构建，再执行 `isos pkg verify <bundle>/release.json <archive>` 和 `ISOS_HOME=<隔离目录> isos pkg link island/mujoco-sim 0.1.2 <bundle> --manifest <bundle>/release.json`；在当前 IsOS 源码版本上两者均通过。`aether-profile catalog --node-types <已链接的 node-types.json>` 接受所贡献的进程，并将 `mujoco-v2` 报为尚未编译。当前 IsOS 预览调用 EOS 不提供的 `validate --file` 命令，因此这些检查尚未证明图 Apply 和托管就绪。完整 CTest 为 25/27；两个场景查看测试需要本地 MuJoCo 安装缺少的 `bin/compile` 与 `bin/simulate`。完整本地输出保存在已忽略的 `data/test/20261111-general-hal/`。
