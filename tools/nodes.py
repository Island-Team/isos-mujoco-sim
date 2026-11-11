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
