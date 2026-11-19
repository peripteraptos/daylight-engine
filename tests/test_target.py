from datetime import UTC, datetime, timedelta

import pytest

from custom_components.daylight_engine.engine.sun import SolarPosition
from custom_components.daylight_engine.engine.target import (
    Curve,
    Ramp,
    SleepTarget,
    TargetConfig,
    TargetMode,
    compute_target,
    compute_target_at,
    interpolate_kelvin,
)

CONFIG = TargetConfig()
BERLIN = (52.52, 13.405)


def pos(elevation: float, morning: bool) -> SolarPosition:
    return SolarPosition(elevation=elevation, azimuth=0, hour_angle=-90 if morning else 90)


def test_ramp_validation():
    with pytest.raises(ValueError):
        Ramp(low_elevation=5, high_elevation=5)
    with pytest.raises(ValueError):
        Ramp(low_elevation=0, high_elevation=5, shape=0)


def test_config_validation():
    with pytest.raises(ValueError):
        TargetConfig(sleep=SleepTarget(brightness=0))
    with pytest.raises(ValueError):
        TargetConfig(sleep=SleepTarget(kelvin=500))


def test_night_and_day_extremes():
    night = compute_target(pos(-30, morning=False), CONFIG)
    day = compute_target(pos(45, morning=True), CONFIG)
    assert night.kelvin == pytest.approx(CONFIG.kelvin.night)
    assert night.brightness == pytest.approx(CONFIG.brightness.night)
    assert day.kelvin == pytest.approx(CONFIG.kelvin.day)
    assert day.brightness == pytest.approx(CONFIG.brightness.day)


def test_monotonic_in_elevation():
    for morning in (True, False):
        last_k = last_b = -1.0
        for e10 in range(-200, 400):
            t = compute_target(pos(e10 / 10, morning), CONFIG)
            assert t.kelvin >= last_k - 1e-9
            assert t.brightness >= last_b - 1e-9
            last_k, last_b = t.kelvin, t.brightness


def test_evening_warmer_than_morning_at_same_elevation():
    # Default config: evening ramp is wider, so at +5° the evening is warmer.
    morning = compute_target(pos(5, morning=True), CONFIG)
    evening = compute_target(pos(5, morning=False), CONFIG)
    assert evening.kelvin < morning.kelvin


def test_kelvin_interpolates_in_mired():
    # Halfway in mired between 2000 K (500 mired) and 5000 K (200 mired) = 350 mired
    assert interpolate_kelvin(2000, 5000, 0.5) == pytest.approx(1e6 / 350)


def test_sleep_overrides():
    t = compute_target(pos(40, morning=True), CONFIG, sleep=True)
    assert t.mode is TargetMode.SLEEP
    assert (t.brightness, t.kelvin) == (CONFIG.sleep.brightness, CONFIG.sleep.kelvin)


def test_shape_bends_curve():
    linear = Curve(night=0.5, day=100, morning=Ramp(0, 10), evening=Ramp(0, 10))
    late = Curve(night=0.5, day=100, morning=Ramp(0, 10, shape=2), evening=Ramp(0, 10, shape=2))
    cfg_a = TargetConfig(brightness=linear)
    cfg_b = TargetConfig(brightness=late)
    p = pos(5, morning=True)
    assert compute_target(p, cfg_b).brightness < compute_target(p, cfg_a).brightness


def test_winter_day_in_berlin_reaches_full_day():
    # Around the winter solstice the sun reaches only ~14° in Berlin; defaults
    # must still reach full daylight values at noon.
    noon = datetime(2026, 12, 21, 11, 10, tzinfo=UTC)
    t = compute_target_at(noon, *BERLIN, CONFIG)
    assert t.kelvin == pytest.approx(CONFIG.kelvin.day, rel=0.01)
    assert t.brightness == pytest.approx(CONFIG.brightness.day, rel=0.01)


def test_continuous_over_a_day():
    start = datetime(2026, 11, 19, tzinfo=UTC)
    prev = compute_target_at(start, *BERLIN, CONFIG)
    for minute in range(1, 24 * 60):
        cur = compute_target_at(start + timedelta(minutes=minute), *BERLIN, CONFIG)
        assert abs(cur.kelvin - prev.kelvin) < 60
        assert abs(cur.brightness - prev.brightness) < 2
        prev = cur


def test_bright_overrides_sleep_and_daylight():
    t = compute_target(pos(-30, morning=False), CONFIG, sleep=True, bright=True)
    assert t.mode is TargetMode.BRIGHT
    assert (t.brightness, t.kelvin) == (CONFIG.bright.brightness, CONFIG.bright.kelvin)
