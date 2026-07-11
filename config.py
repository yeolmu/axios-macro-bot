"""Configuration helpers for the bot."""

import os


class ConfigurationError(RuntimeError):
    """Raised when a required runtime secret is missing."""


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ConfigurationError(f"Required environment variable is missing: {name}")
    return value.strip()
