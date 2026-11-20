import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()  # carga variables desde .env si existe

required_vars = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"]
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    raise RuntimeError(f"Faltan variables de entorno: {', '.join(missing)}")

host = os.environ["SMTP_HOST"]
port = int(os.environ["SMTP_PORT"])
user = os.environ["SMTP_USER"]
password = os.environ["SMTP_PASSWORD"].replace(" ", "")  # por si quedó algún espacio
sender = os.environ["SMTP_FROM"]
recipient = "fragajulian96@gmail.com"

msg = EmailMessage()
msg["Subject"] = "Prueba local SMTP - Módulo Habitar"
msg["From"] = sender
msg["To"] = recipient
msg.set_content("Prueba de envío SMTP desde entorno local.")

print(f"Conectando a {host}:{port} como {user}...")

if port == 465:
    with smtplib.SMTP_SSL(host, port, timeout=15) as server:
        server.login(user, password)
        server.send_message(msg)
else:
    with smtplib.SMTP(host, port, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(user, password)
        server.send_message(msg)

print("Correo enviado correctamente.")