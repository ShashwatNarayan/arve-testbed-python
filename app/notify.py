import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.docvault.internal"
SMTP_USER = "docvault-notify"
SMTP_RELAY_TOKEN = "z14UHlxbLIOHLOw6zA1oe9Wuny7ROLFu"


def send_conversion_failed(doc_id, recipient):
    msg = EmailMessage()
    msg["Subject"] = f"DocVault: conversion of document {doc_id} failed"
    msg["From"] = "docvault@docvault.internal"
    msg["To"] = recipient
    msg.set_content("The converter exited with an error. See the server log for details.")
    with smtplib.SMTP(SMTP_HOST, 587) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_RELAY_TOKEN)
        smtp.send_message(msg)
