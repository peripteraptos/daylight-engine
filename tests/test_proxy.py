from datetime import timedelta
from typing import Any

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.light import DATA_COMPONENT, ColorMode
from homeassistant.config_entries import SOURCE_USER, ConfigSubentryData
from homeassistant.core import Context, HomeAssistant, ServiceCall
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.daylight_engine.const import DOMAIN, STORAGE_KEY_PROFILES, SUBENTRY_LAMP
from custom_components.daylight_engine.settings import default_options

CT_ATTRS = {
    "supported_color_modes": ["color_temp", "xy"],
    "color_mode": "color_temp",
    "min_color_temp_kelvin": 2200,
    "max_color_temp_kelvin": 6500,
    "supported_features": 0,
    "friendly_name": "Stehlampe",
}
WLED_ATTRS = {"supported_color_modes": ["rgb"], "color_mode": "rgb", "friendly_name": "Strip"}
ONOFF_ATTRS = {"supported_color_modes": ["onoff"], "color_mode": "onoff", "friendly_name": "Flur"}

RGB_CCT = {
    "version": 1,
    "type": "dimmable",
    "name": "",
    "kelvin_min": 2200,
    "kelvin_max": 6500,
    "hysteresis": 1.0,
    "segments": [
        {
            "type": "rgb",
            "end": 10,
            "min_kelvin": 1800,
            "max_kelvin": 3000,
            "points": [{"logical": 0, "device": 1}, {"logical": 10, "device": 30}],
        },
        {
            "type": "cct",
            "end": 100,
            "points": [{"logical": 10, "device": 1}, {"logical": 100, "device": 100}],
        },
    ],
}


def lamp(title: str, lights: list[str], proxy: bool = True) -> ConfigSubentryData:
    return ConfigSubentryData(
        data={"lights": lights, "sleep_action": "follow", "advanced": {"proxy": proxy}},
        subentry_type=SUBENTRY_LAMP,
        title=title,
        unique_id=None,
    )


