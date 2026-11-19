"""Sidebar panel registration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PANEL_URL = "daylight-engine"
STATIC_URL = f"/{DOMAIN}_static"
FRONTEND_DIR = Path(__file__).parent / "frontend"
_STATIC_REGISTERED = f"{DOMAIN}_static_registered"


async def async_register_panel(hass: HomeAssistant) -> None:
    if not hass.data.get(_STATIC_REGISTERED):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), cache_headers=False)]
        )
        hass.data[_STATIC_REGISTERED] = True

    # Cache-busting: the file's mtime changes with every update of the integration.
    version = await hass.async_add_executor_job(_file_version)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name="daylight-engine-panel",
        sidebar_title="Daylight",
        sidebar_icon="mdi:theme-light-dark",
        module_url=f"{STATIC_URL}/daylight-panel.js?v={version}",
        require_admin=True,
        config={"domain": DOMAIN},
    )


def _file_version() -> int:
    return int((FRONTEND_DIR / "daylight-panel.js").stat().st_mtime)


def async_unregister_panel(hass: HomeAssistant) -> None:
    frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
