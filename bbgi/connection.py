import psycopg2
from django.conf import settings

def get_connection():
    conn = psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )

    cursor = conn.cursor()
    return cursor