@pytest.fixture
async def setup(hass: HomeAssistant, hass_storage: dict[str, Any]):
    hass_storage[STORAGE_KEY_PROFILES] = {
        "version": 1,
        "key": STORAGE_KEY_PROFILES,
        "data": {"profiles": {"light.stehlampe": RGB_CCT}},
    }
    hass.states.async_set("light.stehlampe", "off", CT_ATTRS)
    hass.states.async_set("light.strip", "off", WLED_ATTRS)
    hass.states.async_set("light.flur", "off", ONOFF_ATTRS)
    hass.states.async_set("light.regal", "off", {**CT_ATTRS, "friendly_name": "Regal"})
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Daylight",
        options=default_options(),
        subentries_data=[
            lamp("Wohnzimmer", ["light.stehlampe", "light.strip", "light.flur"]),
            lamp("Regal", ["light.regal"], proxy=False),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    calls_on = async_mock_service(hass, "light", "turn_on")
    calls_off = async_mock_service(hass, "light", "turn_off")
    return entry, calls_on, calls_off


def proxy(hass: HomeAssistant, entity_id: str):
    return hass.data[DATA_COMPONENT].get_entity(entity_id)


async def report(hass: HomeAssistant, call: ServiceCall, base: dict, **attrs) -> None:
    """Let the source light report back what it was told (with the command's context)."""
    entity_id = call.data["entity_id"][0]
    data = {k: v for k, v in call.data.items() if k not in ("entity_id", "transition")}
    hass.states.async_set(entity_id, "on", {**base, **data, **attrs}, context=call.context)
    await hass.async_block_till_done()


async def test_proxies_created_only_where_enabled(hass: HomeAssistant, setup) -> None:
    for entity_id in ("light.stehlampe_daylight", "light.strip_daylight", "light.flur_daylight"):
        assert hass.states.get(entity_id) is not None, entity_id
    assert hass.states.get("light.regal_daylight") is None
    assert hass.states.get("light.stehlampe_daylight").attributes["source"] == "light.stehlampe"


async def test_color_modes(hass: HomeAssistant, setup) -> None:
    ct = hass.states.get("light.stehlampe_daylight").attributes
    assert set(ct["supported_color_modes"]) == {ColorMode.COLOR_TEMP, ColorMode.HS}
    assert (ct["min_color_temp_kelvin"], ct["max_color_temp_kelvin"]) == (1800, 6500)
    # An RGB-only strip gets a colour temperature mode through its emulating profile
    strip = hass.states.get("light.strip_daylight").attributes
    assert set(strip["supported_color_modes"]) == {ColorMode.COLOR_TEMP, ColorMode.HS}
    assert hass.states.get("light.flur_daylight").attributes["supported_color_modes"] == [ColorMode.ONOFF]


async def test_turn_on_sends_one_calibrated_command(hass: HomeAssistant, setup) -> None:
    entry, calls_on, _ = setup
    controller = entry.runtime_data.controller
    await proxy(hass, "light.stehlampe_daylight").async_turn_on()
    await hass.async_block_till_done()
    assert len(calls_on) == 1
    expected = controller.profile_for("light.stehlampe").resolve(
        controller.target.brightness, controller.target.kelvin
    )
    assert calls_on[0].data["brightness"] == expected.brightness

    # The source reports back -> no second "correction" command (no flash)
    await report(hass, calls_on[0], CT_ATTRS)
    assert len(calls_on) == 1
    state = hass.states.get("light.stehlampe_daylight")
    assert state.state == "on"
    assert state.attributes["brightness"] == round(controller.target.brightness * 255 / 100)
    assert state.attributes["control"] == "automatic"


async def test_low_brightness_uses_rgb_segment(hass: HomeAssistant, setup) -> None:
    _, calls_on, _ = setup
    await proxy(hass, "light.stehlampe_daylight").async_turn_on(brightness=13)  # ≈ 5 % logical
    await hass.async_block_till_done()
    data = calls_on[-1].data
    assert "rgb_color" in data and "color_temp_kelvin" not in data
    await report(hass, calls_on[-1], CT_ATTRS, color_mode="rgb")
    state = hass.states.get("light.stehlampe_daylight")
    # The proxy keeps showing white at the logical brightness the user chose
    assert state.attributes["brightness"] == 13
    assert state.attributes["color_mode"] == ColorMode.COLOR_TEMP


async def test_brightness_override_keeps_kelvin_following(
    hass: HomeAssistant, setup, freezer: FrozenDateTimeFactory
) -> None:
    entry, calls_on, calls_off = setup
    controller = entry.runtime_data.controller
    await proxy(hass, "light.stehlampe_daylight").async_turn_on(brightness=153)  # 60 %
    await hass.async_block_till_done()
    await report(hass, calls_on[-1], CT_ATTRS)
    assert hass.states.get("light.stehlampe_daylight").attributes["control"] == "partial"
    lamp_state = controller.lamps["light.stehlampe"]
    assert lamp_state.override_brightness == pytest.approx(60)

    # Daylight moves on: the colour temperature follows, the brightness stays
    controller.target = type(controller.target)(brightness=20, kelvin=3000)
    calls_on.clear()
    await controller.async_apply(force=True)
    await hass.async_block_till_done()
    assert calls_on[-1].data["color_temp_kelvin"] == 3000
    assert (
        calls_on[-1].data["brightness"]
        == controller.profile_for("light.stehlampe").resolve(60, 3000).brightness
    )

    # Switching off resets the override
    await proxy(hass, "light.stehlampe_daylight").async_turn_off()
    await hass.async_block_till_done()
    assert calls_off[-1].data["entity_id"] == ["light.stehlampe"]
    hass.states.async_set("light.stehlampe", "off", CT_ATTRS, context=calls_off[-1].context)
    await hass.async_block_till_done()
    assert not lamp_state.has_override


async def test_colour_pauses_lamp(hass: HomeAssistant, setup, freezer: FrozenDateTimeFactory) -> None:
    entry, calls_on, _ = setup
    controller = entry.runtime_data.controller
    entity = proxy(hass, "light.stehlampe_daylight")
    await entity.async_turn_on(hs_color=(240.0, 100.0))
    await hass.async_block_till_done()
    assert calls_on[-1].data["hs_color"] == (240.0, 100.0)
    assert controller.manual_lamps == ["light.stehlampe"]
    await report(hass, calls_on[-1], CT_ATTRS, color_mode="xy")
    state = hass.states.get("light.stehlampe_daylight")
    assert state.attributes["color_mode"] == ColorMode.HS
    assert state.attributes["control"] == "manual"

    # Periodic updates leave it alone
    calls_on.clear()
    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    await controller.async_apply(force=True)
    assert calls_on == []

    # Choosing a colour temperature on the proxy hands it back to the automatic (kelvin pinned)
    await entity.async_turn_on(color_temp_kelvin=4000)
    await hass.async_block_till_done()
    assert controller.manual_lamps == []
    assert calls_on[-1].data["color_temp_kelvin"] == 4000


async def test_external_change_is_estimated(
    hass: HomeAssistant, setup, freezer: FrozenDateTimeFactory
) -> None:
    entry, calls_on, _ = setup
    controller = entry.runtime_data.controller
    hass.states.async_set("light.stehlampe", "on", {**CT_ATTRS, "brightness": 128}, context=Context())
    await hass.async_block_till_done()
    await report(hass, calls_on[-1], CT_ATTRS)  # our turn-on correction
    freezer.tick(timedelta(seconds=30))
    # someone dims the source directly to device 50 % (white segment)
    hass.states.async_set(
        "light.stehlampe", "on", {**CT_ATTRS, "brightness": 128, "color_temp_kelvin": 2700}, context=Context()
    )
    await hass.async_block_till_done()
    assert controller.manual_lamps == ["light.stehlampe"]
    logical = hass.states.get("light.stehlampe_daylight").attributes["brightness"] * 100 / 255
    # device 50 % in the 10–100 % white segment ≈ logical 55 %
    assert logical == pytest.approx(55, abs=1.5)


async def test_onoff_proxy(hass: HomeAssistant, setup) -> None:
    _, calls_on, calls_off = setup
    entity = proxy(hass, "light.flur_daylight")
    await entity.async_turn_on()
    await hass.async_block_till_done()
    assert calls_on[-1].data == {"entity_id": ["light.flur"]}
    await entity.async_turn_off()
    await hass.async_block_till_done()
    assert calls_off[-1].data == {"entity_id": ["light.flur"]}


async def test_proxy_cannot_be_managed(hass: HomeAssistant, setup) -> None:
    entry, _, _ = setup
    flow = hass.config_entries.subentries
    result = await flow.async_init((entry.entry_id, SUBENTRY_LAMP), context={"source": SOURCE_USER})
    result = await flow.async_configure(
        result["flow_id"],
        {
            "name": "x",
            "lights": ["light.stehlampe_daylight"],
            "sleep_action": "follow",
            "advanced": {"transition_mode": "auto", "detect_manual": True, "proxy": False},
        },
    )
    assert result["errors"] == {"lights": "proxy_not_allowed"}
