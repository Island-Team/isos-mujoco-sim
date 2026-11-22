"""Declarative EOS node types and graph set shipped with the MuJoCo package."""

import argparse
import re


BACKEND = "eos.process.mujoco.simulator@v0.2"
CAMERA = "eos.hardware.camera.device@v0.2"
PACKAGE_VERSION = "0.2.8"
CAMERA_DEFAULTS = {"camera_width": 1280, "camera_height": 720,
                   "jpeg_quality": 80, "capture_frequency_hz": 30}


def candidate_version(value: str = "") -> str:
  """Validate source candidate versions; IsOS owns publication tag admission."""
  version = value or PACKAGE_VERSION
  if not re.fullmatch(r"0\.2\.(?:0|[1-9][0-9]*)", version):
    raise ValueError("version must be canonical 0.2.x")
  if tuple(map(int, version.split("."))) < tuple(map(int, PACKAGE_VERSION.split("."))):
    raise ValueError(f"this source supports current interfaces; choose {PACKAGE_VERSION} or later")
  return version


def standard_hardware(version: str) -> bool:
  return tuple(int(part) for part in version.split(".")) >= (0, 2, 8)


def per_camera_size(version: str) -> bool:
  return tuple(int(part) for part in version.split(".")) >= (0, 2, 5)


def robocasa_jpeg(version: str) -> bool:
  return tuple(int(part) for part in version.split(".")) >= (0, 2, 7)


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


