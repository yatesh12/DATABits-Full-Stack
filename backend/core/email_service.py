from __future__ import annotations

import logging
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class EmailMessage:
    to: list[str]
    subject: str
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    reply_to: Optional[str] = None
    attachments: list[dict[str, Any]] = field(default_factory=list)


class EmailService:
    def __init__(self) -> None:
        self._host = settings.SMTP_HOST
        self._port = settings.SMTP_PORT
        self._user = settings.SMTP_USER
        self._password = settings.SMTP_PASSWORD
        self._from_email = settings.SMTP_FROM_EMAIL
        self._from_name = settings.SMTP_FROM_NAME
        self._use_tls = settings.SMTP_USE_TLS
        self._enabled = bool(self._host and self._user and self._password)

    async def send_email(self, message: EmailMessage) -> bool:
        if not self._enabled:
            logger.warning("Email service is not configured; skipping send")
            return False

        try:
            import aiosmtplib

            msg = self._build_mime(message)
            async with aiosmtplib.SMTP(
                hostname=self._host,
                port=self._port,
                use_tls=self._use_tls,
            ) as smtp:
                if self._user:
                    await smtp.login(self._user, self._password)
                await smtp.send_message(msg)
            logger.info("Email sent to %s", message.to)
            return True
        except Exception as e:
            logger.error("Failed to send email: %s", e)
            return False

    async def send_templated(
        self,
        to: list[str],
        subject: str,
        template_name: str,
        context: dict[str, Any],
        cc: Optional[list[str]] = None,
    ) -> bool:
        from core.templates import render_email_template

        body_html = render_email_template(template_name, context, format="html")
        body_text = render_email_template(template_name, context, format="text")

        message = EmailMessage(
            to=to,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            cc=cc or [],
        )
        return await self.send_email(message)

    def _build_mime(self, message: EmailMessage) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.subject
        msg["From"] = f"{self._from_name} <{self._from_email}>"
        msg["To"] = ", ".join(message.to)

        if message.cc:
            msg["Cc"] = ", ".join(message.cc)
        if message.reply_to:
            msg["Reply-To"] = message.reply_to

        if message.body_text:
            msg.attach(MIMEText(message.body_text, "plain"))
        if message.body_html:
            msg.attach(MIMEText(message.body_html, "html"))

        for attachment in message.attachments:
            part = MIMEText(attachment.get("content", ""), _subtype=attachment.get("subtype", "plain"))
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=attachment.get("filename", "attachment"),
            )
            msg.attach(part)

        return msg

    async def send_welcome_email(self, email: str, name: str) -> bool:
        return await self.send_templated(
            to=[email],
            subject="Welcome to DATABits",
            template_name="welcome",
            context={"name": name, "email": email},
        )

    async def send_password_reset(self, email: str, reset_link: str) -> bool:
        return await self.send_templated(
            to=[email],
            subject="Password Reset - DATABits",
            template_name="password_reset",
            context={"email": email, "reset_link": reset_link},
        )

    async def send_invitation(self, email: str, inviter: str, invite_link: str) -> bool:
        return await self.send_templated(
            to=[email],
            subject=f"You've been invited to DATABits by {inviter}",
            template_name="invitation",
            context={"email": email, "inviter": inviter, "invite_link": invite_link},
        )


email_service = EmailService()
