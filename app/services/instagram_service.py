import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


async def publish_to_instagram(
    image_url: str,
    caption: str,
    account_id: str | None = None,
    access_token: str | None = None,
) -> str:
    """
    Mock publish — 사업자 등록 후 앱 검수 통과하면 실제 Graph API로 교체.
    Returns: fake media_id
    """
    import uuid
    logger.info(f"[MOCK] Publishing to Instagram: {image_url[:60]}...")
    return f"mock_{uuid.uuid4().hex[:12]}"
