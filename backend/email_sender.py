"""
Envio de e-mail via SMTP (stdlib). Credenciais apenas no .env.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage

SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com').strip()
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587') or '587')
SMTP_USER = os.environ.get('SMTP_USER', '').strip()
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '').strip()
SMTP_FROM = os.environ.get('SMTP_FROM', SMTP_USER).strip() or SMTP_USER


def smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def send_email(*, to: str, subject: str, text_body: str, html_body: str | None = None) -> tuple[bool, str | None]:
    if not smtp_configured():
        return False, 'SMTP não configurado (SMTP_USER e SMTP_PASSWORD no .env).'

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SMTP_FROM
    msg['To'] = to
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype='html')

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True, None
    except Exception as exc:
        return False, str(exc)


def send_device_verification_email(
    *,
    to: str,
    username: str,
    code: str,
    confirm_url: str,
    user_agent: str,
    ip_hint: str,
    expires_minutes: int,
) -> tuple[bool, str | None]:
    subject = 'Confirme o acesso — Automação Equatorial PIENG'
    text = f"""Olá,

Foi solicitado login de administrador ({username}) em um dispositivo ainda não autorizado.

Código de confirmação: {code}
(Válido por {expires_minutes} minutos)

Abra este link no mesmo navegador/computador em que tentou entrar:
{confirm_url}

Detalhes:
- Navegador: {user_agent or '—'}
- IP (aprox.): {ip_hint or '—'}

Se não foi você, ignore este e-mail e altere a senha master.

— Automação Equatorial PIENG
"""
    html = f"""<p>Foi solicitado login de administrador (<strong>{username}</strong>) em um dispositivo novo.</p>
<p style="font-size:24px;letter-spacing:4px;"><strong>{code}</strong></p>
<p><a href="{confirm_url}">Confirmar este dispositivo</a></p>
<p><small>Válido por {expires_minutes} min. Navegador: {user_agent or '—'} · IP: {ip_hint or '—'}</small></p>
<p><small>Se não foi você, ignore este e-mail.</small></p>"""
    return send_email(to=to, subject=subject, text_body=text, html_body=html)
