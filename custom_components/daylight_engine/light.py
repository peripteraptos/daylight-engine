"""Proxy lights: calibrated stand-ins for the real lamps.

A proxy sits in front of a real lamp. Its brightness slider is the *logical*
brightness (through the lamp's calibration profile, including an RGB low end),
and switching it on sends the right values in a single command, so the lamp
never flashes up in its old colour. Picking a colour pauses the automatic
control for that lamp; picking only a brightness or colour temperature
overrides just that part while the rest keeps following the daylight curve.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.const import ATTR_FRIENDLY_NAME, ATTR_SUPPORTED_FEATURES, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from . import DaylightConfigEntry
from .const import CONF_ADVANCED, CONF_PROXY, SUBENTRY_LAMP, signal_update
from .controller import DaylightController
from .engine import DimmableProfile, OnOffProfile, RgbSegment
from .engine.detect import COLOR_MODES_RGB

DEFAULT_MIN_KELVIN = 1800
DEFAULT_MAX_KELVIN = 6500


async def async_setup_entry(
    hass: HomeAssistant, entry: DaylightConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    controller = entry.runtime_data.controller
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_LAMP:
            continue
        if not subentry.data.get(CONF_ADVANCED, {}).get(CONF_PROXY, False):
            continue
        group = next((g for g in controller.groups if g.subentry_id == subentry.subentry_id), None)
        if group is None:
            continue
        async_add_entities(
            [ProxyLight(controller, source) for source in group.lights],
            config_subentry_id=subentry.subentry_id,
        )


class ProxyLight(LightEntity):
    _attr_should_poll = False
    _attr_has_entity_name = False

    def __init__(self, controller: DaylightController, source: str) -> None:
        self.controller = controller
        self.source = source
        self._attr_unique_id = f"{controller.entry_id}_{source}_proxy"
        state = controller.hass.states.get(source)
        base = state.attributes.get(ATTR_FRIENDLY_NAME) if state else None
        self._attr_name = f"{base or source.split('.', 1)[1].replace('_', ' ').title()} Daylight"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_state_change_event(self.hass, [self.source], self._handle_source_change)
        )
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_update(self.controller.entry_id), self._handle_update)
        )

    @callback
    def _handle_source_change(self, _event: Event[EventStateChangedData]) -> None:
        self.async_write_ha_state()

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    # ------------------------------------------------------------------ capabilities

    @property
    def _source_attrs(self) -> dict[str, Any]:
        state = self.hass.states.get(self.source)
        return dict(state.attributes) if state else {}

    @property
    def _profile(self):  # noqa: ANN202
        return self.controller.profile_for(self.source)

    @property
    def _kelvin_range(self) -> tuple[int, int] | None:
        profile = self._profile
        if not isinstance(profile, DimmableProfile):
            return None
        lows, highs = [], []
        if profile.kelvin_min is not None and profile.kelvin_max is not None:
            lows.append(profile.kelvin_min)
            highs.append(profile.kelvin_max)
        for segment in profile.segments:
            if isinstance(segment, RgbSegment):
                lows.append(segment.min_kelvin)
                highs.append(segment.max_kelvin)
        if not lows:
            return None
        return int(min(lows)), int(max(highs))

    @property
    def _source_has_color(self) -> bool:
        modes = self._source_attrs.get(ATTR_SUPPORTED_COLOR_MODES) or []
        return any(str(m) in COLOR_MODES_RGB for m in modes)

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        profile = self._profile
        if profile is None or isinstance(profile, OnOffProfile):
            return {ColorMode.ONOFF}
        modes: set[ColorMode] = set()
        if self._kelvin_range is not None:
            modes.add(ColorMode.COLOR_TEMP)
        if self._source_has_color:
            modes.add(ColorMode.HS)
        return modes or {ColorMode.BRIGHTNESS}

    @property
    def supported_features(self) -> LightEntityFeature:
        features = int(self._source_attrs.get(ATTR_SUPPORTED_FEATURES, 0) or 0)
        return (
            LightEntityFeature.TRANSITION
            if features & LightEntityFeature.TRANSITION
            else LightEntityFeature(0)
        )

    @property
    def min_color_temp_kelvin(self) -> int:
        return (self._kelvin_range or (DEFAULT_MIN_KELVIN, DEFAULT_MAX_KELVIN))[0]

    @property
    def max_color_temp_kelvin(self) -> int:
        return (self._kelvin_range or (DEFAULT_MIN_KELVIN, DEFAULT_MAX_KELVIN))[1]

    # ------------------------------------------------------------------ state

    @property
    def available(self) -> bool:
        state = self.hass.states.get(self.source)
        return state is not None and state.state != STATE_UNAVAILABLE

    @property
    def is_on(self) -> bool:
        state = self.hass.states.get(self.source)
        return state is not None and state.state == STATE_ON

    @property
    def _view(self) -> tuple[float | None, float | None, bool]:
        return self.controller.proxy_view(self.source)

    @property
    def _showing_color(self) -> bool:
        lamp = self.controller.lamps[self.source]
        return (
            lamp.manual
            and ColorMode.HS in self.supported_color_modes
            and str(self._source_attrs.get("color_mode")) in COLOR_MODES_RGB
        )

    @property
    def color_mode(self) -> ColorMode:
        modes = self.supported_color_modes
        if len(modes) == 1:
            return next(iter(modes))
        if self._showing_color:
            return ColorMode.HS
        return ColorMode.COLOR_TEMP if ColorMode.COLOR_TEMP in modes else next(iter(modes))

    @property
    def brightness(self) -> int | None:
        logical, _, _ = self._view
        if logical is None or self.color_mode is ColorMode.ONOFF:
            return None
        return max(1, min(255, round(logical * 255 / 100)))

    @property
    def color_temp_kelvin(self) -> int | None:
        _, kelvin, _ = self._view
        if kelvin is None:
            return None
        return int(max(self.min_color_temp_kelvin, min(self.max_color_temp_kelvin, kelvin)))

    @property
    def hs_color(self) -> tuple[float, float] | None:
        hs = self._source_attrs.get(ATTR_HS_COLOR)
        return tuple(hs) if hs else None  # type: ignore[return-value]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        lamp = self.controller.lamps[self.source]
        if lamp.manual:
            control = "manual"
        elif lamp.has_override:
            control = "partial"
        else:
            control = "automatic"
        return {"source": self.source, "control": control}

    # ------------------------------------------------------------------ commands

    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        color = {ATTR_HS_COLOR: kwargs[ATTR_HS_COLOR]} if ATTR_HS_COLOR in kwargs else None
        await self.controller.async_proxy_turn_on(
            self.source,
            brightness=None if brightness is None else brightness * 100 / 255,
            kelvin=kwargs.get(ATTR_COLOR_TEMP_KELVIN),
            color=color,
            transition=kwargs.get(ATTR_TRANSITION),
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.controller.async_proxy_turn_off(self.source, transition=kwargs.get(ATTR_TRANSITION))
