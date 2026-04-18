import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_sync(to_email: str, subject: str, html_body: str, text_body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(msg)


async def send_invitation_email(
    to_email: str,
    org_name: str,
    inviter_email: str,
    invite_url: str,
) -> bool:
    """Send an invitation email. Returns True if sent, False if SMTP not configured."""
    if not settings.SMTP_HOST:
        logger.info(f"SMTP not configured — invite link for {to_email}: {invite_url}")
        return False

    subject = f"[{org_name}] 초대장"
    text_body = (
        f"{inviter_email}님이 당신을 {org_name} 워크스페이스에 초대했습니다.\n\n"
        f"수락하려면 다음 링크를 클릭하세요:\n{invite_url}\n"
    )
    html_body = f"""
    <div style="font-family: -apple-system, sans-serif; padding: 24px; max-width: 520px;">
      <h2 style="margin: 0 0 16px;">{org_name} 초대</h2>
      <p>{inviter_email}님이 당신을 <strong>{org_name}</strong> 워크스페이스에 초대했습니다.</p>
      <p style="margin: 24px 0;">
        <a href="{invite_url}"
           style="display:inline-block;padding:10px 20px;background:#111;color:#fff;border-radius:6px;text-decoration:none;">
          초대 수락하기
        </a>
      </p>
      <p style="color:#666;font-size:12px;">버튼이 동작하지 않으면 다음 링크를 복사해주세요:<br>{invite_url}</p>
    </div>
    """
    try:
        await asyncio.to_thread(_send_sync, to_email, subject, html_body, text_body)
        return True
    except Exception as e:
        logger.exception(f"Failed to send invitation email to {to_email}: {e}")
        raise
