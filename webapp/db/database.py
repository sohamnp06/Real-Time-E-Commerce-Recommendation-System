import psycopg2

from config import Config


def get_connection():
    """
    Create a new database connection using settings from Config / .env.
    """
    return psycopg2.connect(
        host=Config.DB_HOST,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
    )

