# RoboCasa hardware and replay

[中文](../../docs_cn/core/robocasa_cn.md) · [Docs](../README.md)

The Python hardware API controls one caller-owned Gym environment. The packaged worker owns its separate environment and serializes requests behind the [private service contract](adapter.md). Local recording is a control replay tool; benchmark scoring stays private.

## Discovered robot body (0.2.8 candidate)

The managed worker now constructs the raw RoboCasa environment with `[services.robocasa].robot` (default `PandaOmron`) and uses `robocasa_core.BodyHardware`. It bypasses upstream's fixed PandaOmron Gym key converter. One world contains one robot, whose controller may expose zero or several arms and grippers, an optional base and torso, and selected cameras. The legacy `Hardware` API and version-1 PandaOmron records below remain compatible.

Discovery reads the actual composite controller's action slices, controller class, normalized input and physical output scales, command frame, robot joint names/types/local axes, and available cameras. The private read-only `manifest` operation and startup `robot_manifest` log expose this bounded robot metadata, with no task reward, success, objects, or benchmark truth. Every accepted motion advances exactly one actual environment control step. Leases must cover that step; the manifest records `command_step_ms` (50 ms for the verified PandaOmron).

Supported controls are six-axis Cartesian delta arms with known base/world frames, signed binary grippers, three-axis planar bases, and one-axis torsos. Additional controller families (including whole-body IK, head/leg joint control and absolute Cartesian control) are omitted with bounded warnings. Only the pinned absolute `JOINT_POSITION` controller with fixed impedance receives its measured joint position as an unscaled hold target. Unknown absolute semantics, unknown neutral control semantics, and delta controllers whose scaled zero is nonzero reject before physics advances. This is controller compatibility discovery, not a claim that every upstream robot can load with the installed optional models and assets. Missing optional observations do not discard other available parts; missing physical state is never replaced by zero.

Arm position and quaternion are read from actual end-effector sites, transformed into the declared base/world frame. Gripper and torso channels read actual controlled joint positions: prismatic joints use metres and hinge joints radians. Torso status is no longer fabricated or absent merely because the upstream Gym converter omitted it. RGB frames use only explicitly selected cameras; render operations do not advance physics. Publication time preserves the last successful reset/step measurement time, so repeated reads do not make an old sample appear fresh.

`tools/robot_graph.py` generates `{nodes, capabilities, members, robot_manifest, robot_manifest_digest}` from a fresh selected environment. It creates one full-body Dispatcher with exact typed hardware bindings, model control schemas, frames, units, positive direction descriptions, physical controller scales and neutral payloads. Optional mode availability is recorded in the manifest but omitted from generated Dispatcher bindings until separately qualified. `members` identifies typed observation sources for the EOS combined status pool. The result is an operator preparation fragment; combine it with the IsOS/EI session and pool declarations, review and Apply it through IsOS. Generation itself grants no command authority. The graph hardware adapters pin the manifest SHA-256; a different controller manifest fails readiness, preventing stale model control descriptions from silently addressing a changed robot. Regenerate after changing robot/controller configuration.

```sh
PYTHONPATH=. .local/robocasa-venv/bin/python tools/robot_graph.py \
  --robot PandaOmron --assets /absolute/path/to/robocasa/models/assets \
  --camera-size 256 --output /absolute/path/to/robot-fragment.json
```

The `PandaOmron` preset remains a convenient fixed robot example, not the discovery mechanism. Use generated nodes for another compatible body. The managed service configuration's `robot` is required in the 0.2.8 candidate. A neutral session command is not a Stop proof: the worker's separate Stop lane fences command admission and returns `stopped` only after controlled robot joints settle within the bounded check; failure remains `unknown`.

<a id="robocasa-robot-hardware-core"></a>
## RoboCasa robot hardware core

The Python `robocasa_core.Hardware` owns one caller-supplied, pinned RoboCasa PandaOmron Gym environment. Its catalog uses layer `robocasa`; groups describe hardware functions and nodes are stable bindable endpoints. The caller owns environment creation, serializes all calls, and closes the core. This in-process API has no authentication or transport. The packaged worker exposes the hardware through a private service endpoint; its caller and admission rules are in the [control contract](adapter.md).

| Group / node ID | Command | Observation |
| --- | --- | --- |
| `arm/right-arm` | Position and rotation deltas, each 3 normalized values in `[-1,1]` | Base-relative end-effector position and quaternion |
| `gripper/right-gripper` | Close: `0` open, `1` close | Gripper joint position |
| `base/mobile-base` | 3 normalized base motion values in `[-1,1]` | Base position and quaternion |
| `torso/torso` | 1 normalized torso motion value in `[-1,1]` | None in the pinned wrapper |
| `camera/agentview-left`, `camera/agentview-right`, `camera/eye-in-hand` | None | RGB8 image, height × width × 3 |

Full IDs prefix each row with `robocasa/`. Position and rotation commands are controller inputs, not metres or radians; the upstream controller interprets them. Observed position uses metres and orientation is a quaternion in the upstream wrapper's ordering. The core checks action shapes and required observation keys when constructed; it rejects an incompatible robot profile. Camera dimensions come from the environment. The catalog reports endpoints supported by this pinned profile, and construction fails when any required endpoint is absent.

Call `reset(seed)` before control. `command_arm(position, rotation)`, `command_gripper(close)`, `command_base(motion)`, `command_torso(motion)`, and `set_control_mode(mode)` queue values for one `step()`. Control mode is `0` or `1`, passed unchanged to RoboCasa's `action.control_mode`; the pinned wrapper maps these to its two base modes. A step submits all five upstream action fields together. Unset motion is zero; unset gripper is open and mode is `0`. The queue clears before the environment step, including when that step fails. After a step failure, reset before issuing more commands. `observe()` and step results are copied robot state and camera arrays; they never include task text, reward, success, or fixture state. `close()` closes the environment and makes later control invalid.

