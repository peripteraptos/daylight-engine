from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import Context, HomeAssistant, ServiceCall
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.daylight_engine.const import DOMAIN, SUBENTRY_LAMP
from custom_components.daylight_engine.controller import DaylightController
from custom_components.daylight_engine.engine.profile import (
    CctSegment,
    CurvePoint,
    DimmableProfile,
    RgbPoint,
    RgbSegment,
    pct_to_ha_brightness,
)
from custom_components.daylight_engine.settings import default_options

CCT_ATTRS = {
    "supported_color_modes": ["color_temp", "xy"],
    "color_mode": "color_temp",
    "min_color_temp_kelvin": 2000,
    "max_color_temp_kelvin": 6500,
    "supported_features": 32,
    "brightness": 200,
    "color_temp_kelvin": 4000,
}
ONOFF_ATTRS = {"supported_color_modes": ["onoff"], "color_mode": "onoff"}


def lamp(title: str, lights: list[str], sleep_action: str = "follow") -> ConfigSubentryData:
    return ConfigSubentryData(
        data={"lights": lights, "sleep_action": sleep_action, "advanced": {}},
        subentry_type=SUBENTRY_LAMP,
        title=title,
        unique_id=None,
    )


@pytest.fixture
async def setup(hass: HomeAssistant):
    """Integration with three lights; light services are mocked and recorded."""
    hass.states.async_set("light.desk", "off", CCT_ATTRS)
    hass.states.async_set("light.bed", "off", CCT_ATTRS)
    hass.states.async_set("light.plug", "off", ONOFF_ATTRS)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Daylight",
        options=default_options(),
        subentries_data=[
            lamp("Schreibtisch", ["light.desk"]),
            lamp("Bett", ["light.bed"], sleep_action="off"),
            lamp("Steckdose", ["light.plug"], sleep_action="off"),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    calls_on = async_mock_service(hass, "light", "turn_on")
    calls_off = async_mock_service(hass, "light", "turn_off")
    controller: DaylightController = entry.runtime_data.controller
    return controller, calls_on, calls_off


def entity_ids(call: ServiceCall) -> list[str]:
    value = call.data["entity_id"]
    return [value] if isinstance(value, str) else list(value)


async def switch_on_externally(hass: HomeAssistant, entity_id: str, **attrs) -> None:
    hass.states.async_set(entity_id, "on", {**CCT_ATTRS, **attrs}, context=Context())
    await hass.async_block_till_done()


async def test_entities_created(hass: HomeAssistant, setup) -> None:
    controller, _, _ = setup
    assert hass.states.get("switch.daylight_automatic_control").state == "on"
    assert hass.states.get("switch.daylight_sleep_mode").state == "off"
    brightness = hass.states.get("sensor.daylight_target_brightness")
    kelvin = hass.states.get("sensor.daylight_target_colour_temperature")
    assert float(brightness.state) == pytest.approx(controller.target.brightness, abs=0.1)
    assert float(kelvin.state) == pytest.approx(controller.target.kelvin, abs=1)
    attrs = hass.states.get("switch.daylight_automatic_control").attributes
    assert attrs["managed_lights"] == ["light.bed", "light.desk", "light.plug"]


async def test_corrects_light_switched_on_outside_ha(hass: HomeAssistant, setup) -> None:
    controller, calls_on, _ = setup
    await switch_on_externally(hass, "light.desk")

    assert len(calls_on) == 1
    call = calls_on[0]
    assert entity_ids(call) == ["light.desk"]
    target = controller.target
    assert call.data["color_temp_kelvin"] == round(max(2000, min(6500, target.kelvin)))
    assert call.data["brightness"] == pct_to_ha_brightness(target.brightness)
    assert "transition" not in call.data  # turn_on_transition defaults to 0


async def test_onoff_lamp_is_never_switched_on(hass: HomeAssistant, setup) -> None:
    _, calls_on, _ = setup
    hass.states.async_set("light.plug", "on", ONOFF_ATTRS, context=Context())
    await hass.async_block_till_done()
    assert calls_on == []


async def test_own_state_reports_are_not_manual(
    hass: HomeAssistant, setup, freezer: FrozenDateTimeFactory
) -> None:
    controller, calls_on, _ = setup
    await switch_on_externally(hass, "light.desk")
    sent = calls_on[0]

    # The device reports back with our context -> not manual
    hass.states.async_set(
        "light.desk",
        "on",
        {
            **CCT_ATTRS,
            "brightness": sent.data["brightness"],
            "color_temp_kelvin": sent.data["color_temp_kelvin"],
        },
        context=sent.context,
    )
    await hass.async_block_till_done()
    assert controller.manual_lamps == []

    # A late report without context but matching what we sent -> not manual either
    freezer.tick(timedelta(seconds=30))
    hass.states.async_set(
        "light.desk",
        "on",
        {
            **CCT_ATTRS,
            "brightness": sent.data["brightness"] + 1,
            "color_temp_kelvin": sent.data["color_temp_kelvin"],
        },
        context=Context(),
    )
    await hass.async_block_till_done()
    assert controller.manual_lamps == []


async def test_manual_change_pauses_lamp_until_off(
    hass: HomeAssistant, setup, freezer: FrozenDateTimeFactory
) -> None:
    controller, calls_on, _ = setup
    await switch_on_externally(hass, "light.desk")
    freezer.tick(timedelta(seconds=30))

    hass.states.async_set("light.desk", "on", {**CCT_ATTRS, "brightness": 12}, context=Context())
    await hass.async_block_till_done()
    assert controller.manual_lamps == ["light.desk"]
    assert hass.states.get("switch.daylight_automatic_control").attributes["manual_control"] == ["light.desk"]

    calls_on.clear()
    await hass.services.async_call(DOMAIN, "apply", {}, blocking=True)
    await hass.async_block_till_done()
    assert calls_on == []

    hass.states.async_set("light.desk", "off", CCT_ATTRS, context=Context())
    await hass.async_block_till_done()
    assert controller.manual_lamps == []


async def test_reset_manual_service(hass: HomeAssistant, setup, freezer: FrozenDateTimeFactory) -> None:
    controller, calls_on, _ = setup
    await switch_on_externally(hass, "light.desk")
    freezer.tick(timedelta(seconds=30))
    hass.states.async_set("light.desk", "on", {**CCT_ATTRS, "brightness": 12}, context=Context())
    await hass.async_block_till_done()
    calls_on.clear()

    await hass.services.async_call(DOMAIN, "reset_manual", {"entity_id": ["light.desk"]}, blocking=True)
    await hass.async_block_till_done()
    assert controller.manual_lamps == []
    assert len(calls_on) == 1


async def test_periodic_update_uses_transition_and_thresholds(
    hass: HomeAssistant, setup, freezer: FrozenDateTimeFactory
) -> None:
    controller, calls_on, _ = setup
    await switch_on_externally(hass, "light.desk")
    calls_on.clear()

    # Target unchanged -> tick sends nothing
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert calls_on == []

    # Forced apply sends with the configured transition (light reports transition support)
    await hass.services.async_call(DOMAIN, "apply", {"entity_id": ["light.desk"]}, blocking=True)
    await hass.async_block_till_done()
    assert calls_on[-1].data["transition"] == 10


async def test_sleep_mode_per_lamp_behaviour(hass: HomeAssistant, setup) -> None:
    controller, calls_on, calls_off = setup
    for entity_id in ("light.desk", "light.bed"):
        await switch_on_externally(hass, entity_id)
    hass.states.async_set("light.plug", "on", ONOFF_ATTRS, context=Context())
    await hass.async_block_till_done()
    calls_on.clear()

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.daylight_sleep_mode"}, blocking=True
    )
    await hass.async_block_till_done()

    off_targets = sorted(e for call in calls_off for e in entity_ids(call))
    assert off_targets == ["light.bed", "light.plug"]
    desk = [c for c in calls_on if "light.desk" in entity_ids(c)]
    # "follow": the sleep target (1 %, 2000 K) goes through the lamp's profile
    expected = controller.profile_for("light.desk").resolve(1, 2000)
    assert desk and desk[-1].data["brightness"] == expected.brightness
    assert desk[-1].data["color_temp_kelvin"] == 2000
    assert hass.states.get("sensor.daylight_target_brightness").attributes["mode"] == "sleep"


