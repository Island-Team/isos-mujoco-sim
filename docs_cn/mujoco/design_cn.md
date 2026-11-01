# 场景运行与集成

**状态：** 场景引擎、分帧套接字和包拥有的 P02 场景/设备目录已实现。EOS 与 IsOS 已有 M1 多版本图读取器；IsOS P02 语义准入、P03 选项解析器、MuJoCo R05 严格套接字已实现；EOS 严格客户端集成与 R06 停止协调仍是独立工作。产品版本 `0.1.1` 不代表套接字协议 `2.0.0` 是产品发布版本。

所有者契约见[包描述符与声明](interfaces/package_cn.md)、[EOS 持有的套接字](interfaces/socket_cn.md)和[评测 RPC](../../docs/mujoco/interfaces/benchmark.md)。本页描述算法，不重复负载定义。

## 目标激活算法

1. IsOS 获取精确的 P01 已验证包句柄，检查 P02 场景 profile、XML 校验值、设备映射、逐场景设备支持和外部 MuJoCo 库，然后只把稳定 ID 与不可用原因交给后续 P03 选项解析器。安装包不编辑图。
2. 操作员预览 `sim-hardware`，选择稳定场景/设备 ID，检查草稿并应用一个修订。IsOS 在生成配置中解析验证过的路径；图保留 ID 和精确包锁定。旧 `1.0.0` 图与 `@v1.0` 类型仍可读；所有读取方支持后，新建图使用 `0.1.0`，新注册类型使用 `@v0.1`。
3. EOS 不编辑已应用修订，选择编译在内部的 `mujoco-v2` 适配器工厂，带 R05 管理严格启动标志把已验证模拟器作为直接子进程。严格校验及历史 gRPC 执行器监听器关闭前，子进程不得公告 `strict-socket-v1`。EOS 对每个已声明设备要求严格健康特性之后才发布就绪。健康失败或设备不匹配使节点不可用，并记录 `run_id`、可选 `node_path` 和 `correlation_id`。
4. Dispatcher 先准入执行器命令，适配器再发送。EOS 验证图节点、设备类别、场景和包锁定；模拟器检查精确的设备/操作组合及有限的场景边界，再按 `(node,command_id)` 去重，防止有界传输重发重复执行。EOS 绝不自动重放结果不确定的已下发命令。R06 的专用停止通道和分别确认底盘/机械臂仍是安全停止资格验证的前提。
5. 关闭时 EOS 先停止新命令准入，再以有界期限要求所有已准入执行器停止，记录未确认情况，最后终止并回收子进程。EOS 退出或记录有界强制停止后，IsOS 才报告部署已停止。模拟器正常退出会清理仅所有者可访问的套接字。

## P02 目录生成与兼容

构建工具保留人工定义的稳定场景 ID，从打包的 XML 字节导出其校验值，并根据引擎支持的相机、底盘与机械臂模型元素核对设备目录。确定性样本固定预期 profile 标记、三台设备 ID 和包拥有的进程类型。声明的标记不等于 XML 中唯一标记、模型缺少设备所需元素或场景/设备 ID 重复时，构建或候选包失败。真实 MuJoCo 引擎加载与重放测试证明 XML 仍可运行；仅 XML 目录检查不足以证明模型兼容。

IsOS 先运行 P01 收据与路径验证，再解析精确验证过的描述符。精确的 `catalog_version:"0.1.0"` 判别字段要求完整场景和设备元数据；缺失时必须是完整旧结构。部分混合在发布选项前失败。IsOS 比较所选场景 ID、声明的 profile 和 XML 哈希，核对设备 ID、类别与场景，且在发布图或启动前检查外部库。可修复的草稿显示不可用选项；Apply 用契约规定的稳定 `{code,path,stage}` 诊断拒绝不可用的所选值。Run 与 Restart 再次验证；已链接载荷变化要求显式重新链接，不能静默更新运行中图。场景编辑使用 IsOS 修订 compare-and-swap，只有保存新修订并 Restart 后才进入 EOS。

