"""The op library: every drawing primitive a style recipe can call.

An op is a Python function registered under a name that style JSON uses:

    {"op": "glow", "x": 250, "y": 230, "r": 360, "color": "teal", "alpha": 26}

Ops receive a RenderContext and the op's parameters as keyword arguments, with
every numeric parameter already usable through `ctx.num()`. Adding a primitive
to the platform means writing one function and decorating it — no engine change.
"""
OPS = {}


def op(name):
    """Register a drawing primitive under the name recipes call it by."""
    def register(fn):
        OPS[name] = fn
        fn.op_name = name
        return fn
    return register


def get(name):
    if name not in OPS:
        raise KeyError(
            f"unknown op {name!r}. Available: {', '.join(sorted(OPS))}")
    return OPS[name]


def available():
    return sorted(OPS)


# Import for side effects: each module registers its ops on load.
from . import background, shapes, text  # noqa: E402,F401
