from app import app
from flask import request, jsonify, render_template
from db import connect_first, get_db_connection
from auth import (
    get_user, insert_user, insert_athlete, insert_trainer,
    insert_medical, insert_staff, get_role
)
import bcrypt

@app.route("/")
def index():
    return render_template("app.html")

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data["email"]
    user = get_user(email)
    if not user:
        return jsonify({"error": "Email not found"}), 401

    password = data["password"].encode("utf-8")
    stored_hash = user["password_hash"]

    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode("utf-8")

    if not bcrypt.checkpw(password, stored_hash):
        return jsonify({"error": "Wrong password"}), 401

    user["role"] = get_role(user)
    user.pop("password_hash", None)
    return jsonify(user), 200

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    insert_user(data)
    role = data.get("role")
    if role == "athlete":
        insert_athlete(data)
    elif role == "trainer":
        insert_staff(data); insert_trainer(data)
    elif role == "medical":
        insert_staff(data); insert_medical(data)
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
    """, (athlete_id,))
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
    """, (athlete_id,))
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
        ORDER BY log_time DESC;
    """, (athlete_id,))
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
    """, (athlete_id,))
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
    """, (athlete_id,))
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
        SELECT u.first_name, u.last_name
        FROM user u
        JOIN athlete a ON u.user_id = a.athlete_id
        WHERE a.sports_branch = %s AND u.status = %s
    """
    cursor.execute(sql, (category, status))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(results)

