# 软件包架构

[English](../docs/architecture.md) · [Docs](README_cn.md)

本包通过已验证 IsOS 包声明提供原生 C++ MuJoCo 服务和隔离的 Python RoboCasa 服务。服务向 EOS 提供机器人观察和已准入执行。EGIA 与其他代理通过 EOS 操作，不能获得评测真值。

## 所有权与数据流

| 组件 | 职责 |
| --- | --- |
| IsOS | 验证精确包字节，在 Apply 绑定配置与所选资源，启动所选服务，捕获输出并监督服务子进程。 |
| EOS | 加载已验证适配器，检查设备健康，发布准入后的观察，经 Dispatcher 准入运动并判定 Stop 证明。 |
| 原生服务 | 加载所选 MJCF，检查设备和代际，推进物理，渲染 JPEG 并执行原生停止屏障。 |
| RoboCasa 服务 | 拥有一个 Gym 环境，串行处理有界硬件命令，返回 RGB8 相机数据和实测机器人状态，提供绑定运行的 Stop 结果。 |
| 可信评测器 | 通过独立直接启动边界控制私有评测回合并读取分数。 |

图节点选择精确包、适配器、服务实例和设备。IsOS 验证选择并解析私有端点；EOS 只读已应用配置。物理变化前命令依次经过 Dispatcher 准入、适配器验证和服务验证。回复表达命令结果；节点观察有独立发布路径。

原生 `cam-0` 渲染所选原生场景的 JPEG。RoboCasa 私有套接字返回 RGB8，当前适配器将其编码为 JPEG 后输出 `frame`。相机交付序号属于各适配器实例，不证明缓存场景像素发生变化。详见[相机组](node/eos/hardware/camera_cn.md)。

## 生命周期与故障

托管流程为选择与配置 → Validate → Apply → Run → 设备健康 → 准入控制 → Stop。Apply 不启动服务。依赖缺失、设备无效、渲染失败或服务退出都会阻止成功就绪或观察。EOS 先关闭准入并请求 Stop 证明，IsOS 再终止服务子进程。超时、崩溃或部分证明仍为未知，即使进程随后退出。重建候选或修改配置后须重新 Apply 与 Run。

原生严格服务使用代际身份、命令结果保留和伴随停止通道。RoboCasa 工作进程串行推进 Gym 并锁存绑定运行的停止结果。精确差异、边界和错误由[适配器控制](core/adapter_cn.md)拥有。传输访问或图连接本身不能授予运动权限。

## 源码与兼容

`src/mujoco/` 拥有原生引擎，`src/isos/` 拥有其服务，`src/plugin/` 拥有适配器，`robocasa_core/` 与 `tools/robocasa_worker.py` 拥有 RoboCasa 边界。[核心索引](core/README_cn.md)链接各实现和契约页。历史 EOS 子进程节点及验收记录见[变更记录](changelog_cn.md)，不代表当前 IsOS 服务模型。

源码、包发布、图格式、节点类型、原生 ABI、套接字协议和 protobuf 命名空间独立版本化。旧精确包锁定保留其声明；升级应检查端口与所选配置，不能修改无关版本字符串代替迁移。

<a id="模拟器交互角色映射"></a>
## 模拟器交互角色映射

**目标设计——尚未实现。** IsOS 提议在类型化图路由的每项交互上声明调用方/响应方及发布方/订阅方角色。本文把该设计映射到当前 MuJoCo 软件包，不改变其 socket、软件包、节点 ID 或 benchmark 边界。[IsOS 交互设计](https://github.com/Island-Team/isos-p/blob/docs/interaction-node-roles/docs_cn/isos/design/interaction-nodes_cn.md)拥有图层提案；MuJoCo 仍只拥有其[私有模拟器协议](core/adapter_cn.md)。

<a id="当前边界"></a>
### 当前边界

模拟器响应有界的私有设备请求。EOS 通过选中的适配器，是唯一面向机器人的调用方。相机拍摄或设备观测即使回复中包含图像或状态，仍是请求与回复。EOS 验证并转换回复，然后可在已准入的图输出上发布类型化观测。MuJoCo 本身没有图发布方或订阅方端口。运动只能在 EOS Dispatcher 准入后到达模拟器；私有 benchmark 评分仅供评估方使用。

| 交换 | 面向图的解释 | 归属与约束 |
| --- | --- | --- |
| EOS 健康或观测请求 → MuJoCo 回复 | EOS 适配器是调用方，模拟器是响应方。随后 EOS 可发布经过检查的观测。 | MuJoCo 拥有请求成帧和设备检查；EOS 拥有图路由与新鲜度检查。 |
| EOS 已准入运动请求 → MuJoCo 回复 | EOS 适配器是调用方，模拟器是响应方。回复是一次命令结果，不是观测发布。 | EOS Dispatcher 拥有授权、持久命令身份与结果处理；MuJoCo 执行自己的严格设备和 generation 检查。 |
| EOS 受控 Stop → MuJoCo Stop 证明 | 归属方生命周期操作，不属于普通图发布。 | EOS 验证各执行器证明，IsOS 随后终止并回收所选包服务子进程。 |
| 评估方 benchmark 请求 → benchmark 回复 | 没有图角色。 | 仅可信评估方可用；结果与评分真值不能进入 EOS 或 EI 推理路由。 |

<a id="软件包影响"></a>
### 软件包影响

未来的软件包贡献只有在 IsOS 和 EOS 定义并实现匹配的版本化交互声明与路由适配器之后，才能声明相机观测源或设备请求服务。软件包不得根据 `camera_capture`、`base_observe`、HTTP GET/POST 或 socket 方向推断图角色。其逻辑节点类型仍是模拟器支持的设备；一项注册交互可以面向调用方，另一项则可以面向发布方。端点地址与子进程 generation 针对选中的运行解析，不能写入图的原始内容。

第一项跨仓库检查应通过现有严格 socket 拍摄图像，在 EOS 验证，传送给已声明的订阅方，并在拍摄待处理时停止运行。在声明支持前，应拒绝不可用服务、过期运行或修订、错误设备、无效图像、阻塞的消费者与缺失路由。独立的运动检查必须证明新调用方角色不会绕过 EOS Dispatcher，并且不会用新的命令 ID 重试结果不确定的回复。

实施工作见[交互路线验收 TODO](development_cn.md#interaction-route-todo)。
