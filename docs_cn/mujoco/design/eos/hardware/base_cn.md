# EOS 硬件设计：base

[节点接口](../../../interfaces/node/eos/hardware/base_cn.md) · [核心设计](../../core/mujoco_cn.md)

IsOS 校验包与服务配置，EOS 仅在服务健康、设备匹配后公开端口。执行器命令经过 Dispatcher 准入，停止时先关闭准入并验证服务的停止结果；失败时保留未知结果。