@app.route("/api/createTrainingProgram", methods=["POST"])
@connect_first
def create_training_program(cursor):
    data = request.get_json() or {}
    name = data.get("name")
    difficulty = data.get("difficulty")
    goal = data.get("goal")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    created_by = data.get("trainer_id")

    if not name:
        return jsonify({"error": "Program name is required"}), 400

    sql = """
        INSERT INTO trainingprogram
        (program_name, difficulty_level, goal, start_date, end_date, created_by_trainer)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (name, difficulty, goal, start_date, end_date, created_by))
    return jsonify({"message": "Training program created successfully"}), 201

@app.route("/api/trainingPrograms/<int:trainer_id>", methods=["GET"])
@connect_first
def get_trainer_programs(cursor, trainer_id):
    cursor.execute("""
        SELECT
        program_id, program_name, start_date, end_date
        FROM trainingprogram
        WHERE created_by_trainer = %s
    """, (trainer_id,))
    rows = cursor.fetchall()
    return jsonify(rows), 200

@app.route("/api/athletePrograms/enrolled/<int:athlete_id>", methods=["GET"])
@connect_first
def get_enrolled_training_programs(cursor, athlete_id):
    cursor.execute("""
        SELECT
        tp.program_id, tp.program_name, tp.start_date, tp.end_date
        FROM trainingprogram tp
        NATURAL JOIN programenrollment pe
        WHERE pe.athlete_id = %s
    """, (athlete_id,))
    rows = cursor.fetchall()
    return jsonify(rows), 200


@app.route("/api/athletePrograms/notEnrolled/<int:athlete_id>", methods=["GET"])
@connect_first
def get_available_training_programs(cursor, athlete_id):
    cursor.execute("""
        SELECT
            tp.program_id,
            tp.program_name,
            tp.start_date,
            tp.end_date
        FROM trainingprogram tp
        WHERE tp.program_id NOT IN (
            SELECT program_id 
            FROM programenrollment 
            WHERE athlete_id = %s
        )
        ORDER BY tp.start_date DESC
    """, (athlete_id,))
    programs = cursor.fetchall()
    return jsonify(programs)

@app.route("/api/workoutSessions/<int:program_id>", methods=["GET"])
@connect_first
def get_workout_sessions(cursor, program_id):
    cursor.execute("""
        SELECT
        *
        FROM workoutsession
        WHERE program_id = %s
        ORDER BY (session_date) DESC
    """, (program_id,))
    rows = cursor.fetchall()
    return jsonify(rows), 200

@app.route("/api/trainer/<int:trainer_id>/athletes", methods=["GET"])
@connect_first
def get_trainer_athletes(cursor, trainer_id):
    cursor.execute("""
    SELECT DISTINCT
    u.user_id,
    u.first_name,
    u.last_name
    FROM Athlete a
    JOIN User u ON a.athlete_id = u.user_id
    JOIN ProgramEnrollment pe ON a.athlete_id = pe.athlete_id
    JOIN TrainingProgram tp ON pe.program_id = tp.program_id
    JOIN WorkoutSession ws ON tp.program_id = ws.program_id
    WHERE tp.created_by_trainer = %s;
    """, (trainer_id,))
    athletes = cursor.fetchall()
    return jsonify(athletes), 200

@app.route('/api/workoutSessions/trainer/<int:trainer_id>/athlete/<int:athlete_id>', methods=['GET'])
@connect_first
def get_athlete_workout_sessions(cursor, trainer_id, athlete_id):
    cursor.execute("""
        SELECT
        ws.session_id,
        ws.session_date,
        ws.duration
        FROM workoutsession ws
        JOIN trainingprogram tp ON ws.program_id = tp.program_id
        JOIN programenrollment pe ON tp.program_id = pe.program_id
        WHERE pe.athlete_id = %s AND tp.created_by_trainer = %s;
        """, (athlete_id, trainer_id,))
    sessions = cursor.fetchall()
    return jsonify(sessions), 200

@app.route("/api/addTrainerFeedback", methods=["POST"])
@connect_first
def add_trainer_feedback(cursor):
    data = request.get_json()
    athlete_id = data.get("athlete_id")
    trainer_id = data.get("trainer_id")
    session_id = data.get("session_id")
    comments = data.get("comments")
    rating = data.get("rating")
    
    sql = """
        INSERT INTO trainerfeedback
        (athlete_id, trainer_id, session_id, comments, rating)
        VALUES (%s, %s , %s, %s, %s)
    """
    cursor.execute(sql, (athlete_id, trainer_id, session_id, comments, rating))
    return jsonify({"message": "Trainer feedback added successfully"}), 201



@app.route("/api/addWorkoutSession", methods=["POST"])
@connect_first
def add_workout_session(cursor):
    data = request.get_json()
    program_id = data.get("program_id")
    session_date = data.get("session_date")
    duration = data.get("duration")
    intensity = data.get("intensity")

    if not program_id or not session_date:
        return jsonify({"error": "Missing parameters"}), 400

    sql = """
        INSERT INTO workoutsession
        (program_id, session_date, duration, intensity_level)
        VALUES (%s, %s , %s, %s)
    """
    cursor.execute(sql, (program_id, session_date, duration, intensity))
    return jsonify({"message": "Workout session added successfully"}), 201

@app.route("/api/enrollAthlete", methods=["POST"])
@connect_first
def enroll_athlete(cursor):
    data = request.get_json()
    athlete_id = data.get("athlete_id")
    program_id = data.get("program_id")
    
    if not athlete_id or not program_id:
        return jsonify({"error": "Missing athlete_id or program_id"}), 400
    
    # Check if already enrolled
    cursor.execute("""
        SELECT * FROM programenrollment
        WHERE athlete_id = %s AND program_id = %s 
    """, (athlete_id, program_id))
    
    if cursor.fetchone():
        return jsonify({"error": "Athlete already enrolled in this program"}), 400
    
    sql = """
        INSERT INTO programenrollment
        (athlete_id, program_id, enrollment_date, completion_status)
        VALUES (%s, %s, NOW(), 'ongoing')
    """
    cursor.execute(sql, (athlete_id, program_id))
    return jsonify({"message": "Successfully enrolled in program"}), 201

@app.route("/api/leaderboard/<int:trainer_id>", methods=["GET"])
@connect_first
def get_leaderboard(cursor, trainer_id):
    cursor.execute("""
        WITH per_prog AS (
            SELECT
                ws.program_id,
                pl.athlete_id,
                COUNT(DISTINCT pl.session_id) AS logged_sessions,
                ROUND(AVG(pl.perceived_exertion), 2) AS avg_rpe
            FROM PerformanceLog pl
            JOIN WorkoutSession ws ON ws.session_id = pl.session_id
            GROUP BY ws.program_id, pl.athlete_id
        ),
        ranked AS (
            SELECT
                *,
                RANK() OVER (
                    PARTITION BY program_id
                    ORDER BY logged_sessions DESC, avg_rpe DESC
                ) AS rnk
            FROM per_prog
        )
        SELECT
            r.program_id,
            tp.program_name,
            r.athlete_id,
            CONCAT(u.first_name, ' ', u.last_name) AS athlete_name,
            r.logged_sessions,
            r.avg_rpe,
            r.rnk
        FROM ranked r
        JOIN TrainingProgram tp ON tp.program_id = r.program_id
        JOIN User u ON u.user_id = r.athlete_id
        WHERE r.rnk <= 5 AND tp.created_by_trainer = %s
        ORDER BY r.program_id, r.rnk, r.athlete_id
    """, (trainer_id,))
    rows = cursor.fetchall()
    return jsonify(rows), 200

