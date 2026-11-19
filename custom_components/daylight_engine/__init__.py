"""Daylight Engine – daylight-following light control for Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, SERVICE_APPLY, SERVICE_RESET_MANUAL, SUBENTRY_LAMP
from .controller import DaylightController, LampGroupConfig
from .settings import controller_settings_from_options, target_config_from_options
from .storage import ProfileStore

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass(slots=True)
class RuntimeData:
    controller: DaylightController
    profiles: ProfileStore


type DaylightConfigEntry = ConfigEntry[RuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register services (once, independent of entries)."""

    def _controller() -> DaylightController:
        entries = [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]
        if not entries:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_loaded")
        return entries[0].runtime_data.controller

    async def _reset_manual(call: ServiceCall) -> None:
        await _controller().async_reset_manual(call.data.get(ATTR_ENTITY_ID))

    async def _apply(call: ServiceCall) -> None:
        await _controller().async_update_now(call.data.get(ATTR_ENTITY_ID), call.data.get("transition"))

    entity_schema = vol.Schema({vol.Optional(ATTR_ENTITY_ID): cv.entity_ids})
    hass.services.async_register(DOMAIN, SERVICE_RESET_MANUAL, _reset_manual, schema=entity_schema)
    hass.services.async_register(
        DOMAIN,
        SERVICE_APPLY,
        _apply,
        schema=entity_schema.extend(
            {vol.Optional("transition"): vol.All(vol.Coerce(float), vol.Range(min=0, max=300))}
        ),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: DaylightConfigEntry) -> bool:
    profiles = ProfileStore(hass)
    stored = await profiles.async_load()

    groups = [
        LampGroupConfig.from_subentry(subentry.subentry_id, subentry.title, subentry.data)
        for subentry in entry.subentries.values()
        if subentry.subentry_type == SUBENTRY_LAMP
    ]
    controller = DaylightController(
        hass,
        entry.entry_id,
        target_config_from_options(entry.options),
        controller_settings_from_options(entry.options),
        groups,
        stored,
    )
    entry.runtime_data = RuntimeData(controller=controller, profiles=profiles)

    # Platforms first: the switches restore enabled/sleep before the first apply.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    controller.async_start()
    entry.async_on_unload(controller.async_stop)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: DaylightConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: DaylightConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
