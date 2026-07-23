"""Local deterministic coaching engine; never calls cloud AI."""

from .storage import ENGINE_VERSION as LOCAL_COACH_ENGINE_VERSION

__all__ = ["LOCAL_COACH_ENGINE_VERSION"]
