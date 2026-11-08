# 场景运行与集成

**状态：** 场景引擎、分帧套接字、包拥有的 P02 场景/设备目录及 IsOS P02/P03 准入和选项均已实现。R05 严格启动与健康集成已在固定版本的 IsOS → EOS → MuJoCo 回放中通过限定范围验收。R06 MuJoCo 停止通道已合并，限定范围的真实 IsOS → EOS → MuJoCo 停止回放通过；更完整的 R06 故障验收及 M3 控制验收仍待完成。产品版本 `0.1.1` 不代表套接字协议 `2.0.0` 是产品发布版本。

所有者契约见[包描述符与声明](interfaces/package_cn.md)、[EOS 持有的套接字](interfaces/socket_cn.md)和[评测 RPC](../../docs/mujoco/interfaces/benchmark.md)。本页描述算法，不重复负载定义。

## 目标激活算法

1. IsOS 获取精确的 P01 已验证包句柄，检查 P02 场景 profile、XML 校验值、设备映射、逐场景设备支持和外部 MuJoCo 库，然后只把稳定 ID 与不可用原因交给后续 P03 选项解析器。安装包不编辑图。
2. 操作员预览 `sim-hardware`，选择稳定场景/设备 ID，检查草稿并应用一个修订。IsOS 在生成配置中解析验证过的路径；图保留 ID 和精确包锁定。旧 `1.0.0` 图与 `@v1.0` 类型仍可读；所有读取方支持后，新建图使用 `0.1.0`，新注册类型使用 `@v0.1`。
3. EOS 不编辑已应用修订，选择编译在内部的 `mujoco-v2` 适配器工厂，带 R05 管理严格启动标志把已验证模拟器作为直接子进程。严格校验及历史 gRPC 执行器监听器关闭前，子进程不得公告 `strict-socket-v1`。EOS 对每个已声明设备要求严格健康特性之后才发布就绪。健康失败或设备不匹配使节点不可用，并记录 `run_id`、可选 `node_path` 和 `correlation_id`。
4. Dispatcher 先准入执行器命令，适配器再发送。EOS 验证图节点、设备类别、场景和包锁定；模拟器检查精确的设备/操作组合及有限的场景边界，再按 `(node,command_id)` 去重，防止有界传输重发重复执行。EOS 绝不自动重放结果不确定的已下发命令。已合并的 R06 伴随通道提供物理屏障及底盘/机械臂分别证明；EOS 与 IsOS 仍负责关闭准入、判定回执及进程清理。
5. 关闭时 EOS 先停止新命令准入，再以有界期限要求所有已准入执行器停止，记录未确认情况，最后终止并回收子进程。EOS 退出或记录有界强制停止后，IsOS 才报告部署已停止。模拟器正常退出会清理仅所有者可访问的套接字。

## P02 目录生成与兼容

构建工具保留人工定义的稳定场景 ID，从打包的 XML 字节导出其校验值，并根据引擎支持的相机、底盘与机械臂模型元素核对设备目录。确定性样本固定预期 profile 标记、三台设备 ID 和包拥有的进程类型。声明的标记不等于 XML 中唯一标记、模型缺少设备所需元素或场景/设备 ID 重复时，构建或候选包失败。真实 MuJoCo 引擎加载与重放测试证明 XML 仍可运行；仅 XML 目录检查不足以证明模型兼容。

IsOS 先运行 P01 收据与路径验证，再解析精确验证过的描述符。精确的 `catalog_version:"0.1.0"` 判别字段要求完整场景和设备元数据；缺失时必须是完整旧结构。部分混合在发布选项前失败。IsOS 比较所选场景 ID、声明的 profile 和 XML 哈希，核对设备 ID、类别与场景，且在发布图或启动前检查外部库。可修复的草稿显示不可用选项；Apply 用契约规定的稳定 `{code,path,stage}` 诊断拒绝不可用的所选值。Run 与 Restart 再次验证；已链接载荷变化要求显式重新链接，不能静默更新运行中图。场景编辑使用 IsOS 修订 compare-and-swap，只有保存新修订并 Restart 后才进入 EOS。

