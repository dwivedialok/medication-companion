"""Unit tests for auth_broker.agent_client image transport."""
from unittest.mock import MagicMock, patch

import pytest
from google.genai import types

from auth_broker.agent_client import (
    _build_user_message,
    _image_part,
    _parse_gcs_uri,
)


def test_parse_gcs_uri_valid():
    assert _parse_gcs_uri("gs://my-bucket/prescriptions/a.jpg") == (
        "my-bucket",
        "prescriptions/a.jpg",
    )


def test_parse_gcs_uri_invalid():
    with pytest.raises(ValueError, match="Invalid GCS URI"):
        _parse_gcs_uri("https://example.com/x.jpg")


def test_build_user_message_local_uses_inline_bytes():
    with patch(
        "auth_broker.agent_client._download_gcs_bytes",
        return_value=b"\xff\xd8\xff",
    ):
        content = _build_user_message(
            "gs://bucket/prescriptions/x.jpg",
            "image/jpeg",
            "en-IN",
            inline_image=True,
        )
    image_part = content.parts[1]
    assert image_part.inline_data is not None
    assert image_part.inline_data.data == b"\xff\xd8\xff"
    assert image_part.inline_data.mime_type == "image/jpeg"


def test_image_part_remote_uses_uri():
    part = _image_part(
        "gs://bucket/prescriptions/x.jpg",
        "image/jpeg",
        inline_bytes=False,
    )
    assert part.file_data is not None
    assert part.file_data.file_uri == "gs://bucket/prescriptions/x.jpg"
    assert isinstance(part, types.Part)
