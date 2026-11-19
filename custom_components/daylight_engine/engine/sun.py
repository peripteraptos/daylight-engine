"""Solar position calculation (NOAA algorithm), no external dependencies.

Accuracy is well below 0.1° for dates between 1900 and 2100, which is far more
than needed for lighting purposes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class SolarPosition:
    """Position of the sun as seen from an observer."""

    elevation: float
    """Degrees above the horizon (negative below), without refraction unless requested."""

    azimuth: float
    """Degrees clockwise from north."""

    hour_angle: float
    """Degrees, negative before solar noon, positive after."""

    @property
    def is_morning(self) -> bool:
        """True between solar midnight and solar noon (sun is rising)."""
        return self.hour_angle < 0


def _refraction(elevation: float) -> float:
    """Approximate atmospheric refraction in degrees (NOAA)."""
    if elevation > 85:
        return 0.0
    te = math.tan(math.radians(elevation))
    if elevation > 5:
        arcsec = 58.1 / te - 0.07 / te**3 + 0.000086 / te**5
    elif elevation > -0.575:
        arcsec = 1735 + elevation * (-518.2 + elevation * (103.4 + elevation * (-12.79 + elevation * 0.711)))
    else:
        arcsec = -20.772 / te
    return arcsec / 3600


def solar_position(
    when: datetime,
    latitude: float,
    longitude: float,
    *,
    refraction: bool = False,
) -> SolarPosition:
    """Return the solar position for a timezone-aware datetime.

    ``longitude`` is positive east of Greenwich.
    """
    if when.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    utc = when.astimezone(UTC)

    jd = utc.timestamp() / 86400.0 + 2440587.5
    jc = (jd - 2451545.0) / 36525.0

    geom_mean_long = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360
    geom_mean_anom = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)
    ecc = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)

    m = math.radians(geom_mean_anom)
    eq_center = (
        math.sin(m) * (1.914602 - jc * (0.004817 + 0.000014 * jc))
        + math.sin(2 * m) * (0.019993 - 0.000101 * jc)
        + math.sin(3 * m) * 0.000289
    )
    true_long = geom_mean_long + eq_center
    omega = math.radians(125.04 - 1934.136 * jc)
    app_long = true_long - 0.00569 - 0.00478 * math.sin(omega)

    mean_obliq = 23 + (26 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60) / 60
    obliq = math.radians(mean_obliq + 0.00256 * math.cos(omega))

    decl = math.asin(math.sin(obliq) * math.sin(math.radians(app_long)))

    vary = math.tan(obliq / 2) ** 2
    l0 = math.radians(geom_mean_long)
    eq_time = 4 * math.degrees(
        vary * math.sin(2 * l0)
        - 2 * ecc * math.sin(m)
        + 4 * ecc * vary * math.sin(m) * math.cos(2 * l0)
        - 0.5 * vary**2 * math.sin(4 * l0)
        - 1.25 * ecc**2 * math.sin(2 * m)
    )

    minutes = utc.hour * 60 + utc.minute + (utc.second + utc.microsecond / 1e6) / 60
    true_solar_time = (minutes + eq_time + 4 * longitude) % 1440
    hour_angle = true_solar_time / 4 - 180  # -180 .. 180

    lat = math.radians(latitude)
    ha = math.radians(hour_angle)
    cos_zenith = math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(ha)
    zenith = math.acos(max(-1.0, min(1.0, cos_zenith)))
    elevation = 90 - math.degrees(zenith)

    sin_zenith = math.sin(zenith)
    if abs(sin_zenith) < 1e-9 or abs(math.cos(lat)) < 1e-9:
        azimuth = 180.0 if latitude > math.degrees(decl) else 0.0
    else:
        cos_az = (math.sin(lat) * math.cos(zenith) - math.sin(decl)) / (math.cos(lat) * sin_zenith)
        az = math.degrees(math.acos(max(-1.0, min(1.0, cos_az))))
        azimuth = (az + 180) % 360 if hour_angle > 0 else (540 - az) % 360

    if refraction:
        elevation += _refraction(elevation)

    return SolarPosition(elevation=elevation, azimuth=azimuth, hour_angle=hour_angle)
