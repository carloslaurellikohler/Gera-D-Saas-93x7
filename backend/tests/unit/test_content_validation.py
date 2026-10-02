from __future__ import annotations

import pytest

from app.services.content_validation import (
    ContentFileTooLargeError,
    CorruptedContentFileError,
    UnsupportedContentFileTypeError,
    validate_content_upload,
)


def test_validate_content_upload_pdf_ok():
    content = b"%PDF-1.4" + b"\x00" * 20
    validate_content_upload(file_name="apostila.pdf", content=content, max_upload_mb=10)


def test_validate_content_upload_rejects_unsupported_extension():
    with pytest.raises(UnsupportedContentFileTypeError):
        validate_content_upload(file_name="video.mp4", content=b"\x00" * 20, max_upload_mb=10)


def test_validate_content_upload_rejects_too_large():
    content = b"%PDF-" + b"x" * (2 * 1024 * 1024)
    with pytest.raises(ContentFileTooLargeError):
        validate_content_upload(file_name="grande.pdf", content=content, max_upload_mb=1)


def test_validate_content_upload_rejects_mismatched_content():
    with pytest.raises(CorruptedContentFileError):
        validate_content_upload(file_name="malicioso.pdf", content=b"not a real pdf", max_upload_mb=10)
