"""Sensors exposing the current global target."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import DEGREE, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DaylightConfigEntry
from .entity import DaylightEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: DaylightConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    controller = entry.runtime_data.controller
    async_add_entities(
        [
            TargetBrightnessSensor(controller, entry.title, "target_brightness"),
            TargetKelvinSensor(controller, entry.title, "target_kelvin"),
            SunElevationSensor(controller, entry.title, "sun_elevation"),
        ]
    )


class TargetBrightnessSensor(DaylightEntity, SensorEntity):
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    @property
    def native_value(self) -> float | None:
        target = self.controller.target
        return None if target is None else round(target.brightness, 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        target = self.controller.target
        return {"mode": None if target is None else target.mode.value}


class TargetKelvinSensor(DaylightEntity, SensorEntity):
    _attr_native_unit_of_measurement = "K"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    @property
    def native_value(self) -> float | None:
        target = self.controller.target
        return None if target is None else round(target.kelvin)


class SunElevationSensor(DaylightEntity, SensorEntity):
    _attr_native_unit_of_measurement = DEGREE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> float | None:
        position = self.controller.position
        return None if position is None else round(position.elevation, 2)
