# 发布历史与验收记录

[English](../docs/changelog.md) · [Docs](README_cn.md)

本页保留各版本与日期对应的历史包声明、进程节点行为、设计方案及检查。历史记录中的旧命令、所有权、依赖版本及“当前”“待完成”等表述仅适用于该记录。现行服务模型见[开始使用](start_cn.md)、[软件包](package_cn.md)与[架构](architecture_cn.md)。候选验收不等于发布；源码、包、图、节点、ABI 和套接字版本相互独立。

<a id="标准硬件契约验证2026-11-19"></a>
### 标准硬件契约验证（2026-11-19）

`0.2.8` 源码候选依据当前 EOS 目录注册七个硬件类型。部件 Dispatcher 继承其标准命令契约。原生及 RoboCasa 命令图和单独的 RoboCasa 模式绑定通过验证，未分配硬件及技能直达硬件的绕过路线被拒绝。插件接受标准载荷，检查必需字段、坐标系、关节顺序、限制及租期，并执行私有线路转换。所有者依据已注册输入契约选择标准载荷原样转发，同时保留旧软件包转换。

复现命令为 `cmake --build build -j4`、`ctest --test-dir build --output-on-failure -j4`、`python3 tests/nodes.py` 及 `python3 tests/eos_contracts.py --eos-profile <当前-IsOS-检出目录>/target/debug/aether-profile --plugin build/libmujoco-eos-node.so`。互操作脚本需要 Python `jsonschema`。使用 `python3 tools/bundle.py --build-dir build --mujoco-root <本地-3.3.1-目录> --output <空目录>` 构建候选，默认版本为 `0.2.8`。通过 `isos pkg verify <release.json> <归档>` 检查生成清单和归档。完整命令及输出保存在被忽略的 `data/test/20261119-standard-hardware/`。

检查通过：35 项 CTest、17 项节点声明测试、九项图准入案例、九项标准载荷模式、12 项 RoboCasa 工作进程测试及 13 项硬件测试。真实 EOS 所有者 → 部件 Dispatcher → 插件 → 原生服务回放完成底盘、机械臂与夹爪命令和观测，拒绝错误 Dispatcher 身份，并确认 Stop。这些边界测试中的 RoboCasa 适配器调用使用桩服务，不构成新完整 Gym 部署资格或候选发布。旧精确软件包版本保留其声明及载荷处理。

<a id="历史-020-进程候选"></a>
### 历史 0.2.0 进程候选

历史默认构建 `island/mujoco-sim@0.2.0`。`./build.sh --output <绝对路径空目录> --version 0.2.x` 选择尚未发布的补丁候选；每次已发布版本的修复使用新的补丁号。发布清单使用 `isos.package@v1`、schema `0.2.0`，通过 `lib/libmujoco-eos-node.so` 贡献 `mujoco-v2` 适配器系列。清单在 `adapters` 和 `node_contributions.libraries` 中记录同一 SHA-256；归档固定相同字节。输出目录保留清单中的资产文件名，例如 `mujoco-sim-v0.2.0-linux-x86_64.tar.gz`。归档按路径排序，文件所有者与时间戳归零，gzip 时间戳为零；固定载荷字节的重复归档摘要应一致。`python3 tests/archive.py` 验证此边界。`bin/eos-mujoco-sim` 仍是经过验证、受监督的子进程。动态库导出 `isos_node_v1` 的 create/start/input/health/stop/destroy，读取已准入节点的 `adapter.settings`，探测 `strict-socket-v1`，并将相机、底盘和机械臂观测转换成通用 `@v0.2` 载荷。它只接受 `{"op":"observe"}` 输入，拒绝直接运动命令。历史 `sim-hardware` 节点集只含模拟器进程与 JPEG 相机（观测 JSON 上限 12 MiB），能力标记为 `jpeg`；底盘和机械臂仍在资源目录中，但在执行器 Stop 证明完成前不纳入托管图。发布命令节点集前，EOS 必须负责 Dispatcher 准入和物理停止证明。

运行 `isos pkg check --source` 前，导出 `MUJOCO_ROOT` 指向本地 3.3.1 安装；显式环境值优先于 `config/package.toml` 的 `[host].mujoco_root`；包构建不加载开发用的 `.env`。`python3 tests/build_env.py` 在不下载内容的情况下验证此构建输入边界。清单将 IsOS 兼容范围限定为 `[0.2.3,0.3.0)`，并要求 IsOS `package-process-v1` 与 EOS `native-plugin-v1`；发布检查仍记录实际验证的 IsOS 构建。`.so` 是 Linux C++/protobuf 二进制文件，需要 IsOS 主机的 ABI 表和匹配的运行库。仅构建文件不足以证明兼容：IsOS 检查清单和摘要，EOS 检查 ABI 与回调，托管资格检查模拟器子进程、数据 schema、就绪和 Stop。其他平台及进程内 Python 是未来工作；Python 可使用受监督进程接口。`python3 tests/plugin.py <已构建动态库>` 使用桩验证严格健康、观测、运动拒绝和 Stop。下面旧的 `0.1.2` 记录属于历史候选证据，不是当前硬件候选的操作说明。

在 2026-11-11 的 Linux x86_64 验证主机上，使用实际 MuJoCo 3.3.1 构建后，29 项 CTest 全部通过，包括原生适配器、包目录、严格套接字、相机故障、Stop 和场景查看检查。构建和包进程主机输入均设置 `MUJOCO_ROOT=<MuJoCo 3.3.1 绝对根目录>`。启动 IsOS 时还须设置 `LD_LIBRARY_PATH="$MUJOCO_ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"`，使 EOS 管理的模拟器子进程能加载 `libmujoco.so.3.3.1`；包归档不包含该库。已检查的 `0.2.0` 源码候选通过 `isos pkg check --source ... --version 0.2.0 --graph ...`，覆盖托管 Run、相机观测、日志和 Stop。本地完整构建与 CTest 输出位于被 Git 忽略的 `data/test/20261111-real-mujoco/`；IsOS 资格检查的证据由其检查输出保存。这是源码资格验证记录，不表示 GitHub 发布已完成。

<a id="历史-012-候选说明"></a>
### 历史 0.1.2 候选说明

下述 `0.1.2` 软件包是使用 MuJoCo 3.3.1 的本地开发候选，尚未发布；本页后面的历史 `0.1.1` 证据仍对应 MuJoCo 3.16.0。

