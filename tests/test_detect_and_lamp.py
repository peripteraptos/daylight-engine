import pytest

from custom_components.daylight_engine.engine import (
    DimmableProfile,
    OnOffProfile,
    RgbSegment,
    SleepAction,
    Target,
    TargetMode,
    default_profile,
    detect_capabilities,
    resolve_lamp_command,
)


def test_detect_rgbww_z2m_bulb():
    caps = detect_capabilities(["color_temp", "xy"], min_kelvin=2000, max_kelvin=6535, supported_features=44)
    assert caps.dimmable and caps.color_temp and caps.rgb and caps.transition
    profile = default_profile(caps)
    assert isinstance(profile, DimmableProfile)
    assert (profile.kelvin_min, profile.kelvin_max) == (2000, 6535)
    assert len(profile.segments) == 1  # RGB low-end is opt-in


def test_detect_wled_rgb_strip():
    caps = detect_capabilities(["rgb"])
    profile = default_profile(caps)
    assert isinstance(profile, DimmableProfile)
    assert isinstance(profile.segments[0], RgbSegment)
    assert profile.kelvin_min is None


def test_detect_onoff_and_dimmer():
    assert isinstance(default_profile(detect_capabilities(["onoff"])), OnOffProfile)
    assert isinstance(default_profile(detect_capabilities(None)), OnOffProfile)
    dimmer = default_profile(detect_capabilities(["brightness"]))
    assert isinstance(dimmer, DimmableProfile) and dimmer.kelvin_min is None


SLEEP = Target(brightness=1, kelvin=2000, mode=TargetMode.SLEEP)
DAY = Target(brightness=80, kelvin=4500)
PROFILE = default_profile(detect_capabilities(["color_temp"], min_kelvin=2200, max_kelvin=6500))


@pytest.mark.parametrize(
    "action,expected_on",
    [(SleepAction.OFF, False), (SleepAction.MINIMUM, True), (SleepAction.FOLLOW, True)],
)
def test_sleep_actions(action, expected_on):
    cmd = resolve_lamp_command(SLEEP, PROFILE, sleep_action=action)
    assert cmd is not None and cmd.on is expected_on


def test_sleep_unchanged_returns_none():
    assert resolve_lamp_command(SLEEP, PROFILE, sleep_action=SleepAction.UNCHANGED) is None


def test_sleep_action_ignored_in_daylight():
    cmd = resolve_lamp_command(DAY, PROFILE, sleep_action=SleepAction.OFF)
    assert cmd is not None and cmd.on and cmd.color_temp_kelvin == 4500
