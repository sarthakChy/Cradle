from importlib import import_module

__all__ = [
    "IOEnvironment",
    "GameManager",
    "gui_utils",
]


def __getattr__(name):
    if name == "IOEnvironment":
        return import_module(".io_env", __name__).IOEnvironment
    if name == "GameManager":
        return import_module(".game_manager", __name__).GameManager
    if name == "gui_utils":
        return import_module(".gui_utils", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
