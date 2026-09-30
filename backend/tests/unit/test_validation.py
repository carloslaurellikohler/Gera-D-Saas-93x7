from __future__ import annotations

import pytest

from app.services.validation import (
    CorruptedFileError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    sanitize_filename,
    validate_upload,
)


def test_sanitize_filename_strips_path_and_unsafe_chars():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("relatório final (1).txt") == "relat_rio_final_1_.txt"


def test_sanitize_filename_empty_falls_back():
    assert sanitize_filename("///") == "arquivo"


def test_validate_upload_txt_ok():
    assert validate_upload(file_name="t.txt", content=b"ola mundo", max_upload_mb=10) == "txt"


def test_validate_upload_docx_ok():
    content = b"PK\x03\x04" + b"\x00" * 20
    assert validate_upload(file_name="t.docx", content=content, max_upload_mb=10) == "docx"


def test_validate_upload_mp3_id3_ok():
    content = b"ID3" + b"\x00" * 20
    assert validate_upload(file_name="t.mp3", content=content, max_upload_mb=10) == "mp3"


def test_validate_upload_mp4_ok():
    content = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 20
    assert validate_upload(file_name="t.mp4", content=content, max_upload_mb=10) == "mp4"


def test_validate_upload_rejects_unsupported_extension():
    with pytest.raises(UnsupportedFileTypeError):
        validate_upload(file_name="t.wav", content=b"RIFF", max_upload_mb=10)


def test_validate_upload_rejects_too_large():
    content = b"x" * (2 * 1024 * 1024)
    with pytest.raises(FileTooLargeError):
        validate_upload(file_name="t.txt", content=content, max_upload_mb=1)


def test_validate_upload_rejects_mismatched_content():
    # extensão .mp3 mas conteúdo não tem assinatura de mp3 real
    with pytest.raises(CorruptedFileError):
        validate_upload(file_name="malicious.mp3", content=b"#!/bin/sh\nrm -rf /", max_upload_mb=10)
