from __future__ import annotations

from email.message import EmailMessage
import logging
import smtplib

from .config import Settings, get_settings

logger = logging.getLogger(__name__)


def build_password_reset_message(
    *, to_email: str, username: str, reset_url: str, settings: Settings
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "Redefinição de senha do WikiDev"
    message["From"] = settings.mail_from
    message["To"] = to_email
    message.set_content(
        "\n".join(
            [
                f"Olá, {username}.",
                "",
                "Recebemos uma solicitação para redefinir sua senha no WikiDev.",
                f"Abra este link para escolher uma nova senha: {reset_url}",
                "",
                "O link expira em "
                f"{settings.password_reset_ttl_minutes} minutos e só pode ser usado uma vez.",
                "Se você não solicitou a alteração, ignore este e-mail.",
            ]
        )
    )
    return message


def send_password_reset_email(
    *, to_email: str, username: str, reset_url: str, settings: Settings | None = None
) -> None:
    settings = settings or get_settings()
    message = build_password_reset_message(
        to_email=to_email,
        username=username,
        reset_url=reset_url,
        settings=settings,
    )

    if settings.mail_mode == "console":
        logger.warning("E-mail de recuperação para %s: %s", to_email, reset_url)
        return

    if settings.mail_mode != "smtp":
        raise RuntimeError("MAIL_MODE deve ser 'console' ou 'smtp'")
    if not settings.smtp_host:
        raise RuntimeError("SMTP_HOST é obrigatório quando MAIL_MODE=smtp")

    smtp_class = smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
    with smtp_class(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_use_tls and not settings.smtp_use_ssl:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or "")
        smtp.send_message(message)
