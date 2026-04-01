import re
import uuid
from pathlib import Path

from fastapi import UploadFile

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MIME_TO_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

SHORTNAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
SHORTNAME_MIN = 2
SHORTNAME_MAX = 64


class ImageValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(message)


async def save_upload_image(image: UploadFile, old_filename: str | None = None) -> str:
    """Validate and save an uploaded image to midias/. Returns the new filename.

    Raises ImageValidationError on invalid type or size.
    If old_filename is provided, the old file is deleted before saving the new one.
    """
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise ImageValidationError("image", "Tipo de arquivo não suportado.")
    contents = await image.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise ImageValidationError("image", "Arquivo muito grande (máx. 5MB).")
    if old_filename:
        Path("midias", old_filename).unlink(missing_ok=True)
    ext = MIME_TO_EXT[image.content_type]
    filename = f"{uuid.uuid4().hex}{ext}"
    Path("midias", filename).write_bytes(contents)
    return filename
