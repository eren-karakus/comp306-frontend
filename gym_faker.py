import itertools
from faker import Faker
import random
from datetime import date, datetime, timedelta
import bcrypt

# Faker
fake = Faker()
Faker.seed(306) # Remove for random data
random.seed(306) # Remove for random data

# Output file
OUTPUT_FILE = 'insertion_queries.txt'

# Configuration
NUM_USERS = 100
NUM_ATHLETES = 60
NUM_STAFF = 40
NUM_TRAINERS = 15
NUM_MEDICAL = 25
NUM_PROGRAMS = 20
NUM_EXERCISES = 30 #Currently maxed at 30 exercises, requries manual addition for more
NUM_SESSIONS_PER_PROGRAM = 10

def escape_string(s):
    if s is None:
        return 'NULL'
    if isinstance(s, str):
        return "'" + s.replace("'", "''").replace("\\", "\\\\") + "'"
    return str(s)

def format_value(val):
    if val is None:
        return 'NULL'
    elif isinstance(val, str):
        return escape_string(val)
    elif isinstance(val, datetime):
        return f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'"
    elif isinstance(val, date):
        return f"'{val.strftime('%Y-%m-%d')}'"
    elif isinstance(val, timedelta):
        return f"'{val}'"
    else:
        return str(val)

def write_insert(output_file, table, columns, values_list):
    if not values_list:
        return
    output_file.write(f"INSERT INTO {table} ({', '.join(columns)}) VALUES \n")
    
    for i, values in enumerate(values_list):
        formatted_values = ', '.join(format_value(v) for v in values)
        
        output_file.write(f"({formatted_values})")
        if i < len(values_list) - 1:
            output_file.write(",\n")
        else:
            output_file.write(";\n\n")

def fake_business_datetime():
    dt = fake.date_time_between(start_date="-6M", end_date="now")
    
    business_hour = random.randint(8, 16) 
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    
    return dt.replace(hour=business_hour, minute=minute, second=second)

