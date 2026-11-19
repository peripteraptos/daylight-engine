"""Constants for Daylight Engine."""

from typing import Final

DOMAIN: Final = "daylight_engine"

SUBENTRY_LAMP: Final = "lamp"

# Lamp subentry data
CONF_LIGHTS: Final = "lights"
CONF_SLEEP_ACTION: Final = "sleep_action"
CONF_ADVANCED: Final = "advanced"
CONF_TRANSITION_MODE: Final = "transition_mode"
CONF_DETECT_MANUAL: Final = "detect_manual"

TRANSITION_AUTO: Final = "auto"
TRANSITION_ALWAYS: Final = "always"
TRANSITION_NEVER: Final = "never"
TRANSITION_MODES: Final = (TRANSITION_AUTO, TRANSITION_ALWAYS, TRANSITION_NEVER)

# Option sections
SECTION_KELVIN: Final = "kelvin"
SECTION_BRIGHTNESS: Final = "brightness"
SECTION_SLEEP: Final = "sleep"
SECTION_UPDATES: Final = "updates"
SECTION_MANUAL: Final = "manual"

SERVICE_RESET_MANUAL: Final = "reset_manual"
SERVICE_APPLY: Final = "apply"

STORAGE_KEY_PROFILES: Final = f"{DOMAIN}.profiles"
STORAGE_VERSION: Final = 1


def signal_update(entry_id: str) -> str:
    """Dispatcher signal sent whenever the controller state changes."""
    return f"{DOMAIN}_{entry_id}_update"
