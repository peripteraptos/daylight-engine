import json

import pytest

from custom_components.daylight_engine.engine.color import kelvin_to_rgb
from custom_components.daylight_engine.engine.profile import (
    CctSegment,
    CurvePoint,
    DeviceCommand,
    DimmableProfile,
    OnOffProfile,
    RgbPoint,
    RgbSegment,
    pct_to_ha_brightness,
    profile_from_dict,
    profile_to_dict,
)


def rgb_cct_profile() -> DimmableProfile:
    """The example from the plan: 0-10 % RGB, 10-100 % mapped to 1-100 % CCT."""
    return DimmableProfile(
        name="Stehlampe",
        kelvin_min=2200,
        kelvin_max=6500,
        segments=(
            RgbSegment(
                end=10,
                min_kelvin=1800,
                max_kelvin=2700,
                points=(
                    RgbPoint(logical=0, device=1, gains=(1.0, 0.8, 0.6)),
                    RgbPoint(logical=10, device=40, gains=(1.0, 1.0, 1.0)),
                ),
            ),
            CctSegment(
                end=100,
                points=(CurvePoint(10, 1), CurvePoint(50, 30), CurvePoint(100, 100)),
            ),
        ),
    )


def test_off_at_zero():
    assert rgb_cct_profile().resolve(0, 3000) == DeviceCommand.off()


def test_cct_segment_interpolation_and_kelvin_clamp():
    cmd = rgb_cct_profile().resolve(30, 9000)
    assert cmd.on and cmd.segment == 1
    assert cmd.brightness == pct_to_ha_brightness(15.5)  # halfway between 1 % and 30 %
    assert cmd.color_temp_kelvin == 6500
    assert cmd.rgb_color is None
    assert cmd.to_service_data() == {"brightness": cmd.brightness, "color_temp_kelvin": 6500}


def test_rgb_segment_uses_rgb_and_gains():
    cmd = rgb_cct_profile().resolve(5, 2000)
    assert cmd.segment == 0
    assert cmd.color_temp_kelvin is None
    assert cmd.rgb_color is not None and max(cmd.rgb_color) == 255
    assert cmd.brightness == pct_to_ha_brightness(20.5)
    # Gains at 5 %: (1.0, 0.9, 0.8) -> green/blue reduced relative to plain kelvin colour
    r, g, b = kelvin_to_rgb(2000)
    plain_ratio = g / r
    assert cmd.rgb_color[1] / cmd.rgb_color[0] == pytest.approx(plain_ratio * 0.9, abs=0.01)


def test_rgb_segment_clamps_kelvin():
    p = rgb_cct_profile()
    assert p.resolve(5, 5000).rgb_color == p.resolve(5, 2700).rgb_color


def test_minimum_is_first_point():
    cmd = rgb_cct_profile().resolve_minimum(2000)
    assert cmd.segment == 0 and cmd.brightness == pct_to_ha_brightness(1)


def test_hysteresis_keeps_previous_segment():
    p = rgb_cct_profile()  # border at 10, hysteresis 1
    assert p.resolve(10.5, 2500).segment == 1
    assert p.resolve(10.5, 2500, previous_segment=0).segment == 0
    assert p.resolve(11.5, 2500, previous_segment=0).segment == 1
    assert p.resolve(9.5, 2500, previous_segment=1).segment == 1
    assert p.resolve(8.5, 2500, previous_segment=1).segment == 0


def test_brightness_only_lamp_sends_no_kelvin():
    p = DimmableProfile(segments=(CctSegment(end=100, points=(CurvePoint(0, 1), CurvePoint(100, 100))),))
    assert p.resolve(50, 3000).to_service_data() == {"brightness": pct_to_ha_brightness(50.5)}


def test_ha_brightness_never_zero_when_on():
    assert pct_to_ha_brightness(0.01) == 1
    assert pct_to_ha_brightness(100) == 255


@pytest.mark.parametrize(
    "kwargs",
    [
        {"segments": ()},
        {"segments": (CctSegment(end=50, points=(CurvePoint(0, 1),)),)},
        {
            "segments": (
                CctSegment(end=60, points=(CurvePoint(0, 1),)),
                CctSegment(end=60, points=(CurvePoint(0, 1),)),
            )
        },
        {"segments": (CctSegment(end=100, points=(CurvePoint(0, 1),)),), "kelvin_min": 2000},
    ],
)
def test_invalid_profiles(kwargs):
    with pytest.raises(ValueError):
        DimmableProfile(**kwargs)


def test_invalid_points():
    with pytest.raises(ValueError):
        CurvePoint(10, 0)
    with pytest.raises(ValueError):
        CctSegment(end=100, points=(CurvePoint(50, 1), CurvePoint(40, 2)))
    with pytest.raises(ValueError):
        RgbPoint(0, 1, gains=(0, 0, 0))


def test_onoff_threshold_and_hysteresis():
    p = OnOffProfile(threshold=50, hysteresis=2)
    assert not p.resolve(49, 3000).on
    assert p.resolve(50, 3000).on
    assert p.resolve(49, 3000, previous_segment=1).on
    assert not p.resolve(51, 3000, previous_segment=0).on
    assert p.resolve(50, 3000).to_service_data() == {}


@pytest.mark.parametrize("profile", [rgb_cct_profile(), OnOffProfile(threshold=30, name="Flur")])
def test_serialisation_roundtrip(profile):
    data = json.loads(json.dumps(profile_to_dict(profile)))
    assert profile_from_dict(data) == profile


def test_rejects_newer_schema():
    data = profile_to_dict(rgb_cct_profile())
    data["version"] = 99
    with pytest.raises(ValueError):
        profile_from_dict(data)
