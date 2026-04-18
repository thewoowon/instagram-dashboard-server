from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
import logging

from app.db.session import async_session_factory
from app.models.publish_job import PublishJob
from app.models.post_draft import PostDraft
from app.models.creative_asset import CreativeAsset
from app.services.instagram_service import publish_to_instagram

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def process_due_jobs():
    """예약 시각이 된 publish_job을 처리."""
    async with async_session_factory() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(PublishJob)
            .options(
                selectinload(PublishJob.draft).selectinload(PostDraft.creative_assets),
                selectinload(PublishJob.draft).selectinload(PostDraft.account),
            )
            .where(
                PublishJob.publish_status == "queued",
                PublishJob.scheduled_at <= now,
            )
        )
        jobs = result.scalars().all()

        for job in jobs:
            draft = job.draft
            try:
                image_assets = [a for a in (draft.creative_assets or []) if a.asset_type == "image"]

                if not image_assets:
                    raise ValueError("발행할 이미지가 없습니다. 이미지를 먼저 업로드하세요.")

                if not draft.account.access_token:
                    raise ValueError(f"{draft.account.brand_name} 계정에 access_token이 설정되지 않았습니다.")

                image_urls = (
                    [image_assets[0].storage_url]
                    if draft.format_type == "single"
                    else [a.storage_url for a in image_assets]
                )

                caption_text = (
                    f"{draft.hook}\n\n{draft.caption}\n\n{draft.cta}\n\n"
                    + " ".join(f"#{tag}" for tag in (draft.hashtags or []))
                )

                media_id = await publish_to_instagram(
                    image_urls=image_urls,
                    caption=caption_text,
                    access_token=draft.account.access_token,
                )

                job.publish_status = "published"
                job.meta_publish_id = media_id
                draft.approval_status = "published"
                logger.info(f"Published job {job.id}, media_id={media_id}")

            except Exception as e:
                job.publish_status = "failed"
                job.error_message = str(e)
                logger.error(f"Failed to publish job {job.id}: {e}")

        if jobs:
            await db.commit()


def start_scheduler():
    scheduler.add_job(
        process_due_jobs,
        trigger=IntervalTrigger(minutes=1),
        id="process_publish_jobs",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started.")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped.")
