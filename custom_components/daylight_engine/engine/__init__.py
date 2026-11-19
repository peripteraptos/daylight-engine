"""Pure calculation engine. Must not import Home Assistant."""

from .detect import Capabilities, default_profile, detect_capabilities
from .lamp import SleepAction, resolve_lamp_command
from .profile import (
    CctSegment,
    CurvePoint,
    DeviceCommand,
    DimmableProfile,
    OnOffProfile,
    Profile,
    RgbPoint,
    RgbSegment,
    profile_from_dict,
    profile_to_dict,
)
from .sun import SolarPosition, solar_position
from .target import (
    Curve,
    Ramp,
    SleepTarget,
    Target,
    TargetConfig,
    TargetMode,
    compute_target,
    compute_target_at,
)

__all__ = [
    "Capabilities",
    "CctSegment",
    "Curve",
    "CurvePoint",
    "DeviceCommand",
    "DimmableProfile",
    "OnOffProfile",
    "Profile",
    "Ramp",
    "RgbPoint",
    "RgbSegment",
    "SleepAction",
    "SleepTarget",
    "SolarPosition",
    "Target",
    "TargetConfig",
    "TargetMode",
    "compute_target",
    "compute_target_at",
    "default_profile",
    "detect_capabilities",
    "profile_from_dict",
    "profile_to_dict",
    "resolve_lamp_command",
    "solar_position",
]
