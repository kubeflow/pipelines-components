"""Shared pytest fixtures for validate_metadata tests."""

from datetime import datetime, timezone

import pytest

from .. import validate_metadata as vm_module

FROZEN_NOW = datetime(2025, 11, 20, tzinfo=timezone.utc)


class _FrozenMeta(type(datetime)):
    """Metaclass that makes isinstance(x, _FrozenDatetime) behave like isinstance(x, datetime)."""

    def __instancecheck__(self, instance):
        return type.__instancecheck__(datetime, instance)


class _FrozenDatetime(datetime, metaclass=_FrozenMeta):
    @classmethod
    def now(cls, tz=None):
        return FROZEN_NOW


@pytest.fixture(autouse=True)
def freeze_time(monkeypatch):
    """Pin datetime.now() so date-sensitive tests don't expire with the fixture dates."""
    monkeypatch.setattr(vm_module, "datetime", _FrozenDatetime)