**当前实现：** 本页记录现有包与集成路径。[包描述符与声明](package_cn.md)和[模拟器套接字](core/adapter_cn.md)是本包拥有的字段契约；[架构](architecture_cn.md)说明集成方式，[后续验证](#后续验证)记录尚未完成的检查。协议或已生成描述符文件名中的 `v2` 为兼容而保留；本主题页文件名不带版本后缀。

[English](../docs/start.md)

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

发布清单中的 `node_contributions` 声明 `sim-hardware` 节点集、`mujoco-v2` 适配器系列，以及包拥有的 `eos.process.mujoco.simulator@v0.2` 进程类型。`0.2.1` 节点集添加该进程及 EOS 通用相机、底盘、机械臂 `device@v0.2` 实例。每个硬件节点在 `node.adapter.package` 中固定 `island/mujoco-sim@0.1.2`，并选择稳定的设备 ID。此首版节点集仅供观测：不声明 Dispatcher 命令绑定或相机门。IsOS 先验证发布包，再于预览和 Apply 验证组合图；EOS 就绪和 Stop 仍需另行测试所有者运行时。详见[包贡献契约](#p02-声明与图边界)。

后端节点的 `settings.env` 可设置 `MUJOCO_GUI=1` 或 `MUJOCO_GUI=true`，在支持 X11 的主机上打开 `IsOS MuJoCo — live simulation` 窗口。窗口渲染来自同一个 `SimEngine` 的相机画面；默认不显示 GUI。若请求 GUI 但显示服务不可用，模拟器启动失败。`tools/view.sh` 仍用于独立的静态场景预览。

v2 Unix 套接字帧以八字节小端长度头开头，后接 JSON 元数据和可选 JPEG 负载。元数据上限为 64 KiB，负载上限为 8 MiB。请求包含 `version: "2.0.0"`、字符串 `id`、`node` 和 `op`；响应回显 ID 与版本，并返回 `ok` 或 `error.message`。

**R05 限定范围验收：** EOS 管理的严格子进程只接受帧格式 v2 套接字，拒绝历史 gRPC 机器人套接字与 benchmark 套接字。独立直接启动仍为旧客户端与可信评测保留这些套接字。固定版本的 IsOS → EOS → MuJoCo 回放验证了两个场景中相机、底盘和机械臂的严格健康检查、只读图像及状态、子进程和套接字清理。R06 所有者停止屏障已合并，限定范围跨所有者运动与停止回放通过；更完整的 R06 故障验收仍待完成。详见[所有者套接字契约](core/adapter_cn.md)和 [R05 证据](#r05-跨所有者验收)。

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

<a id="验证"></a>
### 验证

2026-10-30 的现有基线在 Ubuntu 和 MuJoCo 3.3.1 上通过了十个 CTest 用例。`tests/v2.py` 覆盖 JPEG 捕获、底盘运动、六关节命令、安全停止和套接字清理。GUI 检查还验证了可见窗口、运动后像素变化，以及显示服务不可用时的启动失败。完整日志保存在本地 `logs/test/2026-10-30-v2-live/`。新增节点声明可用 `python3 tests/nodes.py` 检查，并需通过 IsOS 与 EOS 的完整图准入及运行集成测试。

2026-10-30，旧版六节点预设及端口元数据通过 `python3 tests/nodes.py` 的四个测试。`python3 tools/bundle.py --build-dir build --output logs/test/20261030-general-interfaces/bundle-r3` 成功生成当时的发布候选包，`ctest --test-dir build --output-on-failure` 的十个模拟器测试全部通过。完整本地输出保存在 `logs/test/20261030-general-interfaces/`。当时的八节点预设也用相同的 Python 命令检查；2026-10-31 的模拟器基线十个测试通过，日志在 `logs/test/20261031-generic-device-preset/`。

随后，独立的 IsOS 目录链接旧版 `bundle-r3`，使用场景和套接字参数预览 `sim-hardware`，并通过 EOS `aether-profile` 验证生成的图。该预览添加六个节点，只在当时四个 MuJoCo 类型上保留包引用，并报告三个由 IsOS 管理的进程。复现细节见 `logs/test/20261030-general-interfaces/graph-preview.log`。这属于历史回放证据；当前两节点 `0.2.1` 相机节点集仍需新的跨所有者回放。

<a id="软件包-012-检查2026-10-31"></a>
### 软件包 0.1.2 检查（2026-10-31）

`python3 tests/nodes.py`、`python3 tests/release.py` 和 `ctest --test-dir build --output-on-failure` 通过（10 项模拟器测试）。`python3 tools/bundle.py --build-dir build --output logs/test/20261031-version-alignment/bundle` 暂存的软件包在发行清单与描述文件中均报告 `0.1.2`。描述文件 schema 和套接字协议保持 `2.0.0`。输出位于忽略 Git 的 `logs/test/20261031-version-alignment/`。

<a id="isos-与-eos-部署"></a>
### IsOS 与 EOS 部署

当前 IsOS/EOS 路径使用本地 `island/mujoco-sim@0.1.2` 包和共享部署图。已发布的 v1.0.1 包属于旧图形态；其[发布文档](#软件包发布记录)仅供旧安装参考。按照 [后端指南](start_cn.md)构建包，并设置真实的 `MUJOCO_ROOT`。

```sh
source .env
python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output /absolute/path/to/mujoco-v2-bundle
isos init --mode dev
isos pkg link island/mujoco-sim 0.1.2 /absolute/path/to/mujoco-v2-bundle --manifest /absolute/path/to/mujoco-v2-bundle/release.json
isos pkg node-sets
```

用 `isos build eos`、`isos version select eos <selector>`、`isos build isosui` 和 `isos version select isosui <selector>` 构建并显式选择版本。同一 EOS 提交有多个构建时，用源码指纹选择唯一收据。`isos init` 创建配置后退出。在一个终端运行 `isos serve`，用 `isos pkg preview-set` 或 IsOS API 预览 `sim-hardware` 节点集，指定场景和仅所有者可访问的套接字，再通过按修订检查的 IsOS 接口 Validate 与 Apply。IsosUI 目录编辑器属于后续 U01 工作台门禁。该节点集声明 EOS 持有的模拟器进程和三个通用硬件适配器；本候选包没有 Dispatcher 命令绑定。已有图会保留至操作员显式应用新修订。

**P02 包目录与 IsOS 选择。** 构建工具现已输出 `0.1.0` 目录描述符和四节点 `0.2.1` 节点集，参数为稳定的 `scene`、`camera_device`、`base_device` 和 `manipulator_device`。用 `python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output <空目录>` 构建并检查包；`backend-v2.json` 含两个场景 ID、标签、profile 和 SHA-256，以及三台设备的描述和场景支持列表。P01 验证精确的 `island/mujoco-sim@0.1.2` 收据后，IsOS P02/P03 切片现已展示可用 ID、依当前已保存修订 Validate 与 Apply 所选场景和设备，并保留不可用的已保存 ID 供修复。修改场景生成新的已保存修订，必须 Restart 才能替换 EOS 持有的子进程。详见 [P02 包契约](#p02-描述符扩展)和[负面样本](../tests/fixtures/scene_catalog/negative-cases.json)。

另一终端运行 `isos run` 启动已应用部署。IsOS 启动前检查精确的软件包、资源、场景、MuJoCo 库、EOS 程序、套接字与端口；EOS 将模拟器作为直接子进程。限定范围的 R06 回放已证明 pick-place 和 navigation 的物理停止顺序；更完整的故障验收仍待完成。`isos deployment stop` 只停止部署，`isos stop` 停止管理器、API、UI、部署和独立服务。EGIA 只通过 EOS 的正常代理接口行动，不连接私有评测套接字。模型类服务管理器独立于此硬件图。

**R05 管理模式就绪，限定范围验收通过：** Apply 后，EOS 以严格模式启动已验证子进程，对图中每台相机、底盘和机械臂设备探测 `health`，要求 `version:"2.0.0"`、回显请求 ID、`ok:true`、`accepted:true` 以及包含 `strict-socket-v1` 的 `features`。套接字文件或进程启动日志只表示进度，不表示就绪。特性缺失、设备错误、相机渲染失败或子进程退出都使后端不可用；先看当前运行的首条失败事件。固定版本跨所有者回放已验证 pick-place 和 navigation 两个场景的这一路径以及只读拍摄和观察。当时的 R05 EOS 目录只公开 `safety.estop`，未公开 `base.velocity` 与 `arm.movej`；下文 R06 回放随后执行了受治理的运动与停止。R05 回放本身没有下发受管理运动。详见[验收证据](#r05-跨所有者验收)。

直接验证模拟器所有者切片：在私有目录运行 `build/eos-mujoco-sim --managed-strict-socket --v2-socket /absolute/private/run/strict.sock --scene "$PWD/assets/scene.xml"`，再发送 `node:"base-0"` 的分帧 `health` 请求。响应必须回显 ID，并包含 `ok:true`、`accepted:true` 与 `strict-socket-v1`。受管理启动拒绝 `--socket` 和 `--benchmark-socket`；不带标志的直接启动继续支持两者。运行 `ctest --test-dir build -R 'strict-socket|strict-capacity|v2-socket' --output-on-failure` 可回放所有者检查，包括完整保留容量。

发生 P02 目录故障时，先查看场景/设备的不可用原因与第一条包或 Apply 失败事件，再修改草稿。已链接资源变化时，按 P01 收据规则显式重新链接。缺少 `MUJOCO_ROOT` 库会阻止启动就绪，场景/profile 不匹配会阻止 Apply。这些失败均保留图与运行中子进程此前的修订。

检查结果和当前运行日志后，通过 `isos deployment stop` 停止。R05 增加严格身份和传输重发保护；已合并的 R06 伴随通道及限定范围回放证明两个场景在模拟器终止并回收前分别确认底盘/机械臂。仅凭 `accepted:true` 响应始终不能证明安全停止已确认；须核对 EOS 选定的终态回执与 IsOS 的最终结果。

**R06 限定范围首次使用行为：** 经审查的 `strict-stop-v1` 所有者实现已在 [PR #21](https://github.com/Island-Team/isos-mujoco-sim/pull/21) 合并；真实 pick-place/navigation 的 IsOS → EOS → MuJoCo 回放执行了受治理的运动与停止。使用精确且已验证的所有者构建，重复 Validate/Apply/Run。受管理子进程在主套接字路径追加 `.stop`，得到仅所有者可访问的伴随套接字；图不增加字段。EOS 目录公开 `base.velocity` 或 `arm.movej` 前，检查每个执行器的 `health` 同时具有 `strict-socket-v1` 与 `strict-stop-v1`，且 EOS 已探测伴随停止套接字。EOS 在第一次有界受管理运动中传入两个健康路径匹配的 32 字符 `generation_id` 和 `stop_epoch:"0"`，之后传入当前已证明的 epoch；旧令牌的**新**命令返回 `stop_fenced`，相同旧命令 ID 仍返回 R05 已存储结果。通过 EOS 下发运动，在运动或拍摄进行时通过 EOS/IsOS 停止；EOS 将带代际 ID 的受管停止送到伴随套接字。上代延迟请求返回 `stale_generation`。严格 `stop` 响应须回显请求 ID，包含 `base_stop:"stopped"`、`arm_stop:"stopped"`、匹配的 `generation_id`、非空十进制字符串 `stop_epoch`、`ok:true` 及 `accepted:true`；EOS 须在终止和回收直接子进程前校验该证明，清理后才发布选定的终态回执。[套接字契约](core/adapter_cn.md#r06-受管理停止契约)定义这些值：状态字符串是无量纲证明状态，`stop_epoch` 是子进程内次序计数，也是运动请求的前提。缺失或未知状态、超时、子进程崩溃、`stop_outcome_unknown` 均表示安全停止未确认；检查首条关联故障事件与 EOS 日志，再核对有界的子进程及两个套接字路径清理。不能仅从进程退出或 `accepted` 推断物理停止。限定范围回放确认了两部分停止、匹配的代际与 epoch `1`，且没有残留子进程、进程组或套接字；停止套接字丢失与子进程崩溃仍判为未知。详见 [R06 证据](#r06-所有者合并与限定范围跨所有者回放)。强制超时/KILL、GUI 不可用、过期或错误管道及崩溃恢复仍需更完整的 R06 验收，才能宣称 M3 控制全部完成。

v2 图中的模拟器节点可以在 `settings.env` 设置 `MUJOCO_GUI=1`，以同一模拟器引擎打开实时 X11 视图；独立启动脚本的 `--gui` 只是静态场景查看器。节点与套接字契约见 [backend_cn.md](start_cn.md)。

<a id="软件包发布记录"></a>
### 软件包发布记录

<a id="island-包发布"></a>
### Island 包发布

[English](../docs/changelog.md#package-release-record)

<a id="011-发布版本--2026-11-04"></a>
### `0.1.1` 发布版本 — 2026-11-04

**状态：**`v0.1.1` 已从准确的二进制构建源码 `04b65882cd11b0aff8ce56473164691dbd662196` 发布。重新下载的公开清单与归档摘要均与下文选定值一致。独立的干净 IsOS 主目录测试已验证并安装公开软件包、选择场景和设备、应用图、将 EOS 启动至就绪，并确认 Stop 与子进程回收。后续五方发布资产重放通过了既定 Q04/M5 关卡；具体范围与限制见下文。从较新的文档提交重新构建会产生新候选包，必须重新验证。

**操作员可见变化。** IsOS 可以验证并安装 `island/mujoco-sim@0.1.1`，列出两个场景及可用的相机、底盘、机械臂设备，预览 `sim-hardware` 节点集，并对选定图执行 Validate/Apply。EOS 将已验证仿真器作为直接子进程启动，读取真实相机帧，经 Dispatcher 准入运动，并在终止和回收子进程前确认物理 Stop。选定的干净主目录运行还覆盖子进程故障、受治理重启、软件包与边拒绝，以及显式图迁移。[Q03 验证记录](architecture_cn.md)及 [EOS Q04 重放记录](https://github.com/Island-Team/Island-eos/blob/master/docs_cn/island/q04-merged-qualification_cn.md)说明范围和原始证据。

**兼容与迁移。** 此包采用 IsOS schema v4，节点集面向 `0.2.1` 图和已注册的 `@v0.2` 类型。先前已验证发布包中的 `eos.process.mujoco@v1.0` 仍由旧读取器处理；本候选包不贡献该类型。迁移须显式执行并检查修订。已发布的 `v1.0.1` 包使用退役图形态，属于另一版本。当前 `0.1.2` 候选包要求操作员提供 MuJoCo 3.3.1 库。已发布 `v0.1.1` 资产使用 MuJoCo 3.16.0，并记录 Ubuntu 24.04、`glibc>=2.39` 和 x86_64。原生依赖规则见[软件包契约](package_cn.md)。

**发布后的安装或升级。** 将 `MUJOCO_ROOT` 指向已安装的 MuJoCo 3.16.0 目录，按下文验证已发布清单和归档，再按[后端指南](start_cn.md)安装或链接精确的 `0.1.1` 软件包，选择场景和设备，执行 Validate/Apply，启动 EOS。已保存的旧图在操作员请求迁移前保持原字节。

**已知范围。** 此次验证使用本地模拟托管 Origin 和 Ubuntu 24.04 原生资产；不证明公网 HTTPS 部署、其他架构或发行版、物理机器人切换或高频执行器通道。MuJoCo 仍是外部运行时依赖。软件包不向 EOS 或 EGIA 暴露基准真实状态。

<a id="已发布的精确字节与候选包检查"></a>
#### 已发布的精确字节与候选包检查

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

<a id="发布后检查"></a>
#### 发布后检查

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

<a id="aether-v2-节点候选包详情"></a>
### Aether v2 节点候选包详情

`tools/bundle.py` 生成本地 `island/mujoco-sim@0.1.2` 后端包、schema v4 `release.json` 和带校验值的归档。`node_contributions` 声明一个由包提供的模拟器进程类型、`mujoco-v2` 适配器系列，以及 `sim-hardware` 节点集。节点集使用通用 EOS 相机、底盘、机械臂、门和 primitive 绑定类型。每个硬件节点在设置中选择并固定 MuJoCo 适配器；通用类型不归该包所有。IsOS 在安装或链接时验证发布信息并展示节点；图预览与应用仍需操作员明确执行。`backend-v2.json` 继续单独描述可执行文件、场景、设备和 MuJoCo 库依赖。构建与验证步骤见 [后端指南](start_cn.md)。

原生 `0.1.2` 候选包先运行 CMake/CTest 门，再执行 `tools/bundle.py --build-dir <构建目录> --mujoco-root "$MUJOCO_ROOT" --output <空目录>`。构建工具暂存 CMake 安装后的程序，并在归档前检查它。审核 `assets[0].libc`、`tested_ubuntu`、`required_libraries`、归档摘要以及解压后 `readelf -d bin/eos-mujoco-sim` 的输出。当前 Ubuntu 24.04 主机记录 `glibc>=2.39` 和精确的 MuJoCo 3.3.1 SONAME。归档程序通过 IsOS 受管理启动时的 `LD_LIBRARY_PATH` 使用外部 MuJoCo 库。干净的 IsOS 管理式重定位与停止回放通过之前，不发布候选包。

<a id="先前发布版本"></a>
### 先前发布版本

版本 1.0.1 已通过 GitHub Release 和 Island 包目录发布为 `island/mujoco-sim`。旧版 v0.1.0 使用旧目录模式；v1.0.1 使用 IsOS schema v4 清单。

`tools/release.py` 构建经过测试的 C++ 模拟器、场景资源、许可证和旧 EOS 配置模板，并生成供审核的归档及清单草稿。示例：

```sh
python3.12 tools/release.py --build-dir build --output dist
```

发布前需审核源代码、归档字节、许可证、SHA-256、依赖和 EOS 行为。候选清单记录 `ldd` 报告的 SONAME；`isos packages doctor` 检查运行时依赖。旧版激活包中的 `module.toml`、`eos.toml` 和 `binding.toml` 属于原 EOS 布局。MuJoCo 3.16.0 仍由操作员提供；可在 IsOS 管理的 EOS 节点 `launch.env` 中设置 `MUJOCO_ROOT`。变更二进制文件必须发布新版本。

<a id="当前-012-候选包验证2026-11-11"></a>
### 当前 `0.1.2` 候选包验证（2026-11-11）

在本源码检出中，`python3 tests/nodes.py` 和 `ctest --test-dir build -R '^(scene-catalog|bundle-catalog|strict-socket|strict-stop-lane|strict-stop-lane-navigation)$' --output-on-failure` 通过。先用 `python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output <空目录>` 构建，再执行 `isos pkg verify <bundle>/release.json <archive>` 和 `ISOS_HOME=<隔离目录> isos pkg link island/mujoco-sim 0.1.2 <bundle> --manifest <bundle>/release.json`；在当前 IsOS 源码版本上两者均通过。`aether-profile catalog --node-types <已链接的 node-types.json>` 接受所贡献的进程，并将 `mujoco-v2` 报为尚未编译。当前 IsOS 预览调用 EOS 不提供的 `validate --file` 命令，因此这些检查尚未证明图 Apply 和托管就绪。完整 CTest 为 25/27；两个场景查看测试需要本地 MuJoCo 安装缺少的 `bin/compile` 与 `bin/simulate`。完整本地输出保存在已忽略的 `data/test/20261111-general-hal/`。

<a id="软件包验收记录"></a>
### 软件包验收记录

选择器检查于 2026-11-15 通过：`python3 tests/nodes.py`（14 项测试）、`python3 -m json.tool config/package-config.json` 和 `git diff --check`。节点测试检查选项与场景目录、已验证任务及样例默认值的一致性。完整命令输出保存在被忽略的 `data/test/20261115-package-selectors/`。

原生相机尺寸修改通过 `cmake --build build -j4`、`ctest --test-dir build --output-on-failure -j4`（35/35）、`python3 tests/nodes.py`（13/13）和 `git diff --check`。完整输出保存在被 Git 忽略的 `data/test/20261115-native-camera-source-dimensions/`。已选原生预设现在声明 1280 × 720，严格服务测试确认 JPEG 元数据及字节；拒绝用例覆盖缺失、小数和零尺寸。

2026-11-13，2048 像素候选版通过 18 项 Python 测试、全部 33 项 CTest、原生插件的 2048 × 2048 RGB8 交换、0.2.4 候选包构建及静态 `isos pkg verify`。修改的双语页面通过链接审计。完整输出位于忽略的 `data/test/20261113-robocasa-2048/`。托管 `pkg check` 和正式发布仍是独立关卡。

`0.2.5` 源码候选版于 2026-11-15 通过 24 项 RoboCasa Python 边界测试、11 项节点声明测试和全部 34 项 CTest。打包启动器在创建套接字前拒绝缺失或不可执行的解释器及未准备好依赖的 Python 环境。IsOS 使用 `pkg check --source <源码目录> --version 0.2.5 --output <空证据目录> --graph <RoboCasa 图> --graph <原生图> --package-config <本机 package.toml>`，对两套预设报告 `qualified:true`，静态验证、原生 ABI、所有者校验和托管回放均通过。准确输入和完整日志位于忽略的 `data/test/20261115-general-hardware/`；其中 `pkg-check/check.json` 记录已检查源码提交和资产摘要。这是候选版资格检查，不是正式发布。

<a id="历史进程节点声明020"></a>
### 历史进程节点声明（0.2.0）

历史 `isos.package@v1` schema `0.2.0` 的 `release.json` 为 `eos.process.mujoco.simulator@v0.2` 增加 `node_contributions.processes[]`。IsOS 根据归档字节和已贡献的进程类型验证声明，EOS 实现指定的生命周期适配器。先前已验证发布包中的历史 `@v1.0` 类型仍按原有路径读取；本清单不贡献该类型。图只保存准确包版本和稳定场景 ID，不保存解析后的路径。

| 字段 | JSON 类型 / 单位 | 用途 | 验证与默认值 |
| --- | --- | --- | --- |
| `processes[].node_type` | 字符串 / — | 要启动的进程类型 | 必需 `eos.process.mujoco.simulator@v0.2`，须为已贡献的进程类型；无默认值。 |
| `processes[].entrypoint` | 相对路径 / — | 已验证的可执行文件 | 必需 `bin/eos-mujoco-sim`，不得越界或经符号链接逃逸；无默认值。 |
| `processes[].lifecycle_adapter` | 字符串 / — | EOS 就绪和停止适配器 | 必需 `mujoco-v2`，EOS 必须注册；无默认值。 |
| `processes[].args` | 字符串数组 / — | 已验证子进程参数模板 | `--managed-strict-socket --v2-socket ${socket} --scene ${resource.scene.path}`；EOS 在运行时绑定私有套接字及已验证场景路径。 |
| `processes[].resources[]` | 数组 / — | 选择器绑定 | 必需一个场景绑定；无默认值。 |
| `resources[].setting` | 字符串 / — | 存放资源 ID 的节点设置 | 必需 `scene`，须匹配节点设置；无默认值。 |
| `resources[].kind` | 字符串 / — | 目录资源种类 | 必需 `scene`，值为稳定场景 ID；无默认值。 |
| `resources[].descriptor` | 相对路径 / — | 已验证的通用目录 | 必需 `package-resources.json`，归档内普通文件，不得越界或经符号链接逃逸；无默认值。 |
| `processes[].host_inputs[]` | 数组 / — | 宿主机启动输入 | 必需一个 `MUJOCO_ROOT` 目录声明；无默认值。 |
| `host_inputs[].name` | 字符串 / — | 环境变量名 | 必需 `MUJOCO_ROOT`，其值不写入图；无默认值。 |
| `host_inputs[].kind` | 字符串 / — | 宿主机值类型 | 必需 `directory`，IsOS 解析现有目录；无默认值。 |
| `host_inputs[].required` | 布尔值 / — | 启动是否需要该输入 | 必需 `true`，缺失时禁止启动。 |

`package-resources.json` 包含 `contract:"isos.package-resources@v1"`、字符串 `schema_version:"0.1.0"` 和 `resources[]`。场景资源必需 `kind:"scene"`、唯一稳定字符串 `id`、非空 `label` 和 `description`、归档内 MJCF 的相对 `path`，以及该文件的小写 SHA-256 `sha256`。设备资源必需 `kind:"device"`、唯一稳定字符串 `id`、非空 `label` 和 `description`、`metadata.device_kind`（`camera`、`base` 或 `manipulator`），以及引用已声明场景 ID 的非空且无重复的 `metadata.scene_ids[]`。所有字段均无默认值。通用 IsOS 选择器读取此文件，`backend-v2.json` 仍为 MuJoCo 专用 EOS 适配器协议及历史描述符。

包的构建入口为 `build.sh --output <空的绝对目录>`。它要求 `MUJOCO_ROOT`，在被 Git 忽略的 `.local/package-build/` CMake 目录中增量构建可执行文件与适配器目标，并在输出目录写入 `release.json` 和清单指定名称的归档，例如 `mujoco-sim-v0.2.0-linux-x86_64.tar.gz`。构建锁保证该目录由单个构建使用。每次调用仍重新执行 CMake 配置与打包；源码、构建选项或选定 MuJoCo 根目录变化时，CMake 会执行对应的构建工作。开发构建及 CTest 仍构建并验证测试目标。清单中的摘要和大小覆盖归档的准确字节。归档按路径排序，文件所有者与时间戳归零，gzip 时间戳为零；固定载荷字节的重复归档摘要应一致。`python3 tests/archive.py` 验证此边界。安装不会激活图或重启运行实例。

**所有权与状态。** 本仓库拥有 MuJoCo 专用 `backend-v2.json` 描述符以及当前发布清单中的 `node_contributions`。以下 P02 小节记录 0.1.2 历史候选；当前源码的外部适配器以本页开头的 0.2.0 契约为准。IsOS 拥有通用发布清单 schema、已验证收据与包准入、图修订和 `/node-options` 响应。`tools/bundle.py` 已输出 P02 目录和 `@v0.2` 进程声明；IsOS 的语义准入及通用 P03 选项 API 已在其所有者仓库实现；固定版本的 R05 回放验证了本包的实际使用。即使新图格式为 `0.2.1`，描述符 schema、协议和套接字线协议 `2.0.0` 仍是独立兼容性标识。

<a id="历史-012-描述符字段"></a>
### 历史 0.1.2 描述符字段

| 字段 | 类型／单位 | 用途／所有者 | 默认、验证和兼容 |
| --- | --- | --- | --- |
| `schema_version` | 字符串 | 描述符解析标识／本包 | 必填 `2.0.0`；IsOS 拒绝未知主版本，并保留此标识。 |
| `package.id`, `package.version` | 字符串 | 精确包锁定／本包 | 必填 `island/mujoco-sim`、`0.1.2`；须匹配已验证收据。 |
| `entrypoint` | 相对路径 | 模拟器程序／本包 | 必填 `bin/eos-mujoco-sim`；IsOS 检查其在已验证包内且可执行。 |
| `protocol` | 字符串 | EOS 适配器工厂标识／本包与 EOS | 必填 `mujoco-v2`；EOS 必须有匹配的编译工厂。 |
| `scenes[] .id` | 唯一字符串 | 稳定场景选择值／本包 | 当前 `pick-place`、`navigation`；图不存路径。 |
| `scenes[] .path` | 相对路径 | 场景 MJCF 与资源／本包 | 必须在已验证包内解析为可读的受支持场景；禁止遍历和符号链接逃逸。 |
| `devices.camera`, `.base`, `.manipulator` | 字符串 | 模拟器设备 ID／本包 | 当前 `cam-0`、`base-0`、`arm-0`；适配器设置使用精确 ID。 |
| `runtime.mujoco_version` | 字符串 | 外部 MuJoCo ABI 要求／本包 | `3.3.1`；IsOS 启动前检查库和程序兼容性。 |
| `runtime.environment_variable` | 字符串 | 安装根目录输入／本包 | `MUJOCO_ROOT`；不能把未验证程序路径或秘密写入图。 |
| `runtime.library` | 相对路径 | 安装根目录下所需动态库／本包 | `lib/libmujoco.so.3.3.1`；IsOS 启动前验证。 |

历史描述符没有场景或设备的人工描述、场景 profile 和逐场景校验值；设备映射适用于整个包。IsOS 现有解析器检查路径包含关系和引用文件字节；其 P02 配套切片增加描述符级 profile 与校验值检查。模拟器引擎加载场景时也会检查该 profile。

<a id="p02-描述符扩展"></a>
### P02 描述符扩展

以下字段在描述符 schema `2.0.0` 内追加。`scenes[].id` 和 `devices.<kind>` 保持为图设置中的稳定值；路径、XML 标记和哈希只属于包元数据。`catalog_version:"0.1.0"` 是唯一目标格式判别字段。存在时，每个场景都必须提供 `label`、`description`、`profile` 和 `sha256`，且 `device_catalog` 必须完整。缺失时，任意位置均不能出现这些目标字段；只有这个精确旧结构属于 legacy。部分混合在发布选项前以 `mujoco_catalog_incomplete` 拒绝；未知 catalog 版本以 `mujoco_catalog_unsupported` 拒绝。缺少元数据的已验证旧描述符仍按旧图行为读取，但 IsOS 不从中推导新图选项。判别仅基于精确字段与结构，不依据文件名或猜测包版本。

| 字段 | JSON 类型／单位 | 用途与所有者 | 默认、验证和兼容 |
| --- | --- | --- | --- |
| `catalog_version` | 字符串／— | 选择 P02 元数据规则；MuJoCo 包 | 仅完整旧结构可缺失；存在时必须精确为 `0.1.0` 且所有目标字段齐备。部分或未知版本关闭失败。 |
| `scenes[].id` | 非空 slug／— | 稳定场景选择值；MuJoCo 包 | 精确版本内唯一；当前为 `pick-place` 与 `navigation`；不是路径。 |
| `scenes[].label` | 非空字符串／— | 操作员显示；MuJoCo 包 | P02 候选必填；旧目录显示可回退为 ID，不修改原字节。 |
| `scenes[].description` | 非空字符串／— | 场景用途与可见任务；MuJoCo 包 | P02 候选必填；不构成图字段或运行权限。 |
| `scenes[].profile` | 枚举字符串／— | 预期的引擎场景类型；MuJoCo 包 | 必填，精确为 `eos_benchmark_pick_place_v1` 或 `eos_benchmark_navigation_v1`；安全解析 XML 后须等于唯一受支持的 MJCF 自定义数值标记，并通过真实引擎加载测试。 |
| `scenes[].path` | 安全相对路径／— | 场景 MJCF；MuJoCo 包 | 现有必填字段；P01 验证载荷内的普通文件，禁止符号链接和遍历；不作为选项值返回。 |
| `scenes[].sha256` | 小写 64 位十六进制字符串／SHA-256 | 将精确 MJCF 字节绑定到场景 ID；MuJoCo 包 | P02 候选必填；发现、Validate、Apply、Run 和 Restart 时与文件比较。P01 的载荷树校验值另行覆盖引用资源。 |
| `devices.<kind>` | 非空 slug／— | 按 `camera`、`base`、`manipulator` 分类的现有设备 ID；MuJoCo 包 | 本模拟器恰好三类、各一个不同 ID；保留旧字符串映射结构。 |
| `device_catalog[]` | 对象数组／— | 人工描述和场景可用性；MuJoCo 包 | P02 候选必填；与 `devices` 每类每个 ID 恰好对应，无额外项或重复 ID。 |
| `device_catalog[].kind`, `.id` | 字符串／— | 设备类别与稳定选项 ID；MuJoCo 包 | 必填且与 `devices[kind]` 精确一致；当前为 `cam-0`、`base-0`、`arm-0`。 |
| `device_catalog[].label`, `.description` | 非空字符串／— | 操作员显示与能力说明；MuJoCo 包 | 必填；不能从标签推断设备能力。 |
| `device_catalog[].scene_ids` | 非空场景 ID 数组／— | 此设备可用的场景；MuJoCo 包 | 必填，ID 在 `scenes[]` 中且不重复；当前两个场景均支持三台设备。所选场景不含该设备时 IsOS 拒绝选择。 |

`runtime.mujoco_version`、`runtime.environment_variable` 和 `runtime.library` 保持原义。IsOS 在 Apply 和 Run 前检查 `MUJOCO_ROOT` 下所声明的 `3.3.1` 库；缺失或不兼容时返回不可用原因。包不内置该库。文件名符合要求并不自动证明 ABI 兼容；启动/就绪边界须在报告 ready 前确定实际加载的版本。P01 先验证精确发布收据、全部载荷字节和路径包含关系；P02 再以该已验证句柄检查场景/profile 与设备映射语义。固定 `0.1.2` 锁定下修改程序、场景 XML、引用资源或贡献 sidecar 会使 P01 收据失效；有意修改须发布新包版本。

P02 描述符固定于 [`target-descriptor.json`](../tests/fixtures/scene_catalog/target-descriptor.json)；[`legacy-descriptor.json`](../tests/fixtures/scene_catalog/legacy-descriptor.json) 固定精确旧结构。构建工具根据复制后的 XML 计算两个 SHA-256，并在打包前检查 profile 标记、声明的模型元素与引用资源。MJCF 相对资源路径可以从场景目录向上遍历，但必须留在已验证包内；缺失、逃逸或符号链接资源均失败。真实引擎加载与回放仍由 CTest 验证。

<a id="p02-声明与图边界"></a>
### P02 声明与图边界

包在 `eos/process/mujoco` 贡献唯一新进程类型 `eos.process.mujoco.simulator@v0.2`；先前已验证发布包中的 `eos.process.mujoco@v1.0` 仍按原有路径读取。新类型声明 `implementation:{"kind":"managed_process","interface":"mujoco-v2","version":"1","lifecycle_adapter":"mujoco-v2"}`，并带非空 `description`；其 `scene` 设置有非空描述和 `selector:{"provider":"package","resource":"scene","package_from":"node.package"}`。`socket`（仅所有者可访问的 Unix 套接字路径）、可选 `env`（字符串表）和 `start_timeout_ms`（正整数毫秒）具有明确的类型、用途与验证。进程状态与健康由运行时拥有，不作为图端口。进程实例锁定 `node.package:{"id":"island/mujoco-sim","version":"0.2.0"}`；设置中不存解析后的程序或场景路径。此 sidecar 不增设执行器或安全适配器路线。

当前 `sim-hardware` 节点集面向 `0.2.1` 图，只含包拥有的进程与一个 EOS 通用 JPEG 相机（观测 JSON 上限 12 MiB） `device@v0.2`。相机实例固定 MuJoCo 适配器并引用进程节点。底盘和机械臂仍在资源目录中，但 EOS 完成执行器 Stop 证明前不贡献其托管实例。本包不贡献或覆盖 EOS 通用类型。包验证与链接不能证明图 Apply 或运行就绪。历史已保存图保留原有读取路径。

**目标图准入。** P02 节点集声明稳定参数 `scene`、`camera_device`、`base_device`、`manipulator_device` 和仅所有者可访问的 `socket`。默认场景为 `pick-place`，三个设备默认值为 `cam-0`、`base-0`、`arm-0`。在 IsOS 与 EOS 的图准入路径可用后，预览与 Apply 必须要求所选 ID 属于精确验证过的描述符、符合硬件类别和所选场景，并通过整图准入。已准入图保存 ID 和精确包锁定。IsOS 拥有组合及修订 compare-and-swap；改选场景必须生成新的已保存修订，仅在 Restart 后作用于子进程。不能原地修改运行中模拟器的场景。当前包验证与链接通过，但预览受 IsOS/EOS 验证命令不匹配阻塞，且当前 EOS 所有者尚未编译 `mujoco-v2`。

P03 拥有通用 `GET`/`POST /node-options` 按 `(node_path,setting)` 分组、所选值回显与不可用选项呈现。本包提供选择器声明和已验证目录元数据，不定义 HTTP 包装。R05 拥有严格套接字特性协商、请求 `node`/操作校验与命令去重。P02 目录项本身不能证明套接字强制检查设备 ID；R05 严格健康与设备/操作测试为受管理启动提供该证明。

<a id="p02-诊断与-isos-准入目标"></a>
### P02 诊断与 IsOS 准入目标

IsOS 保留 P01 诊断结构 `{code,path,message,id,version,stage}` 和 HTTP 422 准入结果。P02 新增下列稳定 `code`。直接包元数据检查的 `stage` 为 `descriptor`，所选图设置或外部库检查为 `admission`。按 P01 要求，直接 install/link/verify 的 `path:""`；固定样本的 `mutation.path` 标出受测描述符字段。Validate、Apply、Run 或 Restart 的 `path` 为表中精确的图 JSON Pointer，实例 ID 取自候选图。例子使用 `sim-hardware` 预设的 `simulator` 与 `arm` ID；底盘设备故障指向对应的 `drive` 适配器设置。格式不完整在选择设置前的包验证阶段即遭拒；若在图准入时发现，其路径指向进程的 `package` 锁定。消息是有界的修复提示，不包含原始 XML 解析错误、本地路径或环境值。未被图锁定的无关安装包不能阻止该图。

| 故障 | 稳定 code | 图准入时的 `path` | Stage |
| --- | --- | --- | --- |
| 缺少判别字段却带任何目标字段，或判别字段存在但字段不全 | `mujoco_catalog_incomplete` | `/cores/eos/layers/process/groups/mujoco/nodes/simulator/package` | `descriptor` |
| `catalog_version` 值不受支持 | `mujoco_catalog_unsupported` | `/cores/eos/layers/process/groups/mujoco/nodes/simulator/package` | `descriptor` |
| 场景 ID 重复/空白、描述空白、profile 字面值不受支持或 P01 路径检查之后的场景声明无效 | `mujoco_scene_invalid` | `/cores/eos/layers/process/groups/mujoco/nodes/simulator/settings/scene` | `descriptor` |
| 声明的 profile 与唯一受支持标记或所需模型元素不符 | `mujoco_scene_profile_mismatch` | `/cores/eos/layers/process/groups/mujoco/nodes/simulator/settings/scene` | `admission` |
| 声明的场景 SHA-256 与已验证 XML 字节不符 | `mujoco_scene_digest_mismatch` | `/cores/eos/layers/process/groups/mujoco/nodes/simulator/settings/scene` | `admission` |
| 所选场景 ID 不在已验证目录中 | `mujoco_scene_unavailable` | `/cores/eos/layers/process/groups/mujoco/nodes/simulator/settings/scene` | `admission` |
| 设备 ID 重复/空白，映射与目录类别或 ID 不符，场景支持列表无效 | `mujoco_device_invalid` | `/cores/eos/layers/hardware/groups/manipulator/nodes/arm/adapter/settings/device_id` | `descriptor` |
| 所选设备不存在、类别错误或所选场景不支持 | `mujoco_device_unavailable` | `/cores/eos/layers/hardware/groups/manipulator/nodes/arm/adapter/settings/device_id` | `admission` |
| 所需 MuJoCo 库缺失或版本/ABI 不兼容 | `mujoco_library_unavailable` | `/cores/eos/layers/process/groups/mujoco/nodes/simulator/package` | `admission` |

仅检查描述符时，即使表中列出相应的图字段，`path` 仍为空。P01 在 `payload` 阶段的 `package_changed` 和相应阶段的 `package_unsafe_path` 优先于所有 P02 代码。特别地，链接后的场景发生修改返回 `package_changed`；场景路径出现符号链接返回 `package_unsafe_path`。载荷字节符合 P01 但声明的场景哈希错误的候选包，在收据发布前的 P02 语义检查返回 `mujoco_scene_digest_mismatch`。P03 用这些有界原因呈现不可用选项，HTTP 选项包装仍归 IsOS。完整变异与预期 `{code,path,stage}` 组合固定于 [`negative-cases.json`](../tests/fixtures/scene_catalog/negative-cases.json)。

目标描述符示例摘录（完整样本含两个场景、三台设备）：

```json
{
  "schema_version": "2.0.0",
  "catalog_version": "0.1.0",
  "package": {
    "id": "island/mujoco-sim",
    "version": "0.1.2"
  },
  "scenes": [
    {
      "id": "pick-place",
      "label": "Pick and place",
      "description": "Reach, grasp and place an object",
      "profile": "eos_benchmark_pick_place_v1",
      "path": "assets/scene.xml",
      "sha256": "6c677b07597ddf3d18cf7b30dddd407a09d1c53086d61c919592d16723d32aea"
    }
  ],
  "devices": {
    "camera": "cam-0",
    "base": "base-0",
    "manipulator": "arm-0"
  }
}
```

若所选 `navigation` 场景的 XML 却声明 `eos_benchmark_pick_place_v1`，IsOS 在进程的 `settings.scene` 路径报告场景/profile 不匹配，已保存及已激活修订不变。若 `navigation` 的设备支持列表缺少 `arm-0`，机械臂选项不可用并附有有界原因，Apply 在其适配器设置处失败。若 `MUJOCO_ROOT` 缺少所需库，包可以保留安装，但所选场景不能就绪。MuJoCo 构建工具使用这些 P02 代码分类直接描述符错误；IsOS 配套切片将图时失败映射到上表精确路径。

通用 `release.json` 字段（ID、版本、校验值、架构、源码、许可证、资源）遵循 IsOS 包契约。本包贡献新进程类型、`mujoco-v2` 适配器系列和 `sim-hardware` 节点集。包只拥有模拟器进程类型；相机、底盘和机械臂类型仍归 EOS。实例的 `description` 描述配置好的实例；注册进程的 `NodeType.description` 描述可复用类型。缺少类型描述的旧版已验证 sidecar 继续使用兼容默认。

<a id="原生-012-资源要求"></a>
#### 原生 `0.1.2` 资源要求

候选归档包含 CMake 安装后的 `bin/eos-mujoco-sim`，其中没有构建目录的绝对 `RPATH` 或 `RUNPATH`。`release.json` 资源中的 `libc` 是在原生构建主机测得的 `glibc>=主版本.次版本`，`tested_ubuntu` 是该主机的 Ubuntu 版本，`required_libraries` 是已安装程序解析出的、排序后的 SONAME 依赖闭包。在 Ubuntu 24.04 验收主机上，保守的 libc 要求是 `glibc>=2.39`。直接依赖和实际解析的 MuJoCo SONAME 必须恰好为 `libmujoco.so.3.3.1`，并位于所选 `MUJOCO_ROOT/lib` 下；缺失、版本不符或任何未解析库都会阻止归档生成。归档不包含外部 MuJoCo 库。IsOS 解析 `MUJOCO_ROOT`，并通过 `LD_LIBRARY_PATH` 将库目录传给 EOS 管理的模拟器子进程；图设置和包锁定均不嵌入构建主机路径。`required_libraries` 与 `tested_ubuntu` 描述已测原生目标，不代表未测试主机也兼容。

<a id="历史声明的兼容性"></a>
### 历史声明的兼容性

历史已验证 sidecar 仅贡献 `eos.process.mujoco@v1.0`，缺少进程类型描述与选择器，且使用固定设备 ID 组合 `1.0.0` 图。读取方可为旧 sidecar 提供仅供目录显示的描述默认值，而不改变验证过的字节。当前构建工具输出一个 `eos.process.mujoco.simulator@v0.2` 进程类型和仅含两节点的 `0.2.1` 相机节点集；IsOS 先接受并验证新描述符，再把该预设发布为图选项。其他包资源以后可使用 P03 选项机制；本版本不定义 `egia.tensor` 执行。

<a id="当前-v02x-二进制适配器"></a>
### 当前 v0.2.x 二进制适配器

发布 schema `0.2.0` 声明 `adapters:[{"family":"mujoco-v2","library":"lib/libmujoco-eos-node.so","sha256":"<64 位小写十六进制>"}]`，且 `node_contributions.libraries` 使用相同路径和摘要。此动态库实现带版本的 `isos_node_v1` C ABI，不是第二个模拟器进程。EOS 将已准入的图实例传给 `create`，管理回调生命周期和模拟器子进程，并在卸载前调用 `stop`。插件 Stop 成功意味着观测回调已静止；EOS 仍须在终止子进程前通过严格 companion 套接字另行证明执行器停止。首个 `sim-hardware` 节点集只含模拟器进程与 JPEG 相机。底盘和机械臂仍作为目录资源列出，但在 EOS 证明执行器 Stop 前不得用于托管执行。

<a id="本地验证"></a>
### 本地验证

2026-11-08，`./launch.sh --robocasa --seed 42 --steps 20` 连续运行两次，均返回相同的任务说明、20 步和 `success: false`。这证明上游任务可加载且成功规则被调用，但不构成代理策略成绩。使用 MuJoCo 3.3.1 的 C++ 构建通过了全部 27 项 CTest。

<a id="本地验证2026-11-16"></a>
### 本地验证，2026-11-16

原生自定义场景 GUI 回放通过并自动退出。使用 256 × 192 相机设置的原生和 RoboCasa 完整图在候选版本 `0.2.6` 上通过 IsOS `pkg check`；`tests/package_logs.py` 找到服务输出与 EOS 运行 ID 的对应记录。三厨房 GUI 记录和无窗口重放在 `1:1`、`2:2`、`3:3` 全部完成，每个厨房执行三个动作且摘要一致。这些有界动作没有完成 `CloseFridge` 任务；此回放验证启动、动作传递、确定性重放、GUI 自动退出及清理。完整本地输出位于忽略目录 `data/test/20261116-full-interfaces/`，其中包含 `robocasa-three-final/summary.json`。

<a id="本地验证2026-11-18"></a>
### 本地验证，2026-11-18

包含软件包自带 RoboCasa 安装辅助程序的 0.2.7 源码候选版通过了 15 项节点测试、归档摘要检查和全部 35 项 CTest。支持安装辅助程序描述符的 IsOS 专题构建对原生及 RoboCasa 完整图通过了 `pkg check`，覆盖托管 Apply、就绪、接口、日志和停止。检查报告记录了精确源码提交；IsOS 专题提交为 `182403ab0`。隔离的 CLI 安装验证了 RoboCasa 提示、拒绝后保留配置，以及使用已准备的本地运行环境接受后保存路径。本次未重放全新网络下载。完整软件包和 CLI 输出位于忽略目录 `data/test/20261118-release-027-audit/`，尤其是 `pkg-check-027-setup-3/`、`setup-decline.log` 和 `setup-accept.log`。这些只是候选证据；发布 0.2.7 软件包前，IsOS 变更必须先完成审查和发布。

<a id="场景运行与集成"></a>
## 场景运行与集成

**状态：** 场景引擎、分帧套接字、包拥有的 P02 场景/设备目录及 IsOS P02/P03 准入和选项均已实现。R05 严格启动与健康集成已在固定版本的 IsOS → EOS → MuJoCo 回放中通过限定范围验收。R06 MuJoCo 停止通道已合并，限定范围的真实 IsOS → EOS → MuJoCo 停止回放通过；更完整的 R06 故障验收及 M3 控制验收仍待完成。产品版本 `0.1.1` 不代表套接字协议 `2.0.0` 是产品发布版本。

所有者契约见[包描述符与声明](package_cn.md)、[EOS 持有的套接字](core/adapter_cn.md)和[评测 RPC](../docs/core/benchmark.md)。本页描述算法，不重复负载定义。

<a id="目标激活算法"></a>
### 目标激活算法

1. IsOS 获取精确的 P01 已验证包句柄，检查 P02 场景 profile、XML 校验值、设备映射、逐场景设备支持和外部 MuJoCo 库，然后只把稳定 ID 与不可用原因交给后续 P03 选项解析器。安装包不编辑图。
2. 操作员预览 `sim-hardware`，选择稳定场景/设备 ID，检查草稿并应用一个修订。IsOS 在生成配置中解析验证过的路径；图保留 ID 和精确包锁定。旧 `1.0.0` 图与 `@v1.0` 类型仍可读；所有读取方支持后，新建图使用 `0.1.0`，新注册类型使用 `@v0.1`。
3. EOS 不编辑已应用修订，选择编译在内部的 `mujoco-v2` 适配器工厂，带 R05 管理严格启动标志把已验证模拟器作为直接子进程。严格校验及历史 gRPC 执行器监听器关闭前，子进程不得公告 `strict-socket-v1`。EOS 对每个已声明设备要求严格健康特性之后才发布就绪。健康失败或设备不匹配使节点不可用，并记录 `run_id`、可选 `node_path` 和 `correlation_id`。
4. Dispatcher 先准入执行器命令，适配器再发送。EOS 验证图节点、设备类别、场景和包锁定；模拟器检查精确的设备/操作组合及有限的场景边界，再按 `(node,command_id)` 去重，防止有界传输重发重复执行。EOS 绝不自动重放结果不确定的已下发命令。已合并的 R06 伴随通道提供物理屏障及底盘/机械臂分别证明；EOS 与 IsOS 仍负责关闭准入、判定回执及进程清理。
5. 关闭时 EOS 先停止新命令准入，再以有界期限要求所有已准入执行器停止，记录未确认情况，最后终止并回收子进程。EOS 退出或记录有界强制停止后，IsOS 才报告部署已停止。模拟器正常退出会清理仅所有者可访问的套接字。

<a id="p02-目录生成与兼容"></a>
### P02 目录生成与兼容

构建工具保留人工定义的稳定场景 ID，从打包的 XML 字节导出其校验值，并根据引擎支持的相机、底盘与机械臂模型元素核对设备目录。确定性样本固定预期 profile 标记、三台设备 ID 和包拥有的进程类型。声明的标记不等于 XML 中唯一标记、模型缺少设备所需元素或场景/设备 ID 重复时，构建或候选包失败。真实 MuJoCo 引擎加载与重放测试证明 XML 仍可运行；仅 XML 目录检查不足以证明模型兼容。

IsOS 先运行 P01 收据与路径验证，再解析精确验证过的描述符。精确的 `catalog_version:"0.1.0"` 判别字段要求完整场景和设备元数据；缺失时必须是完整旧结构。部分混合在发布选项前失败。IsOS 比较所选场景 ID、声明的 profile 和 XML 哈希，核对设备 ID、类别与场景，且在发布图或启动前检查外部库。可修复的草稿显示不可用选项；Apply 用契约规定的稳定 `{code,path,stage}` 诊断拒绝不可用的所选值。Run 与 Restart 再次验证；已链接载荷变化要求显式重新链接，不能静默更新运行中图。场景编辑使用 IsOS 修订 compare-and-swap，只有保存新修订并 Restart 后才进入 EOS。

新的 `sim-hardware` 预设在 EOS core 中有七个节点，并使用 IsOS 初始图已有的 dispatcher control 节点。硬件节点采用 EOS 通用 `@v0.1` 注册类型和精确锁定包的 `mujoco-v2` 适配器；MuJoCo 只贡献进程类型。此前验证过的旧 sidecar 仍按旧图行为可读；新预设不包含旧 `@v1.0` 类型或未注册的 IsOS Vision 类型。P03 拥有通用 `(node_path,setting)` 选项分组与 UI 回显。R05 在受管理严格模式下校验精确设备与操作；直接启动的旧模式仍保留忽略 `node` 的历史行为。详见 [P02 包契约](#p02-描述符扩展)与[固定样本](../tests/fixtures/scene_catalog/README.md)。

设计审查样本检查解析四个 JSON 文件、核对目标/旧格式判别结构和固定诊断组合、对仓库中的两个场景 XML 求哈希、验证声明的 profile 标记与设备/场景关系，并检查相对 Markdown 链接。完整输出记于 `logs/test/20261101-p02-design/fixture-doc-check.log`。实现回放使用 `python3 tests/catalogtest.py`、`python3 tests/nodes.py`、`python3 tests/release.py`、`cmake -S . -B build-p02 -DMUJOCO_ROOT=<MuJoCo 3.16.0 绝对目录>`、`cmake --build build-p02 -j4`、`ctest --test-dir build-p02 --output-on-failure`，以及 `python3 tools/bundle.py --build-dir build-p02 --output logs/test/20261101-p02-scene-catalog/bundle`。在 Linux x86_64 与 MuJoCo 3.16.0 环境，12/12 项 CTest 通过，包含真实场景引擎加载、回放及归档构建；暂存包含两个带哈希的场景、三个有描述的设备、两个进程类型标识和七节点预设。完整输出位于 `logs/test/20261101-p02-scene-catalog/`。先前 IsOS P01 程序的严格解码器只接受旧字段，因此当时新描述符的跨仓库链接探测被拒绝（`isos-p01-link.log`）；后续 IsOS P02 切片已解决此依赖，下方 R05 干净主目录回放可证。

<a id="目标命令与日志算法"></a>
### 目标命令与日志算法

**R05 模拟器实现。** [套接字契约](core/adapter_cn.md)拥有精确的标志、健康字段、边界、错误码及保留期。IsOS 生成配置为 EOS 管理的启动选择已验证包和场景。EOS 根据管理关系推导 `--managed-strict-socket`，而不是从图可写设置读取。严格模式拒绝历史 gRPC `SimulatorService` 与 benchmark 套接字参数；否则 `SimulatorService.Execute` 会成为绕过 Dispatcher 的第二条执行器路线，而 benchmark Reset/Step 也能改变同一引擎状态。可信评测器使用独立直接启动。不带标志的直接启动保留线协议 `2.0.0` 下现有的旧帧、gRPC 和 benchmark 行为。

严格就绪须端到端核对，不能仅依赖连接成功。EOS 探测图中每个已声明的场景设备，检查协议版本、回显请求 ID、正面的 `ok` 与 `accepted`，以及响应特性列表中的 `strict-socket-v1`。模拟器只有能执行精确设备/操作匹配、有限的有类型运动限制与有界 ID 后，才绑定严格帧监听器。子进程遗漏或矛盾地公告特性时，EOS 拒绝并回收。EOS 的 `BackendChild::wait_ready` 与适配器健康现已在发布就绪前要求精确特性；固定版本的真实子进程回放覆盖了两个场景。

对于有效运动或 `stop`，服务在调用引擎前保留 `(node,command_id)`，整个子进程代际都记录规范化的有类型操作指纹和结果。相同传输重发以新传输请求 ID 返回旧结果；冲突返回 `command_id_conflict`。并发重复请求不能下发两次。固定的运动容量与预留停止容量拒绝新命令，不能驱逐键；也不能因 TTL 过期而允许同一子进程内重放。有界进程内保留不能代替 EOS 的持久 Dispatcher 日志：断线、超时或重启后，结果不确定的已下发命令保持未知，EOS 要从新观察核对或要求新的显式准入。受管理服务校验 `node` 与 `command_id`，并串行接受连接；R05 不声称停止可抢占。已合并的 R06 子进程提供专用有界停止通道和分别确认；某次停止能否称为已确认，仍取决于 EOS/IsOS 的回执及子进程清理。

启动时只记录一次含包、场景 ID、协议和 `run_id` 的净化 JSONL 事件；随后在就绪变化、命令准入/结果、套接字故障和关闭时记录。不记录图像字节、任意环境变量或每个高频观察。首次使用者先看当前运行的首条就绪/失败事件，再按规范 `node_path` 和 `correlation_id` 筛选。共享事件格式、轮转和游标读取由 IsOS 定义；本包提供来源 `mujoco` 及自身事件码。

**R05 设计证据：** [31 个固定用例](../tests/fixtures/strict_socket/cases.json)覆盖直接启动兼容、严格启动隔离、健康证明、设备/操作匹配、有类型边界、重复/冲突/容量、畸形帧和 EOS 不重放。2026-11-02 执行 `python3 tests/fixtures/strict_socket/check.py`、`python3 tests/catalogtest.py`、`python3 tests/nodes.py`、`python3 tests/release.py` 与 `git diff --check` 均通过；完整命令和输出见被 Git 忽略的 `logs/test/20261102-r05-strict-design/design-check.log`。这些记录设计门；运行时验证和配套 EOS 严格客户端资格验证另见下文。

**R05 模拟器实现证据：** 在 Linux x86_64、GCC 13.3 和 MuJoCo 3.16.0 环境，执行 `cmake -S . -B build -DMUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0`、`cmake --build build -j4` 和 `ctest --test-dir build --output-on-failure`。初次实现门禁 16 项 CTest 全部通过；最终独立审查门禁 18/18 通过，包含真实严格套接字启动/负面请求、65,536 个运动键、4,096 个预留停止键、不确定结果保留，以及旧 v2/gRPC/benchmark 兼容。固定设计、目录/声明/发布检查、Python 编译和 `git diff --check` 均通过。完整输出见忽略的 `logs/test/20261102-r05-strict-impl/gates.log` 与 `logs/test/20261102-r05-strict-review-fixes/gates.log`。C++ 设备表由包拥有的 P02 目录生成，与已加载引擎 profile 取交集；引擎检查已加载关节范围。EOS 严格客户端与不重放证据记于下方跨所有者验收；在这一 R05 门禁时，R06 抢占停止仍待完成；后续合并证据见下文。

**R05 实现审查修复：** 重复运动/停止响应保留原来的 `timestamp_ns`、`sequence`、准入与错误，仅更换传输 `id`。真实双客户端重发测试核对两个响应，并证明后续重复请求不会重启物理底盘租期。严格相机健康在公告特性前渲染一帧；测试专用 EGL 预加载强制失败并验证 `device_unavailable`。最终门禁命令和结果见忽略的 `logs/test/20261102-r05-strict-review-fixes/gates.log`。

<a id="r05-跨所有者验收"></a>
### R05 跨所有者验收

EOS 中封存的 `logs/test/20261102-r05-cross-owner-qualifier/qualification.md` 与独立 `reviewer-verdict.md` 固定于 EOS `9701a4d449249a3cd90bd5bd8d2ba98809d59435`、MuJoCo `41e17107b7c7abe43cd29cc388b7dd157979d476`、IsOS `1db1aa52df959f06e7c494797edd09a2b5289bcf`。其 85 个封存文件已通过 `sha256sum -c evidence.sha256`；同目录的 `commands.txt` 和完整日志可复现检查。审查者批准在常规 PR 检查及状态文档更新后完成限定范围的 R05 所有者条目。

两个全新 IsOS 主目录链接精确包，选择 pick-place 与 navigation，Validate、Apply 后由 EOS 启动已验证的直接子进程。两个场景均通过相机、底盘、机械臂严格健康检查、只读拍摄和观察、就绪事件顺序及子进程/套接字/授权清理。pick-place 回放覆盖两代进程并拒绝旧授权。负面检查拒绝错误场景、错误设备和被篡改的链接资源，且保存及活动状态不变。MuJoCo 严格 CTest 重点测试 7/7、EOS 线协议 8/8、进程 16/16、两个真实场景的子进程及持久日志中不重放不确定命令的检查均通过。MuJoCo 适配器尚无 `has_terminal_stop_fence`，所以实时 EOS 目录只公开 `safety.estop`，在 Submit 前隐藏 `base.velocity` 与 `arm.movej`；回放没有下发受管理运动。R06 须证明物理停止屏障、专用停止通道、底盘/机械臂分别确认及安全终止顺序，才能宣称完整 M3 首次使用控制通过。

<a id="r06-停止通道设计目标"></a>
### R06 停止通道设计目标

[所有者套接字契约](core/adapter_cn.md#r06-受管理停止契约)固定新增字段、稳定错误码、1000 ms 停止期限、每连接 250 ms 入口期限和 `strict-stop-v1` 特性。[48 个设计用例](../tests/fixtures/strict_stop_lane/cases.json)固定故障、并发及生命周期行为。三个入口工作线程的变更已通过独立设计及实现复审，并在 PR #21 合并。限定范围的跨所有者安全停止回放通过；更完整的故障验收仍待完成。

受管理主监听器最多使用 32 个普通工作槽和 8 个入口槽。它从既有路径推导独立、仅所有者可访问的 `.stop` 套接字，后者具有自己的监听器、三个停止入口工作线程、从 accept 起计算的 250 ms 部分帧到期机制和一个预留停止执行槽。伴随监听器只解析 `health` 与 `stop`；EOS 探测其健康，并把所有受管停止发送到此处。主入口中八条阻塞连接不能占用伴随槽。若此前只有两个部分停止帧且没有其他排队者，第三个工作线程可在有效停止连接后的自身 250 ms 入口期限内完成分类，保持 500 ms 分类上界；若三个较早的部分帧占满入口，第四帧可能在队列中到期，停止结果为未知。不能用脱离管理的线程或无限制的客户分配持有引擎状态。停止通道在预留时记录新的引擎停止 epoch，使两个运动租期及旧命令令牌失效，再在短时引擎命令状态锁内分别保持底盘和机械臂。每个受管理子进程启动时还生成全新的 128 位 `generation_id`；两个健康路径都返回它，EOS 在每次受管理运动和伴随停止中回传。即使旧代请求的 epoch 与新代初始 `"0"` 相同，旧代延迟请求仍以 `stale_generation` 拒绝。每个受管理运动还携带当前 `stop_epoch` 前提，初始值为 `"0"`；引擎在同一锁内写目标前复核。比较**新键**的 epoch 前须先查询运动日志：相同旧键的重发在停止后仍返回原结果，旧键改变 epoch 则报冲突。屏障前已提交的运动可能之后才返回响应，但停止必须覆盖其目标之后才能确认；已排队的旧运动返回 `command_interrupted`，屏障后才解析的延迟**新键**旧帧返回 `stop_fenced`。这是 EOS `has_terminal_stop_fence` 所需的次序证明，旧响应中的 `accepted` 位不足以证明。

渲染须在短时命令状态锁内取得有界不可变状态快照，随后使用独立、有界的渲染上下文。停止取消排队拍摄，并屏蔽已经渲染中的负载发布。服务器在停止预留时关闭活动 JPEG 流，并使用独立的发布闸门：成功停止须等旧流离开闸门；若流在 1000 ms 期限内仍被阻塞，停止结果为未知。固定停止执行线程可能在期限之后继续完成物理保持；响应仍为 `stop_outcome_unknown`，本代子进程的新运动持续被禁止。伴随健康检查从缓存读取身份和特性，不获取引擎互斥锁。EGL 可能无法中断；这时有界停止通道仍须到达引擎，EOS 最终强制终止并回收子进程。成功停止分别返回 `base_stop`、`arm_stop` 和 `stop_epoch`，时间戳和序号在提交之后采样。部分证明返回 `stop_outcome_unknown`；超时或丢失响应对 EOS 来说仍未知，即使子进程实际停止。相同停止重发只返回已存储字段，不重新下发。直接启动 `2.0.0` 行为不变。

**跨所有者责任：** EOS 须推导并探测伴随 `.stop` 路径，比较主监听器与伴随监听器的健康代际，选择长于 500 ms 接受／分类期限加服务器 1000 ms 预算的外层单调期限，同时限制连接、完整帧读写和 SIGTERM/SIGKILL/回收阶段；经审查的 EOS 设计为物理伴随请求预留三秒。每次运动须发送当前 `generation_id` 和 `stop_epoch`，每次伴随停止发送代际 ID，校验两个停止状态及返回的代际／新 epoch，紧急停止前关闭 Dispatcher 准入，防止延迟下发在停止后到达适配器；缺少任一证明时记为 `OutcomeUnknown`。之后明确授权的非锁存控制停止可以允许携带新已证明 epoch 的命令；紧急关闭保持拒绝准入。EOS 仅在特性和终态屏障可用时公开运动能力；更完整的 R06 验收仍待完成。IsOS 须在包／套接字选择时预检推导出的伴随路径长度，按相反依赖顺序停止 EGIA/EOS 进程组；EOS 报未知时，IsOS 不能宣称完成安全停止。模拟器自身不能证明 EOS 次序或 IsOS 进程生命周期。

**R06 仅设计证据，2026-11-02：** `python3 tests/fixtures/strict_stop_lane/check.py` 验证了 47 个唯一目标用例及中英文契约标记。R05 样本检查、场景目录 8 项、节点声明 5 项、发布检查 1 项、Python 编译和 `git diff --check` 均通过。完整命令与输出在被 Git 忽略的 `logs/test/20261102-r06-stop-design/design-check.log`。本设计提交不含 C++ 实现，也不宣称运行时停止通过；下一步是独立设计审查及 EOS 适配器协议确认。

**R06 实现候选证据，2026-11-02：** 在 Linux x86_64、GCC 13.3、MuJoCo 3.16.0 环境运行 `cmake -S . -B build -DMUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0`、`cmake --build build -j4`、`ctest --test-dir build --output-on-failure`；初始 21 项 CTest 全部通过，包括 R05 兼容用例、pick-place/navigation 真实停止套接字、八条阻塞主入口帧、两条阻塞伴随入口帧、跨进程代际拒绝、停止后旧键重发、引擎层延迟写屏障及活动机械臂中断，以及拍摄快照后阻塞图形调用时停止仍完成且旧帧被丢弃。独立审查发现三处 P1 竞态；后续增加确定性的引擎阻塞、伴随健康及 JPEG 发布测试，完整 23 项结果记录在 `logs/test/20261102-r06-strict-stop-review-fixes/`。进一步审查发现 250 ms 入口计时器在队列出队之后才启动。修正后，每个队列条目都携带从 accept 起计算的绝对期限，最后一次读取后再次检查到期，并把伴随入口增至三个工作线程，使此前两个部分帧不能耗尽有效停止的入口预算。新增测试用三个部分帧占满所有工作线程，确认第四个部分帧已被接受，再暂停子进程至原期限之后，验证恢复后立即关闭，并验证此前两个部分帧之后的有效停止分类。完整 24 项 CTest、R06/R05 样本、Python 编译及差异检查记录在被 Git 忽略的 `logs/test/20261102-r06-strict-stop-accept-deadline/`；排队接受期限回归重复十次通过，独立设计与实现复审批准精确头 `212f757`。初始完整输出及精确命令在被 Git 忽略的 `logs/test/20261102-r06-strict-stop-implementation/`。所有者测试本身不证明 EOS 安全停止；下方限定范围的跨所有者回放核验了确认和未知结果，更完整的 R06 验收仍待完成。

<a id="r06-所有者合并与限定范围跨所有者回放"></a>
### R06 所有者合并与限定范围跨所有者回放

[PR #21](https://github.com/Island-Team/isos-mujoco-sim/pull/21) 将经审查的头 `212f7572205eee3dd271d876bf9779eecb76d1f1` 压缩合并到 `master`，合并提交为 `c171208f0ef605fd4d5275d75567928713c50e96`。所有者闸门通过 24/24 项 CTest、十次接受期限回归，以及固定的 R06 48 项和 R05 31 项样本检查。完整输出在忽略的 `logs/test/20261102-r06-strict-stop-accept-deadline/`。

真实 pick-place 和 navigation 回放在全新 P01 链接的 IsOS 主目录中，通过 EGIA 授权的 gRPC 准入底盘和机械臂运动。EOS Stop 在 MuJoCo 终止并回收前输出一份 schema-1 回执，两部分均确认，代际匹配，epoch 为 `1`。IsOS 轮询后保留 `stopped`；独立进程扫描未发现残留子进程、进程组或套接字。停止套接字丢失及 MuJoCo SIGKILL 被判为未知，没有虚假确认。完整命令、原始回执、事件、journal 与校验清单保存在忽略的 `/home/ashex/projects/isos/logs/test/20261102-r06-full-cross-owner/`，范围记录于 [PR #21](https://github.com/Island-Team/isos-mujoco-sim/pull/21)。强制超时/KILL、GUI 不可用、过期或错误管道及崩溃恢复仍属于更完整的 R06 验收。此次合并未标记或发布 `0.1.1`。

**文档状态修正，2026-11-02：** 在已合并的所有者树 `c171208` 上，`python3 tests/fixtures/strict_stop_lane/check.py`、`python3 tests/fixtures/strict_socket/check.py`、`python3 tests/catalogtest.py`、`python3 tests/nodes.py`、`python3 tests/release.py`、`cmake -S . -B build -DMUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0`、`cmake --build build -j4`、`ctest --test-dir build --output-on-failure`、已修改 Markdown 的相对链接检查及 `git diff --check` 均通过。CTest 为 24/24；已修改文档的 119 个相对链接目标均存在。完整输出在忽略的 `logs/test/20261102-r06-doc-status/`。

一个模拟器进程在启动时加载一个场景。引擎持有 MuJoCo 模型与数据、带种子的确定性重置、固定步长物理计算、机器人命令目标、遥测、相机渲染和场景评分。EOS 面向机器人的接口与可信评测接口共享引擎，但发布不同的信息。评测器可以重置、步进、读取真实状态与评分；代理只能通过 EOS 使用已声明的观察和动作。

直接运行以 `--scene` 选场景；当前 IsOS/EOS v2 部署在已应用的共享图中选择场景，EOS 将路径传给其模拟器子进程。MJCF 必须且只能包含一个支持的自定义数值标记：`eos_benchmark_pick_place_v1` 或 `eos_benchmark_navigation_v1`。引擎还验证必要命名元素，包括导航场景的 `navigation_goal`。可加载的任意 XML 不会自动成为受支持的评测场景；新场景需要明确的重置、评分、能力和测试。更换场景需要重启进程。

模拟器仍提供旧版 `eos.simulator.v1.SimulatorService` gRPC 套接字，供旧的直接集成使用。当前 IsOS/EOS v2 运行时使用独立的、仅所有者可访问的帧格式套接字，由 `--v2-socket` 指定；契约见 [backend_cn.md](start_cn.md)。EOS 持有模拟器子进程，将图中声明的观察与 primitive 端口交给代理。benchmark 套接字与两种机器人接口均分离。此软件包不链接到 EOS core。

EGIA 连接已运行的 EOS，发现健康设备和版本化 primitive，并通过 EOS 执行。它不能获得评测种子、目标真值、特权状态或评分。代理评测将通过 EOS 可见的行为与独立评测器的私有结果比较。

已发布的 v1.0.1 包及其生成的 EOS profile 属于旧路线。v2 中，IsOS 链接或安装精确的 `island/mujoco-sim@0.1.1` 包，检查可执行文件、场景、资源和外部 MuJoCo 库，并通过 `sim-hardware` 节点集应用共享图修订。EOS 读取该图，并将经校验的模拟器作为直接子进程启动。源码构建仍可用绝对场景与套接字路径直接运行。

原生 `0.1.1` 发布中，CMake 在构建目录的 RUNPATH 中保留 `MUJOCO_ROOT/lib`，以便本地测试。打包时先用 `cmake --install` 安装到临时目录，检查安装后的程序，再复制进归档。安装后仍有绝对 RUNPATH、MuJoCo SONAME 不符、依赖未解析，或实际库不在选定 MuJoCo 根目录下，都会使打包失败。资源记录包含测得的 Ubuntu 与 glibc 版本以及解析出的 SONAME 依赖闭包。IsOS 在受管理启动时为选定的外部库设置 `LD_LIBRARY_PATH`；这是重定位边界。包集成测试将最终归档解压到另一目录，并在该环境下运行严格套接字路径。

**原生发布证据，2026-11-03：** 在 Ubuntu 24.04 x86_64、glibc 2.39、`/home` 下的 MuJoCo 3.16.0 环境，`cmake -S . -B build-native -DMUJOCO_ROOT=<根目录>`、`cmake --build build-native -j4`、`TMPDIR=<home 临时目录> ctest --test-dir build-native --output-on-failure -j2`、`python3 tests/catalogtest.py`、`python3 tests/nodes.py`、`python3 tests/release.py` 和 `git diff --check` 均通过。CTest 为 26/26，包含原生要求的反向用例，以及归档解压后使用与 IsOS 后端解析器一致的环境进行的异地严格套接字启动。`tools/bundle.py --build-dir build-native --mujoco-root <根目录> --output logs/test/20261103-native-release-metadata/bundle` 生成的资源包含 `glibc>=2.39`、`tested_ubuntu:["24.04"]`、解析出的 SONAME 依赖闭包，归档 SHA-256 为 `eebf8f1e8267b8a766ae4c25dc657516a0b645bdf5867cef974d5535a67a383b`。安装后的 ELF 没有 RUNPATH/RPATH。`isos pkg verify <清单> <归档>` 在本机接受了精确归档。完整输出位于忽略 Git 的 `logs/test/20261103-native-release-metadata/`。发布前仍须另行完成干净的 IsOS/EOS 受管理回放。

<a id="时间与故障"></a>
### 时间与故障

MuJoCo 以固定的 2 毫秒物理步长推进。重置将场景置于确定性的带种子初始状态并暂停实时推进。评测器可以推进有界步数、检查状态、评分，再恢复实时运行。可重复性要求相同的场景版本、种子、命令序列和步进安排；异步实时观察不保证确定性重放。

缺少或无效的场景、必要元素缺失或套接字不可用都会导致启动失败。不可用设备与命令通过 EOS 面向机器人的接口报错。benchmark 服务在 `StateResponse.ok` 和 `error` 中报告重置或步进错误。与当前场景无关的真实状态字段不能用作代理输入，也不能推断为目标。

<a id="旧实现调用者核查"></a>

<a id="旧实现调用者核查2026-11-04"></a>
### 旧实现调用者核查（2026-11-04）

[English](../docs/changelog.md#legacy-caller-audit-2026-11-04)

IsOS 受管理路径使用严格模式的 v2 帧套接字。以下旧路径仍有调用者，因此保留。

| 候选项 | 构建、运行时或测试调用者 | 结论 |
|---|---|---|
| `src/isos/service.cpp`、`src/isos/service.h`、`proto/simulator.proto` | `src/isos/main.cpp` 调用 `Serve`；直接启动的 `launch.sh` 传入 `--socket` 与 `--benchmark-socket`；`tests/smoke.sh`、`tests/eval.py` 和 `smoke-rpc` 检查 gRPC 路径。EOS 也保存 simulator proto。 | 保留直接运行兼容性及已发布 proto。受管理严格模式禁止两个旧监听器。 |
| `proto/benchmark.proto`、`benchmark-eval` | 可信的直接运行评测器调用 Reset、Step 和评分 RPC；`tests/eval.py` 覆盖此路径。 | 保留，仅供评测器使用。 |
| `benchmark-reset` | `tests/q03bench.py` 使用此私有工具进行确定性种子重置；Q03 验证命令也指定该目标。 | 在基准工具有替代实现前保留。 |
| 直接模式的 `--v2-socket` | `tests/v2.py` 与 Q03 工具覆盖该路径；直接运行时可与历史监听器共存。 | 保留。README 和英文用法示例现列出三个不同的套接字。 |

上述候选项均非无调用者实现。IsOS 受管理子进程仍通过 `--managed-strict-socket` 启动，仅使用所有者可访问的 v2 与伴随停止套接字。

<a id="当前基线"></a>
### 当前基线

- 命令：`eos-mujoco-sim --help` 列出直接运行的 `--socket`、`--benchmark-socket`、可选 `--v2-socket` 与 `--managed-strict-socket`；`launch.sh`/`kill.sh` 持有独立进程；`benchmark-eval` 仅供评测器使用。
- 安装：`CMakeLists.txt` 只将 `eos-mujoco-sim` 安装到 `bin`。`tools/bundle.py` 生成独立的 IsOS 包；CMake 不安装测试及基准工具。
- 接口：直接运行的历史 gRPC simulator 与 benchmark 套接字仍为私有路径；受管理路径仅开放 v2 帧套接字和派生的 `.stop` 伴随套接字。精确请求与响应契约见 `docs/core/adapter.md`。
- 图版本：`tools/nodes.py` 输出七个 `@v0.1` 注册类型；`tools/catalog.py` 输出 catalog `0.1.0`。IsOS 持有编写图的版本与持久化；模拟器不修改已应用图。

<a id="后续验证"></a>
### 后续验证

`v0.1.1` 软件包已发布，下述 Q03/Q04 选定版本重放已通过。强制超时或终止、GUI 不可用、错误或过期管道，以及崩溃恢复仍需更完整的 R06 故障验证。IsOS 日志和首次故障查找仍需端到端验证。每次新验证都应记录精确的软件包及各归属方版本、运行 ID、命令和结果。

<a id="q03-仿真器验证设计"></a>
### Q03 仿真器验证设计

[English](../docs/architecture.md)

**状态：**归属方源码检查、Q03 final-17 选定源码重放及 Q04 final-5 合并后提交重放均已通过。独立 Q04 归档审查没有 P1/P2 发现。`v0.1.1` 标签已发布，后续五方发布资产重放通过了其既定 Q04/M5 关卡；详见[软件包发布记录](#软件包发布记录)和 [EOS Q04 验证记录](https://github.com/Island-Team/Island-eos/blob/master/docs_cn/island/q04-merged-qualification_cn.md)。仿真器拥有场景加载、确定性复位、物理、渲染、私有套接字及基准评分。EOS 拥有机器人侧路由。基准真实状态不得通过 EOS、EGIA 或界面暴露。

**Q03 所有者初始基线（2026-11-03）：**已实现 `tests/q03bench.py`、私有 `benchmark-reset` 工具及失败路径单元测试。此处是本机直接套接字证据，不等同于跨仓库安装重放或发布批准。初次完整输出保留在 Git 忽略的 `logs/test/20261103-q03-mujoco/`；最终渲染器探针软件包保存在 `logs/test/20261103-q03-mujoco-review-final/`；无碰撞的逐请求原始样本及六份子进程日志保存在 `logs/test/20261103-q03-mujoco-review-final-2/`。

<a id="固定输入与所有者检查"></a>
### 固定输入与所有者检查

从已获取的 `master` 提交构建，使用 MuJoCo 3.16.0，记录编译器、CMake、CTest、库、源码及场景哈希。对受 Git 跟踪的 C++ 源码运行 `clang-format --dry-run --Werror`；运行 CMake 配置／构建及全部 CTest，再运行严格套接字／容量／Stop、场景、引擎及基准的定向测试。运行节点贡献契约用例，并在空输出目录构建新的 `island/mujoco-sim@0.1.1` 软件包。保存清单／归档 SHA-256，并在干净的 IsOS 主目录验证该包。把完整命令、输出及退出状态保存到忽略 Git 的 `logs/test/<run-id>/`，包括失败的尝试。

已安装的所有者重放必须选择目录中的两个场景，证明精确软件包和场景准入，读取一帧图像，通过 EOS 发送一次获准的底盘或机械臂命令，注入仿真器死亡，并观察当前运行的故障和受控 Stop／回收。保留选定图修订、运行 ID、软件包收据、子进程身份及跨仓库验证器结果。独立的 CTest 必需，但不能替代已安装重放。

<a id="初始套接字基线"></a>
### 初始套接字基线

使用私有、仅所有者可访问的 v2 Unix 套接字，不启用 GUI。针对 `assets/scene.xml` 和 `assets/scenes/navigation/scene.xml`，分别启动三个全新的仿真器进程。使用直接启动的非托管基准进程（绝不作为 EOS 持有的托管子进程），提供私有、绝对且互不相同的 `--socket`、`--benchmark-socket`、`--v2-socket` 与 `--scene` 路径。例如：`build-q03/eos-mujoco-sim --socket /absolute/private/legacy.sock --benchmark-socket /absolute/private/benchmark.sock --v2-socket /absolute/private/v2.sock --scene /absolute/scene.xml --manual-step`。每次进程预热前必须通过私有基准套接字成功执行 `Reset(seed=42)` 并记录响应；测量期间保持引擎暂停，不进行异步步进。使用软件包中仅含 EGL 的 `SimEngine::RenderCamera` 路径及 640×480 的 `cam-0` 捕获。套接字不输出运行时解析的渲染器身份；启用子进程的可选 EGL 上下文探针，从子进程日志记录运行时 EGL 供应商和 GL 渲染器，并在每次重复时断言实际 JPEG 格式、字节长度和图像尺寸。预热 20 次后，串行发送 200 次 `base_observe` 和 20 次 `camera_capture` 请求。记录每次单调时钟耗时、响应状态和字节数，以及每组操作测得的墙钟时长。逐进程和合并样本报告成功请求数／秒或帧数／秒、中位数（偶数样本取中间两数平均）及最近秩 p99（毫秒）；单独报告所有失败与超时。这只测量仿真器套接字，不代表 IsOS HTTP、EOS Dispatcher 或浏览器延迟。初始测量不形成性能目标。

测试工具须对套接字不可用、畸形响应、超时、场景错误和子进程意外退出明确失败；定向测试须覆盖这些路径。独立代理在实现前审查本设计，并在合入 MuJoCo `master` 前审查工具、证据及 PR。Q03 跨仓库摘要记录最终精确提交；Q04 负责发布与标签。

<a id="可重现的所有者证据"></a>
### 可重现的所有者证据

在仓库根目录设置 `MUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0`，依次执行：

```sh
git ls-files -z '*.cc' '*.cpp' '*.h' '*.hpp' | xargs -0 -r clang-format --dry-run --Werror
cmake -S . -B build-q03 -DMUJOCO_ROOT="$MUJOCO_ROOT"
cmake --build build-q03 -j4
ctest --test-dir build-q03 --output-on-failure
ctest --test-dir build-q03 -R 'strict-socket|strict-capacity|strict-stop|v2-socket|benchmark-eval|engine-test|scene-catalog|bundle-catalog|q03-socket' --output-on-failure
python3 tests/fixtures/strict_socket/check.py
python3 tests/fixtures/strict_stop_lane/check.py
python3 tests/nodes.py
python3 tools/bundle.py --build-dir build-q03 --output logs/test/20261103-q03-mujoco-review-final/bundle
python3 tests/q03bench.py --sim build-q03/eos-mujoco-sim --reset build-q03/benchmark-reset --scene assets/scene.xml --warmup 20 --observe 200 --capture 20 --repetitions 3 --json logs/test/20261103-q03-mujoco-review-final-2/pick-place.json
python3 tests/q03bench.py --sim build-q03/eos-mujoco-sim --reset build-q03/benchmark-reset --scene assets/scenes/navigation/scene.xml --warmup 20 --observe 200 --capture 20 --repetitions 3 --json logs/test/20261103-q03-mujoco-review-final-2/navigation.json
```

格式修正后，全部 CTest 为 25/25，定向测试为 16/16；R05、R06 静态用例矩阵分别通过 31、48 项，节点贡献检查通过。初次格式检查在三个原有文件中出现 86 项诊断：`tests/smoke.cpp`、`src/isos/service.cpp`、`src/mujoco/gui.cpp`。单独的纯格式提交已修正，最终受 Git 跟踪的 C++ 格式检查通过。最终软件包为 `mujoco-sim-v0.1.1-linux-x86_64.tar.gz`，SHA-256 为 `05a9346db26f43510c1986ff7431038ae29197ac85300a2f1efd1211f3458fe6`。在这一初始归属方基线时，跨仓库 IsOS→EOS 安装重放尚待完成。

本机为 x86_64 Linux、GCC 13.3.0，使用已安装的 MuJoCo 3.16.0、软件包 EGL 渲染路径且无 GUI。`environment.json` 记录内核、工具版本、源码提交、二进制、场景、库和归档哈希。全部六个进程的运行时探针均报告 EGL 供应商 `NVIDIA` 和 GL 渲染器 `NVIDIA GeForce RTX 2080 Ti/PCIe/SSE2`。种子 42、暂停场景、每个场景三个新进程；每进程预热 20 次，再测量 200 次观察和 20 次图像采集。最终原始测量如下：

| 场景 | 操作 | 成功／失败 | 吞吐量 | 中位数 | p99 |
| --- | --- | ---: | ---: | ---: | ---: |
| 抓取放置 | `base_observe` | 600/0 | 17,549 次／秒 | 0.054 毫秒 | 0.089 毫秒 |
| 抓取放置 | `camera_capture` | 60/0 | 716 帧／秒 | 1.261 毫秒 | 2.961 毫秒 |
| 导航 | `base_observe` | 600/0 | 18,033 次／秒 | 0.053 毫秒 | 0.074 毫秒 |
| 导航 | `camera_capture` | 60/0 | 731 帧／秒 | 1.262 毫秒 | 2.453 毫秒 |

吞吐量为成功次数除以各进程对应操作组的测量总时长。中位数取成功样本排序后的中点，p99 用最近秩。相同日志目录中的较早尝试结果不同，可能受到本机负载影响；此基线不设性能目标，也不作跨主机推断。每次重复分别记录成功的 `Reset(seed=42)`、观察到的 JPEG 探针尺寸，以及全部样本状态、字节数和超时标记。失败请求记录零个已接受的有效负载字节，摘要单独统计超时。可选的子进程日志在上下文创建后记录运行时 EGL 供应商与 GL 渲染器；套接字响应提供观察到的 JPEG 尺寸。日志文件名使用基准输出文件名，确保两个均名为 `scene.xml` 的场景各有独立日志。前一次运行因场景文件同名覆盖了子进程日志；其原始样本仍保留，但子进程日志由本次运行取代。数字只代表仿真器私有套接字。

<a id="选定安装归档证据2026-11-03"></a>
#### 选定安装归档证据（2026-11-03）

选定的 0.1.1 软件包记录 MuJoCo 源码提交 `3bf8a50aa2100b3eb1758ea4795bdcdddb65391e`；`release.json` 必须继续保持这个精确来源身份。选定发布文件 SHA-256 为 `591cd2ec454b659bbe97645811a6c928081045636e82e52b5b2f2dda3247b445`，归档资产 SHA-256 为 `53f9fa5d9af4b92b74635fd22447a9f08450b89a19725b6d26b6bd5850a5be96`。EOS Q03 选定清单 SHA-256 为 `116aef2846750a96275645e4dec3021ad716ce6fb80b05c087a2ce377a74b990`；冻结评审主构建和案例构建收据 SHA-256 分别为 `977293e097779f636cb70bde9f3d5657bc9351b0b9f67534ca7beb41a97ef915` 和 `20b2dc444d4f90ca1e4cf4b8a2404893c53cd20de19a090ce02debf0c539ab5d`。

在封存的干净主目录重放中，IsOS 验证并安装该归档，选择 `pick-place` 场景和可用的相机、底盘、机械臂设备；EOS 将已验证的 MuJoCo 可执行程序作为直接子进程启动。真实的 640×480 相机帧到达 EOS、EGIA Vision 与浏览器观察。R06/A03 选定来源故障试验通过子进程死亡、Stop／回收及重启检查，没有重放结果不明的运动；最终部署 Stop 获确认，受管进程无存活者。六组选定案例和 `Q01_FULL_VERIFIED` 保存在 EOS 中忽略 Git 的 `logs/test/20261103-q03-selected-final-15/`。上文私有套接字基准仍是另一项固定负载测量。此次安装重放只覆盖本地模拟托管 Origin。在 final-15 关卡时，Q04 合并后提交评审和标签发布尚未执行。若更改软件包来源 HEAD，必须重新构建并验证 0.1.1 软件包。

<a id="最终选定源码与合并后提交的归档证据2026-11-04"></a>
#### 最终选定源码与合并后提交的归档证据，2026-11-04

后续封存的 Q03 `20261103-q03-selected-final-17` 归档仍固定软件包源码 `3bf8a50aa2100b3eb1758ea4795bdcdddb65391e`、发布文件 SHA-256 `591cd2ec454b659bbe97645811a6c928081045636e82e52b5b2f2dda3247b445` 和归档 SHA-256 `53f9fa5d9af4b92b74635fd22447a9f08450b89a19725b6d26b6bd5850a5be96`。冻结选择清单 SHA-256 为 `35dd4e5aa4c209bf84935002a4eded756f3eb5a1c147b2fb12bd5d894e46b78a`；精确选定的 EOS 源码 `219f031bae9dbfc9d9f53f62c910b9e235bb2138` 上的验证器对全部六组返回 `Q01_FULL_VERIFIED`。独立 EOS 审核位于 `logs/test/20261104-q03-final17-independent-audit/`：选定源码验证通过，而较新检出因测试工具摘要变化被拒。上文 final-15 记录保留为历史证据。

Q04 `20261103-q04-merged-home-final-5` 的发布文件从已合并的 MuJoCo `master` `04b65882cd11b0aff8ce56473164691dbd662196` 重新构建。`release.json` 的 SHA-256 为 `c421039753c24ffc74658d6b1dfe5c9de6a1ed77b64df8fbaee77063da837096`，已安装归档的 SHA-256 为 `bb2862b01c3ccab8b68570e766a0ad26c8c5783b3c87cf99225eb0edb7a260f4`；冻结的外部选择清单 SHA-256 为 `7f5cefa5b6521d42d28b88c916679f2b668ba93fd61bbcbbfed4bb8fcc722b87`。IsOS 在干净主目录中验证并安装精确软件包；EOS 将仿真器作为直接子进程启动，产生真实相机帧和受治理的底盘结果，随后在子进程终止与回收之前确认物理 Stop。选定的 R06/A03 故障与重启案例通过，没有重放结果不明的运动。完整选定验证器返回 `Q01_FULL_VERIFIED`；独立归档评审检查了 3,630 个封存文件，没有 P1/P2 发现。原始收据、事件、子进程证明和命令保存在 EOS 中忽略 Git 的 `logs/test/20261103-q04-merged-home-final-5/`。这是本地模拟托管 Origin 的重放，不代表已发布 `v0.1.1` 软件包或公网 HTTPS 部署；在该关卡时，发布收尾和标签仍未完成。

<a id="mujoco-模拟器进程节点"></a>
## MuJoCo 模拟器进程节点

**当前软件包类型。** v0.2.0 源码候选在 `core=eos`、`layer=process`、`group=mujoco` 贡献 `eos.process.mujoco.simulator@v0.2`，实现类型为 `managed_process`。当前 `sim-hardware` 预设只含进程与一个 JPEG 相机；底盘和机械臂仍在资源目录中，但在执行器 Stop 证明完成前不得用于托管执行。历史 0.1.x 软件包保留原有读取路径。注册的 `NodeType.description`：“作为 EOS 拥有的子进程启动一个已验证 MuJoCo 场景，只提供图中声明的仿真设备。”实例描述独立记录本次部署用途。

<a id="首次使用行为"></a>
### 首次使用行为

1. IsOS 验证精确包收据、可执行文件、场景资源、设备映射及外部 MuJoCo 库；给出带描述和不可用原因的稳定场景/设备选项。操作者选择 ID，不填写路径。
2. IsOS 校验 `sim-hardware` 预览并应用修订。EOS 不修改图，解析已验证的 `mujoco-v2` 动态库并直接启动经验证的模拟器子进程。
3. 套接字健康及声明设备检查通过后节点才就绪。JPEG 相机适配器是独立的 EOS 节点实例；此进程节点不能绕过 dispatcher 准入。
4. 失败时状态保留不可用节点及原因。日志先显示本次运行第一条就绪/故障事件，再按节点路径和关联 ID 过滤。
5. 关闭时 EOS 先关闭准入并请求 R06 物理停止，再终止和回收子进程。未获确认的停止记录为结果不确定；限定范围的 R06 重放已确认底盘与机械臂分别获确认。

<a id="算法与兼容"></a>
### 算法与兼容

选择顺序为：精确收据 → 摘要/路径验证 → 描述符验证 → 选项解析 → 图校验 → 子进程启动 → 套接字健康 → 适配器激活。更换场景需要新图修订和子进程重启。套接字 `2.0.0`、描述符 `2.0.0`、release schema `0.2.0` 与 `mujoco-v2` 适配器名是独立兼容身份。未知未来图或类型版本给出版本诊断；旧图仅在显式且校验修订后迁移。命令去重与停止顺序见[集成设计](architecture_cn.md)。

<a id="历史-eos-mujoco-进程节点"></a>
## 历史 EOS MuJoCo 进程节点

`eos.process.mujoco.simulator@v0.2` 属于历史 `0.2.0` 的 `sim-hardware` 节点集。它把一个已验证 MuJoCo 场景作为 EOS 管理的子进程启动，为该节点集的 JPEG 相机提供私有服务。它是进程生命周期节点，不是代理控制或观察端口。当前完整硬件预设包含设备节点，由 IsOS 隐式启动所选运行服务，不含此进程节点。

<a id="位置和设置"></a>
### 位置和设置

节点为 `core:eos`、`layer:process`、`group:mujoco`、`kind:software`，生命周期和能力均为 `process`。该节点集包含此节点和 `native/front` 相机。进程类型本身无输入或输出端口。

| 设置 | 类型 / 单位 | 操作员选择 | 验证和默认值 |
| --- | --- | --- | --- |
| `scene` | 字符串 / 稳定 ID | 已验证包目录中的 `pick-place` 或 `navigation` | 必需；图不存解析后的路径；节点集默认 `pick-place`。 |
| `socket` | 字符串 / 私有 Unix 路径 | EOS 管理的子进程端点 | 必需；类型无默认值。 |
| `env` | 字符串表 / — | 子进程环境引用 | 可选；缺失时为空。 |
| `start_timeout_ms` | 正整数 / ms | 子进程就绪期限 | 类型中可选；缺失时使用 EOS 策略。 |

IsOS 验证精确包收据、场景 XML 摘要、所选场景 ID 和宿主 MuJoCo 库。EOS 从已验证包解析 `bin/eos-mujoco-sim` 和场景路径，使用 `mujoco-v2` 生命周期适配器以 `--managed-strict-socket --v2-socket ${socket} --scene ${resource.scene.path}` 启动。操作员不在节点中填写可执行文件或 benchmark 套接字路径。

<a id="就绪和停止"></a>
### 就绪和停止

子进程必须打开仅所有者可访问的套接字，并通过图中已声明设备的严格健康检查，EOS 才公布就绪。场景缺失、库错误、相机渲染不健康、协议不兼容或子进程退出时，节点带原因保持不可用；仅有套接字存在不足以确认就绪。EOS 在停止前关闭命令准入，从伴随停止通道请求全机器人证明，证明缺失时记录未知结果，再回收子进程。改变场景需要新的图修订和子进程重启。此受管理节点不能暴露 benchmark 复位或评分。帧、错误和期限见[运行控制契约](core/adapter_cn.md)。

## 本地构建与配置验证记录

软件包模式复用被 Git 忽略的 `.local/package-build/` CMake 构建树。2026-11-18 的缓存回放记录在忽略目录 `data/test/20261118-package-build-cache/`，两次运行 `./build.sh --output <空目录> --version 0.2.6` 分别耗时 20.25 秒和 4.13 秒；两个归档的 SHA-256 相同。`python3 tests/archive.py` 通过，且无效的 `MUJOCO_ROOT` 被拒绝。
`ctest --test-dir .local/package-build --output-on-failure -j4` 的 35 项测试全部通过。软件包模式现在仅构建可执行文件与适配器目标；需要重新构建测试目标时使用开发构建与 CTest。

运行 `python3 tests/config_modes.py` 可检查两个配置边界：修改软件包选择不会改变 `./launch.sh --show-config` 的结果，而开发设置及 `.env` 不会改变软件包构建所选的 MuJoCo 根目录。2026-11-16 的检查与 `python3 tests/build_env.py` 均通过；完整输出位于已忽略的 `data/test/20261116-config-mode-isolation/checks.log`。

2026-11-19，`cmake --build .local/package-build --target mujoco-eos-node -j2`、`ctest --test-dir .local/package-build -R '^eos-node-plugin' --output-on-failure` 和 `clang-format --dry-run --Werror src/plugin/node.cpp` 通过。四项插件边界测试覆盖在桩服务模拟器状态序号固定时，原生与 RoboCasa 相机分别发布两帧，以及 RGB 负载无效时拒绝、命令、服务故障和 Stop。完整输出位于忽略目录 `data/test/20261119-camera-sample-sequence/`。这些源码检查不发布软件包版本。

<a id="设计验证"></a>

### 设计验证

从 MuJoCo 仓库根目录运行 `git diff --check`，并检查四个改动 Markdown 文件的相对链接，均通过，断链为零。使用同级 IsOS 仓库的 `scripts/check_doc_links.py` 检查全部 58 个 Markdown 文件时，发现五个本次改动之外的已有锚点错误。日志和检查命令保存在被忽略的 `data/test/20261115-interaction-node-roles/`。

## 相机尺寸验收记录

2026-11-13，`0.2.3` 源码候选版使用 IsOS PR #504 的 EOS 命令确认修复，通过隔离的 `isos pkg check`。设置 `ISOS_AETHER_BIN_DIR` 指向已修复的 EOS 可执行文件，并提供本机 EI 与 MuJoCo 路径，当时运行 `isos pkg check --source <本源码目录> --version 0.2.3 --output <空证据目录> --graph <锁定 0.2.3 的 RoboCasa 完整预设图> --graph <锁定 0.2.3 的原生完整预设图> --package-config <本机 package.toml>`。256 × 192 和 512 × 512 两种配置均通过静态验证、原生 ABI、所有者准入、托管观测／控制／日志及两套预设的确认停止；RoboCasa 三路相机帧均报告请求的尺寸。准确命令、输入、`check.json`、所有者交换和完整构建日志保存在被 Git 忽略的 `data/test/2026-11-13-camera-size/`；候选归档 SHA-256 为 `58e3d9fa8d45345d5fe9a0da5f804d016bc6fbddbcb08fcceeece32d92c0bf6f`。发布和更新图中的精确版本锁定仍需另外执行。


## R06 实现审查记录

R06 设计与负面样本见[固定用例](../tests/fixtures/strict_stop_lane/README.md)。经审查的 MuJoCo 所有者头 `212f757` 在 [PR #21](https://github.com/Island-Team/isos-mujoco-sim/pull/21) 于 `c171208` 合并前通过 24/24 项 CTest、十次排队入口期限回归，以及 R06 48 项和 R05 31 项样本检查。限定范围的 IsOS → EOS → MuJoCo 回放确认 pick-place 和 navigation 的双部件停止与清理，并将停止套接字丢失及子进程崩溃判为未知。[证据与可复现命令](#r06-停止通道设计目标)记录精确范围。强制超时/KILL、GUI 不可用、过期或错误管道及崩溃恢复仍属于更完整的 R06 验收；此次包合并不发布 `0.1.1` 标签。


## 软件包资格验证证据 — 2026 年 11 月 20 日

2026-11-20，`./build.sh --output <empty-directory>` 成功构建 schema 0.2.2 候选包；使用 `cmake --build .local/package-build --parallel 4` 和 `ctest --test-dir .local/package-build --output-on-failure -j4`，全部 35 项 CTest 通过。上述专项检查通过，`python3 tests/eos_contracts.py --eos-profile <isos-p>/target/debug/aether-profile --plugin .local/package-build/libmujoco-eos-node.so --output <evidence>/eos-contracts` 通过 21 项 EOS 图准入和九项载荷 schema 检查。EOS 检查使用所有者本地图投影。完整日志位于忽略目录 `data/test/20261120-package-contract/`。这些结果不构成图 0.3.1 软件包发行资格证明。

2026-11-20，干净源码候选提交 `2af08df93d3fdbc96421700cbe0217da2f964284` 使用 IsOS PR #551 的图 0.3.1 回放修复，通过 `isos pkg check --source <checkout> --version 0.2.8 --output <empty evidence directory> --graph <native full-preset graph> --graph <RoboCasa full-preset graph> --package-config <local package.toml>`。两个完整预设均通过静态验证、原生 ABI、所有者准入、托管观测与命令、拒绝和重复命令检查、日志、子进程失败、套接字清理与已确认 Stop。图将每个执行器的命令输入显式绑定至仅供 API 使用的 Dispatcher 部件。将 `MUJOCO_ROOT`、`ISOS_AETHER_BIN_DIR`、`ISOS_EI_BIN_DIR`、`ISOS_EI_FACTORY_DEFAULTS_DIR` 和 `EI_PYTHON` 设置为已准备的本地依赖。完整输入与日志保存在忽略目录 `data/test/20261120-package-merge/check-031-v4/`；`check.json` 记录 `qualified:true`，归档 SHA-256 为 `eb94665a6ca516e74ae0394342e0b286d6eaaa93665096b4913a1ed9b56d68dc`。这些证据验证本地源码候选；发行发布与不可变目录工件仍是独立步骤。
