# RoboCasa local hardware record and replay

[Hardware core](robocasa-hardware.md) · [RoboCasa benchmark](../benchmarks/Robocasa/README.md) · [中文](../../../docs_cn/mujoco/interfaces/robocasa-record_cn.md)

`EpisodeRecorder` writes a versioned local JSON record of one PandaOmron hardware episode. `load_record(path)` selects a local file, validates it, and `replay_record(hardware, record)` resets a fresh environment with the recorded seed, applies the group commands in order, and checks robot state after reset and each step. The caller owns the environment and file path. This is an in-process test interface with no network transport or authentication.

Version `1` has exact top-level fields `version`, `layer`, `profile`, `task`, `split`, `seed`, `camera_width`, `camera_height`, `initial_state`, and `steps`. `layer` is `robocasa`; `profile` is `PandaOmron`. `steps` is an ordered array of `{command,state}` entries. A command may contain `arm:{position,rotation}`, `gripper`, `base`, `torso`, and `mode`; absent groups use the hardware core's neutral values. Motion arrays and binary values have the [hardware contract's](robocasa-hardware.md) shapes and limits. Each state has `gripper_qpos` (2), `base_position` (3), `base_rotation` (4), `end_effector_position_relative` (3), and `end_effector_rotation_relative` (4), with numeric values in upstream observation units. The record contains no images, task text, reward, success, or fixture ground truth.

`EpisodeRecorder.reset()` clears previous steps and stores the initial robot state. Its group command methods validate through `Hardware`; `step()` stores only successfully applied commands and returned robot state. `save(path)` requires an existing directory and atomically replaces the selected file. `load_record` rejects unknown fields or versions, invalid shapes or values, more than 10,000 steps, and files above 8 MB. Replay compares states with absolute tolerance `1e-5` and zero relative tolerance by default, reporting the first step and state field that differs. It does not compare RGB pixels, because rendering may vary across GPU drivers. A replay mismatch is test evidence, not a benchmark score or physical safety proof.

```sh
PYTHONPATH=. .local/robocasa-venv/bin/python tools/robocasarecord.py --demo examples/robocasa/hardware-demo.json
PYTHONPATH=. .local/robocasa-venv/bin/python tools/robocasarecord.py --replay examples/robocasa/hardware-demo.json
```

The checked-in demo uses `CloseFridge`, target split, seed 42, 64×64 cameras, and two steps that exercise arm, gripper, base, torso, and control mode. `--demo` overwrites its selected path; use a different local path to keep the checked-in example intact. `--replay` reads only the path supplied by the caller and constructs a fresh RoboCasa environment from that record's identity. The record does not include asset or source hashes, so reproducibility assumes the pinned local RoboCasa and asset set. Keep benchmark evaluation metadata and scoring in the private benchmark path.

Verification: `PYTHONPATH=. .local/robocasa-venv/bin/python -m unittest discover -s tests -p 'robocasarecord.py' -v` covers local save/load, selected replay, malformed records, and state drift. The CLI command above verifies the demo against the real environment.
