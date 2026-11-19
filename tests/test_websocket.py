from typing import Any

import pytest
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import Context, HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.daylight_engine.const import DOMAIN, STORAGE_KEY_PROFILES, SUBENTRY_LAMP
from custom_components.daylight_engine.engine import profile_from_dict
from custom_components.daylight_engine.settings import default_options

ATTRS = {
    "supported_color_modes": ["color_temp", "xy"],
    "color_mode": "color_temp",
    "min_color_temp_kelvin": 2000,
    "max_color_temp_kelvin": 6500,
    "supported_features": 32,
    "friendly_name": "Stehlampe",
}

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
            "points": [{"logical": 0, "device": 1, "gains": [1, 0.8, 0.6]}, {"logical": 10, "device": 30}],
        },
        {
            "type": "cct",
            "end": 100,
            "points": [{"logical": 10, "device": 1}, {"logical": 100, "device": 100}],
        },
    ],
}


@pytest.fixture
async def setup(hass: HomeAssistant, hass_storage: dict[str, Any]):
    hass_storage[STORAGE_KEY_PROFILES] = {
        "version": 1,
        "key": STORAGE_KEY_PROFILES,
        "data": {"profiles": {"light.shelf": RGB_CCT}},
    }
    hass.states.async_set("light.lamp", "off", ATTRS)
    hass.states.async_set("light.shelf", "on", {**ATTRS, "friendly_name": "Regal", "brightness": 100})
    entry = MockConfigEntry(
        domain=DOMAIN,
        options=default_options(),
        subentries_data=[
            ConfigSubentryData(
                data={"lights": ["light.lamp", "light.shelf"], "sleep_action": "follow", "advanced": {}},
                subentry_type=SUBENTRY_LAMP,
                title="Wohnzimmer",
                unique_id=None,
            )
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    calls_on = async_mock_service(hass, "light", "turn_on")
    calls_off = async_mock_service(hass, "light", "turn_off")
    return entry, calls_on, calls_off


async def test_panel_registered(hass: HomeAssistant, setup) -> None:
    assert "daylight-engine" in hass.data["frontend_panels"]


async def test_lamps(hass: HomeAssistant, setup, hass_ws_client) -> None:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "daylight_engine/lamps"})
    res = await client.receive_json()
    assert res["success"]
    lamps = {lamp["entity_id"]: lamp for lamp in res["result"]["lamps"]}
    assert lamps["light.lamp"]["name"] == "Stehlampe"
    assert lamps["light.lamp"]["group"] == "Wohnzimmer"
    assert lamps["light.lamp"]["profile_source"] == "default"
    assert lamps["light.lamp"]["capabilities"]["rgb"] is True
    assert lamps["light.shelf"]["profile_source"] == "stored"
    assert lamps["light.shelf"]["profile"]["segments"][0]["type"] == "rgb"
    assert res["result"]["target"]["mode"] == "daylight"


async def test_calibration_session(hass: HomeAssistant, setup, hass_ws_client) -> None:
    entry, calls_on, calls_off = setup
    controller = entry.runtime_data.controller
    client = await hass_ws_client(hass)

    # preview without a session is refused
    await client.send_json_auto_id(
        {"type": "daylight_engine/preview", "entity_id": "light.lamp", "logical": 5, "kelvin": 2700}
    )
    assert (await client.receive_json())["error"]["code"] == "not_calibrating"

    await client.send_json_auto_id({"type": "daylight_engine/calibrate", "entity_id": "light.lamp"})
    start = await client.receive_json()
    assert start["success"] and start["result"] == {"was_on": False}
    assert "light.lamp" in controller.calibrating

    # preview with an unsaved draft profile drives the lamp directly, without transition
    await client.send_json_auto_id(
        {
            "type": "daylight_engine/preview",
            "entity_id": "light.lamp",
            "profile": RGB_CCT,
            "logical": 5,
            "kelvin": 2700,
        }
    )
    res = await client.receive_json()
    assert res["success"] and res["result"]["service"] == "turn_on" and res["result"]["segment"] == 0
    await hass.async_block_till_done()
    assert calls_on[-1].data["rgb_color"] and calls_on[-1].data["transition"] == 0

    # while calibrating, state changes from elsewhere don't trigger corrections/manual mode
    calls_on.clear()
    hass.states.async_set("light.lamp", "on", {**ATTRS, "brightness": 3}, context=Context())
    await hass.async_block_till_done()
    assert calls_on == [] and controller.manual_lamps == []

    # ending the session hands the lamp back: it was off before, so it is switched off again
    await client.send_json_auto_id({"type": "unsubscribe_events", "subscription": start["id"]})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()
    assert "light.lamp" not in controller.calibrating
    assert calls_off[-1].data["entity_id"] == ["light.lamp"]


async def test_session_ends_when_connection_closes(hass: HomeAssistant, setup, hass_ws_client) -> None:
    entry, calls_on, _ = setup
    controller = entry.runtime_data.controller
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "daylight_engine/calibrate", "entity_id": "light.shelf"})
    assert (await client.receive_json())["result"] == {"was_on": True}
    calls_on.clear()
    await client.close()
    await hass.async_block_till_done()
    assert controller.calibrating == set()
    # it was on: the current target is re-applied
    assert calls_on and calls_on[-1].data["entity_id"] == ["light.shelf"]


async def test_save_and_reset_profile(hass: HomeAssistant, setup, hass_ws_client, hass_storage) -> None:
    entry, _, _ = setup
    controller = entry.runtime_data.controller
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": "daylight_engine/profile/save", "entity_id": "light.lamp", "profile": {"type": "nonsense"}}
    )
    assert (await client.receive_json())["error"]["code"] == "invalid_profile"

    await client.send_json_auto_id(
        {"type": "daylight_engine/profile/save", "entity_id": "light.lamp", "profile": RGB_CCT}
    )
    res = await client.receive_json()
    assert res["success"] and res["result"]["profile_source"] == "stored"
    assert controller.profile_for("light.lamp") == profile_from_dict(RGB_CCT)
    await hass.async_block_till_done()
    assert "light.lamp" in hass_storage[STORAGE_KEY_PROFILES]["data"]["profiles"]

    await client.send_json_auto_id({"type": "daylight_engine/profile/reset", "entity_id": "light.lamp"})
    res = await client.receive_json()
    assert res["result"]["profile_source"] == "default"
    assert len(res["result"]["profile"]["segments"]) == 1
    await hass.async_block_till_done()
    assert "light.lamp" not in hass_storage[STORAGE_KEY_PROFILES]["data"]["profiles"]


async def test_unknown_lamp(hass: HomeAssistant, setup, hass_ws_client) -> None:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "daylight_engine/calibrate", "entity_id": "light.nope"})
    assert (await client.receive_json())["error"]["code"] == "unknown_lamp"
