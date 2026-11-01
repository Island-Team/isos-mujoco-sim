# MuJoCo 包描述符与节点声明

[English](../../../docs/mujoco/interfaces/package.md) · [套接字](socket_cn.md) · [包发布](../package-release_cn.md)

**所有权与状态。** 本仓库拥有 MuJoCo 专用 `backend-v2.json` 描述符和 schema v4 `release.json` 中的 `node_contributions`。IsOS 拥有通用发布清单 schema、[已验证收据与包准入](https://github.com/Island-Team/isos/blob/master/docs_cn/isos/interfaces/package-verification_cn.md)、图修订和 `/node-options` 响应。`tools/build-backend-bundle.py` 已能生成包；下述 P02 目录扩展与 `@v0.1` 声明是**目标设计，尚未实现**。即使新图格式为 `0.1.0`，描述符 schema、协议和套接字线协议 `2.0.0` 仍是独立兼容性标识。

## 当前描述符字段

| 字段 | 类型／单位 | 用途／所有者 | 默认、验证和兼容 |
| --- | --- | --- | --- |
| `schema_version` | 字符串 | 描述符解析标识／本包 | 必填 `2.0.0`；IsOS 拒绝未知主版本，并保留此标识。 |
| `package.id`, `package.version` | 字符串 | 精确包锁定／本包 | 必填 `island/mujoco-sim`、`0.1.1`；须匹配已验证收据。 |
| `entrypoint` | 相对路径 | 模拟器程序／本包 | 必填 `bin/eos-mujoco-sim`；IsOS 检查其在已验证包内且可执行。 |
| `protocol` | 字符串 | EOS 适配器工厂标识／本包与 EOS | 必填 `mujoco-v2`；EOS 必须有匹配的编译工厂。 |
| `scenes[] .id` | 唯一字符串 | 稳定场景选择值／本包 | 当前 `pick-place`、`navigation`；图不存路径。 |
| `scenes[] .path` | 相对路径 | 场景 MJCF 与资源／本包 | 必须在已验证包内解析为可读的受支持场景；禁止遍历和符号链接逃逸。 |
| `devices.camera`, `.base`, `.manipulator` | 字符串 | 模拟器设备 ID／本包 | 当前 `cam-0`、`base-0`、`arm-0`；适配器设置使用精确 ID。 |
| `runtime.mujoco_version` | 字符串 | 外部 MuJoCo ABI 要求／本包 | `3.16.0`；IsOS 启动前检查库和程序兼容性。 |
| `runtime.environment_variable` | 字符串 | 安装根目录输入／本包 | `MUJOCO_ROOT`；不能把未验证程序路径或秘密写入图。 |
| `runtime.library` | 相对路径 | 安装根目录下所需动态库／本包 | `lib/libmujoco.so.3.16.0`；IsOS 启动前验证。 |

当前描述符没有场景或设备的人工描述、场景 profile 和逐场景校验值；设备映射适用于整个包。IsOS 目前检查路径包含关系和引用文件字节，但不证明 XML 具有声明的评测 profile。模拟器引擎加载场景时会检查该 profile。

## P02 描述符扩展——目标设计，尚未实现

以下字段在描述符 schema `2.0.0` 内追加。`scenes[].id` 和 `devices.<kind>` 保持为图设置中的稳定值；路径、XML 标记和哈希只属于包元数据。新包候选必须提供下列元数据；缺少这些字段的已验证旧描述符仍按旧图行为读取。IsOS 不从旧描述符推导新图选项。

| 字段 | JSON 类型／单位 | 用途与所有者 | 默认、验证和兼容 |
| --- | --- | --- | --- |
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

`runtime.mujoco_version`、`runtime.environment_variable` 和 `runtime.library` 保持原义。IsOS 在 Apply 和 Run 前检查 `MUJOCO_ROOT` 下所声明的 `3.16.0` 库；缺失或不兼容时返回不可用原因。包不内置该库。文件名符合要求并不自动证明 ABI 兼容；启动/就绪边界须在报告 ready 前确定实际加载的版本。P01 先验证精确发布收据、全部载荷字节和路径包含关系；P02 再以该已验证句柄检查场景/profile 与设备映射语义。固定 `0.1.1` 锁定下修改程序、场景 XML、引用资源或贡献 sidecar 会使 P01 收据失效；有意修改须发布新包版本。

P02 目标描述符固定于 [`tests/fixtures/scene_catalog/target-descriptor.json`](../../../tests/fixtures/scene_catalog/target-descriptor.json)，两个 SHA-256 对应仓库当前场景 XML 字节。它是设计样本，当前构建工具尚未输出。

## P02 声明与图边界——目标设计，尚未实现

包在 `eos/process/mujoco` 贡献唯一新进程类型 `eos.process.mujoco@v0.1`，并为已验证旧读取器保留精确的 `eos.process.mujoco@v1.0` 历史标识。新类型带非空 `description`；其 `scene` 设置有非空描述和 `selector:{"provider":"package","resource":"scene","package_from":"node.package"}`。`socket`（仅所有者可访问的 Unix 套接字路径）、可选 `env`（字符串表）和 `start_timeout_ms`（正整数毫秒）具有明确的类型、用途与验证。`status` 和 `health` 输出有完整描述、`in_process` 传输和 `state` 数据类。进程实例锁定 `node.package:{"id":"island/mujoco-sim","version":"0.1.1"}`；设置中不存解析后的程序或场景路径。此 sidecar 不增设执行器或安全适配器路线。

`sim-hardware` 新图节点集是 `0.1.0` 草稿模板，不提供执行权限。它包含包拥有的新进程类型、EOS 通用相机/底盘/机械臂 `@v0.1` 类型、EOS 通用底盘/机械臂 primitive 绑定 `@v0.1` 和 EOS 相机门 `@v0.1`。IsOS 初始图已有 `eos.dispatcher.control@v0.1`，节点集不得重复。每个通用硬件实例在 `node.adapter.package` 中精确锁定 MuJoCo 包、引用进程节点，并在适配器设置中存所选 `device_id` 及一致的 `simulator_node`。包不贡献、重命名或覆盖 EOS 通用类型。旧 `isos.ui.vision@v1.0` 不进入此 `0.1.0` 节点集，直至其所有者注册兼容类型；包不能虚构 IsOS UI 标识。此前验证过的旧 sidecar 与已保存的 `1.0.0` 图按原有行为可读；新预设和旧图读取均不静默改写它们。

P02 节点集声明稳定参数 `scene`、`camera_device`、`base_device`、`manipulator_device` 和仅所有者可访问的 `socket`。默认场景为 `pick-place`，三个设备默认值为 `cam-0`、`base-0`、`arm-0`。预览与 Apply 要求所选 ID 属于精确验证过的描述符、符合硬件类别和所选场景，并通过整图准入。图保存 ID 和精确包锁定。IsOS 拥有组合及修订 compare-and-swap；改选场景生成新的已保存修订，仅在 Restart 后作用于子进程。不能原地修改运行中模拟器的场景。

P03 拥有通用 `GET`/`POST /node-options` 按 `(node_path,setting)` 分组、所选值回显与不可用选项呈现。本包提供选择器声明和已验证目录元数据，不定义 HTTP 包装。R05 拥有严格套接字特性协商、请求 `node`/操作校验与命令去重。P02 目录项不能证明当前套接字已经检查设备 ID。

目标描述符示例摘录（完整样本含两个场景、三台设备）：

```json
{"schema_version":"2.0.0","package":{"id":"island/mujoco-sim","version":"0.1.1"},"scenes":[{"id":"pick-place","label":"Pick and place","description":"Reach, grasp and place an object","profile":"eos_benchmark_pick_place_v1","path":"assets/scene.xml","sha256":"6c677b07597ddf3d18cf7b30dddd407a09d1c53086d61c919592d16723d32aea"}],"devices":{"camera":"cam-0","base":"base-0","manipulator":"arm-0"}}
```

若所选 `navigation` 场景的 XML 却声明 `eos_benchmark_pick_place_v1`，IsOS 在进程的 `settings.scene` 路径报告场景/profile 不匹配，已保存及已激活修订不变。若 `navigation` 的设备支持列表缺少 `arm-0`，机械臂选项不可用并附有有界原因，Apply 在其适配器设置处失败。若 `MUJOCO_ROOT` 缺少所需库，包可以保留安装，但所选场景不能就绪。当前实现仅提供较泛化的错误，尚无上述 P02 诊断。

通用 `release.json` 字段（ID、版本、校验值、架构、源码、许可证、资源）遵循 IsOS 包契约。本包贡献一个进程节点类型、`mujoco-v2` 适配器系列和 `sim-hardware` 节点集。包只拥有模拟器进程类型；相机、底盘、机械臂、门、primitive 绑定和 Vision 类型仍归 EOS 或 IsOS。实例的 `description` 描述配置好的实例；目标注册进程的 `NodeType.description` 描述可复用类型。当前 sidecar 没有类型描述，发布新 sidecar 前由 IsOS 提供规定的兼容默认。

## 当前声明的兼容性

当前 sidecar 仅贡献 `eos.process.mujoco@v1.0`，缺少进程类型描述与选择器，且使用固定设备 ID 组合 `1.0.0` 图。读取方可为旧 sidecar 提供仅供目录显示的描述默认值，而不改变验证过的字节。新的 `@v0.1` 声明只有在 EOS 与 IsOS 读取方支持且 P01 验证封存后才输出。其他包资源以后可使用 P03 选项机制；本版本不定义 `egia.tensor` 执行。
