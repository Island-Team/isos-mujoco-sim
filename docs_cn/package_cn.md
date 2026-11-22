# 软件包声明与验收

[English](../docs/package.md) · [Docs](README_cn.md)

本包贡献 EOS 硬件节点和两个由 IsOS 监督的服务。本页拥有包专属清单、资源及配置规则。[节点组](node/README_cn.md)拥有图端口；[适配器控制](core/adapter_cn.md)拥有私有套接字。通用发布清单准入仍由 IsOS 拥有。历史进程声明保留在[变更记录](changelog_cn.md)。

<a id="mujoco-包描述符与节点声明"></a>
## MuJoCo 包描述符与节点声明

本页定义当前硬件包声明，历史进程节点声明见[变更记录](changelog_cn.md)。RoboCasa 和原生机器人预设的运行控制字段见[控制契约](core/adapter_cn.md)。

可选的 `ubuntu22` CMake 构建配置使用独立的 `.local/package-build-ubuntu22` 目录，要求 Ubuntu 22.04/glibc 2.35 主机及 Python 3.11 或更新版本。开发和打包构建均使用此目录，并拒绝交叉编译。在现有包构建入口设置 `MUJOCO_BUILD_PROFILE=ubuntu22` 即可选择。仅此配置检查已安装模拟器和适配器的 ELF glibc 版本是否超过 2.35。不设置该变量时保留原有原生构建和打包检查。此配置不代表获得发布资格。

<a id="完整机器人硬件软件包"></a>
### 完整机器人硬件软件包

默认源码构建为尚未发布的 `0.2.8` 候选。执行器输入使用当前标准载荷模式和 `{owner:"isos",id:<data_type>,version:"1.0"}` 端口契约。EOS 经选定部件 Dispatcher 原样转发已验证载荷，软件包插件将其转换为原生或 RoboCasa 私有线路字段。非相机观测使用 `observation`，相机输出仍为 `frame`，躯干不伪造输出。截至 `0.2.7` 的版本保留旧声明与适配器转换。标准原生机械臂省略未执行的速度保证。每个软件包预设仍仅包含硬件；组合部件 Dispatcher，并为每个执行器选择一个命令输入。

0.2.8 的发布依赖 IsOS 软件包安装辅助程序描述符支持先完成审查和发布；随后才可对精确软件包做资格检查并发布。

`0.2.8` 源码候选版声明七种 EOS 硬件类型，并提供“原生机器人”和“RoboCasa 机器人”两套设备预设。每个实例以精确软件包版本同时锁定类型所有者和适配器所有者。这些类型位于 EOS 硬件层的 camera、base、manipulator、gripper 和 torso 分组；其他软件包可选择不同的层和分组。预设没有进程节点。IsOS 只启动已选节点引用的软件包服务，并管理子进程及日志，再把私有服务端点交给 EOS。EOS 通过 `isos_node_v2` 加载已验证的 `libmujoco-eos-node.so`，所有执行器命令均由 Dispatcher 准入。

准确节点类型见[EOS 硬件节点接口](node/README_cn.md)。以下字段遵循当前通用 IsOS 软件包发布及运行服务声明；IsOS 校验归档字节，并在 Apply 和 Run 解析主机配置。

