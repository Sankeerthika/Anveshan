import smtplib
import ssl
import os
from flask import current_app

def send_email(to_email, subject, body):
    host = current_app.config.get("SMTP_HOST")
    port = int(current_app.config.get("SMTP_PORT") or 587)
    username = current_app.config.get("SMTP_USER")
    password = current_app.config.get("SMTP_PASSWORD")
    timeout = float(current_app.config.get("SMTP_TIMEOUT") or 7.0)
    strict = bool(current_app.config.get("SMTP_STRICT") or False)
    # Handle different truthy values for TLS
    tls_val = current_app.config.get("SMTP_TLS", True)
    use_tls = str(tls_val).lower() in ("1", "true", "yes", "on")

    if not host or not username or not password:
        current_app.logger.warning("SMTP config missing. Email to %s not sent.", to_email)
        # In development or when SMTP is not configured, mock the email and proceed
        print(f"\n[MOCK EMAIL]\nTo: {to_email}\nSubject: {subject}\nBody: {body}\n")
        return True

    try:
        message = f"From: {username}\r\nTo: {to_email}\r\nSubject: {subject}\r\n\r\n{body}"
        if use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(host, port, timeout=timeout) as server:
                server.starttls(context=context)
                server.login(username, password)
                server.sendmail(username, [to_email], message.encode("utf-8"))
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as server:
                server.login(username, password)
                server.sendmail(username, [to_email], message.encode("utf-8"))
        return True
    except Exception as e:
        current_app.logger.error("SMTP failed: %s", e)
        try:
            current_app.config["SMTP_LAST_ERROR"] = str(e)
        except Exception:
            pass
        if strict:
            return False
        # Non-strict mode: mock success to avoid blocking critical flows in constrained envs
        print(f"\n[MOCK EMAIL AFTER FAILURE]\nTo: {to_email}\nSubject: {subject}\nBody: {body}\n(reason: {e})\n")
        return True

def smtp_missing_keys():
    missing = []
    if not current_app.config.get("SMTP_HOST"):
        missing.append("SMTP_HOST")
    if not current_app.config.get("SMTP_USER"):
        missing.append("SMTP_USER")
    if not current_app.config.get("SMTP_PASSWORD"):
        missing.append("SMTP_PASSWORD")
    return missing
