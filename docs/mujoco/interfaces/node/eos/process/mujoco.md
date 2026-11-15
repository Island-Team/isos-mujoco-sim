# EOS process node: MuJoCo

[Design](../../../../design/eos/process/mujoco.md) · [Package declaration](../../../package.md) · [Runtime control](../../../control.md)

The historical `0.2.0` package declares `eos.process.mujoco.simulator@v0.2`. IsOS verifies the scene resource and exact package pin; EOS starts the child with the `mujoco-v2` lifecycle adapter. New hardware presets use runtime service declarations and contain no process node.

| Setting | Type / unit | Purpose and validation | Default |
| --- | --- | --- | --- |
| `scene` | string / — | Stable verified scene ID; required | none |
| `socket` | string / path | Owner-only Unix socket; required | none |
| `env` | string table / — | Child environment references | empty |
| `start_timeout_ms` | positive integer / ms | Readiness deadline | owner policy |

Strict health failure, scene mismatch, or child exit makes the node unavailable. EOS closes command admission and confirms Stop proof before reaping the child.
