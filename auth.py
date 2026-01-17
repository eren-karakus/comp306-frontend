from db import connect_first
import bcrypt

@connect_first
def get_user(cursor, email):
    sql = "SELECT * FROM user WHERE email = %s"
    cursor.execute(sql, (email,))
    return cursor.fetchone()

@connect_first
def insert_user(cursor, data):
    sql = """INSERT INTO user (
        first_name,
        last_name,
        email,
        phone,
        password_hash,
        gender,
        date_of_birth,
        registration_date,
        status
    ) VALUES (
        %s,%s,%s,%s,%s,%s,%s,NOW(),'active'
    );"""
    password_hash = bcrypt.hashpw(data["signup_password"].encode("utf-8"), bcrypt.gensalt())
    cursor.execute(sql, (
        data["first_name"],
        data["last_name"],
        data["signup_email"],
        data["phone"],
        password_hash,
        data["gender"],
        data["date_of_birth"]
    ))

@connect_first
def insert_athlete(cursor, data):
    user_data = get_user(data["signup_email"])
    sql = "INSERT INTO athlete (athlete_id, sports_branch) VALUES (%s, %s);"
    cursor.execute(sql, (user_data["user_id"], data["sports_branch"]))

@connect_first
def insert_medical(cursor, data):
    user_data = get_user(data["signup_email"])
    sql = "INSERT INTO medical (medical_id, profession, specialization_area) VALUES (%s, %s, %s);"
    cursor.execute(sql, (user_data["user_id"], data["profession"], data["specialization_area"]))

@connect_first
def insert_trainer(cursor, data):
    user_data = get_user(data["signup_email"])
    sql = "INSERT INTO trainer (trainer_id, specialization, experience_years) VALUES (%s, %s, %s);"
    cursor.execute(sql, (user_data["user_id"], data["specialization"], data["years_experience"]))

@connect_first
def insert_staff(cursor, data):
    user_data = get_user(data["signup_email"])
    sql = "INSERT INTO staff (staff_id) VALUES (%s);"
    cursor.execute(sql, (user_data["user_id"],))

@connect_first
def get_role(cursor, user_data):
    roles = ["trainer", "athlete", "medical"]
    for role in roles:
        sql = f"SELECT 1 FROM {role} WHERE {role}_id = %s"
        cursor.execute(sql, (user_data["user_id"],))
        if cursor.fetchone():
            return role
    return None