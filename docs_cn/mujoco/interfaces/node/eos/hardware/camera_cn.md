# EOS 相机节点

[接口目录](../../../README_cn.md) · [设计](../../../../design/eos/hardware/camera_cn.md) · [运行控制](../../../control_cn.md) · [English](../../../../../../docs/mujoco/interfaces/node/eos/hardware/camera.md)

`eos.hardware.camera.device@v0.2` 是只读相机节点。原生预设提供一个 MuJoCo 场景 JPEG 画面；RoboCasa 预设提供三个 PandaOmron RGB8 画面。预设决定具体设备。类型声明 `jpeg` 和 `rgb8`，每个实例只声明实际提供的编码。

| 预设 / 节点引用 | 设备 ID | 画面 |
| --- | --- | --- |
| `native/front` | `cam-0` | 所选 `pick-place` 或 `navigation` 场景的 JPEG |
| `robocasa/left` | `robocasa/camera/agentview-left` | RGB8 代理视角 |
| `robocasa/right` | `robocasa/camera/agentview-right` | RGB8 代理视角 |
| `robocasa/wrist` | `robocasa/camera/eye-in-hand` | RGB8 眼在手上视角 |

## 端口和画面

`cam-0` 是两个原生场景共用渲染器的稳定设备 ID，并非从 RoboCasa 相机名称推断而来。原生 MuJoCo 捕获画面并编码为 JPEG；独立的 RoboCasa Gym worker 从三台具名相机提供原始 RGB8 数组。适配器在解码帧前按服务和准确设备绑定，因此原生场景或相机故障不会暗中改选 RoboCasa 相机，也不会改变其他节点的编码。

没有命令输入。EOS 请求观察，适配器通过进程内事件端口 `frame: image_frame@v0.2` 发出结果。负载含 `width_px`、`height_px`、`encoding`、base64 `data`，以及包含 `source_time_ns`、`sequence`、`clock`、`frame_id` 的 `sample`。原生 `encoding:"jpeg"` 使用模拟时钟；RoboCasa `encoding:"rgb8"` 使用主机单调时钟。RoboCasa 数据解码后恰好为 `width_px × height_px × 3` 字节，按行排列 RGB。配置宽高各为 64–2048 px。原生尺寸来自所选相机渲染。画面不含任务文本、奖励或成功真值。

在 0.2.5 及之后的软件包中，每个相机节点通过 `settings.camera_width` 和 `settings.camera_height` 设置 64 到 2048 的整数像素数。两套预设均为 1280 × 720。IsOS 在 Run 时将原生 `cam-0` 的已选设置传给模拟器；EGL 视口和 JPEG 编码器使用该准确尺寸。三个 RoboCasa 相机可分别选择输出尺寸，其设置传给独立的 Gym 工作进程。没有 IsOS 设置的直接模拟器运行使用场景的离屏尺寸。

注册的 `frame` 输出声明图像数据类别和 30 Hz 预期源频率。每个预设相机将 `node.adapter.settings.frequency_hz` 设为 30 Hz，使 EOS 把采集帧送入来源池。服务或渲染较慢时，实际帧率可以低于该值。

典型输出画面，图像字节已缩短：

```json
{
  "port": "frame",
  "payload": {
    "sample": {
      "source_time_ns": 100000000,
      "sequence": 4,
      "clock": "simulation",
      "frame_id": "cam-0"
    },
    "width_px": 1280,
    "height_px": 720,
    "encoding": "jpeg",
    "data": "/9j/4AAQ"
  }
}
```

示例 `data` 仅用于说明字段。原生预设声明最高 30 帧/秒和 12,582,912 字节观察负载。每个 RoboCasa 相机声明最高 30 帧/秒和 20 MiB；worker 的原始 RGB8 套接字负载另有 12 MiB 上限。这些是准入和负载上限，不保证实际帧率。

## 就绪和失败

已验证实例绑定 `service_instance` 和 `device_id`，不会回退到其他相机。EOS 检查服务健康后才公开 `frame`。原生严格健康检查包含实际渲染探测。尺寸无效、编码错误、字节数不符、EGL/JPEG 不可用、RoboCasa 图像缺失或服务退出时观察失败；适配器不伪造画面。相机 Stop 使回调静止，无执行器停止请求。帧格式和服务错误见[运行控制](../../../control_cn.md)。
