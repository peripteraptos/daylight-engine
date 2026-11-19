"""Lamp profiles: translate a logical target into a device command.

A *logical* brightness (0-100 %) is what the user perceives and what the
global target produces. A profile maps it onto what a particular lamp needs
to look that bright, possibly switching between colour modes on the way.

A dimmable profile consists of consecutive segments covering (0, 100]:

    logical  0%        10%                                    100%
             |--RGB----|---------------CCT---------------------|

Each segment has calibration points (logical % -> device brightness %), which
are linearly interpolated. RGB points additionally carry per-channel gains to
compensate for channels that do not dim linearly relative to each other.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from typing import Any, Self

from .color import RGB, apply_gains, kelvin_to_rgb

SCHEMA_VERSION = 1


# --------------------------------------------------------------------------- #
# Device command
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class DeviceCommand:
    """What to send to a lamp. Mirrors ``light.turn_on`` / ``light.turn_off``."""

    on: bool
    brightness: int | None = None
    """Home Assistant brightness 1-255."""
    color_temp_kelvin: int | None = None
    rgb_color: RGB | None = None
    segment: int | None = None
    """Index of the profile segment used (for hysteresis on the next call)."""

    @classmethod
    def off(cls) -> Self:
        return cls(on=False)

    @property
    def service(self) -> str:
        return "turn_on" if self.on else "turn_off"

    def to_service_data(self) -> dict[str, Any]:
        """Service data for ``light.turn_on``/``light.turn_off`` (without entity_id)."""
        data: dict[str, Any] = {}
        if not self.on:
            return data
        if self.brightness is not None:
            data["brightness"] = self.brightness
        if self.color_temp_kelvin is not None:
            data["color_temp_kelvin"] = self.color_temp_kelvin
        if self.rgb_color is not None:
            data["rgb_color"] = list(self.rgb_color)
        return data


def pct_to_ha_brightness(pct: float) -> int:
    """Device brightness percent -> HA 1..255 (never 0 for an 'on' lamp)."""
    return max(1, min(255, round(pct * 255 / 100)))


# --------------------------------------------------------------------------- #
# Calibration points and segments
# --------------------------------------------------------------------------- #


def _check_pct(name: str, value: float, *, allow_zero: bool) -> None:
    low_ok = value >= 0 if allow_zero else value > 0
    if not (low_ok and value <= 100):
        raise ValueError(f"{name} {value} outside {'[' if allow_zero else '('}0, 100]")


@dataclass(frozen=True, slots=True)
class CurvePoint:
    logical: float
    device: float

    def __post_init__(self) -> None:
        _check_pct("logical", self.logical, allow_zero=True)
        _check_pct("device", self.device, allow_zero=False)


@dataclass(frozen=True, slots=True)
class RgbPoint:
    logical: float
    device: float
    gains: tuple[float, float, float] = (1.0, 1.0, 1.0)

    def __post_init__(self) -> None:
        _check_pct("logical", self.logical, allow_zero=True)
        _check_pct("device", self.device, allow_zero=False)
        if len(self.gains) != 3 or any(g < 0 for g in self.gains) or max(self.gains) <= 0:
            raise ValueError("gains must be three non-negative numbers, not all zero")


def _validate_points(points: tuple[CurvePoint | RgbPoint, ...]) -> None:
    if not points:
        raise ValueError("segment needs at least one calibration point")
    for a, b in zip(points, points[1:], strict=False):
        if b.logical <= a.logical:
            raise ValueError("calibration points must have strictly increasing logical values")


def _locate(points: tuple[CurvePoint | RgbPoint, ...], logical: float) -> tuple[int, int, float]:
    """Return (i, j, t) so that the value is points[i] + t * (points[j] - points[i])."""
    if logical <= points[0].logical:
        return 0, 0, 0.0
    if logical >= points[-1].logical:
        last = len(points) - 1
        return last, last, 0.0
    j = bisect_left([p.logical for p in points], logical)
    i = j - 1
    t = (logical - points[i].logical) / (points[j].logical - points[i].logical)
    return i, j, t


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


@dataclass(frozen=True, slots=True)
class CctSegment:
    """White (colour temperature) segment, or brightness-only for plain dimmers."""

    end: float
    points: tuple[CurvePoint, ...]
    kind = "cct"

    def __post_init__(self) -> None:
        _check_pct("segment end", self.end, allow_zero=False)
        _validate_points(self.points)

    def device_brightness(self, logical: float) -> float:
        i, j, t = _locate(self.points, logical)
        return _lerp(self.points[i].device, self.points[j].device, t)


@dataclass(frozen=True, slots=True)
class RgbSegment:
    """Segment that drives the lamp in RGB mode, emulating a colour temperature."""

    end: float
    points: tuple[RgbPoint, ...]
    min_kelvin: float = 1800
    max_kelvin: float = 3000
    kind = "rgb"

    def __post_init__(self) -> None:
        _check_pct("segment end", self.end, allow_zero=False)
        _validate_points(self.points)
        if self.max_kelvin < self.min_kelvin:
            raise ValueError("max_kelvin must be >= min_kelvin")

    def evaluate(self, logical: float, kelvin: float) -> tuple[float, RGB]:
        i, j, t = _locate(self.points, logical)
        a, b = self.points[i], self.points[j]
        device = _lerp(a.device, b.device, t)
        gains = tuple(_lerp(ga, gb, t) for ga, gb in zip(a.gains, b.gains, strict=True))
        k = max(self.min_kelvin, min(self.max_kelvin, kelvin))
        return device, apply_gains(kelvin_to_rgb(k), gains)  # type: ignore[arg-type]


Segment = CctSegment | RgbSegment


# --------------------------------------------------------------------------- #
# Profiles
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class DimmableProfile:
    """Profile for dimmable lamps (brightness-only, CCT, RGB or a mix)."""

    segments: tuple[Segment, ...]
    kelvin_min: float | None = None
    kelvin_max: float | None = None
    """Native white range of the lamp. ``None`` = no colour temperature support."""
    hysteresis: float = 1.0
    """Logical percent a value must move past a segment border before switching."""
    name: str = ""
    kind = "dimmable"

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("profile needs at least one segment")
        ends = [s.end for s in self.segments]
        if any(b <= a for a, b in zip(ends, ends[1:], strict=False)):
            raise ValueError("segment ends must be strictly increasing")
        if ends[-1] != 100:
            raise ValueError("last segment must end at 100")
        if (self.kelvin_min is None) != (self.kelvin_max is None):
            raise ValueError("kelvin_min and kelvin_max must both be set or both be None")
        if self.kelvin_min is not None and self.kelvin_max is not None:
            if self.kelvin_max < self.kelvin_min:
                raise ValueError("kelvin_max must be >= kelvin_min")
        if self.hysteresis < 0:
            raise ValueError("hysteresis must be >= 0")

    def segment_bounds(self, index: int) -> tuple[float, float]:
        start = 0.0 if index == 0 else self.segments[index - 1].end
        return start, self.segments[index].end

    def segment_index(self, logical: float) -> int:
        for index, segment in enumerate(self.segments):
            if logical <= segment.end:
                return index
        return len(self.segments) - 1

    def resolve(
        self,
        logical: float,
        kelvin: float,
        previous_segment: int | None = None,
    ) -> DeviceCommand:
        if logical <= 0:
            return DeviceCommand.off()
        logical = min(logical, 100.0)

        index = self.segment_index(logical)
        if (
            previous_segment is not None
            and previous_segment != index
            and 0 <= previous_segment < len(self.segments)
        ):
            start, end = self.segment_bounds(previous_segment)
            if start - self.hysteresis <= logical <= end + self.hysteresis:
                index = previous_segment
                logical = max(start, min(end, logical))

        segment = self.segments[index]
        if isinstance(segment, RgbSegment):
            device, rgb = segment.evaluate(logical, kelvin)
            return DeviceCommand(
                on=True,
                brightness=pct_to_ha_brightness(device),
                rgb_color=rgb,
                segment=index,
            )

        device = segment.device_brightness(logical)
        color_temp = None
        if self.kelvin_min is not None and self.kelvin_max is not None:
            color_temp = round(max(self.kelvin_min, min(self.kelvin_max, kelvin)))
        return DeviceCommand(
            on=True,
            brightness=pct_to_ha_brightness(device),
            color_temp_kelvin=color_temp,
            segment=index,
        )

    def resolve_minimum(self, kelvin: float) -> DeviceCommand:
        """Dimmest possible 'on' state (first calibration point)."""
        return self.resolve(1e-6, kelvin)


@dataclass(frozen=True, slots=True)
class OnOffProfile:
    """Lamp that can only be switched. On when target brightness >= threshold."""

    threshold: float = 50.0
    hysteresis: float = 2.0
    name: str = ""
    kind = "onoff"

    def __post_init__(self) -> None:
        _check_pct("threshold", self.threshold, allow_zero=True)

    def resolve(
        self,
        logical: float,
        kelvin: float,
        previous_segment: int | None = None,
    ) -> DeviceCommand:
        # Segment 0 = off, segment 1 = on.
        threshold = self.threshold
        if previous_segment == 1:
            threshold -= self.hysteresis
        elif previous_segment == 0:
            threshold += self.hysteresis
        if logical > 0 and logical >= threshold:
            return DeviceCommand(on=True, segment=1)
        return DeviceCommand(on=False, segment=0)

    def resolve_minimum(self, kelvin: float) -> DeviceCommand:
        return DeviceCommand(on=True, segment=1)


Profile = DimmableProfile | OnOffProfile


# --------------------------------------------------------------------------- #
# Serialisation (for HA storage and import/export)
# --------------------------------------------------------------------------- #


def profile_to_dict(profile: Profile) -> dict[str, Any]:
    if isinstance(profile, OnOffProfile):
        return {
            "version": SCHEMA_VERSION,
            "type": "onoff",
            "name": profile.name,
            "threshold": profile.threshold,
            "hysteresis": profile.hysteresis,
        }
    segments: list[dict[str, Any]] = []
    for segment in profile.segments:
        if isinstance(segment, RgbSegment):
            segments.append(
                {
                    "type": "rgb",
                    "end": segment.end,
                    "min_kelvin": segment.min_kelvin,
                    "max_kelvin": segment.max_kelvin,
                    "points": [
                        {"logical": p.logical, "device": p.device, "gains": list(p.gains)}
                        for p in segment.points
                    ],
                }
            )
        else:
            segments.append(
                {
                    "type": "cct",
                    "end": segment.end,
                    "points": [{"logical": p.logical, "device": p.device} for p in segment.points],
                }
            )
    return {
        "version": SCHEMA_VERSION,
        "type": "dimmable",
        "name": profile.name,
        "kelvin_min": profile.kelvin_min,
        "kelvin_max": profile.kelvin_max,
        "hysteresis": profile.hysteresis,
        "segments": segments,
    }


def profile_from_dict(data: dict[str, Any]) -> Profile:
    version = data.get("version", SCHEMA_VERSION)
    if version > SCHEMA_VERSION:
        raise ValueError(f"profile schema version {version} is newer than supported")
    kind = data.get("type")
    if kind == "onoff":
        return OnOffProfile(
            threshold=float(data.get("threshold", 50.0)),
            hysteresis=float(data.get("hysteresis", 2.0)),
            name=str(data.get("name", "")),
        )
    if kind != "dimmable":
        raise ValueError(f"unknown profile type {kind!r}")

    segments: list[Segment] = []
    for raw in data["segments"]:
        if raw["type"] == "rgb":
            segments.append(
                RgbSegment(
                    end=float(raw["end"]),
                    min_kelvin=float(raw.get("min_kelvin", 1800)),
                    max_kelvin=float(raw.get("max_kelvin", 3000)),
                    points=tuple(
                        RgbPoint(
                            logical=float(p["logical"]),
                            device=float(p["device"]),
                            gains=tuple(float(g) for g in p.get("gains", (1, 1, 1))),  # type: ignore[arg-type]
                        )
                        for p in raw["points"]
                    ),
                )
            )
        elif raw["type"] == "cct":
            segments.append(
                CctSegment(
                    end=float(raw["end"]),
                    points=tuple(
                        CurvePoint(logical=float(p["logical"]), device=float(p["device"]))
                        for p in raw["points"]
                    ),
                )
            )
        else:
            raise ValueError(f"unknown segment type {raw['type']!r}")

    def opt(key: str) -> float | None:
        value = data.get(key)
        return None if value is None else float(value)

    return DimmableProfile(
        segments=tuple(segments),
        kelvin_min=opt("kelvin_min"),
        kelvin_max=opt("kelvin_max"),
        hysteresis=float(data.get("hysteresis", 1.0)),
        name=str(data.get("name", "")),
    )
