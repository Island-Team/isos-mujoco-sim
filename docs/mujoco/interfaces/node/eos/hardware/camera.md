# EOS camera node

[Interface index](../../../README.md) · [Design](../../../../design/eos/hardware/camera.md) · [Runtime control](../../../control.md) · [中文](../../../../../../docs_cn/mujoco/interfaces/node/eos/hardware/camera_cn.md)

`eos.hardware.camera.device@v0.2` is a read-only camera node. The native preset offers one JPEG view of the MuJoCo scene; the RoboCasa preset offers three RGB8 views of the PandaOmron robot. Select a preset to choose the actual camera devices. The type advertises both `jpeg` and `rgb8`; each instance advertises only the encoding it supplies.

| Preset / node ref | Device ID | Frame |
| --- | --- | --- |
| `native/front` | `cam-0` | JPEG image from the selected `pick-place` or `navigation` scene |
| `robocasa/left` | `robocasa/camera/agentview-left` | RGB8 agent view |
| `robocasa/right` | `robocasa/camera/agentview-right` | RGB8 agent view |
| `robocasa/wrist` | `robocasa/camera/eye-in-hand` | RGB8 eye-in-hand view |

## Port and frame

`cam-0` is the stable device ID of the native renderer shared by the two native scenes, rather than a camera name inferred from RoboCasa. Native MuJoCo captures and JPEG-encodes that render; the separate RoboCasa Gym worker supplies raw RGB8 arrays from three named cameras. The adapter chooses the service and exact device before decoding a frame, so a native scene or camera failure cannot silently select a RoboCasa camera or change another node's encoding.

There is no command input. EOS requests an observation and the adapter emits `frame: image_frame@v0.2` as an in-process event. The frame payload has `width_px`, `height_px`, `encoding`, base64 `data`, and a `sample` with `source_time_ns`, `sequence`, `clock`, and `frame_id`. Native `encoding:"jpeg"` uses the simulation clock; RoboCasa `encoding:"rgb8"` uses the host monotonic clock. RoboCasa data decodes to exactly `width_px × height_px × 3` bytes in row-major RGB order. Its configured width and height are each 64–2048 px. Native dimensions come from the selected camera render. A frame includes no task text, reward, or success truth.

A representative emitted frame (shortened image bytes) is:

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
    "width_px": 640,
    "height_px": 480,
    "encoding": "jpeg",
    "data": "/9j/4AAQ"
  }
}
```

The `data` value above is illustrative. The native preset advertises at most 30 frames/s and a 12,582,912-byte observation payload. Each RoboCasa camera advertises at most 30 frames/s and 20 MiB; the worker's raw RGB8 socket payload is separately bounded at 12 MiB. These are admission and payload ceilings, not promised frame rates.

## Readiness and failure

The verified instance binds `service_instance` and `device_id`; neither defaults to another camera. EOS checks service health before publishing `frame`. Native strict health includes a real camera render probe. Invalid dimensions, wrong encoding, a byte-count mismatch, unavailable EGL/JPEG, a missing RoboCasa image, or a service exit makes observation fail; the adapter does not emit a fabricated frame. A camera Stop quiesces callbacks and has no actuator stop request. See [runtime control](../../../control.md) for framing and service errors.