def contributions(version: str = PACKAGE_VERSION) -> dict:
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
  package = {"id": "island/mujoco-sim", "version": version}
  library = "lib/libmujoco-eos-node.so"

  def live_port(name: str, data_type: str, data_class: str) -> dict:
    return {"name": name, "data_type": data_type, "required": False,
            "description": f"MuJoCo {name} {data_class}", "transport": "in_process",
            "delivery_mode": "event", "data_class": data_class,
            "contract": {"owner": "isos" if standard_hardware(version) and data_class == "command" else "eos",
                         "id": data_type,
                         "version": "1.0" if standard_hardware(version) and data_class == "command" else ("0.1" if data_type == "joint_channels@v0.1" else "0.2")}}

  observation = "observation" if standard_hardware(version) else "state"
  hardware_types = (
    (CAMERA, "camera", "camera", ["jpeg", "rgb8"], None, [],
     [live_port("frame", "image_frame@v0.2", "image")]),
    ("eos.hardware.base.device@v0.2", "base", "base", ["body_velocity"],
     "base_velocity", [live_port("command", "base_twist_command@v0.2", "command")],
     [live_port(observation, "base_state@v0.2", "observation")]),
    ("eos.hardware.manipulator.device@v0.2", "manipulator", "manipulator",
     ["joint_positions"], "manipulator_joint_position",
     [live_port("command", "joint_position_command@v0.2", "command")],
     [live_port(observation, "joint_state@v0.2", "observation")]),
    ("eos.hardware.base.normalized_axes@v0.2", "base", "base", ["normalized_axes"],
     "base_normalized_axes", [live_port("command", "normalized_axes_command@v0.2", "command")],
     [live_port(observation, "pose_state@v0.2", "observation")]),
    ("eos.hardware.manipulator.normalized_cartesian@v0.2", "manipulator", "manipulator",
     ["normalized_cartesian"], "manipulator_normalized_cartesian",
     [live_port("command", "normalized_axes_command@v0.2", "command"),
      live_port("mode", "control_mode_command@v0.2", "command")],
     [live_port(observation, "pose_state@v0.2", "observation")]),
    ("eos.hardware.gripper.binary@v0.2", "gripper", "gripper", ["binary"],
     "gripper_binary", [live_port("command", "gripper_binary_command@v0.2", "command")],
     [live_port(observation, "gripper_state@v0.2", "observation")]),
    ("eos.hardware.torso.normalized_axes@v0.2", "torso", "torso", ["normalized_axes"],
     "torso_normalized_axes", [live_port("command", "normalized_axes_command@v0.2", "command")],
     [live_port(observation, "joint_channels@v0.1", "observation")] if standard_hardware(version) else []),
  )
  definitions = []
  for type_id, group, kind, capabilities, safety, inputs, outputs in hardware_types:
    definition = {"id": type_id, "core": "eos", "layer": "hardware", "group": group,
                  "kind": kind, "lifecycle": "adapter", "capabilities": capabilities,
                  "description": f"MuJoCo {kind} device adapter", "settings": [],
                  "inputs": inputs, "outputs": outputs,
                  "implementation": {"kind": "native_plugin", "abi": "isos_node_v2",
                                     "library": library}}
    if kind == "camera":
      definition["outputs"][0]["frequency_hz"] = 30.0
    if safety is not None:
      definition["safety_adapter_type"] = safety
    if type_id == CAMERA and per_camera_size(version):
      definition["settings"] = [
        {"name": name, "data_type": "positive_integer", "required": standard_hardware(version),
         "min": 64, "max": 2048, "unit": "px",
         **({"default": CAMERA_DEFAULTS[name]} if standard_hardware(version) else {}),
         "description": f"Camera {axis} in pixels; takes effect on the next Run"}
        for name, axis in (("camera_width", "width"), ("camera_height", "height"))]
    if type_id == CAMERA and standard_hardware(version):
      definition["settings"] += [
        {"name": "jpeg_quality", "data_type": "positive_integer", "required": False,
         "default": CAMERA_DEFAULTS["jpeg_quality"], "min": 1, "max": 100, "description": "JPEG quality; lower values reduce bandwidth"},
        {"name": "capture_frequency_hz", "data_type": "positive_integer", "required": False,
         "default": CAMERA_DEFAULTS["capture_frequency_hz"], "min": 1, "max": 60, "unit": "Hz",
         "description": "EOS camera capture cadence; rendering may run slower"}]
    definitions.append(definition)
  native = (
    ("front", "camera", CAMERA, "cam-0", ["jpeg"], 30.0, 12582912),
    ("drive", "base", "eos.hardware.base.device@v0.2", "base-0", ["body_velocity"], 50.0, 65536),
    ("arm", "manipulator", "eos.hardware.manipulator.device@v0.2", "arm-0", ["joint_positions"], 50.0, 65536),
    ("gripper", "gripper", "eos.hardware.gripper.binary@v0.2", "gripper-0", ["binary"], 50.0, 65536),
  )
  robocasa = (
    ("left", "camera", CAMERA, "robocasa/camera/agentview-left", ["jpeg"] if robocasa_jpeg(version) else ["rgb8"], 30.0, 20 * 1024 * 1024),
    ("right", "camera", CAMERA, "robocasa/camera/agentview-right", ["jpeg"] if robocasa_jpeg(version) else ["rgb8"], 30.0, 20 * 1024 * 1024),
    ("wrist", "camera", CAMERA, "robocasa/camera/eye-in-hand", ["jpeg"] if robocasa_jpeg(version) else ["rgb8"], 30.0, 20 * 1024 * 1024),
    ("mobile", "base", "eos.hardware.base.normalized_axes@v0.2", "robocasa/base/mobile-base", ["normalized_axes"], 50.0, 65536),
    ("right-arm", "manipulator", "eos.hardware.manipulator.normalized_cartesian@v0.2", "robocasa/arm/right-arm", ["normalized_cartesian"], 50.0, 65536),
    ("hand", "gripper", "eos.hardware.gripper.binary@v0.2", "robocasa/gripper/right-gripper", ["binary"], 50.0, 65536),
    ("lift", "torso", "eos.hardware.torso.normalized_axes@v0.2", "robocasa/torso/torso", ["normalized_axes"], 50.0, 65536),
  )

  if standard_hardware(version):
    robocasa = (("free", "camera", CAMERA, "robocasa/camera/free", ["jpeg"],
                 30.0, 20 * 1024 * 1024),) + robocasa

  def profile(ref: str, kind: str, type_id: str, device: str, capabilities: list[str],
              rate: float, size: int, service: str) -> dict:
    item = hardware_profile(ref, type_id, device, f"{service} {kind} device", device,
                            capabilities, device, rate, size, version)
    if kind == "camera" and standard_hardware(version):
      item["observation"]["max_payload_bytes"] = 4 * 1024 * 1024
    item["package"] = package
    item["references"] = []
    item["adapter"]["settings"] = {"service_instance": service, "device_id": device}
    if kind == "camera" and per_camera_size(version):
      item["settings"] = {"camera_width": 1280, "camera_height": 720}
    if kind == "camera":
      if standard_hardware(version):
        item["settings"] = dict(CAMERA_DEFAULTS)
      else:
        item["adapter"]["settings"]["frequency_hz"] = rate
    if service == "native" and kind == "manipulator":
      item["joint_names"] = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
                             "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]
    if standard_hardware(version):
      if kind == "base":
        item["frame_id"] = "base_link" if service == "native" else "world"
      elif kind == "manipulator":
        item["frame_id"] = "robot_base"
    if kind == "torso" and not standard_hardware(version):
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
      if standard_hardware(version) and mode == "joint_positions":
        limits.pop("max_joint_speed_rad_s")
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
    "node_types": definitions,
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
       **({"required_node_settings": {CAMERA: ["camera_width", "camera_height"]}}
          if per_camera_size(version) else {}),
       "requirements": [{"path": "${config.host.mujoco_root}/lib/libmujoco.so.3.3.1", "kind": "file"}],
       "environment": [{"name": "LD_LIBRARY_PATH",
                        "value": "${config.host.mujoco_root}/lib"},
                       *([{"name": "ISOS_NATIVE_CAMERA_SIZES", "value": "${selected_nodes.settings_json}"}]
                         if per_camera_size(version) else [])],
       "resources": [{"setting": "scene", "kind": "scene",
                      "descriptor": "package-resources.json"}],
       "config_service_type": "native", "node_types": sorted({item[2] for item in native})},
      {"id": "robocasa", "entrypoint": "bin/robocasa-worker",
       "args": ["--socket", "${socket}"], "config_service_type": "robocasa",
       "requirements": [{"path": "${config.host.python_interpreter}", "kind": "file"},
                        {"path": "${config.host.robocasa_assets}", "kind": "directory"}],
       **({"required_node_settings": {CAMERA: ["camera_width", "camera_height"]}}
          if per_camera_size(version) else {}),

       "environment": [
         {"name": "ISOS_PACKAGE_PYTHON", "value": "${config.host.python_interpreter}"},
         {"name": "ISOS_ROBOCASA_ASSETS", "value": "${config.host.robocasa_assets}"},
         {"name": "ISOS_ROBOCASA_ROBOT", "value": "${config.service.robot}"},
         {"name": "ISOS_ROBOCASA_TASK", "value": "${config.service.task}"},
         {"name": "ISOS_ROBOCASA_SEED", "value": "${config.service.seed}"},
         *([{"name": "ISOS_ROBOCASA_CAMERA_SIZES", "value": "${selected_nodes.settings_json}"}]
           if per_camera_size(version) else [
             {"name": "ISOS_ROBOCASA_CAMERA_WIDTH", "value": "${config.service.camera_width}"},
             {"name": "ISOS_ROBOCASA_CAMERA_HEIGHT", "value": "${config.service.camera_height}"}]),
         {"name": "ISOS_PACKAGE_GENERATION", "value": "${generation_id}"},
       ],
       "node_types": sorted({item[2] for item in robocasa})},
    ],
    "node_sets": [preset("native", native), preset("robocasa", robocasa)],
  }


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Select an unpublished package candidate version")
  parser.add_argument("version", nargs="?", default="")
  args = parser.parse_args()
  try:
    print(candidate_version(args.version))
  except ValueError as error:
    parser.error(str(error))
