# 历史 EOS MuJoCo 进程节点

[接口目录](../../../README_cn.md) · [设计](../../../../design/eos/process/mujoco_cn.md) · [包声明](../../../package_cn.md) · [运行控制](../../../control_cn.md) · [English](../../../../../../docs/mujoco/interfaces/node/eos/process/mujoco.md)

`eos.process.mujoco.simulator@v0.2` 属于历史 `0.2.0` 的 `sim-hardware` 节点集。它把一个已验证 MuJoCo 场景作为 EOS 管理的子进程启动，为该节点集的 JPEG 相机提供私有服务。它是进程生命周期节点，不是代理控制或观察端口。当前完整硬件预设包含设备节点，由 IsOS 隐式启动所选运行服务，不含此进程节点。

## 位置和设置

节点为 `core:eos`、`layer:process`、`group:mujoco`、`kind:software`，生命周期和能力均为 `process`。该节点集包含此节点和 `native/front` 相机。进程类型本身无输入或输出端口。

| 设置 | 类型 / 单位 | 操作员选择 | 验证和默认值 |
| --- | --- | --- | --- |
| `scene` | 字符串 / 稳定 ID | 已验证包目录中的 `pick-place` 或 `navigation` | 必需；图不存解析后的路径；节点集默认 `pick-place`。 |
| `socket` | 字符串 / 私有 Unix 路径 | EOS 管理的子进程端点 | 必需；类型无默认值。 |
| `env` | 字符串表 / — | 子进程环境引用 | 可选；缺失时为空。 |
| `start_timeout_ms` | 正整数 / ms | 子进程就绪期限 | 类型中可选；缺失时使用 EOS 策略。 |

IsOS 验证精确包收据、场景 XML 摘要、所选场景 ID 和宿主 MuJoCo 库。EOS 从已验证包解析 `bin/eos-mujoco-sim` 和场景路径，使用 `mujoco-v2` 生命周期适配器以 `--managed-strict-socket --v2-socket ${socket} --scene ${resource.scene.path}` 启动。操作员不在节点中填写可执行文件或 benchmark 套接字路径。

## 就绪和停止

子进程必须打开仅所有者可访问的套接字，并通过图中已声明设备的严格健康检查，EOS 才公布就绪。场景缺失、库错误、相机渲染不健康、协议不兼容或子进程退出时，节点带原因保持不可用；仅有套接字存在不足以确认就绪。EOS 在停止前关闭命令准入，从伴随停止通道请求全机器人证明，证明缺失时记录未知结果，再回收子进程。改变场景需要新的图修订和子进程重启。此受管理节点不能暴露 benchmark 复位或评分。帧、错误和期限见[运行控制契约](../../../control_cn.md)。
