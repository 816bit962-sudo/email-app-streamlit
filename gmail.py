from googleapiclient.discovery import build
from email.message import EmailMessage
import base64
import re


def send_email(credentials, to, subject, body, html=False):
    service = build("gmail", "v1", credentials=credentials)

    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject

    if html:
        # Fallback testo (rimuove i tag HTML)
        text_fallback = re.sub("<[^<]+?>", "", body)

        message.set_content(text_fallback)
        message.add_alternative(body, subtype="html")
    else:
        message.set_content(body)

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    send_body = {"raw": encoded_message}

    service.users().messages().send(
        userId="me",
        body=send_body
    ).execute()
