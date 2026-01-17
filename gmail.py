from googleapiclient.discovery import build
from email.message import EmailMessage
import base64

def send_email(credentials, to, subject, body):
    service = build("gmail", "v1", credentials=credentials)

    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    send_body = {"raw": encoded_message}

    service.users().messages().send(
        userId="me",
        body=send_body
    ).execute()
