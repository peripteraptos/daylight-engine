"""Per-lamp decision: combine global target, mode and profile into a command."""

from __future__ import annotations

from enum import StrEnum

from .profile import DeviceCommand, Profile
from .target import Target, TargetMode


class SleepAction(StrEnum):
    """What a lamp does while sleep mode is active."""

    FOLLOW = "follow"
    """Use the global sleep target (brightness/kelvin) through the profile."""
    MINIMUM = "minimum"
    """Dimmest state the profile can produce (first calibration point)."""
    OFF = "off"
    UNCHANGED = "unchanged"
    """Do not touch the lamp at all."""


def resolve_lamp_command(
    target: Target,
    profile: Profile,
    *,
    sleep_action: SleepAction = SleepAction.FOLLOW,
    previous_segment: int | None = None,
) -> DeviceCommand | None:
    """Return the command for a lamp, or ``None`` if it should be left alone."""
    if target.mode is TargetMode.SLEEP:
        match sleep_action:
            case SleepAction.UNCHANGED:
                return None
            case SleepAction.OFF:
                return DeviceCommand.off()
            case SleepAction.MINIMUM:
                return profile.resolve_minimum(target.kelvin)
            case SleepAction.FOLLOW:
                pass

    return profile.resolve(target.brightness, target.kelvin, previous_segment)
