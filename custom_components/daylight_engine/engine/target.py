"""Global target calculation: what the light *should* look like right now.

The target is device-independent: a perceived brightness in percent and a
colour temperature in Kelvin. Lamp profiles translate it into device commands.

Both quantities follow the sun's elevation (not the clock), with separate
ramps for the morning and the evening so that the evening can get warm earlier
and more slowly than the morning gets cool again.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from .sun import SolarPosition, solar_position

KELVIN_MIN = 1000
KELVIN_MAX = 10000


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _smoothstep(t: float) -> float:
    return t * t * (3 - 2 * t)


@dataclass(frozen=True, slots=True)
class Ramp:
    """Transition between night and day value over a range of sun elevations.

    Below ``low_elevation`` the night value applies, above ``high_elevation``
    the day value. In between, a smooth S-curve is used. ``shape`` > 1 keeps
    the value closer to night for longer, < 1 moves it towards day earlier.
    """

    low_elevation: float
    high_elevation: float
    shape: float = 1.0

    def __post_init__(self) -> None:
        if self.high_elevation <= self.low_elevation:
            raise ValueError("high_elevation must be greater than low_elevation")
        if self.shape <= 0:
            raise ValueError("shape must be positive")

    def day_factor(self, elevation: float) -> float:
        """0.0 = full night, 1.0 = full day."""
        t = (elevation - self.low_elevation) / (self.high_elevation - self.low_elevation)
        return _smoothstep(_clamp(t, 0.0, 1.0)) ** self.shape


@dataclass(frozen=True, slots=True)
class Curve:
    """Night/day values plus separate ramps for morning and evening."""

    night: float
    day: float
    morning: Ramp
    evening: Ramp

    def day_factor(self, position: SolarPosition) -> float:
        ramp = self.morning if position.is_morning else self.evening
        return ramp.day_factor(position.elevation)


@dataclass(frozen=True, slots=True)
class SleepTarget:
    brightness: float = 1.0
    kelvin: float = 2000


@dataclass(frozen=True, slots=True)
class BrightTarget:
    """Fixed target for the "full brightness" mode (e.g. when searching for something)."""

    brightness: float = 100.0
    kelvin: float = 5000


def _default_kelvin() -> Curve:
    return Curve(
        night=2200,
        day=4800,
        morning=Ramp(low_elevation=-6, high_elevation=8),
        evening=Ramp(low_elevation=-6, high_elevation=14, shape=0.8),
    )


def _default_brightness() -> Curve:
    return Curve(
        night=40,
        day=100,
        morning=Ramp(low_elevation=-4, high_elevation=6),
        evening=Ramp(low_elevation=-9, high_elevation=4),
    )


@dataclass(frozen=True, slots=True)
class TargetConfig:
    """Global configuration of the daylight curve."""

    kelvin: Curve = field(default_factory=_default_kelvin)
    brightness: Curve = field(default_factory=_default_brightness)
    sleep: SleepTarget = field(default_factory=SleepTarget)
    bright: BrightTarget = field(default_factory=BrightTarget)

    def __post_init__(self) -> None:
        for value in (self.kelvin.night, self.kelvin.day, self.sleep.kelvin, self.bright.kelvin):
            if not KELVIN_MIN <= value <= KELVIN_MAX:
                raise ValueError(f"kelvin {value} outside {KELVIN_MIN}-{KELVIN_MAX}")
        for value in (
            self.brightness.night,
            self.brightness.day,
            self.sleep.brightness,
            self.bright.brightness,
        ):
            if not 0 < value <= 100:
                raise ValueError(f"brightness {value} outside (0, 100]")


class TargetMode(StrEnum):
    DAYLIGHT = "daylight"
    SLEEP = "sleep"
    BRIGHT = "bright"


@dataclass(frozen=True, slots=True)
class Target:
    """Device-independent light target."""

    brightness: float
    """Perceived (logical) brightness in percent, 0 < x <= 100."""

    kelvin: float
    mode: TargetMode = TargetMode.DAYLIGHT

    kelvin_day_factor: float | None = None
    brightness_day_factor: float | None = None


def interpolate_kelvin(night: float, day: float, factor: float) -> float:
    """Interpolate in mired space, which is perceptually more even than Kelvin."""
    m_night = 1e6 / night
    m_day = 1e6 / day
    return 1e6 / (m_night + (m_day - m_night) * factor)


def compute_target(
    position: SolarPosition,
    config: TargetConfig,
    *,
    sleep: bool = False,
    bright: bool = False,
) -> Target:
    """Compute the global light target for a given sun position.

    ``bright`` wins over ``sleep``; the controller keeps the two exclusive anyway.
    """
    if bright:
        return Target(
            brightness=config.bright.brightness,
            kelvin=config.bright.kelvin,
            mode=TargetMode.BRIGHT,
        )
    if sleep:
        return Target(
            brightness=config.sleep.brightness,
            kelvin=config.sleep.kelvin,
            mode=TargetMode.SLEEP,
        )

    k_factor = config.kelvin.day_factor(position)
    b_factor = config.brightness.day_factor(position)
    kelvin = interpolate_kelvin(config.kelvin.night, config.kelvin.day, k_factor)
    brightness = config.brightness.night + (config.brightness.day - config.brightness.night) * b_factor
    return Target(
        brightness=brightness,
        kelvin=kelvin,
        kelvin_day_factor=k_factor,
        brightness_day_factor=b_factor,
    )


def compute_target_at(
    when: datetime,
    latitude: float,
    longitude: float,
    config: TargetConfig,
    *,
    sleep: bool = False,
    bright: bool = False,
) -> Target:
    """Convenience wrapper: target for a point in time and location."""
    return compute_target(solar_position(when, latitude, longitude), config, sleep=sleep, bright=bright)
