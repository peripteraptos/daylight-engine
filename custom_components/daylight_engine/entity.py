"""Shared entity base."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, signal_update
from .controller import DaylightController


class DaylightEntity(Entity):
    """Entity attached to the single Daylight Engine service device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, controller: DaylightController, entry_title: str, key: str) -> None:
        self.controller = controller
        self._attr_unique_id = f"{controller.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, controller.entry_id)},
            name=entry_title,
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="Daylight Engine",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_update(self.controller.entry_id), self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
