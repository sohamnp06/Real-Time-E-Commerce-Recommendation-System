import os

from dotenv import load_dotenv


# Load variables from a local .env file into the environment.
# .env itself is git-ignored; see .env.example for documented keys.
load_dotenv()


class Config:
    """Central application configuration loaded from environment variables."""

    # Flask / session
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME", "ecommerce_db")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
