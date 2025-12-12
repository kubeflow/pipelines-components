from __future__ import annotations

import importlib
import pkgutil
from typing import Any, Iterable


def eager_reexport_pkg_callables(
    *,
    package: str,
    package_path: Iterable[str],
    globals_dict: dict[str, Any],
) -> list[str]:
    names: list[str] = []
    for m in pkgutil.iter_modules(package_path):
        if not m.ispkg:
            continue
        child_pkg = importlib.import_module(f".{m.name}", package)
        obj = getattr(child_pkg, m.name, None)
        if obj is None:
            continue
        globals_dict[m.name] = obj
        names.append(m.name)
    return names


