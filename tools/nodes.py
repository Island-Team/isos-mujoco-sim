"""Declarative EOS node types and graph set shipped with the MuJoCo package."""


BACKEND = "eos.process.mujoco.simulator@v0.2"
CAMERA = "eos.hardware.camera.device@v0.2"


def node_type(id: str, layer: str, kind: str, lifecycle: str,
              capabilities: list[str], inputs: list[dict], outputs: list[dict],
              settings: list[dict] | None = None,
              safety_adapter_type: str | None = None) -> dict:
  return {
    "id": id,
    "core": "eos",
    "layer": layer,
    "group": "mujoco",
    "kind": kind,
    "lifecycle": lifecycle,
    "capabilities": capabilities,
    "settings": settings or [],
    "inputs": inputs,
    "outputs": outputs,
    "safety_adapter_type": safety_adapter_type,
  }


def setting(name: str, data_type: str, required: bool = False,
            description: str | None = None, selector: dict | None = None) -> dict:
  result = {"name": name, "data_type": data_type, "required": required}
  if description is not None:
    result["description"] = description
  if selector is not None:
    result["selector"] = selector
  return result


def hardware_profile(id: str, type_id: str, label: str, description: str,
                     frame_id: str, capabilities: list[str], device_id: str,
                     max_rate_hz: float, max_payload_bytes: int, version: str) -> dict:
  return {
    "id": id,
    "node_type": type_id,
    "label": label,
    "description": description,
    "frame_id": frame_id,
    "capabilities": capabilities,
    "references": ["@simulator"],
    "adapter": {
      "type": "mujoco-v2",
      "package": {"id": "island/mujoco-sim", "version": version},
      "settings": {
        "backend": "@simulator",
        "socket_path": "${socket}",
        "simulator_node": device_id,
        "device_id": device_id,
      },
    },
    "health_timing": {"poll_interval_ms": 100, "stale_after_ms": 500},
    "observation": {"max_rate_hz": max_rate_hz, "max_payload_bytes": max_payload_bytes},
  }


def contributions(version: str = "0.2.0") -> dict:
  if version != "0.2.0":
    return full_hardware_contributions(version)
  camera = hardware_profile(
    "front", CAMERA, "Front JPEG camera", "MuJoCo JPEG camera frame",
    "front_camera_optical", ["jpeg"], "${camera_device}", 30.0, 12582912, version,
  )
  current = node_type(
    BACKEND, "process", "software", "process", ["process"], [],
    [],
    [setting("scene", "string", True, "Stable verified scene ID",
             {"provider": "package", "resource": "scene", "package_from": "node.package"}),
     setting("socket", "string", True, "Owner-only simulator Unix socket path"),
     setting("env", "string_table", description="Simulator child environment references"),
     setting("start_timeout_ms", "positive_integer",
             description="Simulator readiness deadline in milliseconds")],
  )
  current["implementation"] = {"kind": "managed_process", "interface": "mujoco-v2",
                               "version": "1", "lifecycle_adapter": "mujoco-v2"}
  current["description"] = (
    "Starts one verified MuJoCo scene as an EOS-owned simulator child and supplies "
    "only the graph-declared simulated devices."
  )
  return {
    "processes": [{
      "node_type": BACKEND,
      "entrypoint": "bin/eos-mujoco-sim",
      "args": ["--managed-strict-socket", "--v2-socket", "${socket}",
               "--scene", "${resource.scene.path}"],
      "lifecycle_adapter": "mujoco-v2",
      "resources": [{"setting": "scene", "kind": "scene",
                     "descriptor": "package-resources.json"}],
      "host_inputs": [{"name": "MUJOCO_ROOT", "kind": "directory",
                       "required": True}],
    }],
    "node_types": [
      current,
    ],
    "safety_adapters": [],
    "adapter_families": [{
      "id": "mujoco-v2",
      "device_kinds": ["camera", "base", "manipulator"],
      "transport": "unix_socket",
      "description": "EOS-owned MuJoCo simulator socket adapter for camera, base, and manipulator devices",
      "supported_primitives": [],
    }],
    "node_sets": [{
      "id": "sim-hardware",
      "parameters": {
        "scene": {"type": "string", "default": "pick-place"},
        "camera_device": {"type": "string", "default": "cam-0"},
        "socket": {"type": "string"},
      },
      "nodes": [
        {"ref": "simulator", "core": "eos", "layer": "process", "group": "mujoco",
         "profile": {
           "id": "simulator", "node_type": BACKEND, "label": "MuJoCo simulator",
           "description": "EOS-owned simulator child from the verified package",
           "capabilities": ["process"],
           "settings": {"scene": "${scene}", "socket": "${socket}"},
         }},
        {"ref": "front", "core": "eos", "layer": "hardware", "group": "camera",
         "profile": camera},
      ],
    }],
  }


