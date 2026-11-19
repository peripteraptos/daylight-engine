"""Config flow: one main entry, lamps as subentries, global settings as options."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_ADVANCED,
    CONF_DETECT_MANUAL,
    CONF_LIGHTS,
    CONF_PROXY,
    CONF_SLEEP_ACTION,
    CONF_TRANSITION_MODE,
    DOMAIN,
    SECTION_BRIGHT,
    SECTION_BRIGHTNESS,
    SECTION_KELVIN,
    SECTION_MANUAL,
    SECTION_SLEEP,
    SECTION_UPDATES,
    SUBENTRY_LAMP,
    TRANSITION_AUTO,
    TRANSITION_MODES,
)
from .engine import SleepAction
from .settings import default_options, merged_options, target_config_from_options

DEFAULT_TITLE = "Daylight Engine"


def _num(minimum: float, maximum: float, step: float, unit: str | None = None) -> NumberSelector:
    config = NumberSelectorConfig(min=minimum, max=maximum, step=step, mode=NumberSelectorMode.BOX)
    if unit is not None:
        config["unit_of_measurement"] = unit
    return NumberSelector(config)


def _curve_schema(defaults: Mapping[str, Any], value_selector: NumberSelector) -> vol.Schema:
    elevation = _num(-18, 60, 0.5, "°")
    shape = _num(0.2, 5, 0.1)
    return vol.Schema(
        {
            vol.Required("night", default=defaults["night"]): value_selector,
            vol.Required("day", default=defaults["day"]): value_selector,
            vol.Required("morning_low", default=defaults["morning_low"]): elevation,
            vol.Required("morning_high", default=defaults["morning_high"]): elevation,
            vol.Required("morning_shape", default=defaults["morning_shape"]): shape,
            vol.Required("evening_low", default=defaults["evening_low"]): elevation,
            vol.Required("evening_high", default=defaults["evening_high"]): elevation,
            vol.Required("evening_shape", default=defaults["evening_shape"]): shape,
        }
    )


def options_schema(options: Mapping[str, Any]) -> vol.Schema:
    o = merged_options(options)
    kelvin = _num(1000, 10000, 50, "K")
    percent = _num(0.5, 100, 0.5, "%")
    seconds = _num(0, 300, 1, "s")
    return vol.Schema(
        {
            vol.Required(SECTION_KELVIN): section(
                _curve_schema(o[SECTION_KELVIN], kelvin), {"collapsed": False}
            ),
            vol.Required(SECTION_BRIGHTNESS): section(
                _curve_schema(o[SECTION_BRIGHTNESS], percent), {"collapsed": True}
            ),
            vol.Required(SECTION_SLEEP): section(
                vol.Schema(
                    {
                        vol.Required("brightness", default=o[SECTION_SLEEP]["brightness"]): percent,
                        vol.Required("kelvin", default=o[SECTION_SLEEP]["kelvin"]): kelvin,
                    }
                ),
                {"collapsed": True},
            ),
            vol.Required(SECTION_BRIGHT): section(
                vol.Schema(
                    {
                        vol.Required("brightness", default=o[SECTION_BRIGHT]["brightness"]): percent,
                        vol.Required("kelvin", default=o[SECTION_BRIGHT]["kelvin"]): kelvin,
                        vol.Required("timeout", default=o[SECTION_BRIGHT]["timeout"]): _num(
                            0, 1440, 5, "min"
                        ),
                        vol.Required("turn_on", default=o[SECTION_BRIGHT]["turn_on"]): BooleanSelector(),
                    }
                ),
                {"collapsed": True},
            ),
            vol.Required(SECTION_UPDATES): section(
                vol.Schema(
                    {
                        vol.Required("interval", default=o[SECTION_UPDATES]["interval"]): _num(
                            5, 3600, 1, "s"
                        ),
                        vol.Required("transition", default=o[SECTION_UPDATES]["transition"]): seconds,
                        vol.Required(
                            "turn_on_transition", default=o[SECTION_UPDATES]["turn_on_transition"]
                        ): seconds,
                        vol.Required(
                            "min_brightness_change", default=o[SECTION_UPDATES]["min_brightness_change"]
                        ): _num(0, 20, 0.5, "%"),
                        vol.Required(
                            "min_kelvin_change", default=o[SECTION_UPDATES]["min_kelvin_change"]
                        ): _num(0, 1000, 10, "K"),
                    }
                ),
                {"collapsed": True},
            ),
            vol.Required(SECTION_MANUAL): section(
                vol.Schema(
                    {
                        vol.Required("detect", default=o[SECTION_MANUAL]["detect"]): BooleanSelector(),
                        vol.Required(
                            "reset_on_off", default=o[SECTION_MANUAL]["reset_on_off"]
                        ): BooleanSelector(),
                        vol.Required("timeout", default=o[SECTION_MANUAL]["timeout"]): _num(
                            0, 1440, 5, "min"
                        ),
                    }
                ),
                {"collapsed": True},
            ),
        }
    )


class DaylightEngineConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create the single main entry."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get(CONF_NAME) or DEFAULT_TITLE, data={}, options=default_options()
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Optional(CONF_NAME, default=DEFAULT_TITLE): TextSelector()}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> DaylightOptionsFlow:
        return DaylightOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_LAMP: LampSubentryFlow}


class DaylightOptionsFlow(OptionsFlow):
    """Global daylight curve, sleep target and update behaviour."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                target_config_from_options(user_input)
            except ValueError:
                errors["base"] = "invalid_curve"
            else:
                return self.async_create_entry(data=merged_options(user_input))
        return self.async_show_form(
            step_id="init",
            data_schema=options_schema(user_input or self.config_entry.options),
            errors=errors,
        )


