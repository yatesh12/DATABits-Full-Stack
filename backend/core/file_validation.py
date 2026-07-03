from __future__ import annotations

import imghdr
import logging
import magic
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import BinaryIO, Optional, Union

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AllowedFileType(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"
    XLS = "xls"
    JSON = "json"
    PARQUET = "parquet"
    TSV = "tsv"
    XML = "xml"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    PDF = "pdf"


MAGIC_BYTES: dict[AllowedFileType, list[bytes]] = {
    AllowedFileType.PNG: [b"\x89PNG\r\n\x1a\n"],
    AllowedFileType.JPG: [b"\xff\xd8\xff"],
    AllowedFileType.JPEG: [b"\xff\xd8\xff"],
    AllowedFileType.PDF: [b"%PDF"],
}

EXTENSION_MAP: dict[str, AllowedFileType] = {
    ".csv": AllowedFileType.CSV,
    ".xlsx": AllowedFileType.XLSX,
    ".xls": AllowedFileType.XLS,
    ".json": AllowedFileType.JSON,
    ".parquet": AllowedFileType.PARQUET,
    ".tsv": AllowedFileType.TSV,
    ".xml": AllowedFileType.XML,
    ".png": AllowedFileType.PNG,
    ".jpg": AllowedFileType.JPG,
    ".jpeg": AllowedFileType.JPEG,
    ".pdf": AllowedFileType.PDF,
}

ALLOWED_MIME_PREFIXES: dict[str, list[str]] = {
    "csv": ["text/csv", "text/plain"],
    "xlsx": [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    ],
    "xls": ["application/vnd.ms-excel", "application/octet-stream"],
    "json": ["application/json", "text/plain"],
    "parquet": ["application/octet-stream"],
    "tsv": ["text/tab-separated-values", "text/plain"],
    "xml": ["application/xml", "text/xml", "text/plain"],
}


@dataclass
class FileValidationResult:
    valid: bool
    filename: str
    extension: str
    size_bytes: int
    allowed_type: Optional[AllowedFileType] = None
    mime_type: Optional[str] = None
    detected_magic: Optional[str] = None
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def detect_mime_type(file_content: bytes) -> Optional[str]:
    try:
        return magic.from_buffer(file_content, mime=True)
    except Exception:
        return None


def validate_file(
    file: Union[str, Path, BinaryIO],
    filename: Optional[str] = None,
    max_size: Optional[int] = None,
    allowed_extensions: Optional[list[str]] = None,
    check_magic: bool = True,
) -> FileValidationResult:
    if max_size is None:
        max_size = settings.FILE_UPLOAD_MAX_SIZE
    if allowed_extensions is None:
        allowed_extensions = settings.FILE_UPLOAD_ALLOWED_EXTENSIONS

    if isinstance(file, (str, Path)):
        file_path = Path(file)
        filename = filename or file_path.name
        if not file_path.exists():
            return FileValidationResult(
                valid=False,
                filename=filename,
                extension=get_file_extension(filename),
                size_bytes=0,
                error="File not found",
            )
        size_bytes = file_path.stat().st_size
        with open(file_path, "rb") as f:
            file_content = f.read(4096)
    else:
        pos = file.tell()
        file_content = file.read(4096)
        file.seek(pos)
        size_bytes = 0
        try:
            file.seek(0, os.SEEK_END)
            size_bytes = file.tell()
            file.seek(pos)
        except OSError:
            pass

    if filename is None:
        return FileValidationResult(
            valid=False,
            filename="unknown",
            extension="",
            size_bytes=size_bytes,
            error="Filename is required",
        )

    ext = get_file_extension(filename)

    if ext not in allowed_extensions:
        return FileValidationResult(
            valid=False,
            filename=filename,
            extension=ext,
            size_bytes=size_bytes,
            error=f"File extension '{ext}' is not allowed. Allowed: {', '.join(allowed_extensions)}",
        )

    if size_bytes > max_size:
        max_mb = max_size / (1024 * 1024)
        return FileValidationResult(
            valid=False,
            filename=filename,
            extension=ext,
            size_bytes=size_bytes,
            error=f"File size ({size_bytes / (1024 * 1024):.1f} MB) exceeds maximum allowed ({max_mb:.0f} MB)",
        )

    file_type = EXTENSION_MAP.get(ext)
    mime_type = detect_mime_type(file_content) if file_content else None
    detected_magic = None
    warnings: list[str] = []

    if check_magic and file_type and file_type in MAGIC_BYTES:
        matched = False
        for magic_bytes in MAGIC_BYTES[file_type]:
            if file_content.startswith(magic_bytes):
                matched = True
                detected_magic = magic_bytes.hex()
                break
        if not matched:
            warnings.append(
                f"File extension '{ext}' does not match expected magic bytes for {file_type.value}"
            )

    if mime_type and file_type and file_type.value in ALLOWED_MIME_PREFIXES:
        allowed_mimes = ALLOWED_MIME_PREFIXES[file_type.value]
        if not any(mime_type.startswith(prefix) for prefix in allowed_mimes):
            warnings.append(
                f"MIME type '{mime_type}' does not match expected type for '{ext}' files"
            )

    return FileValidationResult(
        valid=True,
        filename=filename,
        extension=ext,
        size_bytes=size_bytes,
        allowed_type=file_type,
        mime_type=mime_type,
        detected_magic=detected_magic,
        warnings=warnings,
    )


def validate_uploaded_file(
    file: BinaryIO,
    filename: str,
    content_type: Optional[str] = None,
) -> FileValidationResult:
    result = validate_file(file, filename=filename)

    if content_type and result.mime_type:
        if content_type != result.mime_type:
            result.warnings.append(
                f"Declared content type '{content_type}' differs from detected '{result.mime_type}'"
            )

    return result
