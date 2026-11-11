# MuJoCo 包描述符与节点声明

## 通用包进程声明

当前 `isos.package@v1` schema `0.2.0` 的 `release.json` 为 `eos.process.mujoco.simulator@v0.2` 增加 `node_contributions.processes[]`。IsOS 根据归档字节和已贡献的进程类型验证声明，EOS 实现指定的生命周期适配器。先前已验证发布包中的历史 `@v1.0` 类型仍按原有路径读取；本清单不贡献该类型。图只保存准确包版本和稳定场景 ID，不保存解析后的路径。

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

包的构建入口为 `build.sh --output <空的绝对目录>`。它要求 `MUJOCO_ROOT`，从本地源码构建，在输出目录写入 `release.json` 和清单指定名称的归档，例如 `mujoco-sim-v0.2.0-linux-x86_64.tar.gz`。清单中的摘要和大小覆盖归档的准确字节。归档按路径排序，文件所有者与时间戳归零，gzip 时间戳为零；固定载荷字节的重复归档摘要应一致。`python3 tests/archive.py` 验证此边界。安装不会激活图或重启运行实例。

[English](../../../docs/mujoco/interfaces/package.md) · [套接字](socket_cn.md) · [包发布](../usage/isos-pkg_cn.md#软件包发布记录)

**所有权与状态。** 本仓库拥有 MuJoCo 专用 `backend-v2.json` 描述符以及当前发布清单中的 `node_contributions`。以下 P02 小节记录 0.1.2 历史候选；当前源码的外部适配器以本页开头的 0.2.0 契约为准。IsOS 拥有通用发布清单 schema、[已验证收据与包准入](https://github.com/Island-Team/isos/blob/master/docs_cn/isos/interfaces/package-verification_cn.md)、图修订和 `/node-options` 响应。`tools/bundle.py` 已输出 P02 目录和 `@v0.2` 进程声明；IsOS 的语义准入及通用 P03 选项 API 已在其所有者仓库实现；固定版本的 R05 回放验证了本包的实际使用。即使新图格式为 `0.2.1`，描述符 schema、协议和套接字线协议 `2.0.0` 仍是独立兼容性标识。

## 历史 0.1.2 描述符字段

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

## P02 描述符扩展

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

P02 描述符固定于 [`target-descriptor.json`](../../../tests/fixtures/scene_catalog/target-descriptor.json)；[`legacy-descriptor.json`](../../../tests/fixtures/scene_catalog/legacy-descriptor.json) 固定精确旧结构。构建工具根据复制后的 XML 计算两个 SHA-256，并在打包前检查 profile 标记、声明的模型元素与引用资源。MJCF 相对资源路径可以从场景目录向上遍历，但必须留在已验证包内；缺失、逃逸或符号链接资源均失败。真实引擎加载与回放仍由 CTest 验证。

## P02 声明与图边界

包在 `eos/process/mujoco` 贡献唯一新进程类型 `eos.process.mujoco.simulator@v0.2`；先前已验证发布包中的 `eos.process.mujoco@v1.0` 仍按原有路径读取。新类型声明 `implementation:{"kind":"managed_process","interface":"mujoco-v2","version":"1","lifecycle_adapter":"mujoco-v2"}`，并带非空 `description`；其 `scene` 设置有非空描述和 `selector:{"provider":"package","resource":"scene","package_from":"node.package"}`。`socket`（仅所有者可访问的 Unix 套接字路径）、可选 `env`（字符串表）和 `start_timeout_ms`（正整数毫秒）具有明确的类型、用途与验证。进程状态与健康由运行时拥有，不作为图端口。进程实例锁定 `node.package:{"id":"island/mujoco-sim","version":"0.2.0"}`；设置中不存解析后的程序或场景路径。此 sidecar 不增设执行器或安全适配器路线。

当前 `sim-hardware` 节点集面向 `0.2.1` 图，只含包拥有的进程与一个 EOS 通用 JPEG 相机（观测 JSON 上限 12 MiB） `device@v0.2`。相机实例固定 MuJoCo 适配器并引用进程节点。底盘和机械臂仍在资源目录中，但 EOS 完成执行器 Stop 证明前不贡献其托管实例。本包不贡献或覆盖 EOS 通用类型。包验证与链接不能证明图 Apply 或运行就绪。历史已保存图保留原有读取路径。

**目标图准入。** P02 节点集声明稳定参数 `scene`、`camera_device`、`base_device`、`manipulator_device` 和仅所有者可访问的 `socket`。默认场景为 `pick-place`，三个设备默认值为 `cam-0`、`base-0`、`arm-0`。在 IsOS 与 EOS 的图准入路径可用后，预览与 Apply 必须要求所选 ID 属于精确验证过的描述符、符合硬件类别和所选场景，并通过整图准入。已准入图保存 ID 和精确包锁定。IsOS 拥有组合及修订 compare-and-swap；改选场景必须生成新的已保存修订，仅在 Restart 后作用于子进程。不能原地修改运行中模拟器的场景。当前包验证与链接通过，但预览受 IsOS/EOS 验证命令不匹配阻塞，且当前 EOS 所有者尚未编译 `mujoco-v2`。

P03 拥有通用 `GET`/`POST /node-options` 按 `(node_path,setting)` 分组、所选值回显与不可用选项呈现。本包提供选择器声明和已验证目录元数据，不定义 HTTP 包装。R05 拥有严格套接字特性协商、请求 `node`/操作校验与命令去重。P02 目录项本身不能证明套接字强制检查设备 ID；R05 严格健康与设备/操作测试为受管理启动提供该证明。

## P02 诊断与 IsOS 准入目标

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

仅检查描述符时，即使表中列出相应的图字段，`path` 仍为空。P01 在 `payload` 阶段的 `package_changed` 和相应阶段的 `package_unsafe_path` 优先于所有 P02 代码。特别地，链接后的场景发生修改返回 `package_changed`；场景路径出现符号链接返回 `package_unsafe_path`。载荷字节符合 P01 但声明的场景哈希错误的候选包，在收据发布前的 P02 语义检查返回 `mujoco_scene_digest_mismatch`。P03 用这些有界原因呈现不可用选项，HTTP 选项包装仍归 IsOS。完整变异与预期 `{code,path,stage}` 组合固定于 [`negative-cases.json`](../../../tests/fixtures/scene_catalog/negative-cases.json)。

目标描述符示例摘录（完整样本含两个场景、三台设备）：

```json
{"schema_version":"2.0.0","catalog_version":"0.1.0","package":{"id":"island/mujoco-sim","version":"0.1.2"},"scenes":[{"id":"pick-place","label":"Pick and place","description":"Reach, grasp and place an object","profile":"eos_benchmark_pick_place_v1","path":"assets/scene.xml","sha256":"6c677b07597ddf3d18cf7b30dddd407a09d1c53086d61c919592d16723d32aea"}],"devices":{"camera":"cam-0","base":"base-0","manipulator":"arm-0"}}
```

若所选 `navigation` 场景的 XML 却声明 `eos_benchmark_pick_place_v1`，IsOS 在进程的 `settings.scene` 路径报告场景/profile 不匹配，已保存及已激活修订不变。若 `navigation` 的设备支持列表缺少 `arm-0`，机械臂选项不可用并附有有界原因，Apply 在其适配器设置处失败。若 `MUJOCO_ROOT` 缺少所需库，包可以保留安装，但所选场景不能就绪。MuJoCo 构建工具使用这些 P02 代码分类直接描述符错误；IsOS 配套切片将图时失败映射到上表精确路径。

通用 `release.json` 字段（ID、版本、校验值、架构、源码、许可证、资源）遵循 IsOS 包契约。本包贡献新进程类型、`mujoco-v2` 适配器系列和 `sim-hardware` 节点集。包只拥有模拟器进程类型；相机、底盘和机械臂类型仍归 EOS。实例的 `description` 描述配置好的实例；注册进程的 `NodeType.description` 描述可复用类型。缺少类型描述的旧版已验证 sidecar 继续使用兼容默认。

### 原生 `0.1.2` 资源要求

候选归档包含 CMake 安装后的 `bin/eos-mujoco-sim`，其中没有构建目录的绝对 `RPATH` 或 `RUNPATH`。`release.json` 资源中的 `libc` 是在原生构建主机测得的 `glibc>=主版本.次版本`，`tested_ubuntu` 是该主机的 Ubuntu 版本，`required_libraries` 是已安装程序解析出的、排序后的 SONAME 依赖闭包。在 Ubuntu 24.04 验收主机上，保守的 libc 要求是 `glibc>=2.39`。直接依赖和实际解析的 MuJoCo SONAME 必须恰好为 `libmujoco.so.3.3.1`，并位于所选 `MUJOCO_ROOT/lib` 下；缺失、版本不符或任何未解析库都会阻止归档生成。归档不包含外部 MuJoCo 库。IsOS 解析 `MUJOCO_ROOT`，并通过 `LD_LIBRARY_PATH` 将库目录传给 EOS 管理的模拟器子进程；图设置和包锁定均不嵌入构建主机路径。`required_libraries` 与 `tested_ubuntu` 描述已测原生目标，不代表未测试主机也兼容。

## 历史声明的兼容性

历史已验证 sidecar 仅贡献 `eos.process.mujoco@v1.0`，缺少进程类型描述与选择器，且使用固定设备 ID 组合 `1.0.0` 图。读取方可为旧 sidecar 提供仅供目录显示的描述默认值，而不改变验证过的字节。当前构建工具输出一个 `eos.process.mujoco.simulator@v0.2` 进程类型和仅含两节点的 `0.2.1` 相机节点集；IsOS 先接受并验证新描述符，再把该预设发布为图选项。其他包资源以后可使用 P03 选项机制；本版本不定义 `egia.tensor` 执行。

## 当前 v0.2.x 二进制适配器

发布 schema `0.2.0` 声明 `adapters:[{"family":"mujoco-v2","library":"lib/libmujoco-eos-node.so","sha256":"<64 位小写十六进制>"}]`，且 `node_contributions.libraries` 使用相同路径和摘要。此动态库实现带版本的 `isos_node_v1` C ABI，不是第二个模拟器进程。EOS 将已准入的图实例传给 `create`，管理回调生命周期和模拟器子进程，并在卸载前调用 `stop`。插件 Stop 成功意味着观测回调已静止；EOS 仍须在终止子进程前通过严格 companion 套接字另行证明执行器停止。首个 `sim-hardware` 节点集只含模拟器进程与 JPEG 相机。底盘和机械臂仍作为目录资源列出，但在 EOS 证明执行器 Stop 前不得用于托管执行。