def full_hardware_contributions(version: str) -> dict:
  """Package presets contain devices; IsOS activates their service implicitly."""
  native = (
    ("front", "camera", CAMERA, "cam-0", ["jpeg"], 30.0, 12582912),
    ("drive", "base", "eos.hardware.base.device@v0.2", "base-0", ["body_velocity"], 50.0, 65536),
    ("arm", "manipulator", "eos.hardware.manipulator.device@v0.2", "arm-0", ["joint_positions"], 50.0, 65536),
    ("gripper", "gripper", "eos.hardware.gripper.binary@v0.2", "gripper-0", ["binary"], 50.0, 65536),
  )
  robocasa = (
    ("left", "camera", CAMERA, "robocasa/camera/agentview-left", ["rgb8"], 30.0, 12582912),
    ("right", "camera", CAMERA, "robocasa/camera/agentview-right", ["rgb8"], 30.0, 12582912),
    ("wrist", "camera", CAMERA, "robocasa/camera/eye-in-hand", ["rgb8"], 30.0, 12582912),
    ("mobile", "base", "eos.hardware.base.normalized_axes@v0.2", "robocasa/base/mobile-base", ["normalized_axes"], 50.0, 65536),
    ("right-arm", "manipulator", "eos.hardware.manipulator.normalized_cartesian@v0.2", "robocasa/arm/right-arm", ["normalized_cartesian"], 50.0, 65536),
    ("hand", "gripper", "eos.hardware.gripper.binary@v0.2", "robocasa/gripper/right-gripper", ["binary"], 50.0, 65536),
    ("lift", "torso", "eos.hardware.torso.normalized_axes@v0.2", "robocasa/torso/torso", ["normalized_axes"], 50.0, 65536),
  )

  def profile(ref: str, kind: str, type_id: str, device: str, capabilities: list[str],
              rate: float, size: int, service: str) -> dict:
    item = hardware_profile(ref, type_id, device, f"{service} {kind} device", device,
                            capabilities, device, rate, size, version)
    item["references"] = []
    item["adapter"]["settings"] = {"service_instance": service, "device_id": device}
    if kind == "torso":
      item.pop("observation", None)
    if kind != "camera":
      mode = capabilities[0]
      limits = {
        "body_velocity": {"max_linear_m_s": 1.0, "max_angular_rad_s": 1.5,
                          "max_velocity_lease_ms": 1000},
        "joint_positions": {"max_joint_position_rad": 3.14, "max_joint_speed_rad_s": 1.0},
        "normalized_axes": {"max_velocity_lease_ms": 1000},
        "normalized_cartesian": {"max_velocity_lease_ms": 1000},
        "binary": {},
      }[mode]
      item["movement"] = {"modes": [mode], "limits": limits}
    return item

  def preset(name: str, devices: tuple) -> dict:
    labels = {
      "native": ({"en": "Native robot", "cn": "原生机器人"},
                 {"en": "MuJoCo scene camera, base, arm and gripper", "cn": "MuJoCo 场景相机、底盘、机械臂和夹爪"}),
      "robocasa": ({"en": "RoboCasa robot", "cn": "RoboCasa 机器人"},
                   {"en": "RoboCasa cameras, mobile base, arm, gripper and torso", "cn": "RoboCasa 相机、移动底盘、机械臂、夹爪和躯干"}),
    }
    return {"id": name, "label": labels[name][0], "description": labels[name][1],
            "parameters": {}, "nodes": [
      {"ref": ref, "core": "eos", "layer": "hardware", "group": kind,
       "profile": profile(ref, kind, type_id, device, caps, rate, size, name)}
      for ref, kind, type_id, device, caps, rate, size in devices]}

  return {
    "processes": [],
    "node_types": [],
    "safety_adapters": [],
    "adapter_families": [{
      "id": "mujoco-v2", "device_kinds": ["camera", "base", "manipulator", "gripper", "torso"],
      "transport": "unix_socket",
      "description": "IsOS-supervised native MuJoCo or isolated RoboCasa hardware service",
      "supported_primitives": [],
    }],
    "runtime_services": [
      {"id": "native", "entrypoint": "bin/eos-mujoco-sim",
       "args": ["--managed-strict-socket", "--v2-socket", "${socket}",
                "--scene", "${resource.scene.path}"],
       "requirements": [{"path": "${config.host.mujoco_root}/lib/libmujoco.so.3.3.1", "kind": "file"}],
       "environment": [{"name": "LD_LIBRARY_PATH",
                        "value": "${config.host.mujoco_root}/lib"}],
       "resources": [{"setting": "scene", "kind": "scene",
                      "descriptor": "package-resources.json"}],
       "config_service_type": "native", "node_types": sorted({item[2] for item in native})},
      {"id": "robocasa", "entrypoint": "bin/robocasa-worker",
       "args": ["--socket", "${socket}"], "config_service_type": "robocasa",
       "environment": [
         {"name": "ISOS_PACKAGE_PYTHON", "value": "${config.host.python_interpreter}"},
         {"name": "ISOS_ROBOCASA_ASSETS", "value": "${config.host.robocasa_assets}"},
         {"name": "ISOS_ROBOCASA_TASK", "value": "${config.service.task}"},
         {"name": "ISOS_ROBOCASA_SEED", "value": "${config.service.seed}"},
         {"name": "ISOS_PACKAGE_GENERATION", "value": "${generation_id}"},
       ],
       "node_types": sorted({item[2] for item in robocasa})},
    ],
    "node_sets": [preset("native", native), preset("robocasa", robocasa)],
  }
