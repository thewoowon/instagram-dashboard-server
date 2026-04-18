import asyncio
import logging
import httpx

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.instagram.com/v21.0"
CAROUSEL_MAX = 10
CAROUSEL_MIN = 2


async def _create_container(client: httpx.AsyncClient, token: str, **params) -> str:
    resp = await client.post(
        f"{GRAPH_API_BASE}/me/media",
        params={**params, "access_token": token},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Container creation failed: {resp.status_code} {resp.text}")
    creation_id = resp.json().get("id")
    if not creation_id:
        raise RuntimeError(f"No creation_id in response: {resp.text}")
    return creation_id


async def _publish_container(client: httpx.AsyncClient, token: str, creation_id: str) -> str:
    resp = await client.post(
        f"{GRAPH_API_BASE}/me/media_publish",
        params={"creation_id": creation_id, "access_token": token},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Publish failed: {resp.status_code} {resp.text}")
    media_id = resp.json().get("id")
    if not media_id:
        raise RuntimeError(f"No media_id in response: {resp.text}")
    return media_id


async def publish_to_instagram(image_urls: list[str], caption: str, access_token: str) -> str:
    """단일 이미지 또는 캐러셀(2~10장) 게시. 게시된 media_id 반환."""
    if not access_token:
        raise RuntimeError("access_token is required")
    if not image_urls:
        raise RuntimeError("image_urls is empty")

    async with httpx.AsyncClient(timeout=60.0) as client:
        if len(image_urls) == 1:
            creation_id = await _create_container(
                client, access_token, image_url=image_urls[0], caption=caption
            )
        else:
            if len(image_urls) > CAROUSEL_MAX:
                raise RuntimeError(f"carousel supports up to {CAROUSEL_MAX} items, got {len(image_urls)}")
            child_ids = await asyncio.gather(
                *(
                    _create_container(client, access_token, image_url=u, is_carousel_item="true")
                    for u in image_urls
                )
            )
            creation_id = await _create_container(
                client,
                access_token,
                media_type="CAROUSEL",
                children=",".join(child_ids),
                caption=caption,
            )

        media_id = await _publish_container(client, access_token, creation_id)

    logger.info(f"Published to Instagram: media_id={media_id}, items={len(image_urls)}")
    return media_id
