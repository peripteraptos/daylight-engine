"""Generate fixtures so the JS engine port can be checked against Python."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "custom_components" / "daylight_engine"))

from engine import default_profile, detect_capabilities, profile_from_dict, profile_to_dict  # noqa: E402

profiles = [
    profile_from_dict(json.loads((ROOT / "examples" / "rgb_cct_profile.json").read_text())),
    default_profile(detect_capabilities(["color_temp"], min_kelvin=2200, max_kelvin=6500)),
    default_profile(detect_capabilities(["rgb"])),
    default_profile(detect_capabilities(["brightness"])),
    default_profile(detect_capabilities(["onoff"])),
]
cases = []
for profile in profiles:
    for logical in (0, 0.05, 1, 3.3, 9.99, 10, 10.01, 25, 50, 77.7, 100):
        for kelvin in (1500, 2000, 2700, 4000, 6500, 9000):
            cmd = profile.resolve(logical, kelvin)
            cases.append(
                {
                    "profile": profile_to_dict(profile),
                    "logical": logical,
                    "kelvin": kelvin,
                    "expected": {
                        "on": cmd.on,
                        "brightness": cmd.brightness,
                        "color_temp_kelvin": cmd.color_temp_kelvin,
                        "rgb_color": list(cmd.rgb_color) if cmd.rgb_color else None,
                    },
                }
            )
(Path(__file__).parent / "fixtures.json").write_text(json.dumps(cases))
print(len(cases), "cases")