| 声明 | 类型 / 单位 | 用途与必需值 | 缺失、验证及兼容 |
| --- | --- | --- | --- |
| `node_contributions.node_types[]` | 对象数组 / — | 相机、底盘、机械臂、夹爪、躯干的七个 EOS 类型 | 本预设必需；准确类型 ID 和端口见节点接口。未知类型拒绝准入。 |
| `node_contributions.runtime_services[].id` | 字符串 / — | `native` 或 `robocasa` 服务标识 | 必需且唯一，无默认值。 |
| `runtime_services[].entrypoint` | 包内路径 / — | `bin/eos-mujoco-sim` 或 `bin/robocasa-worker` | 必需、已验证、位于归档内；不得越界，无默认值。 |
| `runtime_services[].args` | 字符串数组 / — | 使用 `${socket}` 和已验证场景资源的启动模板 | 必需，引用须能从服务输入解析。 |
| `runtime_services[].config_service_type` | 字符串 / — | 选择 `native` 或 `robocasa` 配置 | 必需，须匹配已配置服务实例。 |
| `runtime_services[].node_types` | 字符串数组 / — | 服务可提供的类型 | 必需且非空，须由精确发布包贡献。 |
| `runtime_services[].resources` | 对象数组 / — | 原生场景选择器，绑定 `package-resources.json` | 原生服务必需；RoboCasa 缺省。 |
| `runtime_services[].environment` | 对象数组 / — | 子进程所需的已验证主机与服务值 | 缺少必需配置值时阻止 Run。 |
| `runtime_services[].requirements` | 路径与种类数组 / — | 所选服务的本地前提 | 原生服务要求 MuJoCo 库文件；RoboCasa 要求配置的 Python 解释器文件及资源目录。IsOS 只检查所选服务。 |
| `runtime_services[].required_node_settings` | 类型到字段映射 / — | 原生和 RoboCasa 已选相机节点必须提供宽高 | IsOS 在 Apply 时检查字段存在且整数值处于声明范围。 |
| `node_sets[].nodes[].profile.adapter.settings` | 对象 / — | `service_instance` 和 `device_id` 绑定预设设备 | 两个必需字符串，无默认值；IsOS 校验服务、类型和设备关系。 |

每个已选服务在私有监听器可用后向标准输出写入有界的就绪行，并在正常清理时写入停止行。IsOS 将标准输出和标准错误捕获为部署 JSONL 中的 `package_service_output` 记录，附带精确包 ID 和版本、服务实例、输出流、代际与运行 ID。EOS 使用相同运行 ID 写入自己的所有者记录。[完整接口回放](development_cn.md)检查此关联；日志读取和保留规则仍归 IsOS 所有。

每个相机硬件节点都有整数 `settings.camera_width` 和 `settings.camera_height`，允许范围为 64–2048 像素。两套预设均提供 1280 × 720。两个服务都要求已选相机节点提供这两个字段。IsOS 通过 `${selected_nodes.settings_json}` 传递已选设置：原生 `cam-0` 使用 `ISOS_NATIVE_CAMERA_SIZES`，RoboCasa 使用 `ISOS_ROBOCASA_CAMERA_SIZES`。原生模拟器按已选尺寸渲染并编码 JPEG；没有这些设置的直接模拟器运行仍使用场景尺寸。工作进程在创建 Gym 前校验已选相机 ID 和尺寸。当前 Gym 包装器让全部相机使用同一渲染尺寸，因此工作进程按已选最大宽高渲染，再将每路 RGB8 观测缩放到该节点的尺寸。图修改在 Apply 后的下次 Run 生效。软件包配置保留共享的本机路径、场景、任务和种子。先前精确版本的软件包仍按其原有相机配置行为运行。

`0.2.8` 候选版在原生适配器中把 RoboCasa RGB8 观测编码为 JPEG，再发出 `image_frame@v0.2`。其 RoboCasa 相机实例声明 `jpeg` 能力；工作进程套接字仍传输有界 RGB8。将锁定 `0.2.8` 的图用于发行版部署前，仍须完成软件包鉴定与发布。

对于 0.2.8，软件包描述符还声明了已验证的 RoboCasa 安装辅助程序。在交互式 IsOS CLI 中，若任一 RoboCasa 本机路径缺失，`isos pkg configure island/mujoco-sim@0.2.8 --service robocasa` 会先询问，再下载固定版本的 RoboCasa 源码、Python 3.11 环境和首个任务的资源，并将所得路径写入配置草稿供操作员检查。拒绝下载后仍可手动配置路径。Web 表单仍需手动填写路径。安装数据保存在 IsOS 部署专用目录，不进入已验证的软件包。

