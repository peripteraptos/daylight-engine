"""Daylight Engine – daylight-following light control for Home Assistant.

Phase 1 only contains the pure calculation engine in ``engine/``. The Home
Assistant glue (config flow, entities, proxy lights) follows in phase 2.

Keep this module free of Home Assistant imports at module level so that the
engine package can be imported and tested without Home Assistant installed.
"""

from .const import DOMAIN

__all__ = ["DOMAIN"]
