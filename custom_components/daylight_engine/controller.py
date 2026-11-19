"""Runtime controller: keeps managed lights in line with the daylight target."""

from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from functools import partial
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    ATTR_TRANSITION,
    LightEntityFeature,
)
from homeassistant.components.light import (
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Context,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ADVANCED,
    CONF_DETECT_MANUAL,
    CONF_LIGHTS,
    CONF_SLEEP_ACTION,
    CONF_TRANSITION_MODE,
    TRANSITION_ALWAYS,
    TRANSITION_AUTO,
    TRANSITION_NEVER,
    signal_update,
)
from .engine import (
    DeviceCommand,
    DimmableProfile,
    OnOffProfile,
    Profile,
    SleepAction,
    SolarPosition,
    Target,
    TargetConfig,
    TargetMode,
    compute_target,
    default_profile,
    detect_capabilities,
    estimate_logical,
    resolve_lamp_command,
    solar_position,
)
from .engine.detect import COLOR_MODES_RGB
from .engine.profile import pct_to_ha_brightness
from .settings import ControllerSettings

_LOGGER = logging.getLogger(__name__)

# State reports arriving this long after our own command (plus its transition)
# are attributed to that command, not to the user.
REPORT_GRACE = timedelta(seconds=5)
DEFAULT_PREVIEW_INTERVAL = 0.25  # seconds between preview commands per lamp
BRIGHTNESS_TOLERANCE = 3  # HA units (0-255)
KELVIN_TOLERANCE = 60
RGB_TOLERANCE = 12

_INVALID_STATES = (None, STATE_UNAVAILABLE, STATE_UNKNOWN)


@dataclass(slots=True)
class LampGroupConfig:
    """Settings of one lamp subentry."""

    subentry_id: str
    title: str
    lights: tuple[str, ...]
    sleep_action: SleepAction = SleepAction.FOLLOW
    transition_mode: str = TRANSITION_AUTO
    detect_manual: bool = True

    @classmethod
    def from_subentry(cls, subentry_id: str, title: str, data: Mapping[str, Any]) -> LampGroupConfig:
        advanced = data.get(CONF_ADVANCED, {})
        return cls(
            subentry_id=subentry_id,
            title=title,
            lights=tuple(data.get(CONF_LIGHTS, ())),
            sleep_action=SleepAction(data.get(CONF_SLEEP_ACTION, SleepAction.FOLLOW)),
            transition_mode=advanced.get(CONF_TRANSITION_MODE, TRANSITION_AUTO),
            detect_manual=bool(advanced.get(CONF_DETECT_MANUAL, True)),
        )


@dataclass(slots=True)
class LampState:
    entity_id: str
    group: LampGroupConfig
    profile: Profile | None = None
    profile_from_store: bool = False
    supports_transition: bool = False
    previous_segment: int | None = None
    manual: bool = False
    manual_since: datetime | None = None
    last_target: tuple[float, float, TargetMode] | None = None
    last_command: DeviceCommand | None = None
    expect_reports_until: datetime | None = None
    override_brightness: float | None = None
    """Logical brightness chosen via the proxy light; the colour temperature keeps following."""
    override_kelvin: float | None = None
    """Colour temperature chosen via the proxy light; the brightness keeps following."""
    override_since: datetime | None = None
    logical: tuple[float, float] | None = None
    """Logical (brightness %, kelvin) last sent – what the proxy light reports."""

    @property
    def has_override(self) -> bool:
        return self.override_brightness is not None or self.override_kelvin is not None

    def clear_override(self) -> None:
        self.override_brightness = self.override_kelvin = self.override_since = None

    def use_transition(self) -> bool:
        if self.group.transition_mode == TRANSITION_ALWAYS:
            return True
        if self.group.transition_mode == TRANSITION_NEVER:
            return False
        return self.supports_transition


@dataclass(slots=True)
class _PreviewState:
    pending: DeviceCommand | None = None
    last_sent: DeviceCommand | None = None
    last_time: float = 0.0
    min_interval: float = 0.25
    timer: CALLBACK_TYPE | None = None


def _same_output(a: DeviceCommand, b: DeviceCommand) -> bool:
    """Same light output, even if computed in a different segment."""
    return (a.on, a.brightness, a.color_temp_kelvin, a.rgb_color) == (
        b.on,
        b.brightness,
        b.color_temp_kelvin,
        b.rgb_color,
    )