`config/package-config.json` 为通用 IsOS 软件包配置界面声明中英文标签和说明。`services.native.scene` 枚举提供已验证的 `pick-place` 和 `navigation` 场景 ID，默认选择 `pick-place`。`services.robocasa.task` 枚举目前仅提供已通过本地冒烟回放验证的 `CloseFridge`，并默认选择该任务；固定版本的上游任务注册表中还有其他任务，但尚未逐项完成本包选择器的验证。IsOS 根据描述符选项校验所选值。`config/package.toml` 提供 `[package]`、`[host]`、`[services.native]` 和 `[services.robocasa]`。已选原生服务需要本地 MuJoCo 3.3.1 目录；已选 RoboCasa 服务需要本地资源及明确选定的 Python 解释器。这些大型主机资源不随软件包下载。路径属于本地部署配置，不属于图节点设置。每个硬件适配器通过 `service_instance` 选择服务；IsOS 在 Apply 与 Run 时解析它。

使用 `./build.sh --output 绝对路径的空目录 --version 0.2.8` 或更高的未使用版本构建候选版。截至 v0.2.6 的已发布标签保持不变。只有两套预设都通过 IsOS `pkg check` 回放，包括拒绝、崩溃、日志和停止场景，候选版才可发布。

RoboCasa 启动器通过 `ISOS_PACKAGE_PYTHON` 接收 `host.python_interpreter`，用 `-B` 执行包内 worker。软件包包含 Python 源码，不包含冻结的 Python 二进制文件或 RoboCasa 环境。IsOS 在 Apply 和 Run 校验所选解释器和资源路径；启动器还要求解释器可执行。缺少 Python 模块或环境不兼容时，worker 在健康检查就绪前启动失败。只选原生服务时不要求 Python。

## 已验证场景与设备资源

`package-resources.json` 使用 `contract:"isos.package-resources@v1"`、字符串 `schema_version:"0.1.0"` 和必需的 `resources` 数组。资源 ID 是稳定选择器，不是可执行路径或图身份。构建器从已检查的原生场景/设备描述符生成目录；IsOS 在 Run 前验证归档文件与所选资源。

| 资源字段 | 类型 / 单位 | 含义、默认与验证 |
| --- | --- | --- |
| `kind` | 字符串 / — | 必需，`scene` 或 `device`，无默认。 |
| `id` | 字符串 / — | 必需且唯一的稳定资源 ID，无默认。 |
| `label`, `description` | 字符串 / — | 必需且非空的展示文本，无默认且不授予执行权限。 |
| 场景 `path` | 字符串 / 包内相对路径 | 必需、受包含约束的普通 MJCF 文件；拒绝路径穿越或符号链接逃逸。 |
| 场景 `sha256` | 字符串 / — | 必需、精确场景字节的小写 SHA-256；不匹配时拒绝选择。 |
| 设备 `metadata.device_kind` | 字符串 / — | 必需，`camera`、`base`、`manipulator` 或 `gripper`，无默认。 |
| 设备 `metadata.scene_ids` | 字符串数组 / — | 必需、非空且唯一的已声明场景引用；所选场景须支持设备。 |

原生描述符 `backend-v2.json` 另行固定 `catalog_version:"0.1.0"`、支持的场景 profile 和私有设备映射。`tools/catalog.py` 拒绝不完整元数据、未知 profile、重复 ID、缺失模型元素或摘要不符。资源目录不描述 RoboCasa Gym 环境。旧精确包字节保留其描述符结构；schema 和包发布版本相互独立。


## 当前包装器准入（schema 0.2.2）

尚未发布的 0.2.8 候选包使用清单 schema `0.2.2`。软件包保持仅硬件范围：七种 EOS 硬件类型、两组设备预设和两个由 IsOS 监督的服务。图 `0.3.1`、端口载荷与 `isos_node_v2` 独立且不变。软件包没有需要文本编辑器或 Unicode 长度约束的节点字符串设置，因此不声明节点扩展，也不要求 `node-extensions-v1`。场景、任务和种子仍是共享服务配置。

当前相机宽高设置是 64–2048 px 的必填整数；预设显式提供 1280 × 720。由于服务交接要求已保存节点设置中存在实际值，类型不声明默认值。RoboCasa 任务和种子是软件包配置的必填字段。种子为无符号 32 位整数（0–4294967295），表单和 TOML 模板均使用 42；worker 在创建 Gym 前也拒绝越界种子。表单默认值不替代缺失的 TOML 值。

