"""Persistent storage for lamp calibration profiles (written by the calibration UI in phase 3)."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY_PROFILES, STORAGE_VERSION
from .engine import Profile, profile_from_dict, profile_to_dict

_LOGGER = logging.getLogger(__name__)


class ProfileStore:
    """Profiles keyed by light entity_id."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY_PROFILES)
        self.profiles: dict[str, Profile] = {}

    async def async_load(self) -> dict[str, Profile]:
        data = await self._store.async_load() or {}
        self.profiles = {}
        for entity_id, raw in data.get("profiles", {}).items():
            try:
                self.profiles[entity_id] = profile_from_dict(raw)
            except (KeyError, TypeError, ValueError) as err:
                _LOGGER.warning("Ignoring invalid stored profile for %s: %s", entity_id, err)
        return self.profiles

    async def async_save_profile(self, entity_id: str, profile: Profile) -> None:
        self.profiles[entity_id] = profile
        await self._async_save()

    async def async_remove_profile(self, entity_id: str) -> None:
        if self.profiles.pop(entity_id, None) is not None:
            await self._async_save()

    async def _async_save(self) -> None:
        await self._store.async_save(
            {"profiles": {entity_id: profile_to_dict(p) for entity_id, p in self.profiles.items()}}
        )
