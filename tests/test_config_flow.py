from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER, ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.daylight_engine.const import DOMAIN, SUBENTRY_LAMP
from custom_components.daylight_engine.settings import default_options

LAMP_INPUT = {
    "name": "Wohnzimmer",
    "lights": ["light.stehlampe", "light.regal"],
    "sleep_action": "minimum",
    "advanced": {"transition_mode": "never", "detect_manual": False},
}


async def test_create_main_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "Licht"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Licht"
    assert result["options"] == default_options()

    # single_config_entry: a second instance is refused
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, options=default_options())
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    bad = default_options()
    bad["kelvin"]["evening_low"] = 20  # above evening_high
    result = await hass.config_entries.options.async_configure(result["flow_id"], bad)
    assert result["errors"] == {"base": "invalid_curve"}

    good = default_options()
    good["kelvin"]["day"] = 5500
    result = await hass.config_entries.options.async_configure(result["flow_id"], good)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["kelvin"]["day"] == 5500
    assert entry.runtime_data.controller.target_config.kelvin.day == 5500  # reloaded


async def test_lamp_subentry_add_validate_reconfigure(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        options=default_options(),
        subentries_data=[
            ConfigSubentryData(
                data={"lights": ["light.flur"], "sleep_action": "off", "advanced": {}},
                subentry_type=SUBENTRY_LAMP,
                title="Flur",
                unique_id=None,
            )
        ],
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    flow = hass.config_entries.subentries
    result = await flow.async_init((entry.entry_id, SUBENTRY_LAMP), context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    result = await flow.async_configure(result["flow_id"], {**LAMP_INPUT, "lights": ["light.flur"]})
    assert result["errors"] == {"lights": "light_in_use"}

    result = await flow.async_configure(result["flow_id"], LAMP_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    sub = next(s for s in entry.subentries.values() if s.title == "Wohnzimmer")
    assert sub.data["lights"] == ["light.stehlampe", "light.regal"]
    assert sub.data["advanced"]["transition_mode"] == "never"
    assert set(entry.runtime_data.controller.lamps) == {"light.flur", "light.stehlampe", "light.regal"}

    result = await flow.async_init(
        (entry.entry_id, SUBENTRY_LAMP),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": sub.subentry_id},
    )
    assert result["type"] is FlowResultType.FORM
    result = await flow.async_configure(
        result["flow_id"], {**LAMP_INPUT, "name": "Wohnen", "lights": ["light.stehlampe"]}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert entry.subentries[sub.subentry_id].title == "Wohnen"
    assert set(entry.runtime_data.controller.lamps) == {"light.flur", "light.stehlampe"}
