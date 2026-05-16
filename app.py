from datetime import datetime
import uuid
import os
import io

from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
from flask_cors import CORS

from supabase import create_client

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from parser import exam_json_to_db, parse_exam_pdf_to_json


# ======================
# App Setup
# ======================
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ======================
# Supabase Setup
# ======================
SUPABASE_URL = "https://yvwtsebueljtuimhytwp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl2d3RzZWJ1ZWxqdHVpbWh5dHdwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg4MzcyMDEsImV4cCI6MjA5NDQxMzIwMX0.oIXJ2CjW00DpGcv5FfXj-j2CtcH_fopqSX5Q8O0hkMM"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ======================
# Pages
# ======================
@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "1234":
            return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    exams = supabase.table("Exam").select("*").execute().data or []
    return render_template("dashboard.html", exams=exams)


@app.route("/create_session_page")
def create_session_page():
    exam_id = request.args.get("exam_id")
    return render_template("create_session.html", exam_id=exam_id)


@app.route("/create_exam_page")
def create_exam_page():
    return render_template("upload_exam.html")



@app.route("/submissions_page")
def submissions_page():
    exam_id = request.args.get("exam_id")

    exam = supabase.table("Exam") \
        .select("*") \
        .eq("exam_id", exam_id) \
        .execute().data

    submissions = supabase.table("Submission") \
        .select("*") \
        .eq("exam_id", exam_id) \
        .execute().data

    exam = exam[0] if exam else None

    return render_template(
        "submissions.html",
        exam=exam,
        submissions=submissions
    )


# ======================
# API - Exams
# ======================
@app.route("/api/doctor/exams")
def get_exams():

    exams = supabase.table("Exam").select("*").execute().data or []
    result = []

    for e in exams:

        subs = supabase.table("Submission").select("*").eq("exam_id", e["exam_id"]).execute().data or []

        total_students = len(subs)
        graded = len([s for s in subs if s.get("grading_status") == "completed"])

        result.append({
            "exam_id": e["exam_id"],
            "title": e["title"],
            "course_code": e["course_code"],
            "instructor": e["instructor"],
            "duration_minutes": e["duration_minutes"],
            "total_marks": e["total_marks"],
            "total_students": total_students,
            "status": "Graded" if graded == total_students and total_students > 0 else "Pending"
        })

    return jsonify(result)


