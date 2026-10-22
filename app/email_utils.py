
from flask import current_app
from flask_mail import Message


def send_email_notification(recipient, subject, body):
    try:
        mail = current_app.extensions.get("mail")

        if mail is None:
            current_app.logger.error("Mail extension is not initialized")
            return False

        message = Message(
            subject=subject,
            recipients=[recipient],
            body=body
        )

        mail.send(message)
        return True

    except Exception:
        current_app.logger.exception("Email notification failed")
        return False
