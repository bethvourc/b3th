"""Compatibility helpers for external-library quirks (Click, Typer, …)."""

from __future__ import annotations

from inspect import signature


def patch_click_make_metavar() -> None:
    """Monkey-patch Click so Typer ≥ 0.9 works with *any* Click 8.x.

    Typer ≥ 0.9 always does:  `Parameter.make_metavar(self, ctx)`
    Click variants:

    | Version | Original signature                        |
    |---------|-------------------------------------------|
    | ≤ 8.0   | `(self)`                                  |
    | 8.1     | `(self, ctx)`                             |
    | 8.2+    | `(self, param, ctx)` _(as of 8.2.0)_      |

    The shim below:

    1. Inspects the original method to see how many *positional* args it wants.
    2. Accepts *any* args/kwargs from Typer.
    3. Feeds the original the exact count it expects, using values Typer passed
       when available and padding the rest with `None`.

    Result: no more “missing 1 required positional argument” errors.
    """
    from click.core import Parameter  # local import to avoid early cycles

    _orig = Parameter.make_metavar  # type: ignore[assignment]
    want = len(signature(_orig).parameters) - 1  # exclude `self`

    def _shim(self, *args, **kwargs):  # noqa: D401
        supplied = list(args[:want])  # use what Typer gave us
        if len(supplied) < want:  # pad if Typer gave fewer
            supplied.extend([None] * (want - len(supplied)))
        return _orig(self, *supplied)  # ignore **kwargs entirely

    Parameter.make_metavar = _shim  # type: ignore[assignment]
