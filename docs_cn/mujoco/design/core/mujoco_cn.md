# MuJoCo 核心设计

[设计目录](../README_cn.md) · [运行控制](../../interfaces/control_cn.md) · [包契约](../../interfaces/package_cn.md)

模拟器核心负责场景加载、确定性复位、物理、渲染和私有评测评分。IsOS 校验并配置精确的软件包服务；EOS 管理机器人侧命令准入、健康检查和停止。原生服务与 RoboCasa 服务均通过私有端点向适配器提供数据，评测真实状态不通过这些端点暴露。
