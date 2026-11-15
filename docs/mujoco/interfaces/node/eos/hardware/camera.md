# EOS hardware nodes: camera

[Design](../../../../design/eos/hardware/camera.md) · [Package contract](../../../package.md) · [Runtime control](../../../control.md)

EOS owns these node types; the MuJoCo package supplies their verified `isos_node_v2` adapter. IsOS admits an exact package pin and service instance before Run; EOS owns command admission, delivery, and Stop.

| Type ID | Capability | Input ports | Output ports | Safety adapter |
| --- | --- | --- | --- | --- |
| `eos.hardware.camera.device@v0.2` | `jpeg`, `rgb8` | — | `frame: image_frame@v0.2` | — |

All ports are in-process events with `required:false`. EOS admits command data against the declared type and Dispatcher policy; observations contain no benchmark reward or success data. Adapter settings `service_instance` and `device_id` are required strings without defaults and select a verified service and device. Unknown services, devices, package pins, or failed commands leave the node unavailable. EOS does not replay an action with an unknown outcome.

The native service uses JPEG; RoboCasa uses RGB8. The [runtime control contract](../../../control.md) owns payloads, bounds, units, stop proof, errors, and deadlines. When the service exits, EOS makes the ports unavailable; a new Run uses a new generation.
