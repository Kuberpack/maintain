import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.config import get_settings
from app.core.deps import require_roles
from app.models import UserRole
from app.schemas.photos import UploadedPhoto

router = APIRouter(prefix="/photos", tags=["photos"])

# Same roles as who marks tasks done -- this endpoint only exists to back
# that flow's proof-of-completion photo.
_upload_roles = require_roles(UserRole.operator, UserRole.supervisor, UserRole.admin)

_EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
}


@router.post("", response_model=UploadedPhoto, status_code=201)
async def upload_photo(file: UploadFile, _user=Depends(_upload_roles)) -> UploadedPhoto:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must be an image")

    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"Photo must be under {settings.max_upload_size_mb}MB"
        )

    extension = _EXTENSION_BY_CONTENT_TYPE.get(file.content_type, ".jpg")
    filename = f"{uuid.uuid4()}{extension}"

    uploads_path = Path(settings.uploads_dir)
    uploads_path.mkdir(parents=True, exist_ok=True)
    (uploads_path / filename).write_bytes(content)

    return UploadedPhoto(url=f"/uploads/{filename}")
