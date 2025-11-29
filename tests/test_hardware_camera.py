import pytest

@pytest.mark.hardware
def test_camera_smoke_import():
    # Ensure camera smoke test script is present and importable
    import scripts.camera_smoke_test as _smoke  # type: ignore
    assert hasattr(_smoke, "main")
