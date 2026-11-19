"""Colour helpers."""

from __future__ import annotations

import math

RGB = tuple[int, int, int]


def kelvin_to_rgb(kelvin: float) -> tuple[float, float, float]:
    """Approximate RGB (0-255 floats) of a black body at ``kelvin``.

    Uses the Tanner Helland approximation, the same one Home Assistant uses in
    ``homeassistant.util.color.color_temperature_to_rgb``, so results match
    what HA itself would send for a colour temperature.
    """
    temp = max(1000.0, min(40000.0, kelvin)) / 100.0

    if temp <= 66:
        red = 255.0
        green = 99.4708025861 * math.log(temp) - 161.1195681661
        blue = 0.0 if temp <= 19 else 138.5177312231 * math.log(temp - 10) - 305.0447927307
    else:
        red = 329.698727446 * (temp - 60) ** -0.1332047592
        green = 288.1221695283 * (temp - 60) ** -0.0755148492
        blue = 255.0

    def clamp(v: float) -> float:
        return max(0.0, min(255.0, v))

    return clamp(red), clamp(green), clamp(blue)


def apply_gains(rgb: tuple[float, float, float], gains: tuple[float, float, float]) -> RGB:
    """Multiply channels by gains and normalise so the brightest channel is 255.

    Normalising keeps "colour" and "brightness" separate: the gains only change
    the hue/tint, the device brightness is sent separately.
    """
    scaled = [max(0.0, c * g) for c, g in zip(rgb, gains, strict=True)]
    peak = max(scaled)
    if peak <= 0:
        return (255, 255, 255)
    return tuple(int(round(c / peak * 255)) for c in scaled)  # type: ignore[return-value]
