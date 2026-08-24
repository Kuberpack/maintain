"""Photo storage: local disk, or S3-compatible when S3_BUCKET is set."""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger("storage")

_SAFE_FILENAME = re.compile(r"^[0-9a-f-]{36}\.(jpg|jpeg|png|webp|heic)$", re.IGNORECASE)


def is_safe_filename(filename: str) -> bool:
    return bool(_SAFE_FILENAME.match(filename))


def public_url(filename: str) -> str:
    return f"/uploads/{filename}"


def filename_from_url(url: str) -> str | None:
    name = url.rsplit("/", 1)[-1]
    return name if is_safe_filename(name) else None


def save_bytes(content: bytes, extension: str) -> str:
    filename = f"{uuid.uuid4()}{extension}"
    settings = get_settings()
    if settings.s3_bucket:
        _s3_put(settings, filename, content)
    else:
        uploads_path = Path(settings.uploads_dir)
        uploads_path.mkdir(parents=True, exist_ok=True)
        (uploads_path / filename).write_bytes(content)
    return public_url(filename)


def read_bytes(filename: str) -> bytes | None:
    if not is_safe_filename(filename):
        return None
    settings = get_settings()
    if settings.s3_bucket:
        return _s3_get(settings, filename)
    path = Path(settings.uploads_dir) / filename
    if not path.is_file():
        return None
    return path.read_bytes()


def _s3_client(settings):  # type: ignore[no-untyped-def]
    import boto3  # imported only when S3 is configured

    kwargs: dict = {
        "aws_access_key_id": settings.s3_access_key,
        "aws_secret_access_key": settings.s3_secret_key,
        "region_name": settings.s3_region,
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return boto3.client("s3", **kwargs)


def _s3_put(settings, filename: str, content: bytes) -> None:
    client = _s3_client(settings)
    client.put_object(Bucket=settings.s3_bucket, Key=filename, Body=content, ContentType=_content_type(filename))


def _s3_get(settings, filename: str) -> bytes | None:
    from botocore.exceptions import ClientError

    client = _s3_client(settings)
    try:
        response = client.get_object(Bucket=settings.s3_bucket, Key=filename)
    except ClientError:
        logger.warning("S3 get failed for %s", filename)
        return None
    return response["Body"].read()


def _content_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "heic": "image/heic",
    }.get(ext, "application/octet-stream")