新的 `sim-hardware` 预设在 EOS core 中有七个节点，并使用 IsOS 初始图已有的 dispatcher control 节点。硬件节点采用 EOS 通用 `@v0.1` 注册类型和精确锁定包的 `mujoco-v2` 适配器；MuJoCo 只贡献进程类型。此前验证过的旧 sidecar 仍按旧图行为可读；新预设不包含旧 `@v1.0` 类型或未注册的 IsOS Vision 类型。P03 拥有通用 `(node_path,setting)` 选项分组与 UI 回显。R05 在受管理严格模式下校验精确设备与操作；直接启动的旧模式仍保留忽略 `node` 的历史行为。详见 [P02 包契约](interfaces/package_cn.md#p02-描述符扩展)与[固定样本](../../tests/fixtures/scene_catalog/README.md)。

设计审查样本检查解析四个 JSON 文件、核对目标/旧格式判别结构和固定诊断组合、对仓库中的两个场景 XML 求哈希、验证声明的 profile 标记与设备/场景关系，并检查相对 Markdown 链接。完整输出记于 `logs/test/20261101-p02-design/fixture-doc-check.log`。实现回放使用 `python3 tests/catalogtest.py`、`python3 tests/nodes.py`、`python3 tests/release.py`、`cmake -S . -B build-p02 -DMUJOCO_ROOT=<MuJoCo 3.16.0 绝对目录>`、`cmake --build build-p02 -j4`、`ctest --test-dir build-p02 --output-on-failure`，以及 `python3 tools/bundle.py --build-dir build-p02 --output logs/test/20261101-p02-scene-catalog/bundle`。在 Linux x86_64 与 MuJoCo 3.16.0 环境，12/12 项 CTest 通过，包含真实场景引擎加载、回放及归档构建；暂存包含两个带哈希的场景、三个有描述的设备、两个进程类型标识和七节点预设。完整输出位于 `logs/test/20261101-p02-scene-catalog/`。先前 IsOS P01 程序的严格解码器只接受旧字段，因此当时新描述符的跨仓库链接探测被拒绝（`isos-p01-link.log`）；后续 IsOS P02 切片已解决此依赖，下方 R05 干净主目录回放可证。

## 目标命令与日志算法

**R05 模拟器实现。** [套接字契约](interfaces/socket_cn.md)拥有精确的标志、健康字段、边界、错误码及保留期。IsOS 生成配置为 EOS 管理的启动选择已验证包和场景。EOS 根据管理关系推导 `--managed-strict-socket`，而不是从图可写设置读取。严格模式拒绝历史 gRPC `SimulatorService` 与 benchmark 套接字参数；否则 `SimulatorService.Execute` 会成为绕过 Dispatcher 的第二条执行器路线，而 benchmark Reset/Step 也能改变同一引擎状态。可信评测器使用独立直接启动。不带标志的直接启动保留线协议 `2.0.0` 下现有的旧帧、gRPC 和 benchmark 行为。

严格就绪须端到端核对，不能仅依赖连接成功。EOS 探测图中每个已声明的场景设备，检查协议版本、回显请求 ID、正面的 `ok` 与 `accepted`，以及响应特性列表中的 `strict-socket-v1`。模拟器只有能执行精确设备/操作匹配、有限的有类型运动限制与有界 ID 后，才绑定严格帧监听器。子进程遗漏或矛盾地公告特性时，EOS 拒绝并回收。EOS 的 `BackendChild::wait_ready` 与适配器健康现已在发布就绪前要求精确特性；固定版本的真实子进程回放覆盖了两个场景。

对于有效运动或 `stop`，服务在调用引擎前保留 `(node,command_id)`，整个子进程代际都记录规范化的有类型操作指纹和结果。相同传输重发以新传输请求 ID 返回旧结果；冲突返回 `command_id_conflict`。并发重复请求不能下发两次。固定的运动容量与预留停止容量拒绝新命令，不能驱逐键；也不能因 TTL 过期而允许同一子进程内重放。有界进程内保留不能代替 EOS 的持久 Dispatcher 日志：断线、超时或重启后，结果不确定的已下发命令保持未知，EOS 要从新观察核对或要求新的显式准入。受管理服务校验 `node` 与 `command_id`，并串行接受连接；R05 不声称停止可抢占。已合并的 R06 子进程提供专用有界停止通道和分别确认；某次停止能否称为已确认，仍取决于 EOS/IsOS 的回执及子进程清理。

启动时只记录一次含包、场景 ID、协议和 `run_id` 的净化 JSONL 事件；随后在就绪变化、命令准入/结果、套接字故障和关闭时记录。不记录图像字节、任意环境变量或每个高频观察。首次使用者先看当前运行的首条就绪/失败事件，再按规范 `node_path` 和 `correlation_id` 筛选。共享事件格式、轮转和游标读取由 IsOS 定义；本包提供来源 `mujoco` 及自身事件码。

**R05 设计证据：** [31 个固定用例](../../tests/fixtures/strict_socket/cases.json)覆盖直接启动兼容、严格启动隔离、健康证明、设备/操作匹配、有类型边界、重复/冲突/容量、畸形帧和 EOS 不重放。2026-11-02 执行 `python3 tests/fixtures/strict_socket/check.py`、`python3 tests/catalogtest.py`、`python3 tests/nodes.py`、`python3 tests/release.py` 与 `git diff --check` 均通过；完整命令和输出见被 Git 忽略的 `logs/test/20261102-r05-strict-design/design-check.log`。这些记录设计门；运行时验证和配套 EOS 严格客户端资格验证另见下文。

**R05 模拟器实现证据：** 在 Linux x86_64、GCC 13.3 和 MuJoCo 3.16.0 环境，执行 `cmake -S . -B build -DMUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0`、`cmake --build build -j4` 和 `ctest --test-dir build --output-on-failure`。初次实现门禁 16 项 CTest 全部通过；最终独立审查门禁 18/18 通过，包含真实严格套接字启动/负面请求、65,536 个运动键、4,096 个预留停止键、不确定结果保留，以及旧 v2/gRPC/benchmark 兼容。固定设计、目录/声明/发布检查、Python 编译和 `git diff --check` 均通过。完整输出见忽略的 `logs/test/20261102-r05-strict-impl/gates.log` 与 `logs/test/20261102-r05-strict-review-fixes/gates.log`。C++ 设备表由包拥有的 P02 目录生成，与已加载引擎 profile 取交集；引擎检查已加载关节范围。EOS 严格客户端与不重放证据记于下方跨所有者验收；在这一 R05 门禁时，R06 抢占停止仍待完成；后续合并证据见下文。

**R05 实现审查修复：** 重复运动/停止响应保留原来的 `timestamp_ns`、`sequence`、准入与错误，仅更换传输 `id`。真实双客户端重发测试核对两个响应，并证明后续重复请求不会重启物理底盘租期。严格相机健康在公告特性前渲染一帧；测试专用 EGL 预加载强制失败并验证 `device_unavailable`。最终门禁命令和结果见忽略的 `logs/test/20261102-r05-strict-review-fixes/gates.log`。

## R05 跨所有者验收

EOS 中封存的 `logs/test/20261102-r05-cross-owner-qualifier/qualification.md` 与独立 `reviewer-verdict.md` 固定于 EOS `9701a4d449249a3cd90bd5bd8d2ba98809d59435`、MuJoCo `41e17107b7c7abe43cd29cc388b7dd157979d476`、IsOS `1db1aa52df959f06e7c494797edd09a2b5289bcf`。其 85 个封存文件已通过 `sha256sum -c evidence.sha256`；同目录的 `commands.txt` 和完整日志可复现检查。审查者批准在常规 PR 检查及状态文档更新后完成限定范围的 R05 所有者条目。

两个全新 IsOS 主目录链接精确包，选择 pick-place 与 navigation，Validate、Apply 后由 EOS 启动已验证的直接子进程。两个场景均通过相机、底盘、机械臂严格健康检查、只读拍摄和观察、就绪事件顺序及子进程/套接字/授权清理。pick-place 回放覆盖两代进程并拒绝旧授权。负面检查拒绝错误场景、错误设备和被篡改的链接资源，且保存及活动状态不变。MuJoCo 严格 CTest 重点测试 7/7、EOS 线协议 8/8、进程 16/16、两个真实场景的子进程及持久日志中不重放不确定命令的检查均通过。MuJoCo 适配器尚无 `has_terminal_stop_fence`，所以实时 EOS 目录只公开 `safety.estop`，在 Submit 前隐藏 `base.velocity` 与 `arm.movej`；回放没有下发受管理运动。R06 须证明物理停止屏障、专用停止通道、底盘/机械臂分别确认及安全终止顺序，才能宣称完整 M3 首次使用控制通过。

## R06 停止通道设计目标

[所有者套接字契约](interfaces/socket_cn.md#r06-受管理停止契约)固定新增字段、稳定错误码、1000 ms 停止期限、每连接 250 ms 入口期限和 `strict-stop-v1` 特性。[48 个设计用例](../../tests/fixtures/strict_stop_lane/cases.json)固定故障、并发及生命周期行为。三个入口工作线程的变更已通过独立设计及实现复审，并在 PR #21 合并。限定范围的跨所有者安全停止回放通过；更完整的故障验收仍待完成。

受管理主监听器最多使用 32 个普通工作槽和 8 个入口槽。它从既有路径推导独立、仅所有者可访问的 `.stop` 套接字，后者具有自己的监听器、三个停止入口工作线程、从 accept 起计算的 250 ms 部分帧到期机制和一个预留停止执行槽。伴随监听器只解析 `health` 与 `stop`；EOS 探测其健康，并把所有受管停止发送到此处。主入口中八条阻塞连接不能占用伴随槽。若此前只有两个部分停止帧且没有其他排队者，第三个工作线程可在有效停止连接后的自身 250 ms 入口期限内完成分类，保持 500 ms 分类上界；若三个较早的部分帧占满入口，第四帧可能在队列中到期，停止结果为未知。不能用脱离管理的线程或无限制的客户分配持有引擎状态。停止通道在预留时记录新的引擎停止 epoch，使两个运动租期及旧命令令牌失效，再在短时引擎命令状态锁内分别保持底盘和机械臂。每个受管理子进程启动时还生成全新的 128 位 `generation_id`；两个健康路径都返回它，EOS 在每次受管理运动和伴随停止中回传。即使旧代请求的 epoch 与新代初始 `"0"` 相同，旧代延迟请求仍以 `stale_generation` 拒绝。每个受管理运动还携带当前 `stop_epoch` 前提，初始值为 `"0"`；引擎在同一锁内写目标前复核。比较**新键**的 epoch 前须先查询运动日志：相同旧键的重发在停止后仍返回原结果，旧键改变 epoch 则报冲突。屏障前已提交的运动可能之后才返回响应，但停止必须覆盖其目标之后才能确认；已排队的旧运动返回 `command_interrupted`，屏障后才解析的延迟**新键**旧帧返回 `stop_fenced`。这是 EOS `has_terminal_stop_fence` 所需的次序证明，旧响应中的 `accepted` 位不足以证明。

渲染须在短时命令状态锁内取得有界不可变状态快照，随后使用独立、有界的渲染上下文。停止取消排队拍摄，并屏蔽已经渲染中的负载发布。服务器在停止预留时关闭活动 JPEG 流，并使用独立的发布闸门：成功停止须等旧流离开闸门；若流在 1000 ms 期限内仍被阻塞，停止结果为未知。固定停止执行线程可能在期限之后继续完成物理保持；响应仍为 `stop_outcome_unknown`，本代子进程的新运动持续被禁止。伴随健康检查从缓存读取身份和特性，不获取引擎互斥锁。EGL 可能无法中断；这时有界停止通道仍须到达引擎，EOS 最终强制终止并回收子进程。成功停止分别返回 `base_stop`、`arm_stop` 和 `stop_epoch`，时间戳和序号在提交之后采样。部分证明返回 `stop_outcome_unknown`；超时或丢失响应对 EOS 来说仍未知，即使子进程实际停止。相同停止重发只返回已存储字段，不重新下发。直接启动 `2.0.0` 行为不变。

**跨所有者责任：** EOS 须推导并探测伴随 `.stop` 路径，比较主监听器与伴随监听器的健康代际，选择长于 500 ms 接受／分类期限加服务器 1000 ms 预算的外层单调期限，同时限制连接、完整帧读写和 SIGTERM/SIGKILL/回收阶段；经审查的 EOS 设计为物理伴随请求预留三秒。每次运动须发送当前 `generation_id` 和 `stop_epoch`，每次伴随停止发送代际 ID，校验两个停止状态及返回的代际／新 epoch，紧急停止前关闭 Dispatcher 准入，防止延迟下发在停止后到达适配器；缺少任一证明时记为 `OutcomeUnknown`。之后明确授权的非锁存控制停止可以允许携带新已证明 epoch 的命令；紧急关闭保持拒绝准入。EOS 仅在特性和终态屏障可用时公开运动能力；更完整的 R06 验收仍待完成。IsOS 须在包／套接字选择时预检推导出的伴随路径长度，按相反依赖顺序停止 EGIA/EOS 进程组；EOS 报未知时，IsOS 不能宣称完成安全停止。模拟器自身不能证明 EOS 次序或 IsOS 进程生命周期。

**R06 仅设计证据，2026-11-02：** `python3 tests/fixtures/strict_stop_lane/check.py` 验证了 47 个唯一目标用例及中英文契约标记。R05 样本检查、场景目录 8 项、节点声明 5 项、发布检查 1 项、Python 编译和 `git diff --check` 均通过。完整命令与输出在被 Git 忽略的 `logs/test/20261102-r06-stop-design/design-check.log`。本设计提交不含 C++ 实现，也不宣称运行时停止通过；下一步是独立设计审查及 EOS 适配器协议确认。

**R06 实现候选证据，2026-11-02：** 在 Linux x86_64、GCC 13.3、MuJoCo 3.16.0 环境运行 `cmake -S . -B build -DMUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0`、`cmake --build build -j4`、`ctest --test-dir build --output-on-failure`；初始 21 项 CTest 全部通过，包括 R05 兼容用例、pick-place/navigation 真实停止套接字、八条阻塞主入口帧、两条阻塞伴随入口帧、跨进程代际拒绝、停止后旧键重发、引擎层延迟写屏障及活动机械臂中断，以及拍摄快照后阻塞图形调用时停止仍完成且旧帧被丢弃。独立审查发现三处 P1 竞态；后续增加确定性的引擎阻塞、伴随健康及 JPEG 发布测试，完整 23 项结果记录在 `logs/test/20261102-r06-strict-stop-review-fixes/`。进一步审查发现 250 ms 入口计时器在队列出队之后才启动。修正后，每个队列条目都携带从 accept 起计算的绝对期限，最后一次读取后再次检查到期，并把伴随入口增至三个工作线程，使此前两个部分帧不能耗尽有效停止的入口预算。新增测试用三个部分帧占满所有工作线程，确认第四个部分帧已被接受，再暂停子进程至原期限之后，验证恢复后立即关闭，并验证此前两个部分帧之后的有效停止分类。完整 24 项 CTest、R06/R05 样本、Python 编译及差异检查记录在被 Git 忽略的 `logs/test/20261102-r06-strict-stop-accept-deadline/`；排队接受期限回归重复十次通过，独立设计与实现复审批准精确头 `212f757`。初始完整输出及精确命令在被 Git 忽略的 `logs/test/20261102-r06-strict-stop-implementation/`。所有者测试本身不证明 EOS 安全停止；下方限定范围的跨所有者回放核验了确认和未知结果，更完整的 R06 验收仍待完成。

## R06 所有者合并与限定范围跨所有者回放

[PR #21](https://github.com/Island-Team/isos-mujoco-sim/pull/21) 将经审查的头 `212f7572205eee3dd271d876bf9779eecb76d1f1` 压缩合并到 `master`，合并提交为 `c171208f0ef605fd4d5275d75567928713c50e96`。所有者闸门通过 24/24 项 CTest、十次接受期限回归，以及固定的 R06 48 项和 R05 31 项样本检查。完整输出在忽略的 `logs/test/20261102-r06-strict-stop-accept-deadline/`。

真实 pick-place 和 navigation 回放在全新 P01 链接的 IsOS 主目录中，通过 EGIA 授权的 gRPC 准入底盘和机械臂运动。EOS Stop 在 MuJoCo 终止并回收前输出一份 schema-1 回执，两部分均确认，代际匹配，epoch 为 `1`。IsOS 轮询后保留 `stopped`；独立进程扫描未发现残留子进程、进程组或套接字。停止套接字丢失及 MuJoCo SIGKILL 被判为未知，没有虚假确认。完整命令、原始回执、事件、journal 与校验清单保存在忽略的 `/home/ashex/projects/isos/logs/test/20261102-r06-full-cross-owner/`，范围记录于 [PR #21](https://github.com/Island-Team/isos-mujoco-sim/pull/21)。强制超时/KILL、GUI 不可用、过期或错误管道及崩溃恢复仍属于更完整的 R06 验收。此次合并未标记或发布 `0.1.1`。

**文档状态修正，2026-11-02：** 在已合并的所有者树 `c171208` 上，`python3 tests/fixtures/strict_stop_lane/check.py`、`python3 tests/fixtures/strict_socket/check.py`、`python3 tests/catalogtest.py`、`python3 tests/nodes.py`、`python3 tests/release.py`、`cmake -S . -B build -DMUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0`、`cmake --build build -j4`、`ctest --test-dir build --output-on-failure`、已修改 Markdown 的相对链接检查及 `git diff --check` 均通过。CTest 为 24/24；已修改文档的 119 个相对链接目标均存在。完整输出在忽略的 `logs/test/20261102-r06-doc-status/`。

[English](../../docs/mujoco/architecture.md) · [使用指南](usage/README_cn.md)

一个模拟器进程在启动时加载一个场景。引擎持有 MuJoCo 模型与数据、带种子的确定性重置、固定步长物理计算、机器人命令目标、遥测、相机渲染和场景评分。EOS 面向机器人的接口与可信评测接口共享引擎，但发布不同的信息。评测器可以重置、步进、读取真实状态与评分；代理只能通过 EOS 使用已声明的观察和动作。

直接运行以 `--scene` 选场景；当前 IsOS/EOS v2 部署在已应用的共享图中选择场景，EOS 将路径传给其模拟器子进程。MJCF 必须且只能包含一个支持的自定义数值标记：`eos_benchmark_pick_place_v1` 或 `eos_benchmark_navigation_v1`。引擎还验证必要命名元素，包括导航场景的 `navigation_goal`。可加载的任意 XML 不会自动成为受支持的评测场景；新场景需要明确的重置、评分、能力和测试。更换场景需要重启进程。

模拟器仍提供旧版 `eos.simulator.v1.SimulatorService` gRPC 套接字，供旧的直接集成使用。当前 IsOS/EOS v2 运行时使用独立的、仅所有者可访问的帧格式套接字，由 `--v2-socket` 指定；契约见 [backend_cn.md](usage/isos-pkg_cn.md)。EOS 持有模拟器子进程，将图中声明的观察与 primitive 端口交给代理。benchmark 套接字与两种机器人接口均分离。此软件包不链接到 EOS core。

EGIA 连接已运行的 EOS，发现健康设备和版本化 primitive，并通过 EOS 执行。它不能获得评测种子、目标真值、特权状态或评分。代理评测将通过 EOS 可见的行为与独立评测器的私有结果比较。

已发布的 v1.0.1 包及其生成的 EOS profile 属于旧路线。v2 中，IsOS 链接或安装精确的 `island/mujoco-sim@0.1.1` 包，检查可执行文件、场景、资源和外部 MuJoCo 库，并通过 `sim-hardware` 节点集应用共享图修订。EOS 读取该图，并将经校验的模拟器作为直接子进程启动。源码构建仍可用绝对场景与套接字路径直接运行。

原生 `0.1.1` 发布中，CMake 在构建目录的 RUNPATH 中保留 `MUJOCO_ROOT/lib`，以便本地测试。打包时先用 `cmake --install` 安装到临时目录，检查安装后的程序，再复制进归档。安装后仍有绝对 RUNPATH、MuJoCo SONAME 不符、依赖未解析，或实际库不在选定 MuJoCo 根目录下，都会使打包失败。资源记录包含测得的 Ubuntu 与 glibc 版本以及解析出的 SONAME 依赖闭包。IsOS 在受管理启动时为选定的外部库设置 `LD_LIBRARY_PATH`；这是重定位边界。包集成测试将最终归档解压到另一目录，并在该环境下运行严格套接字路径。

**原生发布证据，2026-11-03：** 在 Ubuntu 24.04 x86_64、glibc 2.39、`/home` 下的 MuJoCo 3.16.0 环境，`cmake -S . -B build-native -DMUJOCO_ROOT=<根目录>`、`cmake --build build-native -j4`、`TMPDIR=<home 临时目录> ctest --test-dir build-native --output-on-failure -j2`、`python3 tests/catalogtest.py`、`python3 tests/nodes.py`、`python3 tests/release.py` 和 `git diff --check` 均通过。CTest 为 26/26，包含原生要求的反向用例，以及归档解压后使用与 IsOS 后端解析器一致的环境进行的异地严格套接字启动。`tools/bundle.py --build-dir build-native --mujoco-root <根目录> --output logs/test/20261103-native-release-metadata/bundle` 生成的资源包含 `glibc>=2.39`、`tested_ubuntu:["24.04"]`、解析出的 SONAME 依赖闭包，归档 SHA-256 为 `eebf8f1e8267b8a766ae4c25dc657516a0b645bdf5867cef974d5535a67a383b`。安装后的 ELF 没有 RUNPATH/RPATH。`isos pkg verify <清单> <归档>` 在本机接受了精确归档。完整输出位于忽略 Git 的 `logs/test/20261103-native-release-metadata/`。发布前仍须另行完成干净的 IsOS/EOS 受管理回放。

## 时间与故障

MuJoCo 以固定的 2 毫秒物理步长推进。重置将场景置于确定性的带种子初始状态并暂停实时推进。评测器可以推进有界步数、检查状态、评分，再恢复实时运行。可重复性要求相同的场景版本、种子、命令序列和步进安排；异步实时观察不保证确定性重放。

缺少或无效的场景、必要元素缺失或套接字不可用都会导致启动失败。不可用设备与命令通过 EOS 面向机器人的接口报错。benchmark 服务在 `StateResponse.ok` 和 `error` 中报告重置或步进错误。与当前场景无关的真实状态字段不能用作代理输入，也不能推断为目标。

## 旧实现调用者核查（2026-11-04）

[English](../../docs/mujoco/architecture.md#legacy-caller-audit)

IsOS 受管理路径使用严格模式的 v2 帧套接字。以下旧路径仍有调用者，因此保留。

| 候选项 | 构建、运行时或测试调用者 | 结论 |
|---|---|---|
| `src/isos/service.cpp`、`src/isos/service.h`、`proto/simulator.proto` | `src/isos/main.cpp` 调用 `Serve`；直接启动的 `launch.sh` 传入 `--socket` 与 `--benchmark-socket`；`tests/smoke.sh`、`tests/eval.py` 和 `smoke-rpc` 检查 gRPC 路径。EOS 也保存 simulator proto。 | 保留直接运行兼容性及已发布 proto。受管理严格模式禁止两个旧监听器。 |
| `proto/benchmark.proto`、`benchmark-eval` | 可信的直接运行评测器调用 Reset、Step 和评分 RPC；`tests/eval.py` 覆盖此路径。 | 保留，仅供评测器使用。 |
| `benchmark-reset` | `tests/q03bench.py` 使用此私有工具进行确定性种子重置；Q03 验证命令也指定该目标。 | 在基准工具有替代实现前保留。 |
| 直接模式的 `--v2-socket` | `tests/v2.py` 与 Q03 工具覆盖该路径；直接运行时可与历史监听器共存。 | 保留。README 和英文用法示例现列出三个不同的套接字。 |

上述候选项均非无调用者实现。IsOS 受管理子进程仍通过 `--managed-strict-socket` 启动，仅使用所有者可访问的 v2 与伴随停止套接字。

## 当前基线

- 命令：`eos-mujoco-sim --help` 列出直接运行的 `--socket`、`--benchmark-socket`、可选 `--v2-socket` 与 `--managed-strict-socket`；`launch.sh`/`kill.sh` 持有独立进程；`benchmark-eval` 仅供评测器使用。
- 安装：`CMakeLists.txt` 只将 `eos-mujoco-sim` 安装到 `bin`。`tools/bundle.py` 生成独立的 IsOS 包；CMake 不安装测试及基准工具。
- 接口：直接运行的历史 gRPC simulator 与 benchmark 套接字仍为私有路径；受管理路径仅开放 v2 帧套接字和派生的 `.stop` 伴随套接字。精确请求与响应契约见 `docs/mujoco/interfaces/socket.md`。
- 图版本：`tools/nodes.py` 输出七个 `@v0.1` 注册类型；`tools/catalog.py` 输出 catalog `0.1.0`。IsOS 持有编写图的版本与持久化；模拟器不修改已应用图。

## 后续工作

## MuJoCo 0.1.1 集成 TODO

实施跟踪见 [MuJoCo 包 0.1.1](https://github.com/Island-Team/isos-mujoco-sim/milestone/1)，并纳入共享 [M2 已验证输入](https://github.com/Island-Team/Island-eos/milestone/2)、[M3 受治理执行](https://github.com/Island-Team/Island-eos/milestone/3) 和 [M5 集成验收](https://github.com/Island-Team/Island-eos/milestone/5)。下列步骤按依赖顺序完成。

[English](../../docs/mujoco/architecture.md#remaining-work) · [设计](architecture_cn.md) · [套接字契约](interfaces/socket_cn.md)

**进度，2026-11-02：** 第 2 项已在固定版本的 MuJoCo、EOS 和 IsOS 上通过限定范围的 R05 所有者验收；详见[跨所有者证据](architecture_cn.md#r05-跨所有者验收)。第 3 项的 MuJoCo 所有者停止通道已在 [PR #21](https://github.com/Island-Team/isos-mujoco-sim/pull/21) 合并，限定范围的实时运动/停止回放通过；强制超时/KILL、GUI 不可用、过期或错误管道、崩溃恢复及完整 R06 验收仍待完成。第 4–5 项的完整日志和发布验收也仍待完成。两次限定范围的结果均不意味着已发布 `v0.1.1` 标签。

1. 为贡献的进程类型及其场景设置增加非空描述和选择器元数据。只有 IsOS/EOS 目录读取方支持后才发布 `@v0.1` 类型；保留 `@v1.0` 别名和已安装 schema-v4 包身份。描述符选项必须来自已验证场景/设备资源。
2. 增加受管理的严格套接字启动与健康特性确认，同时保留直接启动的旧 `2.0.0` 语义。在严格模式下检查套接字 `node` 模拟器设备 ID 与操作/设备匹配，并在 EOS 检查图到设备的映射、有限有类型输入、向后兼容的稳定错误码、有界请求 ID。按 `(node, command_id)` 实现幂等，拒绝冲突重放并限制保留量。保持分帧格式与线协议 `2.0.0` 不变。
3. Stop 可抢占进行中的运动或慢速拍摄，遵守有限期限，并确认底盘与机械臂；EOS 必须在终止子进程前停止已准入执行器。测试相同传输重发、结果不确定时不自动重放、重复运动、冲突重放、不支持的节点/设备、损坏或超长帧、GUI 不可用、子进程崩溃和清理。
4. 按共享格式记录经净化的 JSONL 启动、就绪、故障与停止事件，包含运行/节点/关联 ID；不记录 JPEG 帧或秘密。通过 IsOS 测试轮转/游标与 UI 中首次故障查找。
5. 运行 `python3 tests/nodes.py`、`python3 tests/release.py`、`ctest --test-dir build --output-on-failure` 和 IsOS → EOS → MuJoCo → EGIA 成功、故障与安全停止集成测试。完整输出存于 `logs/test/<run-id>/`，记录可复现命令、环境、结果与限制。之后才考虑发布 `v0.1.1`；保留历史标签。

`src/mujoco/` 核心与 `src/isos/` 软件包包装层实现本模拟器，**不是** EOS 无用的旧 `src/eos/` 运行时。包装层现有的 gRPC 模拟器服务在最后调用方审查证明可移除前仍是历史兼容侧链。

## Q03 仿真器验证设计

[English](../../docs/mujoco/architecture.md)

**状态：**归属方源码检查、Q03 final-17 选定源码重放及 Q04 final-5 合并后提交重放均已通过。独立 Q04 归档审查没有 P1/P2 发现。`v0.1.1` 标签已发布，后续五方发布资产重放通过了其既定 Q04/M5 关卡；详见[软件包发布记录](usage/isos-pkg_cn.md#软件包发布记录)和 [EOS Q04 验证记录](https://github.com/Island-Team/Island-eos/blob/master/docs_cn/island/q04-merged-qualification_cn.md)。仿真器拥有场景加载、确定性复位、物理、渲染、私有套接字及基准评分。EOS 拥有机器人侧路由。基准真实状态不得通过 EOS、EGIA 或界面暴露。

**Q03 所有者初始基线（2026-11-03）：**已实现 `tests/q03bench.py`、私有 `benchmark-reset` 工具及失败路径单元测试。此处是本机直接套接字证据，不等同于跨仓库安装重放或发布批准。初次完整输出保留在 Git 忽略的 `logs/test/20261103-q03-mujoco/`；最终渲染器探针软件包保存在 `logs/test/20261103-q03-mujoco-review-final/`；无碰撞的逐请求原始样本及六份子进程日志保存在 `logs/test/20261103-q03-mujoco-review-final-2/`。

## 固定输入与所有者检查

从已获取的 `master` 提交构建，使用 MuJoCo 3.16.0，记录编译器、CMake、CTest、库、源码及场景哈希。对受 Git 跟踪的 C++ 源码运行 `clang-format --dry-run --Werror`；运行 CMake 配置／构建及全部 CTest，再运行严格套接字／容量／Stop、场景、引擎及基准的定向测试。运行节点贡献契约用例，并在空输出目录构建新的 `island/mujoco-sim@0.1.1` 软件包。保存清单／归档 SHA-256，并在干净的 IsOS 主目录验证该包。把完整命令、输出及退出状态保存到忽略 Git 的 `logs/test/<run-id>/`，包括失败的尝试。

已安装的所有者重放必须选择目录中的两个场景，证明精确软件包和场景准入，读取一帧图像，通过 EOS 发送一次获准的底盘或机械臂命令，注入仿真器死亡，并观察当前运行的故障和受控 Stop／回收。保留选定图修订、运行 ID、软件包收据、子进程身份及跨仓库验证器结果。独立的 CTest 必需，但不能替代已安装重放。

## 初始套接字基线

使用私有、仅所有者可访问的 v2 Unix 套接字，不启用 GUI。针对 `assets/scene.xml` 和 `assets/scenes/navigation/scene.xml`，分别启动三个全新的仿真器进程。使用直接启动的非托管基准进程（绝不作为 EOS 持有的托管子进程），提供私有、绝对且互不相同的 `--socket`、`--benchmark-socket`、`--v2-socket` 与 `--scene` 路径。例如：`build-q03/eos-mujoco-sim --socket /absolute/private/legacy.sock --benchmark-socket /absolute/private/benchmark.sock --v2-socket /absolute/private/v2.sock --scene /absolute/scene.xml --manual-step`。每次进程预热前必须通过私有基准套接字成功执行 `Reset(seed=42)` 并记录响应；测量期间保持引擎暂停，不进行异步步进。使用软件包中仅含 EGL 的 `SimEngine::RenderCamera` 路径及 640×480 的 `cam-0` 捕获。套接字不输出运行时解析的渲染器身份；启用子进程的可选 EGL 上下文探针，从子进程日志记录运行时 EGL 供应商和 GL 渲染器，并在每次重复时断言实际 JPEG 格式、字节长度和图像尺寸。预热 20 次后，串行发送 200 次 `base_observe` 和 20 次 `camera_capture` 请求。记录每次单调时钟耗时、响应状态和字节数，以及每组操作测得的墙钟时长。逐进程和合并样本报告成功请求数／秒或帧数／秒、中位数（偶数样本取中间两数平均）及最近秩 p99（毫秒）；单独报告所有失败与超时。这只测量仿真器套接字，不代表 IsOS HTTP、EOS Dispatcher 或浏览器延迟。初始测量不形成性能目标。

测试工具须对套接字不可用、畸形响应、超时、场景错误和子进程意外退出明确失败；定向测试须覆盖这些路径。独立代理在实现前审查本设计，并在合入 MuJoCo `master` 前审查工具、证据及 PR。Q03 跨仓库摘要记录最终精确提交；Q04 负责发布与标签。
## 可重现的所有者证据

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

### 选定安装归档证据（2026-11-03）

选定的 0.1.1 软件包记录 MuJoCo 源码提交 `3bf8a50aa2100b3eb1758ea4795bdcdddb65391e`；`release.json` 必须继续保持这个精确来源身份。选定发布文件 SHA-256 为 `591cd2ec454b659bbe97645811a6c928081045636e82e52b5b2f2dda3247b445`，归档资产 SHA-256 为 `53f9fa5d9af4b92b74635fd22447a9f08450b89a19725b6d26b6bd5850a5be96`。EOS Q03 选定清单 SHA-256 为 `116aef2846750a96275645e4dec3021ad716ce6fb80b05c087a2ce377a74b990`；冻结评审主构建和案例构建收据 SHA-256 分别为 `977293e097779f636cb70bde9f3d5657bc9351b0b9f67534ca7beb41a97ef915` 和 `20b2dc444d4f90ca1e4cf4b8a2404893c53cd20de19a090ce02debf0c539ab5d`。

在封存的干净主目录重放中，IsOS 验证并安装该归档，选择 `pick-place` 场景和可用的相机、底盘、机械臂设备；EOS 将已验证的 MuJoCo 可执行程序作为直接子进程启动。真实的 640×480 相机帧到达 EOS、EGIA Vision 与浏览器观察。R06/A03 选定来源故障试验通过子进程死亡、Stop／回收及重启检查，没有重放结果不明的运动；最终部署 Stop 获确认，受管进程无存活者。六组选定案例和 `Q01_FULL_VERIFIED` 保存在 EOS 中忽略 Git 的 `logs/test/20261103-q03-selected-final-15/`。上文私有套接字基准仍是另一项固定负载测量。此次安装重放只覆盖本地模拟托管 Origin。在 final-15 关卡时，Q04 合并后提交评审和标签发布尚未执行。若更改软件包来源 HEAD，必须重新构建并验证 0.1.1 软件包。

### 最终选定源码与合并后提交的归档证据，2026-11-04

后续封存的 Q03 `20261103-q03-selected-final-17` 归档仍固定软件包源码 `3bf8a50aa2100b3eb1758ea4795bdcdddb65391e`、发布文件 SHA-256 `591cd2ec454b659bbe97645811a6c928081045636e82e52b5b2f2dda3247b445` 和归档 SHA-256 `53f9fa5d9af4b92b74635fd22447a9f08450b89a19725b6d26b6bd5850a5be96`。冻结选择清单 SHA-256 为 `35dd4e5aa4c209bf84935002a4eded756f3eb5a1c147b2fb12bd5d894e46b78a`；精确选定的 EOS 源码 `219f031bae9dbfc9d9f53f62c910b9e235bb2138` 上的验证器对全部六组返回 `Q01_FULL_VERIFIED`。独立 EOS 审核位于 `logs/test/20261104-q03-final17-independent-audit/`：选定源码验证通过，而较新检出因测试工具摘要变化被拒。上文 final-15 记录保留为历史证据。

Q04 `20261103-q04-merged-home-final-5` 的发布文件从已合并的 MuJoCo `master` `04b65882cd11b0aff8ce56473164691dbd662196` 重新构建。`release.json` 的 SHA-256 为 `c421039753c24ffc74658d6b1dfe5c9de6a1ed77b64df8fbaee77063da837096`，已安装归档的 SHA-256 为 `bb2862b01c3ccab8b68570e766a0ad26c8c5783b3c87cf99225eb0edb7a260f4`；冻结的外部选择清单 SHA-256 为 `7f5cefa5b6521d42d28b88c916679f2b668ba93fd61bbcbbfed4bb8fcc722b87`。IsOS 在干净主目录中验证并安装精确软件包；EOS 将仿真器作为直接子进程启动，产生真实相机帧和受治理的底盘结果，随后在子进程终止与回收之前确认物理 Stop。选定的 R06/A03 故障与重启案例通过，没有重放结果不明的运动。完整选定验证器返回 `Q01_FULL_VERIFIED`；独立归档评审检查了 3,630 个封存文件，没有 P1/P2 发现。原始收据、事件、子进程证明和命令保存在 EOS 中忽略 Git 的 `logs/test/20261103-q04-merged-home-final-5/`。这是本地模拟托管 Origin 的重放，不代表已发布 `v0.1.1` 软件包或公网 HTTPS 部署；在该关卡时，发布收尾和标签仍未完成。
