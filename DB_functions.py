import psycopg2
from psycopg2 import pool
from datetime import datetime, timezone
import os

database_url = os.environ.get('DATABASE_URL')

'''
result = urllib.parse.urlparse(database_url)

db_pool = pool.SimpleConnectionPool(
    1, 10,
    user=result.username,
    password=result.password,
    host=result.hostname,
    port=result.port,
    dbname=result.path.lstrip('/')
)'''

'''db_pool = pool.SimpleConnectionPool(
    1, 10,
    dbname="postgres",
    user="abdulrahman",
    password="99628662",
    host="localhost",
    port=5432
)'''

db_pool = pool.SimpleConnectionPool(
    1, 10,
    dsn=database_url
)


def user_id(email):
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s;", (email,))
        result = cursor.fetchone()
        print(f"this is the user id according to the db {result[0]}")
        cursor.close()
        return result[0]  # True if user exists
    finally:
        db_pool.putconn(conn)


# tables
def create_table():
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS userrs (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    finally:
        cursor.close()
        db_pool.putconn(conn)


def save_user_email(email):
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO userrs (email)
                VALUES (%s)
                ON CONFLICT (email)
                DO NOTHING
            """, (email,))

            conn.commit()
    except Exception as e:
        conn.rollback()
        return None
    finally:
        db_pool.putconn(conn)




def print_all_user_data():
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM userrs;")
        users = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        cursor.close()

        if users:
            print("All Users:")
            for user in users:
                user_data = dict(zip(column_names, user))
                for key, value in user_data.items():
                    print(f"{key}: {value}")
                print("-" * 20)  # separator between users
            return users
        else:
            print("No users found.")
            return []

    finally:
        db_pool.putconn(conn)

def count_users():
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM userrs;")
            count = cursor.fetchone()[0]
            print(f"There are currently {count} user(s) in the database.")
            return count
    finally:
        db_pool.putconn(conn)
def print_users():
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users;")
        for row in cursor.fetchall():
            print(row)
        cursor.close()
    finally:
        db_pool.putconn(conn)
