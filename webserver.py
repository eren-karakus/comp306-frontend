from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
import bcrypt
from functools import wraps

app = Flask(__name__)
CORS(app)

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


@connect_first
def get_user(cursor, email):
    sql = """
        SELECT *
        FROM user
        WHERE email = %s
    """

    cursor.execute(sql, (email, ))

    row = cursor.fetchone()
    
    if not row:
        return jsonify(False), 401
    
    return row

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
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        NOW(),
        'active'
    );"""
    
    password_hash = bcrypt.hashpw(data["signup_password"].encode("utf-8"), bcrypt.gensalt())

    cursor.execute(sql, (data["first_name"], data["last_name"], data["signup_email"], data["phone"], password_hash, data["gender"], data["date_of_birth"]))

@connect_first
def insert_athlete(cursor, data):
    user_data = get_user(data["signup_email"])

    sql = """INSERT INTO athlete (
        athlete_id,
        sports_branch
    ) VALUES (
        %s,
        %s
    );"""

    cursor.execute(sql, (user_data["user_id"], data["sports_branch"]))

@connect_first
def insert_medical(cursor, data):
    user_data = get_user(data["signup_email"])

    sql = """INSERT INTO medical (
        medical_id,
        profession,
        specialization_area
    ) VALUES (
        %s,
        %s,
        %s
    );"""

    cursor.execute(sql, (user_data["user_id"], data["profession"], data["specialization_area"]))

@connect_first
def insert_trainer(cursor, data):
    user_data = get_user(data["signup_email"])

    sql = """INSERT INTO trainer (
        trainer_id,
        specialization,
        experience_years
    ) VALUES (
        %s,
        %s,
        %s
    );"""

    cursor.execute(sql, (user_data["user_id"], data["specialization"], data["years_experience"]))

@connect_first
def insert_staff(cursor, data):
    user_data = get_user(data["signup_email"])

    sql = """INSERT INTO staff (
        staff_id
    ) VALUES (
        %s
    );"""

    cursor.execute(sql, (user_data["user_id"], ))

@connect_first
def get_role(cursor, user_data):
    roles = ["trainer", "athlete", "medical"]
    
    for role in roles:
        sql = f"""SELECT * FROM {role} WHERE {role}_id = %s"""
        cursor.execute(sql, (user_data["user_id"], ))
        
        if cursor.fetchone():
            return role

@app.route("/")
def index():
    return render_template("app.html")

@connect_first
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    email = data["email"]
    user = get_user(email)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    
    password = data["password"].encode("utf-8")
    stored_hash = user["password_hash"].encode("utf-8")

    if not bcrypt.checkpw(password, stored_hash):
        return jsonify({"error": "Invalid credentials"}), 401
    
    user["role"] = get_role(user)

    del user["password_hash"]

    return jsonify(user), 200


@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()

    insert_user(data)
    
    role = data["role"]

    if role == "athlete":
        insert_athlete(data)

    elif role == "trainer":
        insert_staff(data)
        insert_trainer(data)

    elif role == "medical":
        insert_staff(data)
        insert_medical(data)

    return jsonify({"status": "ok"})

@app.route("/api/athletes", methods=["GET"])
@connect_first
def get_athletes(cursor):
    cursor.execute("""
        SELECT 
            a.athlete_id AS id,
            CONCAT(u.first_name, ' ', u.last_name) AS name
        FROM athlete a
        JOIN user u ON u.user_id = a.athlete_id
        ORDER BY name
    """)

    athletes = cursor.fetchall()

    return jsonify(athletes), 200

@app.route("/api/measurements/<int:athlete_id>", methods=["GET"])
@connect_first
def get_measurements(cursor, athlete_id):
    cursor.execute("""
        SELECT
            measurement_date,
            height,
            weight,
            body_fat_percentage,
            muscle_mass,
            bmi
        FROM bodymeasurement
        WHERE athlete_id = %s
        ORDER BY measurement_date
    """, (athlete_id, ))

    rows = cursor.fetchall()

    return jsonify(rows)

@app.route("/api/medicalAssessments/<int:athlete_id>", methods=["GET"])
@connect_first
def get_medical_assessments(cursor, athlete_id):
    cursor.execute("""
        SELECT
            CONCAT(u.first_name, ' ', u.last_name) AS doctor,
            ma.assessment_date as date,
            ma.assessment_type as type,
            ma.notes as notes,
            ma.clearance_status as clearance
        FROM medicalassessment ma JOIN user u ON u.user_id = ma.medical_id
        WHERE athlete_id = %s
        ORDER BY assessment_date
    """, (athlete_id, ))

    rows = cursor.fetchall()

    return jsonify(rows)

@app.route("/api/lastTraining/<int:athlete_id>", methods=["GET"])
@connect_first
def get_lastTraining(cursor, athlete_id):
    cursor.execute("""
        WITH x AS (
        SELECT
            athlete_id,
            exercise_id,
            exercise_name,
            weight_used,
            completed_sets,
            completed_reps,
            perceived_exertion,
            log_time,
            ROW_NUMBER() OVER (
            PARTITION BY athlete_id, exercise_id
            ORDER BY log_time DESC
            ) AS rn
        FROM v_log_enriched
        )
        SELECT *
        FROM x
        WHERE rn = 1 AND athlete_id = %s
        ORDER BY athlete_id, exercise_id;
    """, (athlete_id, ))

    rows = cursor.fetchall()

    return jsonify(rows)

@app.route("/api/sessionAdherence/<int:athlete_id>", methods=["GET"])
@connect_first
def get_sessionAdherence(cursor, athlete_id):
    cursor.execute("""
    SELECT
        pl.athlete_id,
        pl.session_id,
        ws.session_date,
        ROUND(100 * SUM(pl.completed_sets) / NULLIF(SUM(se.planned_sets), 0), 2) AS percentage_sets_done,
        ROUND(100 * SUM(pl.completed_reps) / NULLIF(SUM(se.planned_reps), 0), 2) AS percentage_reps_done,
        ROUND(AVG(pl.perceived_exertion), 2) AS average_rate_of_perceived_exertion
    FROM PerformanceLog pl
    JOIN SessionExercise se
    ON se.session_id = pl.session_id AND se.exercise_id = pl.exercise_id
    JOIN WorkoutSession ws
    ON ws.session_id = pl.session_id
    WHERE athlete_id = %s
    GROUP BY pl.athlete_id, pl.session_id, ws.session_date
    ORDER BY ws.session_date DESC, pl.athlete_id;
    """, (athlete_id, ))

    rows = cursor.fetchall()

    return jsonify(rows)

@app.route("/api/topThreeExercises/<int:athlete_id>", methods=["GET"])
@connect_first
def get_topThreeExercises(cursor, athlete_id):
    cursor.execute("""
    WITH vol AS (
    SELECT
        athlete_id,
        exercise_id,
        exercise_name,
        ROUND(SUM(completed_sets * completed_reps * IFNULL(weight_used, 0)), 2) AS total_volume
    FROM v_log_enriched
    GROUP BY athlete_id, exercise_id, exercise_name
    ),
    ranked AS (
    SELECT
        *,
        DENSE_RANK() OVER (
        PARTITION BY athlete_id
        ORDER BY total_volume DESC
        ) AS rnk
    FROM vol
    )
    SELECT athlete_id, exercise_id, exercise_name, total_volume, rnk
    FROM ranked
    WHERE rnk <= 3 AND athlete_id = %s
    ORDER BY athlete_id, rnk, total_volume DESC;
    """, (athlete_id, ))

    rows = cursor.fetchall()

    return jsonify(rows)

@app.route("/api/addMedicalExam", methods=["POST"])
@connect_first
def addMedicalExam(cursor):
    data = request.get_json()

    sql = """
        INSERT INTO medicalassessment
        (athlete_id, medical_id, assessment_date, assessment_type, notes, clearance_status)
        VALUES (%s, %s, NOW(), %s, %s, %s)
    """

    cursor.execute(sql, (
        data["athlete_id"],
        data["medical_id"],
        data["assessment_type"],
        data["notes"],
        data["clearance_status"]
    ))

    return jsonify({"message": "Medical exam submitted successfully"}), 201

@app.route("/query", methods=["POST"])
def query():
    data = request.get_json()

    category = data.get("category")
    status = data.get("status")

    if not category or not status:
        return jsonify({"error": "Missing parameters"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT first_name, last_name
        FROM athlete
        WHERE user_id == 100 OR user_id == 99
    """
    
    cursor.execute(sql, (category, status))
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(results)

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