@dataclass(slots=True)
class _Batch:
    service: str
    data: dict[str, Any]
    entity_ids: list[str] = field(default_factory=list)


class DaylightController:
    """Owns the lamp states and applies the target to them."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        target_config: TargetConfig,
        settings: ControllerSettings,
        groups: Iterable[LampGroupConfig],
        stored_profiles: Mapping[str, Profile] | None = None,
    ) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.target_config = target_config
        self.settings = settings
        self.groups = list(groups)
        self._stored_profiles = dict(stored_profiles or {})
        self.lamps: dict[str, LampState] = {}
        for group in self.groups:
            for entity_id in group.lights:
                self.lamps[entity_id] = LampState(entity_id=entity_id, group=group)

        self.enabled = True
        self.sleep = False
        self.bright = False
        self.calibrating: set[str] = set()
        """Lights currently driven by the calibration panel; the controller leaves them alone."""
        self._bright_turned_on: set[str] = set()
        self._bright_timer: CALLBACK_TYPE | None = None
        self._previews: dict[str, _PreviewState] = {}
        self.position: SolarPosition | None = None
        self.target: Target | None = None

        self._own_contexts: deque[str] = deque(maxlen=256)
        self._unsubs: list[CALLBACK_TYPE] = []
        self._recompute_target()

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #

    @callback
    def async_start(self) -> None:
        _LOGGER.debug(
            "Starting with %d light(s): %s (location %.3f, %.3f)",
            len(self.lamps),
            ", ".join(self.lamps) or "none",
            self.hass.config.latitude,
            self.hass.config.longitude,
        )
        self._recompute_target()
        self._notify()
        if self.lamps:
            self._unsubs.append(
                async_track_state_change_event(self.hass, list(self.lamps), self._handle_state_change)
            )
        self._unsubs.append(
            async_track_time_interval(self.hass, self._handle_tick, timedelta(seconds=self.settings.interval))
        )
        self.hass.async_create_task(self.async_apply(force=True), eager_start=False)

    @callback
    def async_stop(self) -> None:
        self._cancel_bright_timer()
        for entity_id in list(self._previews):
            self._reset_preview(entity_id)
        while self._unsubs:
            self._unsubs.pop()()

    # ------------------------------------------------------------------ #
    # public API (switches, services)
    # ------------------------------------------------------------------ #

    async def async_set_enabled(self, enabled: bool, *, apply: bool = True) -> None:
        self.enabled = enabled
        self._notify()
        if enabled and apply:
            await self.async_apply(force=True)

    async def async_set_sleep(self, sleep: bool, *, apply: bool = True) -> None:
        if sleep and self.bright:
            await self._async_end_bright(apply=False)
        if sleep != self.sleep:
            for lamp in self.lamps.values():
                lamp.clear_override()
        self.sleep = sleep
        self._recompute_target()
        self._notify()
        if apply:
            await self.async_apply(force=True)

    async def async_set_bright(self, bright: bool, *, apply: bool = True) -> None:
        """Full-brightness mode: exclusive with sleep, clears manual overrides, optional auto-off."""
        if not bright:
            if self.bright:
                await self._async_end_bright(apply=apply)
            return
        self.sleep = False
        self.bright = True
        for lamp in self.lamps.values():
            lamp.manual, lamp.manual_since = False, None
            lamp.clear_override()
        self._cancel_bright_timer()
        if self.settings.bright_timeout > 0:
            self._bright_timer = async_call_later(
                self.hass, self.settings.bright_timeout * 60, self._handle_bright_timeout
            )
        self._recompute_target()
        self._notify()
        if apply:
            await self.async_apply(force=True, include_off=self.settings.bright_turn_on)

    async def _async_end_bright(self, *, apply: bool) -> None:
        self._cancel_bright_timer()
        self.bright = False
        to_turn_off = [
            entity_id
            for entity_id in self._bright_turned_on
            if (state := self.hass.states.get(entity_id)) is not None and state.state == STATE_ON
        ]
        self._bright_turned_on.clear()
        if to_turn_off:
            await self._async_send("turn_off", {}, sorted(to_turn_off))
        self._recompute_target()
        self._notify()
        if apply:
            await self.async_apply(force=True)

    def _cancel_bright_timer(self) -> None:
        if self._bright_timer is not None:
            self._bright_timer()
            self._bright_timer = None

    @callback
    def _handle_bright_timeout(self, _now: datetime) -> None:
        self._bright_timer = None
        self.hass.async_create_task(self.async_set_bright(False), eager_start=True)

    async def async_reset_manual(
        self, entity_ids: Iterable[str] | None = None, *, apply: bool = True
    ) -> None:
        targets = self.lamps.keys() if entity_ids is None else [e for e in entity_ids if e in self.lamps]
        for entity_id in targets:
            lamp = self.lamps[entity_id]
            lamp.manual = False
            lamp.manual_since = None
            lamp.clear_override()
        self._notify()
        if apply:
            await self.async_apply(entity_ids=list(targets), force=True)

    async def async_update_now(
        self, entity_ids: Iterable[str] | None = None, transition: float | None = None
    ) -> None:
        """Recompute the target and push it to the lamps regardless of thresholds."""
        self._recompute_target()
        self._notify()
        await self.async_apply(entity_ids=entity_ids, force=True, transition=transition)

    # ------------------------------------------------------------------ #
    # calibration (used by the panel via the websocket API)
    # ------------------------------------------------------------------ #

    def set_profile(self, entity_id: str, profile: Profile | None) -> None:
        """Use a new profile for a lamp (``None`` = back to the auto-detected default)."""
        lamp = self.lamps[entity_id]
        lamp.profile = profile
        lamp.profile_from_store = profile is not None
        lamp.previous_segment = None
        lamp.last_command = None
        lamp.last_target = None
        if profile is None:
            self._stored_profiles.pop(entity_id, None)
            self._ensure_profile(lamp, self.hass.states.get(entity_id))
        else:
            self._stored_profiles[entity_id] = profile

    def calibration_start(self, entity_id: str) -> bool:
        """Hand the lamp to the panel. Returns whether it was on before."""
        if entity_id not in self.lamps:
            raise KeyError(entity_id)
        self.calibrating.add(entity_id)
        self._reset_preview(entity_id)
        state = self.hass.states.get(entity_id)
        return state is not None and state.state == STATE_ON

    async def async_calibration_end(self, entity_id: str, *, was_on: bool) -> None:
        """Give the lamp back: switch it off again or re-apply the current target."""
        self.calibrating.discard(entity_id)
        self._reset_preview(entity_id)
        lamp = self.lamps.get(entity_id)
        if lamp is None:
            return
        lamp.last_command = None
        lamp.last_target = None
        lamp.previous_segment = None
        if not was_on:
            await self._async_send("turn_off", {}, [entity_id])
        elif not lamp.manual:
            await self.async_apply(entity_ids=[entity_id], force=True, transition=0)

    async def async_preview(
        self,
        entity_id: str,
        profile: Profile,
        logical: float,
        kelvin: float,
        *,
        min_interval: float = DEFAULT_PREVIEW_INTERVAL,
    ) -> DeviceCommand:
        """Drive a lamp directly with a (possibly unsaved) profile.

        Zigbee lamps drop commands when flooded, so previews are coalesced per
        lamp: at most one command per ``min_interval`` seconds, always the most
        recent value, identical commands are skipped and only changed
        attributes are sent.
        """
        lamp = self.lamps[entity_id]
        self._ensure_profile(lamp, self.hass.states.get(entity_id))
        command = profile.resolve(logical, kelvin)
        preview = self._previews.setdefault(entity_id, _PreviewState())
        preview.pending = command
        preview.min_interval = max(0.05, min(2.0, min_interval))
        if preview.timer is None:
            wait = preview.last_time + preview.min_interval - time.monotonic()
            if wait <= 0:
                await self._async_flush_preview(entity_id)
            else:
                preview.timer = async_call_later(
                    self.hass, wait, partial(self._handle_preview_timer, entity_id)
                )
        return command

    @callback
    def _handle_preview_timer(self, entity_id: str, _now: datetime) -> None:
        preview = self._previews.get(entity_id)
        if preview is not None:
            preview.timer = None
            self.hass.async_create_task(self._async_flush_preview(entity_id), eager_start=True)

    async def _async_flush_preview(self, entity_id: str) -> None:
        preview = self._previews.get(entity_id)
        if preview is None or preview.pending is None or entity_id not in self.calibrating:
            return
        command, preview.pending = preview.pending, None
        last = preview.last_sent
        if command == last or (last is not None and _same_output(command, last)):
            return
        preview.last_sent = command
        preview.last_time = time.monotonic()
        if not command.on:
            await self._async_send("turn_off", {}, [entity_id])
            return
        data: dict[str, Any] = {}
        if last is None or not last.on or last.brightness != command.brightness:
            data["brightness"] = command.brightness
        if (
            last is None
            or not last.on
            or last.color_temp_kelvin != command.color_temp_kelvin
            or last.rgb_color != command.rgb_color
        ):
            if command.color_temp_kelvin is not None:
                data["color_temp_kelvin"] = command.color_temp_kelvin
            if command.rgb_color is not None:
                data["rgb_color"] = list(command.rgb_color)
        if command.brightness is None:
            data.pop("brightness", None)
        if self.lamps[entity_id].use_transition():
            data[ATTR_TRANSITION] = 0
        await self._async_send("turn_on", data, [entity_id])

    def _reset_preview(self, entity_id: str) -> None:
        preview = self._previews.pop(entity_id, None)
        if preview is not None and preview.timer is not None:
            preview.timer()

    # ------------------------------------------------------------------ #
    # proxy lights
    # ------------------------------------------------------------------ #

    async def async_proxy_turn_on(
        self,
        entity_id: str,
        *,
        brightness: float | None = None,
        kelvin: float | None = None,
        color: Mapping[str, Any] | None = None,
        transition: float | None = None,
    ) -> None:
        """Switch a lamp on through its proxy: calibrated values in one command, no flash.

        ``brightness`` is logical (0-100 %). An explicit ``color`` (e.g. ``hs_color``)
        is passed through and pauses the automatic control for that lamp.
        """
        lamp = self.lamps[entity_id]
        state = self.hass.states.get(entity_id)
        self._ensure_profile(lamp, state)
        now = dt_util.utcnow()
        target = self.target or self._recompute_target()
        extra = {} if transition is None else {ATTR_TRANSITION: transition}

        if lamp.profile is None:  # unknown capabilities: plain pass-through
            data = dict(color or {})
            if brightness is not None:
                data[ATTR_BRIGHTNESS] = pct_to_ha_brightness(brightness)
            await self._async_send("turn_on", {**data, **extra}, [entity_id])
            return

        last_brightness, last_kelvin = lamp.logical or (target.brightness, target.kelvin)

        if color:
            lamp.manual, lamp.manual_since = True, now
            lamp.clear_override()
            logical = brightness if brightness is not None else last_brightness
            data = dict(color)
            if isinstance(lamp.profile, DimmableProfile):
                data[ATTR_BRIGHTNESS] = lamp.profile.resolve(max(logical, 0.01), last_kelvin).brightness
            lamp.logical = (logical, last_kelvin)
            lamp.last_command = None
            lamp.expect_reports_until = now + REPORT_GRACE
            await self._async_send("turn_on", {**data, **extra}, [entity_id])
            self._notify()
            return

        if brightness is None and kelvin is None and lamp.manual:
            # Plain "on" while paused (e.g. a colour was chosen): don't touch the colour.
            await self._async_send("turn_on", extra, [entity_id])
            return

        if brightness is not None or kelvin is not None:
            lamp.manual, lamp.manual_since = False, None
            if brightness is not None:
                lamp.override_brightness = max(0.1, min(100.0, brightness))
            if kelvin is not None:
                lamp.override_kelvin = kelvin
            lamp.override_since = now

        if self.enabled:
            lamp_target = self._lamp_target(lamp, target)
        else:
            lamp_target = Target(
                brightness=lamp.override_brightness or last_brightness,
                kelvin=lamp.override_kelvin or last_kelvin,
            )
        command = self._command_for(lamp, lamp_target, turned_on=True)
        if command is None or not command.on:
            command = (
                DeviceCommand(on=True, segment=1)
                if isinstance(lamp.profile, OnOffProfile)
                else lamp.profile.resolve_minimum(lamp_target.kelvin)
            )
        lamp.last_command = command
        lamp.last_target = (lamp_target.brightness, lamp_target.kelvin, lamp_target.mode)
        lamp.logical = (lamp_target.brightness, lamp_target.kelvin)
        if command.segment is not None:
            lamp.previous_segment = command.segment
        lamp.expect_reports_until = now + timedelta(seconds=transition or 0) + REPORT_GRACE
        await self._async_send("turn_on", {**command.to_service_data(), **extra}, [entity_id])
        self._notify()

    async def async_proxy_turn_off(self, entity_id: str, *, transition: float | None = None) -> None:
        extra = {} if transition is None else {ATTR_TRANSITION: transition}
        await self._async_send("turn_off", extra, [entity_id])

    def proxy_view(self, entity_id: str) -> tuple[float | None, float | None, bool]:
        """(logical brightness %, kelvin, follows_profile) as the proxy should report it.

        If the source still shows what we sent, report the logical values we
        sent; otherwise estimate them from the source state.
        """
        lamp = self.lamps[entity_id]
        state = self.hass.states.get(entity_id)
        if state is None or state.state != STATE_ON:
            return (
                lamp.logical[0] if lamp.logical else None,
                lamp.logical[1] if lamp.logical else None,
                True,
            )
        trusted = lamp.logical is not None and (
            (lamp.last_command is not None and _state_matches(lamp.last_command, state))
            or (lamp.expect_reports_until is not None and dt_util.utcnow() <= lamp.expect_reports_until)
        )
        if trusted and not lamp.manual:
            return (lamp.logical[0], lamp.logical[1], True)
        kelvin = state.attributes.get(ATTR_COLOR_TEMP_KELVIN) or (lamp.logical[1] if lamp.logical else None)
        ha_brightness = state.attributes.get(ATTR_BRIGHTNESS)
        if isinstance(lamp.profile, DimmableProfile) and ha_brightness:
            rgb_mode = state.attributes.get("color_mode") in COLOR_MODES_RGB
            logical = estimate_logical(lamp.profile, ha_brightness, rgb_mode=rgb_mode)
        else:
            logical = 100.0 if ha_brightness is None else ha_brightness / 255 * 100
        follows = not lamp.manual
        return (logical, kelvin, follows)

    @property
    def manual_lamps(self) -> list[str]:
        return sorted(e for e, lamp in self.lamps.items() if lamp.manual)

    def profile_for(self, entity_id: str) -> Profile | None:
        lamp = self.lamps.get(entity_id)
        if lamp is None:
            return None
        self._ensure_profile(lamp, self.hass.states.get(entity_id))
        return lamp.profile

    # ------------------------------------------------------------------ #
    # core
    # ------------------------------------------------------------------ #

    def _recompute_target(self) -> Target:
        self.position = solar_position(
            dt_util.utcnow(), self.hass.config.latitude, self.hass.config.longitude
        )
        self.target = compute_target(self.position, self.target_config, sleep=self.sleep, bright=self.bright)
        return self.target

    @callback
    def _notify(self) -> None:
        async_dispatcher_send(self.hass, signal_update(self.entry_id))

    def _ensure_profile(self, lamp: LampState, state: State | None) -> None:
        if state is None or state.state in _INVALID_STATES:
            return
        features = int(state.attributes.get(ATTR_SUPPORTED_FEATURES, 0) or 0)
        lamp.supports_transition = bool(features & LightEntityFeature.TRANSITION)
        if lamp.profile is not None:
            return
        stored = self._stored_profiles.get(lamp.entity_id)
        if stored is not None:
            lamp.profile, lamp.profile_from_store = stored, True
            return
        caps = detect_capabilities(
            state.attributes.get(ATTR_SUPPORTED_COLOR_MODES),
            min_kelvin=state.attributes.get(ATTR_MIN_COLOR_TEMP_KELVIN),
            max_kelvin=state.attributes.get(ATTR_MAX_COLOR_TEMP_KELVIN),
            supported_features=features,
        )
        lamp.profile = default_profile(caps, name=lamp.entity_id)
        _LOGGER.debug("%s: detected %s -> %s profile", lamp.entity_id, caps, lamp.profile.kind)

    def _significant_change(self, lamp: LampState, target: Target) -> bool:
        if lamp.last_target is None:
            return True
        brightness, kelvin, mode = lamp.last_target
        return (
            mode != target.mode
            or abs(brightness - target.brightness) >= self.settings.min_brightness_change
            or abs(kelvin - target.kelvin) >= self.settings.min_kelvin_change
        )

    @staticmethod
    def _lamp_target(lamp: LampState, target: Target) -> Target:
        """Global target with the lamp's proxy overrides applied."""
        if not lamp.has_override:
            return target
        return replace(
            target,
            brightness=lamp.override_brightness
            if lamp.override_brightness is not None
            else target.brightness,
            kelvin=lamp.override_kelvin if lamp.override_kelvin is not None else target.kelvin,
        )

    def _command_for(self, lamp: LampState, target: Target, *, turned_on: bool) -> DeviceCommand | None:
        assert lamp.profile is not None
        action = lamp.group.sleep_action
        if lamp.has_override:
            # An explicit choice on the proxy wins over the sleep behaviour.
            action = SleepAction.FOLLOW
        if turned_on and target.mode is TargetMode.SLEEP and action is SleepAction.OFF:
            # The user deliberately switched a lamp on during sleep: dim it, don't fight them.
            action = SleepAction.MINIMUM

        if isinstance(lamp.profile, OnOffProfile):
            # On/off lamps are never switched automatically, except by the modes.
            if target.mode is TargetMode.BRIGHT:
                return DeviceCommand(on=True, segment=1)
            if target.mode is TargetMode.SLEEP and action is SleepAction.OFF:
                return DeviceCommand.off()
            return None

        return resolve_lamp_command(
            target, lamp.profile, sleep_action=action, previous_segment=lamp.previous_segment
        )

    async def async_apply(
        self,
        *,
        entity_ids: Iterable[str] | None = None,
        force: bool = False,
        turned_on: bool = False,
        transition: float | None = None,
        include_off: bool = False,
    ) -> None:
        """Send the current target to lamps that are on and not under manual control.

        ``include_off`` also switches on lamps that are off (full-brightness mode only).
        """
        if not self.enabled:
            _LOGGER.debug("Apply skipped: automatic control is off")
            return
        target = self.target or self._recompute_target()
        _LOGGER.debug(
            "Apply (force=%s, turned_on=%s): target %.1f %% / %.0f K (%s)",
            force,
            turned_on,
            target.brightness,
            target.kelvin,
            target.mode,
        )
        if transition is None:
            transition = self.settings.turn_on_transition if turned_on else self.settings.transition
        now = dt_util.utcnow()

        batches: dict[tuple[str, tuple[tuple[str, Any], ...]], _Batch] = {}
        for entity_id in list(entity_ids) if entity_ids is not None else list(self.lamps):
            lamp = self.lamps.get(entity_id)
            if lamp is None or entity_id in self.calibrating:
                continue
            state = self.hass.states.get(entity_id)
            switch_on = include_off and state is not None and state.state == STATE_OFF
            if state is None or (state.state != STATE_ON and not switch_on):
                _LOGGER.debug("%s: skipped, state is %s", entity_id, None if state is None else state.state)
                continue
            if lamp.manual:
                _LOGGER.debug("%s: skipped, under manual control", entity_id)
                continue
            self._ensure_profile(lamp, state)
            if lamp.profile is None:
                _LOGGER.debug("%s: skipped, no profile (attributes not available yet)", entity_id)
                continue
            lamp_target = self._lamp_target(lamp, target)
            if not force and not self._significant_change(lamp, lamp_target):
                continue

            command = self._command_for(lamp, lamp_target, turned_on=turned_on)
            lamp.last_target = (lamp_target.brightness, lamp_target.kelvin, lamp_target.mode)
            if command is None:
                _LOGGER.debug("%s: nothing to do for %s profile", entity_id, lamp.profile.kind)
                continue

            data = command.to_service_data()
            used_transition = transition if command.on and transition > 0 and lamp.use_transition() else 0
            if used_transition:
                data[ATTR_TRANSITION] = used_transition
            if lamp.last_command == command and not force:
                continue
            if switch_on:
                if not command.on:
                    continue
                self._bright_turned_on.add(entity_id)
            lamp.last_command = command
            if command.on:
                lamp.logical = (lamp_target.brightness, lamp_target.kelvin)
            if command.segment is not None:
                lamp.previous_segment = command.segment
            lamp.expect_reports_until = now + timedelta(seconds=used_transition) + REPORT_GRACE

            key = (command.service, tuple(sorted((k, _hashable(v)) for k, v in data.items())))
            batch = batches.setdefault(key, _Batch(service=command.service, data=data))
            batch.entity_ids.append(entity_id)

        for batch in batches.values():
            await self._async_send(batch.service, batch.data, batch.entity_ids)

    async def _async_send(self, service: str, data: dict[str, Any], entity_ids: list[str]) -> None:
        _LOGGER.debug("Sending light.%s %s to %s", service, data, entity_ids)
        context = Context()
        self._own_contexts.append(context.id)
        await self.hass.services.async_call(
            LIGHT_DOMAIN,
            service,
            {**data, ATTR_ENTITY_ID: entity_ids},
            blocking=False,
            context=context,
        )

    def _is_own(self, context: Context) -> bool:
        return context.id in self._own_contexts or (
            context.parent_id is not None and context.parent_id in self._own_contexts
        )

    # ------------------------------------------------------------------ #
    # events
    # ------------------------------------------------------------------ #

    async def _handle_tick(self, _now: datetime) -> None:
        self._expire_manual()
        self._recompute_target()
        self._notify()
        await self.async_apply()

    def _expire_manual(self) -> None:
        if self.settings.manual_timeout <= 0:
            return
        limit = dt_util.utcnow() - timedelta(minutes=self.settings.manual_timeout)
        for lamp in self.lamps.values():
            if lamp.manual and lamp.manual_since is not None and lamp.manual_since <= limit:
                lamp.manual, lamp.manual_since = False, None
            if lamp.has_override and lamp.override_since is not None and lamp.override_since <= limit:
                lamp.clear_override()

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        lamp = self.lamps.get(entity_id)
        old, new = event.data["old_state"], event.data["new_state"]
        if lamp is None or new is None or new.state in _INVALID_STATES or entity_id in self.calibrating:
            return
        self._ensure_profile(lamp, new)
        was_on = old is not None and old.state == STATE_ON
        is_on = new.state == STATE_ON
        own = self._is_own(new.context)
        if not own:
            # Touched by someone else: full-brightness mode must not switch it off later.
            self._bright_turned_on.discard(entity_id)

        if not is_on:
            lamp.last_command = None
            lamp.last_target = None
            if was_on and self.settings.reset_manual_on_off and (lamp.manual or lamp.has_override):
                lamp.manual, lamp.manual_since = False, None
                lamp.clear_override()
                self._notify()
            return

        if not was_on:
            if own:
                return
            _LOGGER.debug("%s switched on externally, correcting", entity_id)
            # Switched on by someone else (UI, wall switch, app): correct immediately.
            if lamp.manual:
                lamp.manual, lamp.manual_since = False, None
                self._notify()
            self.hass.async_create_task(
                self.async_apply(entity_ids=[entity_id], force=True, turned_on=True),
                eager_start=True,
            )
            return

        # on -> on: attribute change
        if own or not self.settings.detect_manual or not lamp.group.detect_manual or lamp.manual:
            return
        if old is not None and not _light_attributes_changed(old, new):
            return
        if lamp.expect_reports_until is not None and dt_util.utcnow() <= lamp.expect_reports_until:
            return
        if lamp.last_command is not None and _state_matches(lamp.last_command, new):
            return
        _LOGGER.debug("Manual change detected on %s", entity_id)
        lamp.manual, lamp.manual_since = True, dt_util.utcnow()
        self._notify()


def _hashable(value: Any) -> Any:
    return tuple(value) if isinstance(value, list) else value


_WATCHED = (ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN, ATTR_RGB_COLOR, "color_mode")


def _light_attributes_changed(old: State, new: State) -> bool:
    return any(old.attributes.get(a) != new.attributes.get(a) for a in _WATCHED)


def _state_matches(command: DeviceCommand, state: State) -> bool:
    """True if the reported state is (close to) what we last sent."""
    attrs = state.attributes
    if command.brightness is not None:
        brightness = attrs.get(ATTR_BRIGHTNESS)
        if brightness is None or abs(brightness - command.brightness) > BRIGHTNESS_TOLERANCE:
            return False
    if command.color_temp_kelvin is not None:
        kelvin = attrs.get(ATTR_COLOR_TEMP_KELVIN)
        if kelvin is None or abs(kelvin - command.color_temp_kelvin) > KELVIN_TOLERANCE:
            return False
    if command.rgb_color is not None:
        rgb = attrs.get(ATTR_RGB_COLOR)
        if rgb is None or any(
            abs(a - b) > RGB_TOLERANCE for a, b in zip(rgb, command.rgb_color, strict=False)
        ):
            return False
    return True