def _lamp_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    advanced = defaults.get(CONF_ADVANCED, {})
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): TextSelector(),
            vol.Required(CONF_LIGHTS, default=list(defaults.get(CONF_LIGHTS, []))): EntitySelector(
                EntitySelectorConfig(domain=LIGHT_DOMAIN, multiple=True)
            ),
            vol.Required(
                CONF_SLEEP_ACTION, default=defaults.get(CONF_SLEEP_ACTION, SleepAction.FOLLOW)
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[a.value for a in SleepAction],
                    translation_key=CONF_SLEEP_ACTION,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_ADVANCED): section(
                vol.Schema(
                    {
                        vol.Required(
                            CONF_TRANSITION_MODE, default=advanced.get(CONF_TRANSITION_MODE, TRANSITION_AUTO)
                        ): SelectSelector(
                            SelectSelectorConfig(
                                options=list(TRANSITION_MODES),
                                translation_key=CONF_TRANSITION_MODE,
                                mode=SelectSelectorMode.DROPDOWN,
                            )
                        ),
                        vol.Required(
                            CONF_DETECT_MANUAL, default=advanced.get(CONF_DETECT_MANUAL, True)
                        ): BooleanSelector(),
                        vol.Required(CONF_PROXY, default=advanced.get(CONF_PROXY, False)): BooleanSelector(),
                    }
                ),
                {"collapsed": True},
            ),
        }
    )


class LampSubentryFlow(ConfigSubentryFlow):
    """Add or edit a lamp (or several lamps sharing the same settings)."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        return await self._async_step_form("user", user_input, None)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        subentry = self._get_reconfigure_subentry()
        return await self._async_step_form("reconfigure", user_input, subentry.subentry_id)

    async def _async_step_form(
        self, step_id: str, user_input: dict[str, Any] | None, subentry_id: str | None
    ) -> SubentryFlowResult:
        entry = self._get_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            lights = list(user_input.get(CONF_LIGHTS, []))
            used = {
                light
                for sub_id, sub in entry.subentries.items()
                if sub_id != subentry_id and sub.subentry_type == SUBENTRY_LAMP
                for light in sub.data.get(CONF_LIGHTS, [])
            }
            registry = er.async_get(self.hass)
            if not lights:
                errors[CONF_LIGHTS] = "no_lights"
            elif any(
                (reg := registry.async_get(light)) is not None and reg.platform == DOMAIN for light in lights
            ):
                errors[CONF_LIGHTS] = "proxy_not_allowed"
            elif used.intersection(lights):
                errors[CONF_LIGHTS] = "light_in_use"
            else:
                title = user_input.get(CONF_NAME) or ", ".join(lights)
                data = {
                    CONF_LIGHTS: lights,
                    CONF_SLEEP_ACTION: user_input[CONF_SLEEP_ACTION],
                    CONF_ADVANCED: dict(user_input.get(CONF_ADVANCED, {})),
                }
                if subentry_id is None:
                    return self.async_create_entry(title=title, data=data)
                return self.async_update_and_abort(
                    entry, self._get_reconfigure_subentry(), title=title, data=data
                )

        if user_input is not None:
            defaults: Mapping[str, Any] = user_input
        elif subentry_id is not None:
            sub = self._get_reconfigure_subentry()
            defaults = {**sub.data, CONF_NAME: sub.title}
        else:
            defaults = {}
        return self.async_show_form(step_id=step_id, data_schema=_lamp_schema(defaults), errors=errors)
