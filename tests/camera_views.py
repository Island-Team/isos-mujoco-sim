#!/usr/bin/env python3
"""Optional real RoboCasa camera render check; requires prepared assets/runtime."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.robocasa_worker import CAMERA_NODES, create_hardware
from tools.nodes import CAMERA_DEFAULTS

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--assets", required=True)
args = parser.parse_args()
width, height = CAMERA_DEFAULTS["camera_width"], CAMERA_DEFAULTS["camera_height"]
hardware = create_hardware("CloseFridge", 42, args.assets, width, height,
                           camera_sizes=dict.fromkeys(CAMERA_NODES, (width, height)))
try:
    report = []
    for part in hardware.manifest()["parts"]:
        if part["role"] == "camera":
            image = next(iter(hardware.status(part["id"]).values()))
            assert image.shape == (height, width, 3) and image.var() > 0
            report.append({"id": part["id"], "view_role": part["view_role"],
                           "shape": list(image.shape)})
    assert len(report) == 4
    assert sum(item["view_role"] == "spectator" for item in report) == 1
    print(json.dumps(report, indent=2))
finally:
    hardware.close()
