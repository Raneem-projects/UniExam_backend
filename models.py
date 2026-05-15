from extensions import db
from datetime import datetime


# ======================
# Exam
# ======================
class Exam(db.Model):
    __tablename__ = "exam"

    exam_id = db.Column(db.String, primary_key=True)
    title = db.Column(db.String)
    course_code = db.Column(db.String)
    instructor = db.Column(db.String)
    duration_minutes = db.Column(db.Integer)
    total_marks = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ======================
# Session
# ======================
class Session(db.Model):
    __tablename__ = "sessions"

    session_id = db.Column(db.Integer, primary_key=True)

    exam_id = db.Column(
        db.String,
        db.ForeignKey("exam.exam_id"),
        nullable=False
    )

    session_pin = db.Column(db.String(6), unique=True, nullable=False)

    title = db.Column(db.String)
    course_code = db.Column(db.String)
    instructor = db.Column(db.String)

    duration_minutes = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    total_marks = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)


# ======================
# Question
# ======================
class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)

    exam_id = db.Column(
        db.String,
        db.ForeignKey("exam.exam_id"),
        nullable=False
    )

    question_id = db.Column(db.Integer, nullable=False)

    type = db.Column(db.String, nullable=False)
    text = db.Column(db.Text, nullable=False)

    marks = db.Column(db.Integer, nullable=False)

    options = db.Column(db.JSON)
    correct_answer = db.Column(db.String)

    page_number = db.Column(db.Integer)


# ======================
# Submission
# ======================
class Submission(db.Model):
    __tablename__ = "submissions"

    submission_id = db.Column(db.String, primary_key=True)

    exam_id = db.Column(
        db.String,
        db.ForeignKey("exam.exam_id")
    )

    session_id = db.Column(
        db.Integer,
        db.ForeignKey("sessions.session_id")
    )

    student_name = db.Column(db.String)
    student_id = db.Column(db.String)

    pdf_path = db.Column(db.String)

    submitted_at = db.Column(db.DateTime)

    mcq_score = db.Column(db.Float, default=0)
    essay_score = db.Column(db.Float, default=0)

    total_score = db.Column(db.Float, default=0)

    total_grade = db.Column(db.Float, default=0)

    time_taken = db.Column(db.Integer)

    grading_status = db.Column(db.String, default="pending")


# ======================
# Student
# ======================
class Student(db.Model):
    __tablename__ = "students"

    student_id = db.Column(db.String, primary_key=True)

    student_name = db.Column(db.String)

    exam_id = db.Column(
        db.String,
        db.ForeignKey("exam.exam_id")
    )

    device_id = db.Column(db.String)

    submitted_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# ======================
# Answer
# ======================
class Answer(db.Model):
    __tablename__ = "answers"

    id = db.Column(db.Integer, primary_key=True)

    submission_id = db.Column(
        db.String,
        db.ForeignKey("submissions.submission_id"),
        nullable=False
    )

    exam_id = db.Column(
        db.String,
        db.ForeignKey("exam.exam_id")
    )

    student_id = db.Column(
        db.String,
        db.ForeignKey("students.student_id")
    )

    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.question_id")
    )

    type = db.Column(db.String)

    selected_option = db.Column(db.String)

    answer_image = db.Column(db.String)

    answer_text = db.Column(db.Text)

    is_correct = db.Column(db.Boolean)

    marks_obtained = db.Column(db.Integer, default=0)

    marks_available = db.Column(db.Integer)