Invalid shape, nonfinite or out-of-range motion, nonbinary gripper or mode, missing observation, and use before reset or after close raise `HardwareError`. When RoboCasa reports a terminated or truncated episode, the final step returns robot observations and further control requires reset. An upstream environment exception propagates and faults the core until reset. There is no deadline, asynchronous command, or physical stop guarantee in this in-process interface. A caller needing an emergency stop must provide that policy at its owning control layer.

`control(device_id, payload)` is the general in-process control entry point. It accepts the full `robocasa/...` device ID and an object containing that device's own fields: arm `position` and `rotation` (or `mode`), gripper `close`, and base or torso `motion`. It reads supported fields and ignores unrelated keys. A payload with no usable control field, an incomplete arm pair, or an unknown or read-only device raises `HardwareError`; an invalid supported value still fails its normal validation. `status(device_id)` returns only that device's copied measured fields. The torso reports status unavailable because the pinned wrapper has no torso measurement. Camera status returns its selected RGB8 image; camera control is unsupported. The existing specialized command methods and `observe()` remain available.

```python
hardware = Hardware(env)
hardware.reset(42)
hardware.control("robocasa/arm/right-arm", {"position": [0, 0, 0], "rotation": [0, 0, 0]})
hardware.control("robocasa/gripper/right-gripper", {"close": 0})
hardware.step()
frame = hardware.status("robocasa/camera/eye-in-hand")["eye-in-hand"]
hardware.close()
```

The package offers an isolated RoboCasa worker as an IsOS-owned runtime service. EOS hardware adapters bind the declared device IDs through the governed service endpoint. This in-process `Hardware` API remains useful for local tests; its reset and step calls are not an agent-facing route. The C++ scene catalog and EOS simulator protobuf do not describe RoboCasa.

For saving commands and checking a selected local episode, use the [record and replay interface](robocasa.md). Verification: `PYTHONPATH=. .local/robocasa-venv/bin/python -m unittest discover -s tests -p 'robocasahardware.py' -v` runs stubbed boundary tests; `PYTHONPATH=. .local/robocasa-venv/bin/python tests/robocasareplay.py` runs two fixed-seed `CloseFridge` hardware replays.

<a id="robocasa-local-hardware-record-and-replay"></a>
## RoboCasa local hardware record and replay

`EpisodeRecorder` writes a versioned local JSON record of one PandaOmron hardware episode. `load_record(path)` selects a local file, validates it, and `replay_record(hardware, record)` resets a fresh environment with the recorded seed, applies the group commands in order, and checks robot state after reset and each step. The caller owns the environment and file path. This is an in-process test interface with no network transport or authentication.

Version `1` has exact top-level fields `version`, `layer`, `profile`, `task`, `split`, `seed`, `camera_width`, `camera_height`, `initial_state`, and `steps`. `layer` is `robocasa`; `profile` is `PandaOmron`. `steps` is an ordered array of `{command,state}` entries. A command may contain `arm:{position,rotation}`, `gripper`, `base`, `torso`, and `mode`; absent groups use the hardware core's neutral values. Motion arrays and binary values have the [hardware contract's](robocasa.md) shapes and limits. Each state has `gripper_qpos` (2), `base_position` (3), `base_rotation` (4), `end_effector_position_relative` (3), and `end_effector_rotation_relative` (4), with numeric values in upstream observation units. The record contains no images, task text, reward, success, or fixture ground truth.

`EpisodeRecorder.reset()` clears previous steps and stores the initial robot state. Its group command methods validate through `Hardware`; `step()` stores only successfully applied commands and returned robot state. `save(path)` requires an existing directory and atomically replaces the selected file. `load_record` rejects unknown fields or versions, invalid shapes or values, more than 10,000 steps, and files above 8 MB. Replay compares states with absolute tolerance `1e-5` and zero relative tolerance by default, reporting the first step and state field that differs. It does not compare RGB pixels, because rendering may vary across GPU drivers. A replay mismatch is test evidence, not a benchmark score or physical safety proof.

```sh
./launch.sh --record-demo
./launch.sh --replay-record examples/robocasa/hardware-demo.json
```

The checked-in demo uses `CloseFridge`, target split, seed 42, 64×64 cameras, and two steps that exercise arm, gripper, base, torso, and control mode. `--demo` overwrites its selected path; use a different local path to keep the checked-in example intact. `--replay` reads only the path supplied by the caller and constructs a fresh RoboCasa environment from that record's identity. The record does not include asset or source hashes, so reproducibility assumes the pinned local RoboCasa and asset set. Keep benchmark evaluation metadata and scoring in the private benchmark path.

<a id="local-recording-configuration"></a>
### Local recording configuration
Set `[record].enabled` (boolean, default `false`) and `[record].path` (nonempty path, default `.run/hardware-record.json`) in `config/benchmarks/robocasa.toml`. Relative paths resolve from the repository root. Exported `BENCHMARK_RECORD_ENABLED` and `BENCHMARK_RECORD_PATH` in `.env` override them. `./launch.sh --record-demo` uses the configured path; `--record-demo FILE` overrides it for one run. A write request fails while recording is disabled; `--replay-record FILE` can still read an existing record. The default path gets a private parent directory and the writer uses umask `0077`.

```sh
./launch.sh --record-demo
./launch.sh --replay-record .run/hardware-record.json
```

Verification: `PYTHONPATH=. .local/robocasa-venv/bin/python -m unittest discover -s tests -p 'robocasarecord.py' -v` covers local save/load, selected replay, malformed records, and state drift. The CLI command above verifies the demo against the real environment.
