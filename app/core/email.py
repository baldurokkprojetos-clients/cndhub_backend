import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.base import Configuracao
import asyncio

logger = logging.getLogger(__name__)

def _build_frontend_url(path: str, token: str) -> str:
    base_url = (settings.FRONTEND_URL or "http://localhost:3000").rstrip("/")
    normalized_path = path.lstrip("/")
    return f"{base_url}/{normalized_path}?token={token}"

def get_resend_api_key():
    db = SessionLocal()
    try:
        config = db.query(Configuracao).filter(Configuracao.chave == "resend_api_key").first()
        if config and config.valor:
            return config.valor
        return None
    except Exception as e:
        logger.error(f"Error fetching resend_api_key: {e}")
        return None
    finally:
        db.close()

def get_resend_from_email():
    db = SessionLocal()
    try:
        config = db.query(Configuracao).filter(Configuracao.chave == "resend_from_email").first()
        if config and config.valor:
            return config.valor
        return "Cadastro Politehub <onboarding@resend.dev>"
    except Exception as e:
        logger.error(f"Error fetching resend_from_email: {e}")
        return "Cadastro Politehub <onboarding@resend.dev>"
    finally:
        db.close()

def get_smtp_config():
    db = SessionLocal()
    try:
        rows = db.query(Configuracao).filter(
            Configuracao.chave.in_(["smtp_host", "smtp_port", "smtp_user", "smtp_pass", "smtp_from"])
        ).all()
        data = {row.chave: row.valor for row in rows}
        smtp_host = data.get("smtp_host")
        smtp_user = data.get("smtp_user")
        smtp_pass = data.get("smtp_pass")
        smtp_from = data.get("smtp_from") or smtp_user
        smtp_port_raw = data.get("smtp_port") or "465"
        try:
            smtp_port = int(smtp_port_raw)
        except ValueError:
            smtp_port = 465
        if not smtp_host or not smtp_user or not smtp_pass:
            return None
        return {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "smtp_user": smtp_user,
            "smtp_pass": smtp_pass,
            "smtp_from": smtp_from
        }
    except Exception as e:
        logger.error(f"Error fetching smtp config: {e}")
        return None
    finally:
        db.close()

def _try_send_smtp(smtp_host: str, smtp_port: int, smtp_user: str, smtp_pass: str, from_email: str, email_to: str, subject: str, body: str):
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = email_to
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        logger.info(f"Attempting to send email via SSL {smtp_host}:{smtp_port} using {smtp_user}...")

        server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        server.set_debuglevel(1)
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()

        logger.info(f"Real email successfully sent to {email_to}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Auth Error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending real email: {e}")
        return False

def _send_real_email_sync(email_to: str, subject: str, body: str):
    resend_key = get_resend_api_key()

    if resend_key:
        if _try_send_smtp(
            "smtp.resend.com",
            465,
            "resend",
            resend_key,
            get_resend_from_email(),
            email_to,
            subject,
            body,
        ):
            return True
    smtp_config = get_smtp_config()
    if not smtp_config:
        return False
    return _try_send_smtp(
        smtp_config["smtp_host"],
        smtp_config["smtp_port"],
        smtp_config["smtp_user"],
        smtp_config["smtp_pass"],
        smtp_config["smtp_from"],
        email_to,
        subject,
        body,
    )

def send_verification_email(email_to: str, token: str):
    verification_url = _build_frontend_url("verify-email", token)
    
    subject = "Verifique seu cadastro no sistema"
    body = f"""
    <html>
      <body>
        <h2>Bem-vindo ao Politeto CND!</h2>
        <p>Clique no link abaixo para validar seu e-mail e ativar sua conta:</p>
        <p><a href="{verification_url}">{verification_url}</a></p>
      </body>
    </html>
    """
    
    if _send_real_email_sync(email_to, subject, body):
        return True
    logger.warning(f"Email sending failed for {email_to}")
    return False

async def send_verification_email_async(email_to: str, token: str):
    verification_url = _build_frontend_url("verify-email", token)

    subject = "Verifique seu cadastro no sistema"
    body = f"""
    <html>
      <body>
        <h2>Bem-vindo ao Politeto CND!</h2>
        <p>Clique no link abaixo para validar seu e-mail e ativar sua conta:</p>
        <p><a href="{verification_url}">{verification_url}</a></p>
      </body>
    </html>
    """

    logger.info(f"Triggering email send to {email_to}")

    success = await asyncio.to_thread(_send_real_email_sync, email_to, subject, body)
    if success:
        logger.info("Email sent successfully")
        return True

    logger.warning(f"Email sending failed for {email_to}")
    return False

async def send_password_reset_email_async(email_to: str, token: str):
    reset_url = _build_frontend_url("reset-password", token)
    
    subject = "Recuperação de Senha - Politeto CND"
    body = f"""
    <html>
      <body>
        <h2>Recuperação de Senha</h2>
        <p>Você solicitou a redefinição da sua senha.</p>
        <p>Clique no link abaixo para criar uma nova senha:</p>
        <p><a href="{reset_url}">{reset_url}</a></p>
        <p>Se você não solicitou isso, pode ignorar este e-mail.</p>
      </body>
    </html>
    """
    
    # Try sending real email
    logger.info(f"Triggering email send to {email_to}")
    
    # Run the synchronous email sending in a thread
    success = await asyncio.to_thread(_send_real_email_sync, email_to, subject, body)
    if success:
        logger.info("Email sent successfully")
        return True
        
    logger.warning(f"Email sending failed for {email_to}")
    return False

def send_password_reset_email(email_to: str, token: str):
    # This is the old synchronous wrapper if needed, but we will use the async one in the router
    pass
