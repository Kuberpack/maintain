from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.config import get_settings
from app.core.deps import get_current_user, require_roles
from app.models import UserRole
from app.schemas.photos import UploadedPhoto
from app.services import storage

router = APIRouter(prefix="/photos", tags=["photos"])

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
    url = storage.save_bytes(content, extension)
    return UploadedPhoto(url=url)


@router.get("/files/{filename}")
def get_photo(filename: str, _user=Depends(get_current_user)) -> Response:
    """Authenticated photo fetch. Replaces the old unauthenticated /uploads mount."""
    content = storage.read_bytes(filename)
    if content is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")
    ext = filename.rsplit(".", 1)[-1].lower()
    media = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "heic": "image/heic",
    }.get(ext, "application/octet-stream")
    return Response(content=content, media_type=media)
