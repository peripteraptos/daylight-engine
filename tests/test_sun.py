from datetime import UTC, datetime, timedelta

import pytest

from custom_components.daylight_engine.engine.sun import solar_position

BERLIN = (52.52, 13.405)


def test_requires_aware_datetime():
    with pytest.raises(ValueError):
        solar_position(datetime(2026, 6, 21, 12), *BERLIN)


def test_summer_noon_berlin():
    # Solar noon in Berlin around 11:08 UTC on the June solstice, elevation ≈ 60.9°
    pos = solar_position(datetime(2026, 6, 21, 11, 8, tzinfo=UTC), *BERLIN)
    assert pos.elevation == pytest.approx(60.9, abs=0.2)
    assert pos.azimuth == pytest.approx(180, abs=3)


def test_morning_flag():
    assert solar_position(datetime(2026, 3, 1, 7, tzinfo=UTC), *BERLIN).is_morning
    assert not solar_position(datetime(2026, 3, 1, 15, tzinfo=UTC), *BERLIN).is_morning


@pytest.mark.parametrize(
    "lat,lon",
    [BERLIN, (-33.87, 151.21), (64.15, -21.94), (0.0, 0.0), (40.71, -74.0)],
)
def test_matches_astral(lat, lon):
    astral_sun = pytest.importorskip("astral.sun")
    from astral import Observer

    observer = Observer(latitude=lat, longitude=lon)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for hours in range(0, 24 * 365, 37):  # spread over a year and all times of day
        when = start + timedelta(hours=hours)
        ours = solar_position(when, lat, lon)
        expected_el = astral_sun.elevation(observer, when, with_refraction=False)
        expected_az = astral_sun.azimuth(observer, when)
        assert ours.elevation == pytest.approx(expected_el, abs=0.05), when
        if ours.elevation > -80:
            diff = (ours.azimuth - expected_az + 180) % 360 - 180
            assert abs(diff) < 0.2, when