async def test_switching_on_during_sleep_with_off_action_dims_instead(hass: HomeAssistant, setup) -> None:
    controller, calls_on, calls_off = setup
    await controller.async_set_sleep(True)
    await switch_on_externally(hass, "light.bed")
    assert calls_off == []
    assert calls_on[-1].data["brightness"] == pct_to_ha_brightness(1)


async def test_disabled_does_nothing(hass: HomeAssistant, setup) -> None:
    _, calls_on, _ = setup
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.daylight_automatic_control"}, blocking=True
    )
    await switch_on_externally(hass, "light.desk")
    assert calls_on == []


async def test_stored_profile_is_used(hass: HomeAssistant, setup) -> None:
    controller, calls_on, _ = setup
    profile = DimmableProfile(
        kelvin_min=2200,
        kelvin_max=6500,
        segments=(
            RgbSegment(end=50, points=(RgbPoint(0, 1), RgbPoint(50, 30))),
            CctSegment(end=100, points=(CurvePoint(50, 1), CurvePoint(100, 100))),
        ),
    )
    controller.lamps["light.desk"].profile = profile
    await controller.async_set_sleep(True)
    await switch_on_externally(hass, "light.desk")
    call = calls_on[-1]
    assert "rgb_color" in call.data and "color_temp_kelvin" not in call.data
