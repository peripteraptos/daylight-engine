"""Translate stored options into engine/controller settings.

Options are stored nested by UI section (that is what config-flow sections
produce), e.g. ``{"kelvin": {"night": 2200, ...}, "updates": {...}}``.
Defaults are derived from the engine defaults so there is a single source.
No Home Assistant imports here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .const import (
    SECTION_BRIGHT,
    SECTION_BRIGHTNESS,
    SECTION_KELVIN,
    SECTION_MANUAL,
    SECTION_SLEEP,
    SECTION_UPDATES,
)
from .engine import BrightTarget, Curve, Ramp, SleepTarget, TargetConfig


def _curve_to_options(curve: Curve) -> dict[str, float]:
    return {
        "night": curve.night,
        "day": curve.day,
        "morning_low": curve.morning.low_elevation,
        "morning_high": curve.morning.high_elevation,
        "morning_shape": curve.morning.shape,
        "evening_low": curve.evening.low_elevation,
        "evening_high": curve.evening.high_elevation,
        "evening_shape": curve.evening.shape,
    }


def _curve_from_options(data: Mapping[str, Any], default: Curve) -> Curve:
    merged = _curve_to_options(default) | dict(data)
    return Curve(
        night=float(merged["night"]),
        day=float(merged["day"]),
        morning=Ramp(
            float(merged["morning_low"]), float(merged["morning_high"]), float(merged["morning_shape"])
        ),
        evening=Ramp(
            float(merged["evening_low"]), float(merged["evening_high"]), float(merged["evening_shape"])
        ),
    )


@dataclass(frozen=True, slots=True)
class ControllerSettings:
    interval: float = 60.0
    """Seconds between periodic updates."""
    transition: float = 10.0
    """Transition for periodic updates (seconds)."""
    turn_on_transition: float = 0.0
    """Transition when correcting a lamp right after it was switched on (0 = none)."""
    min_brightness_change: float = 1.0
    """Logical percent the target must move before a lamp is updated."""
    min_kelvin_change: float = 30.0
    detect_manual: bool = True
    reset_manual_on_off: bool = True
    manual_timeout: float = 0.0
    """Minutes after which a manual override expires, 0 = never."""
    bright_timeout: float = 30.0
    """Minutes after which full-brightness mode switches itself off, 0 = never."""
    bright_turn_on: bool = False
    """Full-brightness mode also switches on lights that are off (and off again afterwards)."""


def default_options() -> dict[str, dict[str, Any]]:
    target = TargetConfig()
    settings = ControllerSettings()
    return {
        SECTION_KELVIN: _curve_to_options(target.kelvin),
        SECTION_BRIGHTNESS: _curve_to_options(target.brightness),
        SECTION_SLEEP: {"brightness": target.sleep.brightness, "kelvin": target.sleep.kelvin},
        SECTION_BRIGHT: {
            "brightness": target.bright.brightness,
            "kelvin": target.bright.kelvin,
            "timeout": settings.bright_timeout,
            "turn_on": settings.bright_turn_on,
        },
        SECTION_UPDATES: {
            "interval": settings.interval,
            "transition": settings.transition,
            "turn_on_transition": settings.turn_on_transition,
            "min_brightness_change": settings.min_brightness_change,
            "min_kelvin_change": settings.min_kelvin_change,
        },
        SECTION_MANUAL: {
            "detect": settings.detect_manual,
            "reset_on_off": settings.reset_manual_on_off,
            "timeout": settings.manual_timeout,
        },
    }


def merged_options(options: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Defaults overlaid with stored options, section by section."""
    result = default_options()
    for section, values in options.items():
        if section in result and isinstance(values, Mapping):
            result[section] = result[section] | dict(values)
    return result


def target_config_from_options(options: Mapping[str, Any]) -> TargetConfig:
    """Build the engine config. Raises ValueError for inconsistent values."""
    opts = merged_options(options)
    defaults = TargetConfig()
    return TargetConfig(
        kelvin=_curve_from_options(opts[SECTION_KELVIN], defaults.kelvin),
        brightness=_curve_from_options(opts[SECTION_BRIGHTNESS], defaults.brightness),
        sleep=SleepTarget(
            brightness=float(opts[SECTION_SLEEP]["brightness"]),
            kelvin=float(opts[SECTION_SLEEP]["kelvin"]),
        ),
        bright=BrightTarget(
            brightness=float(opts[SECTION_BRIGHT]["brightness"]),
            kelvin=float(opts[SECTION_BRIGHT]["kelvin"]),
        ),
    )


def controller_settings_from_options(options: Mapping[str, Any]) -> ControllerSettings:
    opts = merged_options(options)
    updates, manual, bright = opts[SECTION_UPDATES], opts[SECTION_MANUAL], opts[SECTION_BRIGHT]
    return ControllerSettings(
        interval=max(5.0, float(updates["interval"])),
        transition=max(0.0, float(updates["transition"])),
        turn_on_transition=max(0.0, float(updates["turn_on_transition"])),
        min_brightness_change=max(0.0, float(updates["min_brightness_change"])),
        min_kelvin_change=max(0.0, float(updates["min_kelvin_change"])),
        detect_manual=bool(manual["detect"]),
        reset_manual_on_off=bool(manual["reset_on_off"]),
        manual_timeout=max(0.0, float(manual["timeout"])),
        bright_timeout=max(0.0, float(bright["timeout"])),
        bright_turn_on=bool(bright["turn_on"]),
    )