def generate_users(output_file, n):
    users = []
    
    pw_hash = bcrypt.hashpw('123456'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    for i in range(1, n + 1):
        gender = random.choice(['male', 'female', 'other'])
        first_name = fake.first_name()
        last_name = fake.last_name()
        date_of_birth = fake.date_time_between(start_date='-65y', end_date='-18y')
        registration_datetime = fake_business_datetime()
        user = (
            i,
            first_name,
            last_name,
            first_name.lower() + '.' + last_name.lower() + str(date_of_birth.year)[2:] + '@' + fake.free_email_domain(),
            fake.unique.phone_number()[:20],
            pw_hash,
            gender,
            date_of_birth,
            registration_datetime,
            random.choice(['active', 'inactive'])
        )
        users.append(user)
    
    write_insert(output_file, '`User`', ['user_id', 'first_name', 'last_name', 'email', 'phone', 'password_hash', 'gender', 'date_of_birth', 'registration_date', 'status'], users)
    return [u[0] for u in users]

def generate_athletes(output_file, user_ids, n):
    selected_users = random.sample(user_ids, n)
    
    sports = ['Basketball', 'Football', 'Swimming', 'Track and Field', 'Tennis', 'Volleyball', 'Boxing', 'Wrestling', 'Gymnastics', 'Cycling']
    
    athletes = [(user_id, random.choice(sports)) for user_id in selected_users]
    
    write_insert(output_file, 'Athlete', ['athlete_id', 'sports_branch'], athletes)
    return selected_users

def generate_staff(output_file, user_ids, athlete_ids, n):
    available_users = [uid for uid in user_ids if uid not in athlete_ids]
    selected_users = random.sample(available_users, n)
    
    staff = [
        (user_id, 
         fake.date_between(start_date='-5y', end_date='today'),
         round(random.uniform(30000, 80000), 2),
         random.choice(['full-time', 'part-time']))
        for user_id in selected_users
    ]
    
    write_insert(output_file, 'Staff', ['staff_id', 'hire_date', 'salary', 'employment_type'], staff)
    return selected_users

def generate_trainers(output_file, staff_ids, n):
    selected_staff = random.sample(staff_ids, n)
    specializations = ['Strength Training', 'Cardio', 'CrossFit', 'Olympic Lifting', 'Sports Performance', 'Rehabilitation', 'Nutrition', 'HIIT']
    trainers = [
        (staff_id, random.choice(specializations), random.randint(1, 15))
        for staff_id in selected_staff
    ]
    write_insert(output_file, 'Trainer', ['trainer_id', 'specialization', 'experience_years'], trainers)
    return selected_staff

def generate_medical(output_file, staff_ids, trainer_ids, n):
    available_staff = [sid for sid in staff_ids if sid not in trainer_ids]
    selected_staff = random.sample(available_staff, n)
    
    professions = {
        'doctor': ['Sports Medicine', 'Orthopedics', 'General Practice'],
        'physiotherapist': ['Sports Rehabilitation', 'Manual Therapy', 'Injury Prevention'],
        'dietitian': ['Sports Nutrition', 'Weight Management', 'Performance Nutrition']
    }
    
    medical = []
    for staff_id in selected_staff:
        profession = random.choice(list(professions.keys()))
        specialization = random.choice(professions[profession])
        medical.append((staff_id, profession, specialization))
    
    write_insert(output_file, 'Medical', ['medical_id', 'profession', 'specialization_area'], medical)
    return selected_staff

def generate_training_programs(output_file, trainer_ids, n):
    program_names = [
        'Strength Building Phase', 'Endurance Training', 'Power Development', 'Speed and Agility', 'Muscle Hypertrophy', 'Fat Loss Program', 
        'Athletic Performance', 'Functional Fitness', 'Olympic Prep', 'Off-Season Conditioning', 'Pre-Season Training', 'Competition Prep']
    programs = []
    for i in range(1, n + 1):
        start_date = fake.date_between(start_date='-6M', end_date='today')
        end_date = start_date + timedelta(days=random.randint(30, 120))
        
        program = (
            i,
            random.choice(program_names),
            random.choice(['beginner', 'intermediate', 'advanced']),
            fake.text(max_nb_chars=200),
            start_date,
            end_date,
            random.choice(trainer_ids)
        )
        programs.append(program)
    
    write_insert(output_file, 'TrainingProgram', ['program_id', 'program_name', 'difficulty_level', 'goal', 'start_date', 'end_date', 'created_by_trainer'], programs)

    return [p[0] for p in programs]

def generate_program_enrollments(output_file, athlete_ids, program_ids):
    enrollments = []
    for athlete_id in athlete_ids:
        num_programs = random.randint(1, 3)
        selected_programs = random.sample(program_ids, min(num_programs, len(program_ids)))
        
        for program_id in selected_programs:
            enrollment = (
                athlete_id,
                program_id,
                fake.date_between(start_date='-6M', end_date='today'),
                random.choice(['ongoing', 'completed', 'dropped'])
            )
            enrollments.append(enrollment)
    
    write_insert(output_file, 'ProgramEnrollment', ['athlete_id', 'program_id', 'enrollment_date', 'completion_status'], enrollments)

def generate_exercises(output_file, n):
    exercises_data = [
        ('Dips', 'Strength', 'Parallel Bars', 'medium'),
        ('Turkish Get-Up', 'Strength', 'Kettlebell', 'hard'),
        ('Running', 'Cardio', 'Treadmill', 'easy'),
        ('Dead Bug', 'Core', 'None', 'easy'),
        ('Box Jumps', 'Plyometrics', 'Plyo Box', 'medium'),
        ('Hanging Leg Raises', 'Core', 'Pull-up Bar', 'medium'),
        ('Sled Push', 'Conditioning', 'Prowler Sled', 'hard'),
        ('Lateral Raises', 'Strength', 'Dumbbells', 'easy'),
        ('Rowing', 'Cardio', 'Rowing Machine', 'medium'),
        ('Pistol Squat', 'Strength', 'None', 'hard'),
        ('Incline Bench Press', 'Strength', 'Barbell, Incline Bench', 'medium'),
        ('Calf Raises', 'Strength', 'Step', 'easy'),
        ('Burpees', 'Cardio', 'None', 'hard'),
        ('Kettlebell Swings', 'Strength', 'Kettlebell', 'medium'),
        ('Battle Ropes', 'Cardio', 'Ropes', 'medium'),
        ('Shadow Boxing', 'Cardio', 'None', 'medium'),
        ('Superman', 'Core', 'None', 'easy'),
        ('Preacher Curls', 'Strength', 'EZ Bar, Preacher Bench', 'easy'),
        ('Thrusters', 'Strength', 'Barbell', 'hard'),
        ('Wall Sits', 'Strength', 'Wall', 'easy'),
        ('Pull-ups', 'Strength', 'Pull-up Bar', 'medium'),
        ('Face Pulls', 'Strength', 'Cable Machine, Rope', 'easy'),
        ('Assault Bike', 'Cardio', 'Fan Bike', 'hard'),
        ('Russian Twists', 'Core', 'Medicine Ball', 'easy'),
        ('Snatch', 'Olympic Lifting', 'Barbell', 'hard'),
        ('Hammer Curls', 'Strength', 'Dumbbells', 'easy'),
        ('Ab Wheel Rollouts', 'Core', 'Ab Wheel', 'hard'),
        ('Barbell Squat', 'Strength', 'Barbell, Rack', 'hard'),
        ('Mountain Climbers', 'Cardio', 'None', 'easy'),
        ('T-Bar Row', 'Strength', 'Barbell, Landmine', 'medium')
    ]
    
    exercises = []
    for i in range(1, n+1):
        ex = (i,) + exercises_data[i-1]
        exercises.append(ex)

    write_insert(output_file, 'Exercise', ['exercise_id', 'exercise_name', 'type', 'equipment_required', 'difficulty'], exercises)
    return [e[0] for e in exercises]

def generate_workout_sessions(output_file, program_ids):
    sessions = []
    session_id = 1
    for program_id in program_ids:
        for i in range(NUM_SESSIONS_PER_PROGRAM):
            session = (
                session_id,
                program_id,
                fake.date_between(start_date='-6M', end_date='today'),
                random.randint(30, 120),
                random.choice(['low', 'medium', 'high'])
            )
            sessions.append(session)
            session_id += 1
    
    write_insert(output_file, 'WorkoutSession', ['session_id', 'program_id', 'session_date', 'duration', 'intensity_level'], sessions)
    return [s[0] for s in sessions]

def generate_session_exercises(output_file, session_ids, exercise_ids):
    session_exercises = []
    for session_id in session_ids:
        num_exercises = random.randint(4, 8)
        selected_exercises = random.sample(exercise_ids, min(num_exercises, len(exercise_ids)))
        
        for exercise_id in selected_exercises:
            se = (
                session_id,
                exercise_id,
                random.randint(3, 5),
                random.randint(8, 15),
                random.randint(30, 120)
            )
            session_exercises.append(se)
    
    write_insert(output_file, 'SessionExercise', ['session_id', 'exercise_id', 'planned_sets', 'planned_reps', 'rest_duration'], session_exercises)
    return session_exercises

def generate_performance_logs(output_file, athlete_ids, session_exercises):
    se_dict = {}
    for se in session_exercises:
        session_id, exercise_id, planned_sets, planned_reps = se[0], se[1], se[2], se[3]
        se_dict.setdefault(session_id, []).append((exercise_id, planned_sets, planned_reps))
    
    candidates = []
    for athlete_id in athlete_ids:
        for session_id, exercises in se_dict.items():
            for exercise_id, planned_sets, planned_reps in exercises:
                candidates.append((athlete_id, session_id, exercise_id, planned_sets, planned_reps))

    random.shuffle(candidates)
    max_logs = min(500, len(athlete_ids) * 8, len(candidates))
    selected_candidates = candidates[:max_logs]

    logs = []
    for athlete_id, session_id, exercise_id, planned_sets, planned_reps in selected_candidates:
        log = (
            athlete_id,
            session_id,
            exercise_id,
            random.randint(max(1, planned_sets - 1), planned_sets),
            random.randint(max(1, planned_reps - 3), planned_reps + 2),
            round(random.uniform(10, 200), 2),
            random.randint(1, 10),
            fake_business_datetime()
        )
        logs.append(log)

    write_insert(output_file, 'PerformanceLog', ['athlete_id', 'session_id', 'exercise_id', 'completed_sets', 'completed_reps', 'weight_used', 'perceived_exertion', 'log_time'], logs)

def generate_body_measurements(output_file, athlete_ids):
    measurements = []
    for athlete_id in athlete_ids:
        num_measurements = random.randint(2, 5)
        height = round(random.uniform(150, 200), 2)
        weight = round(random.uniform(50, 120), 2)
        body_fat = round(random.uniform(8, 30), 2)
        muscle_mass = round(random.uniform(30, 70), 2)
        bmi = round(weight / ((height / 100) ** 2), 2)
        
        seen_dates = set()
        for i in range(num_measurements):
            measurement_date = fake.date_between(start_date='-1y', end_date='today')
            while measurement_date in seen_dates:
                measurement_date = fake.date_between(start_date='-1y', end_date='today')
            seen_dates.add(measurement_date)

            height = round((height + random.uniform(-0.5, 0.5)), 2)
            weight = round((weight + random.uniform(-2, 2)), 2)
            body_fat = round((body_fat + random.uniform(-1, 1)), 2)
            muscle_mass = round((muscle_mass + random.uniform(-1, 1)), 2)
            bmi = round(weight / ((height / 100) ** 2), 2)

            measurements.append((athlete_id, measurement_date, height, weight, body_fat, muscle_mass, bmi))
    
    write_insert(output_file, 'BodyMeasurement', ['athlete_id', 'measurement_date', 'height', 'weight', 'body_fat_percentage', 'muscle_mass', 'bmi'], measurements)

def generate_medical_assessments(output_file, athlete_ids, medical_ids):
    assessment_types = ['Physical Examination', 'Injury Assessment', 'Clearance Check', 'Nutritional Consultation', 'Recovery Assessment']
    
    assessments = []
    for athlete_id in athlete_ids:
        num_assessments = random.randint(1, 3)
        for i in range(num_assessments):
            assessment = (
                athlete_id,
                random.choice(medical_ids),
                fake.date_between(start_date='-6M', end_date='today'),
                random.choice(assessment_types),
                fake.text(max_nb_chars=300),
                random.choice(['cleared', 'restricted', 'not_cleared'])
            )
            assessments.append(assessment)
    
    write_insert(output_file, 'MedicalAssessment', ['athlete_id', 'medical_id', 'assessment_date','assessment_type', 'notes', 'clearance_status'], assessments)

def generate_trainer_feedback(output_file, trainer_ids, athlete_ids, session_ids):
    feedback_list = []
    keys = list(itertools.product(trainer_ids, athlete_ids, session_ids))
    sample_size = min(200, len(keys))
    selected_keys = random.sample(keys, sample_size)

    for trainer_id, athlete_id, session_id in selected_keys:
        feedback = (
            trainer_id,
            athlete_id,
            session_id,
            random.randint(1, 5),
            fake.text(max_nb_chars=200)
        )
        feedback_list.append(feedback)

    write_insert(output_file, 'TrainerFeedback', ['trainer_id', 'athlete_id', 'session_id', 'rating', 'comments'], feedback_list)

def main():
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as output_file:
            user_ids = generate_users(output_file, NUM_USERS)
            athlete_ids = generate_athletes(output_file, user_ids, NUM_ATHLETES)
            staff_ids = generate_staff(output_file, user_ids, athlete_ids, NUM_STAFF)
            trainer_ids = generate_trainers(output_file, staff_ids, NUM_TRAINERS)
            medical_ids = generate_medical(output_file, staff_ids, trainer_ids, NUM_MEDICAL)
            program_ids = generate_training_programs(output_file, trainer_ids, NUM_PROGRAMS)
            generate_program_enrollments(output_file, athlete_ids, program_ids)
            exercise_ids = generate_exercises(output_file, NUM_EXERCISES)
            session_ids = generate_workout_sessions(output_file, program_ids)
            session_exercises = generate_session_exercises(output_file, session_ids, exercise_ids)
            generate_performance_logs(output_file, athlete_ids, session_exercises)
            generate_body_measurements(output_file, athlete_ids)
            generate_medical_assessments(output_file, athlete_ids, medical_ids)
            generate_trainer_feedback(output_file, trainer_ids, athlete_ids, session_ids)
            print(f"Data generation complete. SQL queries written to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Error occurred: {e}")
        
if __name__ == "__main__":
    main()
