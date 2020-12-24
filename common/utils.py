from typing import Any


def class_name(cls: Any) -> str:
    """Returns the resolved, human-friendly class name of a class.

    Not extensively tested - for informational/debug purposes only.
    """
    try:
        if hasattr(cls, "__name__"):
            return cls.__name__
        return cls.__class__.__name__
    except AttributeError:
        return str(cls)
