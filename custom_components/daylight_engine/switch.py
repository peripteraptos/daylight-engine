"""Global switches: automatic control on/off and sleep mode."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import DaylightConfigEntry
from .entity import DaylightEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: DaylightConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    controller = entry.runtime_data.controller
    async_add_entities(
        [
            EnabledSwitch(controller, entry.title),
            SleepSwitch(controller, entry.title),
            BrightSwitch(controller, entry.title),
        ]
    )


class EnabledSwitch(DaylightEntity, SwitchEntity, RestoreEntity):
    """Turns the automatic adjustment on or off for all lamps."""

    def __init__(self, controller, title: str) -> None:  # noqa: ANN001
        super().__init__(controller, title, "enabled")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            await self.controller.async_set_enabled(last.state == STATE_ON, apply=False)

    @property
    def is_on(self) -> bool:
        return self.controller.enabled

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        overrides = {
            entity_id: {
                k: v
                for k, v in (("brightness", lamp.override_brightness), ("kelvin", lamp.override_kelvin))
                if v is not None
            }
            for entity_id, lamp in sorted(self.controller.lamps.items())
            if lamp.has_override
        }
        return {
            "managed_lights": sorted(self.controller.lamps),
            "manual_control": self.controller.manual_lamps,
            "partial_override": overrides,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.controller.async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.controller.async_set_enabled(False)


class SleepSwitch(DaylightEntity, SwitchEntity, RestoreEntity):
    """One sleep switch for all lamps; each lamp decides what sleep means for it."""

    def __init__(self, controller, title: str) -> None:  # noqa: ANN001
        super().__init__(controller, title, "sleep")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            await self.controller.async_set_sleep(last.state == STATE_ON, apply=False)

    @property
    def is_on(self) -> bool:
        return self.controller.sleep

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.controller.async_set_sleep(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.controller.async_set_sleep(False)


class BrightSwitch(DaylightEntity, SwitchEntity):
    """Full brightness for all lamps, e.g. when searching for something.

    Not restored after a restart on purpose: it is a temporary mode.
    """

    def __init__(self, controller, title: str) -> None:  # noqa: ANN001
        super().__init__(controller, title, "bright")

    @property
    def is_on(self) -> bool:
        return self.controller.bright

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.controller.async_set_bright(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.controller.async_set_bright(False)
