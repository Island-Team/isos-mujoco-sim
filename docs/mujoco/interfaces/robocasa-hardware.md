# RoboCasa robot hardware core

[RoboCasa benchmark](../benchmarks/Robocasa/README.md) · [中文](../../../docs_cn/mujoco/interfaces/robocasa-hardware_cn.md)

The Python `robocasa_core.Hardware` owns one caller-supplied, pinned RoboCasa PandaOmron Gym environment. Its catalog uses layer `robocasa`; groups describe hardware functions and nodes are stable bindable endpoints. The caller owns environment creation, serializes all calls, and closes the core. This in-process interface has no authentication or transport. EOS and IsOS wrappers are not implemented.

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

```python
hardware = Hardware(env)
hardware.reset(42)
hardware.command_arm([0, 0, 0], [0, 0, 0])
hardware.command_gripper(0)
robot = hardware.step()
frame = robot["eye-in-hand"]
hardware.close()
```

**Target design — not implemented:** a RoboCasa process node will own environment lifecycle, and EOS hardware nodes will bind to the stable catalog IDs through a governed adapter. IsOS package and graph composition will follow that process contract. The current C++ scene catalog and EOS simulator protobuf do not describe this core.

For saving commands and checking a selected local episode, use the [record and replay interface](robocasa-record.md). Verification: `PYTHONPATH=. .local/robocasa-venv/bin/python -m unittest discover -s tests -p 'robocasahardware.py' -v` runs stubbed boundary tests; `PYTHONPATH=. .local/robocasa-venv/bin/python tests/robocasareplay.py` runs two fixed-seed `CloseFridge` hardware replays.