新的 `sim-hardware` 预设在 EOS core 中有七个节点，并使用 IsOS 初始图已有的 dispatcher control 节点。硬件节点采用 EOS 通用 `@v0.1` 注册类型和精确锁定包的 `mujoco-v2` 适配器；MuJoCo 只贡献进程类型。此前验证过的旧 sidecar 仍按旧图行为可读；新预设不包含旧 `@v1.0` 类型或未注册的 IsOS Vision 类型。P03 拥有通用 `(node_path,setting)` 选项分组与 UI 回显。R05 拥有受管理套接字的设备/操作校验；当前套接字忽略 `node`，因此 P02 元数据本身不能证明命令路由安全。详见 [P02 包契约](interfaces/package_cn.md#p02-描述符扩展)与[固定样本](../../tests/fixtures/scene_catalog/README.md)。

设计审查样本检查解析四个 JSON 文件、核对目标/旧格式判别结构和固定诊断组合、对仓库中的两个场景 XML 求哈希、验证声明的 profile 标记与设备/场景关系，并检查相对 Markdown 链接。完整输出记于 `logs/test/20261101-p02-design/fixture-doc-check.log`。实现回放使用 `python3 tests/scene_catalog.py`、`python3 tests/node_contributions.py`、`python3 tests/release.py`、`cmake -S . -B build-p02 -DMUJOCO_ROOT=<MuJoCo 3.16.0 绝对目录>`、`cmake --build build-p02 -j4`、`ctest --test-dir build-p02 --output-on-failure`，以及 `python3 tools/build-backend-bundle.py --build-dir build-p02 --output logs/test/20261101-p02-scene-catalog/bundle`。在 Linux x86_64 与 MuJoCo 3.16.0 环境，12/12 项 CTest 通过，包含真实场景引擎加载、回放及归档构建；暂存包含两个带哈希的场景、三个有描述的设备、两个进程类型标识和七节点预设。完整输出位于 `logs/test/20261101-p02-scene-catalog/`。当前 IsOS P01 程序的严格解码器只接受旧字段，因此新描述符的跨仓库链接探测被拒绝（`isos-p01-link.log`）；IsOS 干净主目录准入须由其 P02 配套切片实现。

## 目标命令与日志算法

**R05 模拟器实现。** [套接字契约](interfaces/socket_cn.md)拥有精确的标志、健康字段、边界、错误码及保留期。IsOS 生成配置为 EOS 管理的启动选择已验证包和场景。EOS 根据管理关系推导 `--managed-strict-socket`，而不是从图可写设置读取。严格模式拒绝历史 gRPC `SimulatorService` 与 benchmark 套接字参数；否则 `SimulatorService.Execute` 会成为绕过 Dispatcher 的第二条执行器路线，而 benchmark Reset/Step 也能改变同一引擎状态。可信评测器使用独立直接启动。不带标志的直接启动保留线协议 `2.0.0` 下现有的旧帧、gRPC 和 benchmark 行为。

严格就绪须端到端核对，不能仅依赖连接成功。EOS 探测图中每个已声明的场景设备，检查协议版本、回显请求 ID、正面的 `ok` 与 `accepted`，以及响应特性列表中的 `strict-socket-v1`。模拟器只有能执行精确设备/操作匹配、有限的有类型运动限制与有界 ID 后，才绑定严格帧监听器。子进程遗漏或矛盾地公告特性时，EOS 拒绝并回收。EOS 的 `BackendChild::wait_ready` 与适配器健康仍是严格客户端配套入口；发布就绪前必须核对精确特性。

对于有效运动或 `stop`，服务在调用引擎前保留 `(node,command_id)`，整个子进程代际都记录规范化的有类型操作指纹和结果。相同传输重发以新传输请求 ID 返回旧结果；冲突返回 `command_id_conflict`。并发重复请求不能下发两次。固定的运动容量与预留停止容量拒绝新命令，不能驱逐键；也不能因 TTL 过期而允许同一子进程内重放。有界进程内保留不能代替 EOS 的持久 Dispatcher 日志：断线、超时或重启后，结果不确定的已下发命令保持未知，EOS 要从新观察核对或要求新的显式准入。受管理服务校验 `node` 与 `command_id`，并串行接受连接；R05 不声称停止可抢占。R06 必须增加专用有界停止通道和分别确认，才能在终止/回收子进程前声称安全停止。

启动时只记录一次含包、场景 ID、协议和 `run_id` 的净化 JSONL 事件；随后在就绪变化、命令准入/结果、套接字故障和关闭时记录。不记录图像字节、任意环境变量或每个高频观察。首次使用者先看当前运行的首条就绪/失败事件，再按规范 `node_path` 和 `correlation_id` 筛选。共享事件格式、轮转和游标读取由 IsOS 定义；本包提供来源 `mujoco` 及自身事件码。

**R05 设计证据：** [31 个固定用例](../../tests/fixtures/strict_socket/cases.json)覆盖直接启动兼容、严格启动隔离、健康证明、设备/操作匹配、有类型边界、重复/冲突/容量、畸形帧和 EOS 不重放。2026-11-02 执行 `python3 tests/fixtures/strict_socket/check.py`、`python3 tests/scene_catalog.py`、`python3 tests/node_contributions.py`、`python3 tests/release.py` 与 `git diff --check` 均通过；完整命令和输出见被 Git 忽略的 `logs/test/20261102-r05-strict-design/design-check.log`。这些记录设计门；运行时验证和配套 EOS 严格客户端资格验证另见下文。

**R05 模拟器实现证据：** 在 Linux x86_64、GCC 13.3 和 MuJoCo 3.16.0 环境，执行 `cmake -S . -B build -DMUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0`、`cmake --build build -j4` 和 `ctest --test-dir build --output-on-failure`。16 项 CTest 全部通过，包含真实严格套接字启动/负面请求、65,536 个运动键、4,096 个预留停止键、不确定结果保留，以及旧 v2/gRPC/benchmark 兼容。固定设计、目录/声明/发布检查、Python 编译和 `git diff --check` 均通过。完整输出见忽略的 `logs/test/20261102-r05-strict-impl/gates.log`。C++ 设备表由包拥有的 P02 目录生成，与已加载引擎 profile 取交集；引擎检查已加载关节范围。EOS 严格客户端启动/就绪、不确定命令不重放及 R06 抢占停止仍需配套切片。

[English](../../docs/mujoco/design.md) · [使用指南](usage_cn.md)

一个模拟器进程在启动时加载一个场景。引擎持有 MuJoCo 模型与数据、带种子的确定性重置、固定步长物理计算、机器人命令目标、遥测、相机渲染和场景评分。EOS 面向机器人的接口与可信评测接口共享引擎，但发布不同的信息。评测器可以重置、步进、读取真实状态与评分；代理只能通过 EOS 使用已声明的观察和动作。

直接运行以 `--scene` 选场景；当前 IsOS/EOS v2 部署在已应用的共享图中选择场景，EOS 将路径传给其模拟器子进程。MJCF 必须且只能包含一个支持的自定义数值标记：`eos_benchmark_pick_place_v1` 或 `eos_benchmark_navigation_v1`。引擎还验证必要命名元素，包括导航场景的 `navigation_goal`。可加载的任意 XML 不会自动成为受支持的评测场景；新场景需要明确的重置、评分、能力和测试。更换场景需要重启进程。

模拟器仍提供旧版 `eos.simulator.v1.SimulatorService` gRPC 套接字，供旧的直接集成使用。当前 IsOS/EOS v2 运行时使用独立的、仅所有者可访问的帧格式套接字，由 `--v2-socket` 指定；契约见 [backend_cn.md](backend_cn.md)。EOS 持有模拟器子进程，将图中声明的观察与 primitive 端口交给代理。benchmark 套接字与两种机器人接口均分离。此软件包不链接到 EOS core。

EGIA 连接已运行的 EOS，发现健康设备和版本化 primitive，并通过 EOS 执行。它不能获得评测种子、目标真值、特权状态或评分。代理评测将通过 EOS 可见的行为与独立评测器的私有结果比较。

已发布的 v1.0.1 包及其生成的 EOS profile 属于旧路线。v2 中，IsOS 链接或安装精确的 `island/mujoco-sim@0.1.1` 包，检查可执行文件、场景、资源和外部 MuJoCo 库，并通过 `sim-hardware` 节点集应用共享图修订。EOS 读取该图，并将经校验的模拟器作为直接子进程启动。源码构建仍可用绝对场景与套接字路径直接运行。

## 时间与故障

MuJoCo 以固定的 2 毫秒物理步长推进。重置将场景置于确定性的带种子初始状态并暂停实时推进。评测器可以推进有界步数、检查状态、评分，再恢复实时运行。可重复性要求相同的场景版本、种子、命令序列和步进安排；异步实时观察不保证确定性重放。

缺少或无效的场景、必要元素缺失或套接字不可用都会导致启动失败。不可用设备与命令通过 EOS 面向机器人的接口报错。benchmark 服务在 `StateResponse.ok` 和 `error` 中报告重置或步进错误。与当前场景无关的真实状态字段不能用作代理输入，也不能推断为目标。
