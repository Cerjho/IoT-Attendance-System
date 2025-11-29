import pytest

@pytest.mark.hardware
def test_gpio_module_exists():
    # Verify hardware module path exists and is importable
    import src.hardware  # type: ignore
    assert src.hardware is not None
