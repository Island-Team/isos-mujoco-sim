# 场景运行与集成

**状态：** 场景引擎、分帧套接字、包拥有的 P02 场景/设备目录及 IsOS P02/P03 准入和选项均已实现。R05 严格启动与健康集成已在固定版本的 IsOS → EOS → MuJoCo 回放中通过限定范围验收。R06 物理停止协调、实时受管理运动及完整 M3 控制验收仍待完成。产品版本 `0.1.1` 不代表套接字协议 `2.0.0` 是产品发布版本。

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

新的 `sim-hardware` 预设在 EOS core 中有七个节点，并使用 IsOS 初始图已有的 dispatcher control 节点。硬件节点采用 EOS 通用 `@v0.1` 注册类型和精确锁定包的 `mujoco-v2` 适配器；MuJoCo 只贡献进程类型。此前验证过的旧 sidecar 仍按旧图行为可读；新预设不包含旧 `@v1.0` 类型或未注册的 IsOS Vision 类型。P03 拥有通用 `(node_path,setting)` 选项分组与 UI 回显。R05 在受管理严格模式下校验精确设备与操作；直接启动的旧模式仍保留忽略 `node` 的历史行为。详见 [P02 包契约](interfaces/package_cn.md#p02-描述符扩展)与[固定样本](../../tests/fixtures/scene_catalog/README.md)。

设计审查样本检查解析四个 JSON 文件、核对目标/旧格式判别结构和固定诊断组合、对仓库中的两个场景 XML 求哈希、验证声明的 profile 标记与设备/场景关系，并检查相对 Markdown 链接。完整输出记于 `logs/test/20261101-p02-design/fixture-doc-check.log`。实现回放使用 `python3 tests/scene_catalog.py`、`python3 tests/node_contributions.py`、`python3 tests/release.py`、`cmake -S . -B build-p02 -DMUJOCO_ROOT=<MuJoCo 3.16.0 绝对目录>`、`cmake --build build-p02 -j4`、`ctest --test-dir build-p02 --output-on-failure`，以及 `python3 tools/build-backend-bundle.py --build-dir build-p02 --output logs/test/20261101-p02-scene-catalog/bundle`。在 Linux x86_64 与 MuJoCo 3.16.0 环境，12/12 项 CTest 通过，包含真实场景引擎加载、回放及归档构建；暂存包含两个带哈希的场景、三个有描述的设备、两个进程类型标识和七节点预设。完整输出位于 `logs/test/20261101-p02-scene-catalog/`。先前 IsOS P01 程序的严格解码器只接受旧字段，因此当时新描述符的跨仓库链接探测被拒绝（`isos-p01-link.log`）；后续 IsOS P02 切片已解决此依赖，下方 R05 干净主目录回放可证。

## 目标命令与日志算法

**R05 模拟器实现。** [套接字契约](interfaces/socket_cn.md)拥有精确的标志、健康字段、边界、错误码及保留期。IsOS 生成配置为 EOS 管理的启动选择已验证包和场景。EOS 根据管理关系推导 `--managed-strict-socket`，而不是从图可写设置读取。严格模式拒绝历史 gRPC `SimulatorService` 与 benchmark 套接字参数；否则 `SimulatorService.Execute` 会成为绕过 Dispatcher 的第二条执行器路线，而 benchmark Reset/Step 也能改变同一引擎状态。可信评测器使用独立直接启动。不带标志的直接启动保留线协议 `2.0.0` 下现有的旧帧、gRPC 和 benchmark 行为。

严格就绪须端到端核对，不能仅依赖连接成功。EOS 探测图中每个已声明的场景设备，检查协议版本、回显请求 ID、正面的 `ok` 与 `accepted`，以及响应特性列表中的 `strict-socket-v1`。模拟器只有能执行精确设备/操作匹配、有限的有类型运动限制与有界 ID 后，才绑定严格帧监听器。子进程遗漏或矛盾地公告特性时，EOS 拒绝并回收。EOS 的 `BackendChild::wait_ready` 与适配器健康现已在发布就绪前要求精确特性；固定版本的真实子进程回放覆盖了两个场景。

对于有效运动或 `stop`，服务在调用引擎前保留 `(node,command_id)`，整个子进程代际都记录规范化的有类型操作指纹和结果。相同传输重发以新传输请求 ID 返回旧结果；冲突返回 `command_id_conflict`。并发重复请求不能下发两次。固定的运动容量与预留停止容量拒绝新命令，不能驱逐键；也不能因 TTL 过期而允许同一子进程内重放。有界进程内保留不能代替 EOS 的持久 Dispatcher 日志：断线、超时或重启后，结果不确定的已下发命令保持未知，EOS 要从新观察核对或要求新的显式准入。受管理服务校验 `node` 与 `command_id`，并串行接受连接；R05 不声称停止可抢占。R06 必须增加专用有界停止通道和分别确认，才能在终止/回收子进程前声称安全停止。

启动时只记录一次含包、场景 ID、协议和 `run_id` 的净化 JSONL 事件；随后在就绪变化、命令准入/结果、套接字故障和关闭时记录。不记录图像字节、任意环境变量或每个高频观察。首次使用者先看当前运行的首条就绪/失败事件，再按规范 `node_path` 和 `correlation_id` 筛选。共享事件格式、轮转和游标读取由 IsOS 定义；本包提供来源 `mujoco` 及自身事件码。

**R05 设计证据：** [31 个固定用例](../../tests/fixtures/strict_socket/cases.json)覆盖直接启动兼容、严格启动隔离、健康证明、设备/操作匹配、有类型边界、重复/冲突/容量、畸形帧和 EOS 不重放。2026-11-02 执行 `python3 tests/fixtures/strict_socket/check.py`、`python3 tests/scene_catalog.py`、`python3 tests/node_contributions.py`、`python3 tests/release.py` 与 `git diff --check` 均通过；完整命令和输出见被 Git 忽略的 `logs/test/20261102-r05-strict-design/design-check.log`。这些记录设计门；运行时验证和配套 EOS 严格客户端资格验证另见下文。

**R05 模拟器实现证据：** 在 Linux x86_64、GCC 13.3 和 MuJoCo 3.16.0 环境，执行 `cmake -S . -B build -DMUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0`、`cmake --build build -j4` 和 `ctest --test-dir build --output-on-failure`。初次实现门禁 16 项 CTest 全部通过；最终独立审查门禁 18/18 通过，包含真实严格套接字启动/负面请求、65,536 个运动键、4,096 个预留停止键、不确定结果保留，以及旧 v2/gRPC/benchmark 兼容。固定设计、目录/声明/发布检查、Python 编译和 `git diff --check` 均通过。完整输出见忽略的 `logs/test/20261102-r05-strict-impl/gates.log` 与 `logs/test/20261102-r05-strict-review-fixes/gates.log`。C++ 设备表由包拥有的 P02 目录生成，与已加载引擎 profile 取交集；引擎检查已加载关节范围。EOS 严格客户端与不重放证据记于下方跨所有者验收；R06 抢占停止仍待完成。

**R05 实现审查修复：** 重复运动/停止响应保留原来的 `timestamp_ns`、`sequence`、准入与错误，仅更换传输 `id`。真实双客户端重发测试核对两个响应，并证明后续重复请求不会重启物理底盘租期。严格相机健康在公告特性前渲染一帧；测试专用 EGL 预加载强制失败并验证 `device_unavailable`。最终门禁命令和结果见忽略的 `logs/test/20261102-r05-strict-review-fixes/gates.log`。

## R05 跨所有者验收

EOS 中封存的 `logs/test/20261102-r05-cross-owner-qualifier/qualification.md` 与独立 `reviewer-verdict.md` 固定于 EOS `9701a4d449249a3cd90bd5bd8d2ba98809d59435`、MuJoCo `41e17107b7c7abe43cd29cc388b7dd157979d476`、IsOS `1db1aa52df959f06e7c494797edd09a2b5289bcf`。其 85 个封存文件已通过 `sha256sum -c evidence.sha256`；同目录的 `commands.txt` 和完整日志可复现检查。审查者批准在常规 PR 检查及状态文档更新后完成限定范围的 R05 所有者条目。

两个全新 IsOS 主目录链接精确包，选择 pick-place 与 navigation，Validate、Apply 后由 EOS 启动已验证的直接子进程。两个场景均通过相机、底盘、机械臂严格健康检查、只读拍摄和观察、就绪事件顺序及子进程/套接字/授权清理。pick-place 回放覆盖两代进程并拒绝旧授权。负面检查拒绝错误场景、错误设备和被篡改的链接资源，且保存及活动状态不变。MuJoCo 严格 CTest 重点测试 7/7、EOS 线协议 8/8、进程 16/16、两个真实场景的子进程及持久日志中不重放不确定命令的检查均通过。MuJoCo 适配器尚无 `has_terminal_stop_fence`，所以实时 EOS 目录只公开 `safety.estop`，在 Submit 前隐藏 `base.velocity` 与 `arm.movej`；回放没有下发受管理运动。R06 须证明物理停止屏障、专用停止通道、底盘/机械臂分别确认及安全终止顺序，才能宣称完整 M3 首次使用控制通过。

## R06 停止通道设计目标

[所有者套接字契约](interfaces/socket_cn.md#r06-受管理停止契约设计目标)固定新增字段、稳定错误码、1000 ms 停止期限、每连接 250 ms 入口期限和 `strict-stop-v1` 特性。[48 个设计用例](../../tests/fixtures/strict_stop_lane/cases.json)固定故障、并发及生命周期行为。本分支现有实现候选；三个入口工作线程的变更仍需独立设计复审，独立实现审查及跨所有者安全停止验收仍未完成。

受管理主监听器最多使用 32 个普通工作槽和 8 个入口槽。它从既有路径推导独立、仅所有者可访问的 `.stop` 套接字，后者具有自己的监听器、三个停止入口工作线程、从 accept 起计算的 250 ms 部分帧到期机制和一个预留停止执行槽。伴随监听器只解析 `health` 与 `stop`；EOS 探测其健康，并把所有受管停止发送到此处。主入口中八条阻塞连接不能占用伴随槽。若此前只有两个部分停止帧且没有其他排队者，第三个工作线程可在有效停止连接后的自身 250 ms 入口期限内完成分类，保持 500 ms 分类上界；若三个较早的部分帧占满入口，第四帧可能在队列中到期，停止结果为未知。不能用脱离管理的线程或无限制的客户分配持有引擎状态。停止通道在预留时记录新的引擎停止 epoch，使两个运动租期及旧命令令牌失效，再在短时引擎命令状态锁内分别保持底盘和机械臂。每个受管理子进程启动时还生成全新的 128 位 `generation_id`；两个健康路径都返回它，EOS 在每次受管理运动和伴随停止中回传。即使旧代请求的 epoch 与新代初始 `"0"` 相同，旧代延迟请求仍以 `stale_generation` 拒绝。每个受管理运动还携带当前 `stop_epoch` 前提，初始值为 `"0"`；引擎在同一锁内写目标前复核。比较**新键**的 epoch 前须先查询运动日志：相同旧键的重发在停止后仍返回原结果，旧键改变 epoch 则报冲突。屏障前已提交的运动可能之后才返回响应，但停止必须覆盖其目标之后才能确认；已排队的旧运动返回 `command_interrupted`，屏障后才解析的延迟**新键**旧帧返回 `stop_fenced`。这是 EOS `has_terminal_stop_fence` 所需的次序证明，旧响应中的 `accepted` 位不足以证明。

渲染须在短时命令状态锁内取得有界不可变状态快照，随后使用独立、有界的渲染上下文。停止取消排队拍摄，并屏蔽已经渲染中的负载发布。服务器在停止预留时关闭活动 JPEG 流，并使用独立的发布闸门：成功停止须等旧流离开闸门；若流在 1000 ms 期限内仍被阻塞，停止结果为未知。固定停止执行线程可能在期限之后继续完成物理保持；响应仍为 `stop_outcome_unknown`，本代子进程的新运动持续被禁止。伴随健康检查从缓存读取身份和特性，不获取引擎互斥锁。EGL 可能无法中断；这时有界停止通道仍须到达引擎，EOS 最终强制终止并回收子进程。成功停止分别返回 `base_stop`、`arm_stop` 和 `stop_epoch`，时间戳和序号在提交之后采样。部分证明返回 `stop_outcome_unknown`；超时或丢失响应对 EOS 来说仍未知，即使子进程实际停止。相同停止重发只返回已存储字段，不重新下发。直接启动 `2.0.0` 行为不变。

**待 EOS 设计审查的跨所有者决定：** EOS 须推导并探测伴随 `.stop` 路径，比较主监听器与伴随监听器的健康代际，选择长于 500 ms 接受／分类期限加服务器 1000 ms 预算的外层单调期限，同时限制连接、完整帧读写和 SIGTERM/SIGKILL/回收阶段。每次运动须发送当前 `generation_id` 和 `stop_epoch`，每次伴随停止发送代际 ID，校验两个停止状态及返回的代际／新 epoch，紧急停止前关闭 Dispatcher 准入，防止延迟下发在停止后到达适配器；缺少任一证明时记为 `OutcomeUnknown`。之后明确授权的非锁存控制停止可以允许携带新已证明 epoch 的命令；紧急关闭保持拒绝准入。在特性和终态屏障通过验收前，实时运动能力不得进入公开目录。IsOS 须在包／套接字选择时预检推导出的伴随路径长度，按相反依赖顺序停止 EGIA/EOS 进程组；EOS 报未知时，IsOS 不能宣称完成安全停止。模拟器自身不能证明 EOS 次序或 IsOS 进程生命周期。

**R06 仅设计证据，2026-11-02：** `python3 tests/fixtures/strict_stop_lane/check.py` 验证了 47 个唯一目标用例及中英文契约标记。R05 样本检查、场景目录 8 项、节点声明 5 项、发布检查 1 项、Python 编译和 `git diff --check` 均通过。完整命令与输出在被 Git 忽略的 `logs/test/20261102-r06-stop-design/design-check.log`。本设计提交不含 C++ 实现，也不宣称运行时停止通过；下一步是独立设计审查及 EOS 适配器协议确认。

**R06 实现候选证据，2026-11-02：** 在 Linux x86_64、GCC 13.3、MuJoCo 3.16.0 环境运行 `cmake -S . -B build -DMUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0`、`cmake --build build -j4`、`ctest --test-dir build --output-on-failure`；初始 21 项 CTest 全部通过，包括 R05 兼容用例、pick-place/navigation 真实停止套接字、八条阻塞主入口帧、两条阻塞伴随入口帧、跨进程代际拒绝、停止后旧键重发、引擎层延迟写屏障及活动机械臂中断，以及拍摄快照后阻塞图形调用时停止仍完成且旧帧被丢弃。独立审查发现三处 P1 竞态；后续增加确定性的引擎阻塞、伴随健康及 JPEG 发布测试，完整 23 项结果记录在 `logs/test/20261102-r06-strict-stop-review-fixes/`。进一步审查发现 250 ms 入口计时器在队列出队之后才启动。修正后，每个队列条目都携带从 accept 起计算的绝对期限，最后一次读取后再次检查到期，并把伴随入口增至三个工作线程，使此前两个部分帧不能耗尽有效停止的入口预算。新增测试用三个部分帧占满所有工作线程，确认第四个部分帧已被接受，再暂停子进程至原期限之后，验证恢复后立即关闭，并验证此前两个部分帧之后的有效停止分类。完整 24 项 CTest、R06/R05 样本、Python 编译及差异检查记录在被 Git 忽略的 `logs/test/20261102-r06-strict-stop-accept-deadline/`；三个工作线程的契约仍需独立设计复审。初始完整输出及精确命令在被 Git 忽略的 `logs/test/20261102-r06-strict-stop-implementation/`。此候选不是 EOS 安全停止验收：独立实现复审及 EOS/IsOS 跨所有者回放仍需核验 Dispatcher 准入关闭、双重证明解释、子进程终止和回收。

[English](../../docs/mujoco/design.md) · [使用指南](usage_cn.md)

一个模拟器进程在启动时加载一个场景。引擎持有 MuJoCo 模型与数据、带种子的确定性重置、固定步长物理计算、机器人命令目标、遥测、相机渲染和场景评分。EOS 面向机器人的接口与可信评测接口共享引擎，但发布不同的信息。评测器可以重置、步进、读取真实状态与评分；代理只能通过 EOS 使用已声明的观察和动作。

直接运行以 `--scene` 选场景；当前 IsOS/EOS v2 部署在已应用的共享图中选择场景，EOS 将路径传给其模拟器子进程。MJCF 必须且只能包含一个支持的自定义数值标记：`eos_benchmark_pick_place_v1` 或 `eos_benchmark_navigation_v1`。引擎还验证必要命名元素，包括导航场景的 `navigation_goal`。可加载的任意 XML 不会自动成为受支持的评测场景；新场景需要明确的重置、评分、能力和测试。更换场景需要重启进程。

模拟器仍提供旧版 `eos.simulator.v1.SimulatorService` gRPC 套接字，供旧的直接集成使用。当前 IsOS/EOS v2 运行时使用独立的、仅所有者可访问的帧格式套接字，由 `--v2-socket` 指定；契约见 [backend_cn.md](backend_cn.md)。EOS 持有模拟器子进程，将图中声明的观察与 primitive 端口交给代理。benchmark 套接字与两种机器人接口均分离。此软件包不链接到 EOS core。

EGIA 连接已运行的 EOS，发现健康设备和版本化 primitive，并通过 EOS 执行。它不能获得评测种子、目标真值、特权状态或评分。代理评测将通过 EOS 可见的行为与独立评测器的私有结果比较。

已发布的 v1.0.1 包及其生成的 EOS profile 属于旧路线。v2 中，IsOS 链接或安装精确的 `island/mujoco-sim@0.1.1` 包，检查可执行文件、场景、资源和外部 MuJoCo 库，并通过 `sim-hardware` 节点集应用共享图修订。EOS 读取该图，并将经校验的模拟器作为直接子进程启动。源码构建仍可用绝对场景与套接字路径直接运行。

## 时间与故障

MuJoCo 以固定的 2 毫秒物理步长推进。重置将场景置于确定性的带种子初始状态并暂停实时推进。评测器可以推进有界步数、检查状态、评分，再恢复实时运行。可重复性要求相同的场景版本、种子、命令序列和步进安排；异步实时观察不保证确定性重放。

缺少或无效的场景、必要元素缺失或套接字不可用都会导致启动失败。不可用设备与命令通过 EOS 面向机器人的接口报错。benchmark 服务在 `StateResponse.ok` 和 `error` 中报告重置或步进错误。与当前场景无关的真实状态字段不能用作代理输入，也不能推断为目标。
