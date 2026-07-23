"""Local macOS scheduling boundary for the shared sync pipeline."""

from .config import (
    DEFAULT_CONFIG,
    SchedulerConfig,
    SchedulerConfigError,
    SchedulerConfigLoad,
    load_scheduler_config,
    save_scheduler_config,
    validate_scheduler_config,
)

SCHEDULER_VERSION = "1.1.0"
TRIGGER_TYPES = ("manual", "scheduled", "catch_up")

__all__ = [
    "DEFAULT_CONFIG",
    "SCHEDULER_VERSION",
    "TRIGGER_TYPES",
    "SchedulerConfig",
    "SchedulerConfigError",
    "SchedulerConfigLoad",
    "load_scheduler_config",
    "save_scheduler_config",
    "validate_scheduler_config",
]
