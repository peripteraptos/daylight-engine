"""Runtime controller: keeps managed lights in line with the daylight target."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
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
    resolve_lamp_command,
    solar_position,
)
from .settings import ControllerSettings

_LOGGER = logging.getLogger(__name__)

# State reports arriving this long after our own command (plus its transition)
# are attributed to that command, not to the user.
REPORT_GRACE = timedelta(seconds=5)
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

    def use_transition(self) -> bool:
        if self.group.transition_mode == TRANSITION_ALWAYS:
            return True
        if self.group.transition_mode == TRANSITION_NEVER:
            return False
        return self.supports_transition


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
        self.sleep = sleep
        self._recompute_target()
        self._notify()
        if apply:
            await self.async_apply(force=True)

    async def async_reset_manual(
        self, entity_ids: Iterable[str] | None = None, *, apply: bool = True
    ) -> None:
        targets = self.lamps.keys() if entity_ids is None else [e for e in entity_ids if e in self.lamps]
        for entity_id in targets:
            lamp = self.lamps[entity_id]
            lamp.manual = False
            lamp.manual_since = None
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
        self.target = compute_target(self.position, self.target_config, sleep=self.sleep)
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

    def _command_for(self, lamp: LampState, target: Target, *, turned_on: bool) -> DeviceCommand | None:
        assert lamp.profile is not None
        action = lamp.group.sleep_action
        if turned_on and target.mode is TargetMode.SLEEP and action is SleepAction.OFF:
            # The user deliberately switched a lamp on during sleep: dim it, don't fight them.
            action = SleepAction.MINIMUM

        if isinstance(lamp.profile, OnOffProfile):
            # On/off lamps are never switched automatically, except sleep "off".
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
    ) -> None:
        """Send the current target to lamps that are on and not under manual control."""
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
            if lamp is None:
                continue
            state = self.hass.states.get(entity_id)
            if state is None or state.state != STATE_ON:
                _LOGGER.debug("%s: skipped, state is %s", entity_id, None if state is None else state.state)
                continue
            if lamp.manual:
                _LOGGER.debug("%s: skipped, under manual control", entity_id)
                continue
            self._ensure_profile(lamp, state)
            if lamp.profile is None:
                _LOGGER.debug("%s: skipped, no profile (attributes not available yet)", entity_id)
                continue
            if not force and not self._significant_change(lamp, target):
                continue

            command = self._command_for(lamp, target, turned_on=turned_on)
            lamp.last_target = (target.brightness, target.kelvin, target.mode)
            if command is None:
                _LOGGER.debug("%s: nothing to do for %s profile", entity_id, lamp.profile.kind)
                continue

            data = command.to_service_data()
            used_transition = transition if command.on and transition > 0 and lamp.use_transition() else 0
            if used_transition:
                data[ATTR_TRANSITION] = used_transition
            if lamp.last_command == command and not force:
                continue
            lamp.last_command = command
            if command.segment is not None:
                lamp.previous_segment = command.segment
            lamp.expect_reports_until = now + timedelta(seconds=used_transition) + REPORT_GRACE

            key = (command.service, tuple(sorted((k, _hashable(v)) for k, v in data.items())))
            batch = batches.setdefault(key, _Batch(service=command.service, data=data))
            batch.entity_ids.append(entity_id)

        for batch in batches.values():
            _LOGGER.debug("Sending light.%s %s to %s", batch.service, batch.data, batch.entity_ids)
            context = Context()
            self._own_contexts.append(context.id)
            await self.hass.services.async_call(
                LIGHT_DOMAIN,
                batch.service,
                {**batch.data, ATTR_ENTITY_ID: batch.entity_ids},
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

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        lamp = self.lamps.get(entity_id)
        old, new = event.data["old_state"], event.data["new_state"]
        if lamp is None or new is None or new.state in _INVALID_STATES:
            return
        self._ensure_profile(lamp, new)
        was_on = old is not None and old.state == STATE_ON
        is_on = new.state == STATE_ON
        own = self._is_own(new.context)

        if not is_on:
            lamp.last_command = None
            lamp.last_target = None
            if was_on and self.settings.reset_manual_on_off and lamp.manual:
                lamp.manual, lamp.manual_since = False, None
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
