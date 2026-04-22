"""Compatibility loader for the project math engine.

Exposes the blackjack math engine at the repo root so scripts, docs, and tests
can consistently import `engine` without colliding with Python's stdlib
`math` module.
"""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_ENGINE_PATH = Path(__file__).resolve().parent / "math" / "engine.py"
_SPEC = spec_from_file_location("_submittal_engine", _ENGINE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load engine module from {_ENGINE_PATH}")

_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

__all__ = [name for name in dir(_MODULE) if not name.startswith("_")]

globals().update({name: getattr(_MODULE, name) for name in __all__})
