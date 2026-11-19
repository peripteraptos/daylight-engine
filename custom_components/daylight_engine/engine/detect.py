"""Derive lamp capabilities and a sensible default profile from HA attributes.

Input is what Home Assistant exposes on every light entity
(``supported_color_modes``, ``min_color_temp_kelvin``, ``max_color_temp_kelvin``,
``supported_features``), so detection works the same for Zigbee2MQTT, WLED,
ESPHome, Shelly, Hue, … without platform-specific code.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .profile import CctSegment, CurvePoint, DimmableProfile, OnOffProfile, Profile, RgbPoint, RgbSegment

COLOR_MODES_RGB = frozenset({"hs", "xy", "rgb", "rgbw", "rgbww"})
COLOR_MODES_BRIGHTNESS = frozenset({"brightness", "white"}) | COLOR_MODES_RGB | {"color_temp"}

# LightEntityFeature.TRANSITION
FEATURE_TRANSITION = 32

DEFAULT_RGB_KELVIN_RANGE = (1800.0, 6500.0)


@dataclass(frozen=True, slots=True)
class Capabilities:
    dimmable: bool
    color_temp: bool
    rgb: bool
    transition: bool
    min_kelvin: float | None
    max_kelvin: float | None


def detect_capabilities(
    color_modes: Iterable[str] | None,
    *,
    min_kelvin: float | None = None,
    max_kelvin: float | None = None,
    supported_features: int = 0,
) -> Capabilities:
    modes = {str(m) for m in (color_modes or ())}
    color_temp = "color_temp" in modes
    return Capabilities(
        dimmable=bool(modes & COLOR_MODES_BRIGHTNESS),
        color_temp=color_temp,
        rgb=bool(modes & COLOR_MODES_RGB),
        transition=bool(supported_features & FEATURE_TRANSITION),
        min_kelvin=float(min_kelvin) if color_temp and min_kelvin else None,
        max_kelvin=float(max_kelvin) if color_temp and max_kelvin else None,
    )


def default_profile(caps: Capabilities, name: str = "") -> Profile:
    """Linear, uncalibrated starting profile; the calibration UI refines it.

    RGB+CCT lamps start CCT-only: the RGB low-end segment is opt-in during
    calibration because whether it looks better depends on the lamp.
    """
    linear = (CurvePoint(logical=0, device=1), CurvePoint(logical=100, device=100))

    if not caps.dimmable:
        return OnOffProfile(name=name)

    if caps.color_temp:
        return DimmableProfile(
            segments=(CctSegment(end=100, points=linear),),
            kelvin_min=caps.min_kelvin or 2700.0,
            kelvin_max=caps.max_kelvin or 6500.0,
            name=name,
        )

    if caps.rgb:
        low, high = DEFAULT_RGB_KELVIN_RANGE
        return DimmableProfile(
            segments=(
                RgbSegment(
                    end=100,
                    points=(RgbPoint(logical=0, device=1), RgbPoint(logical=100, device=100)),
                    min_kelvin=low,
                    max_kelvin=high,
                ),
            ),
            name=name,
        )

    return DimmableProfile(segments=(CctSegment(end=100, points=linear),), name=name)
