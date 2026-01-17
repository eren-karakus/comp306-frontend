import mysql.connector
from functools import wraps

def get_db_connection():
    with open("password.txt", "r") as f:
        password = f.readline().strip()

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=password,
        database="gym"
    )

def connect_first(fun):
    @wraps(fun)
    def wrapper(*args, **kwargs):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            result = fun(cursor, *args, **kwargs)
            conn.commit()
            return result
        finally:
            cursor.close()
            conn.close()
    return wrapper