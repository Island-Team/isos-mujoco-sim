# 模拟器交互角色映射

[English](../../../docs/mujoco/design/interaction-nodes.md) · [设计目录](README_cn.md) · [运行控制](../interfaces/control_cn.md)

**目标设计——尚未实现。** IsOS 提议在类型化图路由的每项交互上声明调用方/响应方及发布方/订阅方角色。本文把该设计映射到当前 MuJoCo 软件包，不改变其 socket、软件包、节点 ID 或 benchmark 边界。[IsOS 交互设计](https://github.com/Island-Team/isos-p/blob/docs/interaction-node-roles/docs_cn/isos/design/interaction-nodes_cn.md)拥有图层提案；MuJoCo 仍只拥有其[私有模拟器协议](../interfaces/control_cn.md)。

## 当前边界

模拟器响应有界的私有设备请求。EOS 通过选中的适配器，是唯一面向机器人的调用方。相机拍摄或设备观测即使回复中包含图像或状态，仍是请求与回复。EOS 验证并转换回复，然后可在已准入的图输出上发布类型化观测。MuJoCo 本身没有图发布方或订阅方端口。运动只能在 EOS Dispatcher 准入后到达模拟器；私有 benchmark 评分仅供评估方使用。

| 交换 | 面向图的解释 | 归属与约束 |
| --- | --- | --- |
| EOS 健康或观测请求 → MuJoCo 回复 | EOS 适配器是调用方，模拟器是响应方。随后 EOS 可发布经过检查的观测。 | MuJoCo 拥有请求成帧和设备检查；EOS 拥有图路由与新鲜度检查。 |
| EOS 已准入运动请求 → MuJoCo 回复 | EOS 适配器是调用方，模拟器是响应方。回复是一次命令结果，不是观测发布。 | EOS Dispatcher 拥有授权、持久命令身份与结果处理；MuJoCo 执行自己的严格设备和 generation 检查。 |
| EOS 受控 Stop → MuJoCo Stop 证明 | 归属方生命周期操作，不属于普通图发布。 | EOS 验证各执行器证明并回收其直接监管的模拟器子进程；IsOS 另行监管其拥有的软件包服务子进程。 |
| 评估方 benchmark 请求 → benchmark 回复 | 没有图角色。 | 仅可信评估方可用；结果与评分真值不能进入 EOS 或 EI 推理路由。 |

## 软件包影响

未来的软件包贡献只有在 IsOS 和 EOS 定义并实现匹配的版本化交互声明与路由适配器之后，才能声明相机观测源或设备请求服务。软件包不得根据 `camera_capture`、`base_observe`、HTTP GET/POST 或 socket 方向推断图角色。其逻辑节点类型仍是模拟器支持的设备；一项注册交互可以面向调用方，另一项则可以面向发布方。端点地址与子进程 generation 针对选中的运行解析，不能写入图的原始内容。

第一项跨仓库检查应通过现有严格 socket 拍摄图像，在 EOS 验证，传送给已声明的订阅方，并在拍摄待处理时停止运行。在声明支持前，应拒绝不可用服务、过期运行或修订、错误设备、无效图像、阻塞的消费者与缺失路由。独立的运动检查必须证明新调用方角色不会绕过 EOS Dispatcher，并且不会用新的命令 ID 重试结果不确定的回复。

## 设计验证

从 MuJoCo 仓库根目录运行 `git diff --check`，并检查四个改动 Markdown 文件的相对链接，均通过，断链为零。使用同级 IsOS 仓库的 `scripts/check_doc_links.py` 检查全部 58 个 Markdown 文件时，发现五个本次改动之外的已有锚点错误。日志和检查命令保存在被忽略的 `data/test/20261115-interaction-node-roles/`。
