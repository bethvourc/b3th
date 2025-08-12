from b3th._compat import patch_click_make_metavar


def test_patch_click_make_metavar_safe_to_call() -> None:
    """Calling the shim should be a no-op on current Click and never explode."""
    patch_click_make_metavar()
