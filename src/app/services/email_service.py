
from fastapi import HTTPException

from fastapi_mail import FastMail, ConnectionConfig

import os
from dotenv import load_dotenv

load_dotenv()


def mail_data():
    required_variables = ["MAIL_USERNAME_ENV", "MAIL_APP_PASSWORD_ENV"]
    my_mail = list(map(os.getenv, required_variables))
    # print(my_mail, "*" * 19)
    if all(my_mail):

        MAIL_CONF = ConnectionConfig(
            MAIL_USERNAME=my_mail[0],
            MAIL_PASSWORD=my_mail[1],
            MAIL_FROM=os.getenv("MAIL_USERNAME_ENV"),
            MAIL_PORT=465,
            MAIL_SERVER="smtp.gmail.com",
            MAIL_STARTTLS=False,
            MAIL_SSL_TLS=True,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )
        return MAIL_CONF


fastmail = FastMail(mail_data())


class AsyncEmailSender:
    def __init__(self, message):
        self.message = message

    async def __aenter__(self):
        await fastmail.send_message(self.message)
        return self.message

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            error_detail = f"Error sending email: {str(exc_val)}"
            raise HTTPException(status_code=500, detail="Error sending email")