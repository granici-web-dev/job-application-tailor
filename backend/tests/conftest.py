import io

import pytest


@pytest.fixture
def tiny_jpeg() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (120, 120), (180, 180, 180)).save(buffer, format="JPEG")
    return buffer.getvalue()
