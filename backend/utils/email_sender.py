import smtplib
import ssl
import os
from flask import current_app

def send_email(to_email, subject, body):
    host = current_app.config.get("SMTP_HOST")
    port = int(current_app.config.get("SMTP_PORT") or 587)
    username = current_app.config.get("SMTP_USER")
    password = current_app.config.get("SMTP_PASSWORD")
    # Handle different truthy values for TLS
    tls_val = current_app.config.get("SMTP_TLS", True)
    use_tls = str(tls_val).lower() in ("1", "true", "yes", "on")

    if not host or not username or not password:
        current_app.logger.warning("SMTP config missing. Email to %s not sent.", to_email)
        # In development, mock the email by logging it and returning True so the flow continues
        print(f"\n[DEV MODE] MOCKED EMAIL\nTo: {to_email}\nSubject: {subject}\nBody: {body}\n")
        return True

    try:
        message = f"From: {username}\r\nTo: {to_email}\r\nSubject: {subject}\r\n\r\n{body}"
        if use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(host, port) as server:
                server.starttls(context=context)
                server.login(username, password)
                server.sendmail(username, [to_email], message.encode("utf-8"))
        else:
            with smtplib.SMTP(host, port) as server:
                server.login(username, password)
                server.sendmail(username, [to_email], message.encode("utf-8"))
        return True
    except Exception as e:
        current_app.logger.error("SMTP failed: %s", e)
        return False

def smtp_missing_keys():
    missing = []
    if not current_app.config.get("SMTP_HOST"):
        missing.append("SMTP_HOST")
    if not current_app.config.get("SMTP_USER"):
        missing.append("SMTP_USER")
    if not current_app.config.get("SMTP_PASSWORD"):
        missing.append("SMTP_PASSWORD")
    return missing
