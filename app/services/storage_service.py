import uuid
import httpx
from app.core.config import settings


async def upload_to_storage(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    folder: str = "uploads",
) -> str:
    """Supabase Storage에 파일 업로드 후 public URL 반환."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    storage_path = f"{folder}/{uuid.uuid4()}.{ext}"

    url = f"{settings.SUPABASE_URL}/storage/v1/object/{settings.STORAGE_BUCKET}/{storage_path}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            content=file_bytes,
            headers={
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": content_type,
                "x-upsert": "false",
            },
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Storage upload failed: {resp.status_code} {resp.text}")

    public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.STORAGE_BUCKET}/{storage_path}"
    return public_url
