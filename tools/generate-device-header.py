#!/usr/bin/env python3
"""Compile stable device identities from the package-owned P02 catalog."""

from pathlib import Path
import sys

from scene_catalog import DEVICES, SCENES


def main() -> None:
    profiles = {scene["id"]: scene["profile"] for scene in SCENES}
    lines = [
        "// Generated from tools/scene_catalog.py; do not edit.",
        "#pragma once",
        "namespace eos_mujoco {",
        "struct SceneDevice { const char* id; const char* kind; const char* profile; };",
        "inline constexpr SceneDevice kSceneDevices[] = {",
    ]
    for device in DEVICES:
        for scene_id in device["scene_ids"]:
            lines.append(
                f'    {{"{device["id"]}", "{device["kind"]}", '
                f'"{profiles[scene_id]}"}},'
            )
    lines.extend(["};", "}  // namespace eos_mujoco", ""])
    Path(sys.argv[1]).write_text("\n".join(lines))


if __name__ == "__main__":
    main()
