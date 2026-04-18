import logging
import httpx

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.instagram.com/v21.0"

# Fields available directly on media object
MEDIA_FIELDS = "like_count,comments_count"

# Insights metrics available for IMAGE/CAROUSEL media in Graph API v21
# Note: some metrics differ by media type — we request conservatively and tolerate missing keys.
INSIGHTS_METRICS = "reach,saved,shares,total_interactions"


async def fetch_media_insights(media_id: str, access_token: str) -> dict:
    """Fetch Instagram Insights + basic counts for a single media item.

    Returns a dict with keys: likes, comments, reach, saves, shares, impressions, profile_visits.
    Missing or unsupported metrics default to 0. Never raises on partial failure —
    callers should treat the return as best-effort.
    """
    if not media_id or not access_token:
        raise ValueError("media_id and access_token are required")

    result = {
        "likes": 0,
        "comments": 0,
        "reach": 0,
        "saves": 0,
        "shares": 0,
        "impressions": 0,
        "profile_visits": 0,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(
                f"{GRAPH_API_BASE}/{media_id}",
                params={"fields": MEDIA_FIELDS, "access_token": access_token},
            )
            if resp.status_code == 200:
                data = resp.json()
                result["likes"] = int(data.get("like_count", 0) or 0)
                result["comments"] = int(data.get("comments_count", 0) or 0)
            else:
                logger.warning(f"media fields fetch failed: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.warning(f"media fields fetch exception: {e}")

        try:
            resp = await client.get(
                f"{GRAPH_API_BASE}/{media_id}/insights",
                params={"metric": INSIGHTS_METRICS, "access_token": access_token},
            )
            if resp.status_code == 200:
                for entry in resp.json().get("data", []):
                    name = entry.get("name")
                    values = entry.get("values") or []
                    value = int(values[0].get("value", 0) or 0) if values else 0
                    if name == "reach":
                        result["reach"] = value
                    elif name == "saved":
                        result["saves"] = value
                    elif name == "shares":
                        result["shares"] = value
                    elif name == "total_interactions":
                        # not stored separately — used as fallback signal only
                        pass
            else:
                logger.warning(f"insights fetch failed: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.warning(f"insights fetch exception: {e}")

    return result
