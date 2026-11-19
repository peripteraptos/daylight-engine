"""Print the daylight target over one day, optionally with a lamp's device commands.

python scripts/simulate_day.py --lat 52.52 --lon 13.405 --date 2026-11-19 --step 30
python scripts/simulate_day.py --profile my_lamp.json --csv > day.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.daylight_engine.engine import (  # noqa: E402
    TargetConfig,
    compute_target,
    profile_from_dict,
    solar_position,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--lat", type=float, default=52.52)
    parser.add_argument("--lon", type=float, default=13.405)
    parser.add_argument("--tz", default="Europe/Berlin")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--step", type=int, default=30, help="minutes between rows")
    parser.add_argument("--profile", type=Path, help="lamp profile JSON (profile_to_dict format)")
    parser.add_argument("--csv", action="store_true")
    args = parser.parse_args()

    config = TargetConfig()
    profile = profile_from_dict(json.loads(args.profile.read_text())) if args.profile else None
    tz = ZoneInfo(args.tz)
    start = datetime.combine(args.date, datetime.min.time(), tzinfo=tz)

    header = ["time", "elevation", "brightness_pct", "kelvin"]
    if profile:
        header += ["on", "ha_brightness", "color_temp_kelvin", "rgb_color", "segment"]
    sep = "," if args.csv else "\t"
    print(sep.join(header))

    previous_segment = None
    for minute in range(0, 24 * 60, args.step):
        when = start + timedelta(minutes=minute)
        pos = solar_position(when, args.lat, args.lon)
        target = compute_target(pos, config)
        row = [
            when.strftime("%H:%M"),
            f"{pos.elevation:.1f}",
            f"{target.brightness:.1f}",
            f"{target.kelvin:.0f}",
        ]
        if profile:
            cmd = profile.resolve(target.brightness, target.kelvin, previous_segment)
            previous_segment = cmd.segment
            rgb = "" if cmd.rgb_color is None else "/".join(map(str, cmd.rgb_color))
            row += [
                str(cmd.on),
                str(cmd.brightness or ""),
                str(cmd.color_temp_kelvin or ""),
                rgb,
                str(cmd.segment),
            ]
        print(sep.join(row))


if __name__ == "__main__":
    main()
