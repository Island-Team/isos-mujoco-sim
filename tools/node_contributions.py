"""Declarative EOS node types and graph set shipped with the MuJoCo package."""


BACKEND = "eos.process.mujoco@v0.1"
LEGACY_BACKEND = "eos.process.mujoco@v1.0"
CAMERA = "eos.hardware.camera@v0.1"
BASE = "eos.hardware.base@v0.1"
MANIPULATOR = "eos.hardware.manipulator@v0.1"
CAMERA_GATE = "eos.interface.camera_gate@v0.1"
BASE_PRIMITIVE = "eos.dispatcher.primitive_base@v0.1"
MANIPULATOR_PRIMITIVE = "eos.dispatcher.primitive_manipulator@v0.1"


def port(name: str, data_type: str, required: bool = False,
         description: str = "", expected_rate_hz: float | None = None,
         data_class: str = "state") -> dict:
  result = {"name": name, "data_type": data_type, "required": required,
            "description": description, "transport": "in_process",
            "data_class": data_class}
  if expected_rate_hz is not None:
    result["expected_rate_hz"] = expected_rate_hz
  return result


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
                     max_rate_hz: float, max_payload_bytes: int) -> dict:
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
      "package": {"id": "island/mujoco-sim", "version": "0.1.1"},
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


def contributions() -> dict:
  camera = hardware_profile(
    "front", CAMERA, "Front RGB camera", "MuJoCo JPEG camera decoded to RGB8",
    "front_camera_optical", ["rgb8"], "${camera_device}", 30.0, 8388608,
  )
  base = hardware_profile(
    "drive", BASE, "Planar base", "MuJoCo base velocity controller",
    "base_link", ["body_velocity"], "${base_device}", 50.0, 4096,
  )
  base["movement"] = {
    "modes": ["body_velocity"],
    "limits": {"max_linear_m_s": 1.0, "max_angular_rad_s": 1.5,
               "max_velocity_lease_ms": 500},
  }
  base["inputs"] = {"command": [{"node": "@base-velocity", "output": "command"}]}
  arm = hardware_profile(
    "arm", MANIPULATOR, "Six axis arm", "MuJoCo six-joint position controller",
    "arm_base", ["joint_positions"], "${manipulator_device}", 50.0, 4096,
  )
  arm["joint_names"] = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]
  arm["movement"] = {
    "modes": ["joint_positions"],
    "limits": {"max_joint_position_rad": 3.14, "max_joint_speed_rad_s": 1.0},
  }
  arm["inputs"] = {"command": [{"node": "@arm-movej", "output": "command"}]}
  legacy = node_type(
    LEGACY_BACKEND, "process", "software", "process", ["process"], [],
    [port("status", "status", description="Simulator process lifecycle"),
     port("health", "health", description="Simulator process health")],
    [setting("scene", "string", True), setting("socket", "string", True),
     setting("env", "string_table"), setting("start_timeout_ms", "positive_integer")],
  )
  current = node_type(
    BACKEND, "process", "software", "process", ["process"], [],
    [port("status", "status", description="Simulator process lifecycle"),
     port("health", "health", description="Simulator process health")],
    [setting("scene", "string", True, "Stable verified scene ID",
             {"provider": "package", "resource": "scene", "package_from": "node.package"}),
     setting("socket", "string", True, "Owner-only simulator Unix socket path"),
     setting("env", "string_table", description="Simulator child environment references"),
     setting("start_timeout_ms", "positive_integer",
             description="Simulator readiness deadline in milliseconds")],
  )
  current["description"] = (
    "Starts one verified MuJoCo scene as an EOS-owned simulator child and supplies "
    "only the graph-declared simulated devices."
  )
  return {
    "node_types": [
      legacy,
      current,
    ],
    "safety_adapters": [],
    "adapter_families": [{
      "id": "mujoco-v2",
      "device_kinds": ["camera", "base", "manipulator"],
      "transport": "unix_socket",
      "description": "EOS-owned MuJoCo simulator socket adapter for camera, base, and manipulator devices",
      "supported_primitives": ["base.velocity@1.0.0", "arm.movej@1.0.0"],
    }],
    "node_sets": [{
      "id": "sim-hardware",
      "parameters": {
        "scene": {"type": "string", "default": "pick-place"},
        "camera_device": {"type": "string", "default": "cam-0"},
        "base_device": {"type": "string", "default": "base-0"},
        "manipulator_device": {"type": "string", "default": "arm-0"},
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
        {"ref": "drive", "core": "eos", "layer": "hardware", "group": "base",
         "profile": base},
        {"ref": "arm", "core": "eos", "layer": "hardware", "group": "manipulator",
         "profile": arm},
        {"ref": "base-velocity", "core": "eos", "layer": "dispatcher", "group": "base",
         "profile": {
           "id": "base-velocity", "node_type": BASE_PRIMITIVE,
           "label": "Base velocity primitive", "description": "Admitted base.velocity binding for the drive device",
           "settings": {"primitive_name": "base.velocity", "primitive_version": "1.0.0",
                        "movement_type": "body_velocity"},
         }},
        {"ref": "arm-movej", "core": "eos", "layer": "dispatcher", "group": "manipulator",
         "profile": {
           "id": "arm-movej", "node_type": MANIPULATOR_PRIMITIVE,
           "label": "Arm joint primitive", "description": "Admitted arm.movej binding for the six-joint arm",
           "settings": {"primitive_name": "arm.movej", "primitive_version": "1.0.0",
                        "movement_type": "joint_positions"},
         }},
        {"ref": "camera-gate", "core": "eos", "layer": "interface", "group": "gate",
         "profile": {
           "id": "front-preview", "node_type": CAMERA_GATE,
           "label": "Front camera preview gate",
           "description": "Publishes a bounded preview of the MuJoCo front camera",
           "inputs": {"frame": {"node": "@front", "output": "frame"}},
         }},
      ],
    }],
  }