`./build.sh --output ABSOLUTE_EMPTY_DIRECTORY` 选择当前源码候选版本；`--version 0.2.x` 可选择规范格式的后续未发布候选版本。两个构建入口均拒绝低于当前候选版本的历史版本，因为当前配置与接口不能重建这些历史发行包。本地发行标签不阻止显式选择的源码构建，包括干净 HEAD 变化后重新构建已登记的源码版本。这些构建仍是本地源码候选；IsOS 资格验证和发布检查负责未占用目录版本、已发布标签及发行工件的不可变性。

运行 `python3 tests/nodes.py`、`python3 tests/build_env.py`、`python3 tests/config_modes.py`、`python3 tests/robocasaworker.py` 和 `python3 tests/bundle.py BUILD/eos-mujoco-sim MUJOCO_ROOT`，检查声明、调用方式、配置隔离、worker 失败与 Stop，以及当前归档迁移。归档检查验证配置和资源摘要、设置助手与可执行服务入口，随后检查原生采集、拒绝、Stop 和缺失 RoboCasa 解释器。完整资格验证仍需在干净源码上运行 `isos pkg check`，提供两个服务的图和部署本地软件包配置。

0.2.8 候选通过原始复合控制器发现支持的 RoboCasa 全身部件。[全身准备工具](core/robocasa_cn.md)生成精确硬件、Dispatcher 和模型动作声明，并固定运行时 manifest 摘要。固定 preset 保持为兼容示例。服务配置新增必填 robot 模型；躯干 observation 使用真实 joint_channels@v0.1，保留移动/转动关节单位。

## 本地候选资格验证，2026 年 11 月 22 日

从源码 `d0d6cda4b4cdc50849498f8f54f73231e3c36428` 构建的未发布0.2.8候选，针对完整原生服务图与自动发现的 PandaOmron 服务图，通过当前 IsOS 软件包资格验证。归档 SHA-256 为 `b125e54a8db1867ebd67148199f777bbf65675d21b9081c2838610ce5097f3d2`；资格 SHA-256 为 `2ff22a77f0adbac94af9ad54cfdc0244988ee9ca7e5fdbefa6b6c4eb85ab9808`。检查覆盖精确 Apply/readiness、全部类型化观测/动作、身份拒绝与去重、子进程失败、确认 Stop、socket 清理及必需服务/EOS 日志身份。完整本地证据保留在忽略目录 `data/test/20261122-body/qualification-clock-stable/`，`tests/package_logs.py` 通过。

候选包含显式观测采集时钟、暂停世界保留真实仿真采样时间，以及24步有界初始 Stop 稳定窗口，连续两次测量证明的容差不变。独立空闲 worker 测试在没有先发运动命令时确认 Stop。固定底座 `Panda` 对当前固定厨房仍未验证，因为 reset 要求移动底盘 yaw 关节。可选不支持控制器保持不可用；本地资格验证不代表发布标签/版本或自主任务成功。复现命令见[开发验证](development_cn.md)。

当前 0.2.8 相机节点提供 1280 × 720 默认值及可调 JPEG 质量/采样频率，新增独立自由旁观相机；详细接口见 [相机节点](node/eos/hardware/camera_cn.md)。

## 相机候选验证，2026-11-23

源码 `258b4163046c65d78f692bf654b2a34b69bf4f66` 通过当前 IsOS 隔离 `pkg check`，覆盖完整原生与四相机 RoboCasa 图。静态验证、原生 ABI、owner 准入、托管观测/命令/拒绝、服务故障、关联日志与确认 Stop 均通过。归档 SHA-256 为 `b0a8a4ef8ef984dd6257eae79b8ea2dafcc9196706488680bc98a2663b55057e`；验证 SHA-256 为 `5e89da04c4bb8edd3cf1364c83f2583e3f5af3abdc7d093f99e28ed35706b615`。`tests/package_logs.py` 对两套图均通过。完整证据保存在忽略目录 `data/test/20261123-camera-node/qualification/`。这是本地 0.2.8 候选验证，不代表发布或模型完成任务。
