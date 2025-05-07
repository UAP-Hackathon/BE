import logging
import random
from datetime import datetime
from passlib.context import CryptContext
from email.message import EmailMessage
import ssl
import smtplib
from config import settings

pwdContext = CryptContext(schemes=["bcrypt"], deprecated="auto")

logging.basicConfig(level=logging.INFO)

emailSender = settings.email_sender
emailPassword = settings.email_password

def hash(password: str):
    return pwdContext.hash(password)

def verify(plainPassword, hashedPassword):
    return pwdContext.verify(plainPassword, hashedPassword)

def createUserName(name: str):
    name = name.lower()
    name = name.split(" ")
    if len(name) == 1:
        userName = name[0] + str(random.randint(0, 9999))
    else:
        userName = name[0] + name[1] + str(random.randint(0, 9999))
    return userName

def sendEmail(subject: str, body: str, receiver_email: str):
    message = EmailMessage()
    message.set_content(body)
    message["Subject"] = subject
    message["From"] = emailSender
    message["To"] = receiver_email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(emailSender, emailPassword)
        server.send_message(message)
