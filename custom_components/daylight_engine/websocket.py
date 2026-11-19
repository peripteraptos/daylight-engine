"""Websocket API for the calibration panel."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.light import (
    ATTR_MAX_COLOR_TEMP_KELVIN,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_SUPPORTED_COLOR_MODES,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_FRIENDLY_NAME, ATTR_SUPPORTED_FEATURES
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .controller import DaylightController
from .engine import DeviceCommand, detect_capabilities, profile_from_dict, profile_to_dict

PREFIX = f"{DOMAIN}/"


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    for handler in (ws_lamps, ws_profile_save, ws_profile_reset, ws_calibrate, ws_preview):
        websocket_api.async_register_command(hass, handler)


def _entry(hass: HomeAssistant):  # noqa: ANN202
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry
    return None


def _controller(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> DaylightController | None:
    entry = _entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_loaded", "Daylight Engine is not loaded")
        return None
    return entry.runtime_data.controller


def _command_dict(command: DeviceCommand) -> dict[str, Any]:
    return {"service": command.service, "segment": command.segment, **command.to_service_data()}


def _lamp_info(controller: DaylightController, entity_id: str) -> dict[str, Any]:
    lamp = controller.lamps[entity_id]
    state = controller.hass.states.get(entity_id)
    profile = controller.profile_for(entity_id)
    attrs = state.attributes if state else {}
    caps = detect_capabilities(
        attrs.get(ATTR_SUPPORTED_COLOR_MODES),
        min_kelvin=attrs.get(ATTR_MIN_COLOR_TEMP_KELVIN),
        max_kelvin=attrs.get(ATTR_MAX_COLOR_TEMP_KELVIN),
        supported_features=int(attrs.get(ATTR_SUPPORTED_FEATURES, 0) or 0),
    )
    return {
        "entity_id": entity_id,
        "name": attrs.get(ATTR_FRIENDLY_NAME, entity_id),
        "group": lamp.group.title,
        "state": state.state if state else None,
        "capabilities": asdict(caps),
        "profile": profile_to_dict(profile) if profile else None,
        "profile_source": "stored" if lamp.profile_from_store else "default",
        "manual": lamp.manual,
        "calibrating": entity_id in controller.calibrating,
    }


@websocket_api.websocket_command({vol.Required("type"): PREFIX + "lamps"})
@websocket_api.require_admin
@callback
def ws_lamps(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    if (controller := _controller(hass, connection, msg)) is None:
        return
    target = controller.target
    connection.send_result(
        msg["id"],
        {
            "lamps": [_lamp_info(controller, e) for e in sorted(controller.lamps)],
            "target": None
            if target is None
            else {"brightness": target.brightness, "kelvin": target.kelvin, "mode": target.mode.value},
        },
    )


def _known_lamp(controller: DaylightController, connection, msg: dict) -> bool:  # noqa: ANN001
    if msg["entity_id"] in controller.lamps:
        return True
    connection.send_error(msg["id"], "unknown_lamp", f"{msg['entity_id']} is not managed by Daylight Engine")
    return False


@websocket_api.websocket_command(
    {
        vol.Required("type"): PREFIX + "profile/save",
        vol.Required("entity_id"): str,
        vol.Required("profile"): dict,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_profile_save(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    if (controller := _controller(hass, connection, msg)) is None or not _known_lamp(
        controller, connection, msg
    ):
        return
    try:
        profile = profile_from_dict(msg["profile"])
    except (KeyError, TypeError, ValueError) as err:
        connection.send_error(msg["id"], "invalid_profile", str(err))
        return
    await _entry(hass).runtime_data.profiles.async_save_profile(msg["entity_id"], profile)
    controller.set_profile(msg["entity_id"], profile)
    connection.send_result(msg["id"], _lamp_info(controller, msg["entity_id"]))


@websocket_api.websocket_command(
    {vol.Required("type"): PREFIX + "profile/reset", vol.Required("entity_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_profile_reset(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    if (controller := _controller(hass, connection, msg)) is None or not _known_lamp(
        controller, connection, msg
    ):
        return
    await _entry(hass).runtime_data.profiles.async_remove_profile(msg["entity_id"])
    controller.set_profile(msg["entity_id"], None)
    connection.send_result(msg["id"], _lamp_info(controller, msg["entity_id"]))


@websocket_api.websocket_command({vol.Required("type"): PREFIX + "calibrate", vol.Required("entity_id"): str})
@websocket_api.require_admin
@callback
def ws_calibrate(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Subscription: the lamp belongs to the panel until the subscription ends.

    Closing the panel, the browser tab or the connection ends it, so a lamp can
    never get stuck in calibration mode.
    """
    if (controller := _controller(hass, connection, msg)) is None or not _known_lamp(
        controller, connection, msg
    ):
        return
    entity_id = msg["entity_id"]
    was_on = controller.calibration_start(entity_id)

    @callback
    def _end() -> None:
        hass.async_create_task(controller.async_calibration_end(entity_id, was_on=was_on), eager_start=True)

    connection.subscriptions[msg["id"]] = _end
    connection.send_result(msg["id"], {"was_on": was_on})


@websocket_api.websocket_command(
    {
        vol.Required("type"): PREFIX + "preview",
        vol.Required("entity_id"): str,
        vol.Optional("profile"): dict,
        vol.Required("logical"): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
        vol.Required("kelvin"): vol.All(vol.Coerce(float), vol.Range(min=1000, max=10000)),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_preview(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    if (controller := _controller(hass, connection, msg)) is None or not _known_lamp(
        controller, connection, msg
    ):
        return
    entity_id = msg["entity_id"]
    if entity_id not in controller.calibrating:
        connection.send_error(msg["id"], "not_calibrating", "Start a calibration session first")
        return
    if "profile" in msg:
        try:
            profile = profile_from_dict(msg["profile"])
        except (KeyError, TypeError, ValueError) as err:
            connection.send_error(msg["id"], "invalid_profile", str(err))
            return
    else:
        profile = controller.profile_for(entity_id)
        if profile is None:
            connection.send_error(msg["id"], "unavailable", "Lamp is unavailable")
            return
    command = await controller.async_preview(entity_id, profile, msg["logical"], msg["kelvin"])
    connection.send_result(msg["id"], _command_dict(command))
