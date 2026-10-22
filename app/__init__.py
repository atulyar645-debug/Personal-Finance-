from flask import Flask, app
import mysql.connector
import os
from dotenv import load_dotenv
from flask_mail import Mail
from pathlib import Path

mail = Mail()


def create_app():
    app = Flask(__name__)
    load_dotenv(
    dotenv_path=Path(__file__).resolve().parent.parent / ".env",
    override=True
    )

    app.config["MAIL_SERVER"] = os.getenv(
        "MAIL_SERVER", "smtp.gmail.com"
    )
    app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", "587"))
    app.config["MAIL_USE_TLS"] = (
        os.getenv("MAIL_USE_TLS", "True").lower() == "true"
    )
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
    app.config["MAIL_DEFAULT_SENDER"] = os.getenv(
        "MAIL_DEFAULT_SENDER", os.getenv("MAIL_USERNAME")
    )

    mail.init_app(app)

    app.config["MYSQL_HOST"] = os.getenv("MYSQL_HOST", "localhost")
    app.config["MYSQL_USER"] = os.getenv("MYSQL_USER", "root")
    app.config["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD")
    app.config["MYSQL_DATABASE"] = os.getenv("MYSQL_DATABASE", "finance_app")

    from app.routes import main
    app.register_blueprint(main)

    from app.errors import register_error_handlers
    register_error_handlers(app)

    try:
        db = mysql.connector.connect(
            host=app.config["MYSQL_HOST"],
            user=app.config["MYSQL_USER"],
            password=app.config["MYSQL_PASSWORD"],
            database=app.config["MYSQL_DATABASE"]
        )
        print("✅ MySQL connection successful!")
        db.close()
    except mysql.connector.Error as err:
        print(f"❌ MySQL connection failed: {err}")

    return app