# ======================
# Create Session
# ======================
@app.route("/api/create-session", methods=["POST"])
def create_session():

    data = request.get_json()
    exam_id = data.get("exam_id")

    exam = supabase.table("Exam").select("*").eq("exam_id", exam_id).execute().data
    if not exam:
        return jsonify({"error": "Exam not found"}), 404

    exam = exam[0]

    pin = "".join([str(uuid.uuid4().int)[:6]])

    supabase.table("Session").insert({
        "exam_id": exam_id,
        "session_pin": pin,
        "title": exam["title"],
        "course_code": exam["course_code"],
        "instructor": exam["instructor"],
        "duration_minutes": exam["duration_minutes"],
        "total_marks": exam["total_marks"],
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    return jsonify({"session_pin": pin})


@app.route("/session/<exam_id>")
def session_page(exam_id):
    exam = supabase.table("Exam").select("*").eq("exam_id", exam_id).execute().data
    return render_template("create_session.html", exam=exam)


# ======================
# Submissions API
# ======================
@app.route("/api/doctor/exam/<exam_id>/submissions")
def get_submissions(exam_id):

    subs = supabase.table("Submission").select("*").eq("exam_id", exam_id).execute().data

    data = []
    for s in subs:
        data.append({
            "section": s.get("section"),
            "student_id": s.get("student_id"),
            "mcq_score": s.get("mcq_score"),
            "total_score": s.get("total_grade"),
            "submitted_at": s.get("submitted_at")
        })

    return jsonify(data)


# ======================
# # Upload PDF
# ======================
@app.route("/api/doctor/upload-pdf", methods=["POST"])
def upload_pdf():

    if "pdf" not in request.files:
        return jsonify({"error": "No file"}), 400

    file = request.files["pdf"]
    filename = file.filename

    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    exam_json = parse_exam_pdf_to_json(save_path)
    exam_id = exam_json_to_db(exam_json)

    return jsonify({"status": "success", "exam_id": exam_id})


# ======================
# Student verify PIN
# ======================
@app.route("/api/student/verify-pin", methods=["POST"])
def verify_pin():

    data = request.get_json()

    pin = data.get("session_pin")
    student_name = data.get("student_name", "")
    device_id = data.get("device_id", "")

    session = supabase.table("Session").select("*").eq("session_pin", pin).eq("is_active", True).execute().data

    if not session:
        return jsonify({"status": "error", "message": "Invalid PIN"}), 404

    session = session[0]

    student_id = f"STU-{uuid.uuid4().hex[:6].upper()}"

    supabase.table("Student").insert({
        "student_id": student_id,
        "student_name": student_name,
        "exam_id": session["exam_id"],
        "device_id": device_id
    }).execute()

    exam = supabase.table("Exam").select("*").eq("exam_id", session["exam_id"]).execute().data[0]

    return jsonify({
        "status": "success",
        "exam_id": exam["exam_id"],
        "student_id": student_id,
        "exam_title": exam["title"],
        "duration_minutes": exam["duration_minutes"]
    })


# ======================
# Get Exam
# ======================
@app.route("/api/student/get_exam/<exam_id>")
def student_get_exam(exam_id):

    session = supabase.table("Session").select("*").eq("exam_id", exam_id).eq("is_active", True).execute().data
    if not session:
        return jsonify({"error": "No active session"}), 404

    session = session[0]

    exam = supabase.table("Exam").select("*").eq("exam_id", exam_id).execute().data[0]
    questions = supabase.table("Question").select("*").eq("exam_id", exam_id).execute().data

    return jsonify({
        "exam_id": exam["exam_id"],
        "title": exam["title"],
        "session_pin": session["session_pin"],
        "duration_minutes": exam["duration_minutes"],
        "total_marks": exam["total_marks"],
        "questions": questions
    })


# ======================
# Submit Exam
# ======================
@app.route("/api/student/submit_exam", methods=["POST"])
def student_submit_exam():

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data"}), 400

        section = data.get("section")
        session_pin = data.get("session_pin")
        student_id = data.get("student_id")
        exam_id = data.get("exam_id")
        answers = data.get("answers", [])

       
        session = supabase.table("Session") \
            .select("*") \
            .eq("session_pin", session_pin) \
            .eq("is_active", True) \
            .execute().data

        if not session:
            return jsonify({"error": "Invalid session"}), 404

        session = session[0]

       
        submission_id = f"SUB-{uuid.uuid4().hex[:8]}"

        mcq_score = 0

        
        supabase.table("Submission").insert({
            "submission_id": submission_id,
            "exam_id": exam_id,
            "session_id": session["session_id"],
            "student_id": student_id,
            "student_name": student_id + " | Sec:" + str(section),
            "section": section,
            "mcq_score": 0,
            "total_grade": 0,
            "grading_status": "completed",
            "submitted_at": datetime.utcnow().isoformat()
        }).execute()

        
        for ans in answers:

            q = supabase.table("Question") \
                .select("*") \
                .eq("question_id", ans["question_id"]) \
                .eq("exam_id", exam_id) \
                .execute().data

            if not q:
                continue

            q = q[0]

            marks = 0

            #MCQ AUTO GRADING
            if q["type"] in ["mcq", "true_false"]:
                if (ans.get("selected_option") or "").strip().upper() == \
                   (q.get("correct_answer") or "").strip().upper():

                    marks = q["marks"]
                    mcq_score += marks

            supabase.table("Answer").insert({
                "submission_id": submission_id,
                "exam_id": exam_id,
                "student_id": student_id,
                "question_id": ans["question_id"],
                "selected_option": ans.get("selected_option"),
                "answer_text": ans.get("answer_text"),
                "marks_obtained": marks
            }).execute()

        supabase.table("Submission") \
            .update({
                "mcq_score": mcq_score,
                "total_grade": mcq_score
            }) \
            .eq("submission_id", submission_id) \
            .execute()

        return jsonify({
            "status": "success",
            "submission_id": submission_id,
            "mcq_score": mcq_score
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ======================
# Result
# ======================
@app.route("/api/student/result/<submission_id>")
def student_result(submission_id):

    sub = supabase.table("Submission").select("*").eq("submission_id", submission_id).execute().data

    if not sub:
        return jsonify({"error": "Not found"}), 404

    sub = sub[0]

    return jsonify({
        "student_name": sub.get("student_name"),
        "section": sub.get("section"), 
        "total_grade": sub.get("total_grade"),
        "status": sub.get("grading_status")
    })


# ======================
# Delete Exam
# ======================
@app.route("/api/doctor/delete_exam/<exam_id>", methods=["DELETE"])
def delete_exam(exam_id):
    try:
        supabase.table("Answer").delete().eq("exam_id", exam_id).execute()
        supabase.table("Submission").delete().eq("exam_id", exam_id).execute()
        supabase.table("Student").delete().eq("exam_id", exam_id).execute()
        supabase.table("Session").delete().eq("exam_id", exam_id).execute()
        supabase.table("Question").delete().eq("exam_id", exam_id).execute()
        supabase.table("Exam").delete().eq("exam_id", exam_id).execute()

        return jsonify({"status": "deleted"})
    
    except Exception as e:
        print("DELETE ERROR:", e)   
        return jsonify({"error": str(e)}), 500


# ======================
# Delete Submission
# ======================
@app.route("/api/doctor/delete_submission/<submission_id>", methods=["DELETE"])
def delete_submission(submission_id):

    supabase.table("Answer").delete().eq("submission_id", submission_id).execute()
    supabase.table("Submission").delete().eq("submission_id", submission_id).execute()

    return jsonify({"status": "deleted"})


# =========================
# LOGO (FIXED FOR RENDER)
# =========================
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(BASE_DIR, "static", "logo.png")

if os.path.exists(logo_path):
    try:
        logo = Image(logo_path, width=90, height=90)
    except Exception as e:
        print("Logo load error:", e)
else:
    print("Logo NOT FOUND at:", logo_path)


# ======================
# PDF Export
# ======================
@app.route("/api/doctor/export_pdf/<submission_id>")
def export_pdf(submission_id):

    submission = supabase.table("Submission") \
        .select("*") \
        .eq("submission_id", submission_id) \
        .execute().data

    if not submission:
        return "Not found", 404

    submission = submission[0]

    answers = supabase.table("Answer") \
        .select("*") \
        .eq("submission_id", submission_id) \
        .execute().data

    exam = supabase.table("Exam") \
        .select("*") \
        .eq("exam_id", submission["exam_id"]) \
        .execute().data

    exam = exam[0] if exam else None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    elements = []

    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(BASE_DIR, "static", "logo.png")

    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=90, height=90)
            elements.append(logo)
        except Exception as e:
            print("Logo error:", e)

    elements.append(Spacer(1, 10))

    
    elements.append(Paragraph("UniExam Student Report", styles["Title"]))
    elements.append(Spacer(1, 15))

   
    if exam:
        elements.append(Paragraph(f"Exam: {exam['title']}", styles["Normal"]))
    else:
        elements.append(Paragraph(f"Exam ID: {submission['exam_id']}", styles["Normal"]))

    elements.append(Paragraph(f"Student ID: {submission['student_id']}", styles["Normal"]))
    elements.append(Paragraph(f"Section: {submission['section']}", styles["Normal"]))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Total Grade: {submission['total_grade']}", styles["Normal"]))
    elements.append(Spacer(1, 15))

    # =========================
    # TABLE
    # =========================
    table_data = [["Question", "Answer", "Marks"]]

    for a in answers:
        answer_text = a.get("answer_text") or a.get("selected_option") or "-"
        marks = a.get("marks_obtained") if a.get("marks_obtained") is not None else 0

        table_data.append([
            str(a.get("question_id")),
            answer_text,
            str(marks)
        ])

    table = Table(table_data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))

    elements.append(table)

    doc.build(elements)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{submission['student_id']}_report.pdf",
        mimetype="application/pdf"
    )
    


# ======================
# Ping
# ======================
@app.route("/ping")
def ping():
    return jsonify({"status": "alive"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
