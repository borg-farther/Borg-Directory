"""Core package lazy exports for compatibility with patch/import paths.

This allows dotted references like `borg.core.apply.apply_handler` to resolve
without eagerly importing every submodule.
"""

from importlib import import_module

_LAZY_SUBMODULES = {
    "apply",
    "search",
    "session",
    "dirs",
    "publish",
    "convert",
    "generate",
}


def __getattr__(name):
    if name in _LAZY_SUBMODULES:
        module = import_module(f"borg.core.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module 'borg.core' has no attribute {name!r}")


def __dir__():
    return sorted(set(list(globals().keys()) + list(_LAZY_SUBMODULES)))
