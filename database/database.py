import psycopg2

def get_connection():

    conn = psycopg2.connect(
        host="localhost",
        database="ecommerce_db",
        user="postgres",
        password="root"
    )

    return conn