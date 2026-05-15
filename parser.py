import fitz
import uuid
import re
from datetime import datetime
from supabase import create_client


# ===============================
# Supabase Setup
# ===============================
SUPABASE_URL = "https://yvwtsebueljtuimhytwp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl2d3RzZWJ1ZWxqdHVpbWh5dHdwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg4MzcyMDEsImV4cCI6MjA5NDQxMzIwMX0.oIXJ2CjW00DpGcv5FfXj-j2CtcH_fopqSX5Q8O0hkMM"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ===============================
# PDF to JSON
# ===============================
def parse_exam_pdf_to_json(pdf_path):

    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"

    lines = text.splitlines()

    merged_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        if line.startswith("Q") and len(line) > 1 and line[1].isdigit():
            combined = line
            while "(mcq)" not in combined and "(true_false)" not in combined and i + 1 < len(lines):
                i += 1
                next_line = lines[i].strip()
                if next_line:
                    combined += " " + next_line

            merged_lines.append(combined)
        else:
            merged_lines.append(line)

        i += 1

    exam = {
        "exam_id": "EX" + uuid.uuid4().hex[:4].upper(),
        "title": "",
        "course_code": "",
        "instructor": "",
        "duration_minutes": 60,
        "total_marks": 0,
        "created_at": datetime.utcnow().isoformat(),
        "questions": []
    }

    current_q = None

    for line in merged_lines:

        if line.startswith("Title"):
            exam["title"] = line.split(":", 1)[-1].strip()

        elif line.startswith("Course Code"):
            exam["course_code"] = line.split(":", 1)[-1].strip()

        elif line.startswith("Instructor"):
            exam["instructor"] = line.split(":", 1)[-1].strip()

        elif line.startswith("Duration"):
            try:
                exam["duration_minutes"] = int(line.split(":", 1)[-1].strip())
            except:
                pass

        elif line.startswith("Q") and len(line) > 1 and line[1].isdigit():

            if current_q:
                exam["questions"].append(current_q)

            qid = int(line.split(".")[0][1:])
            qtype = "mcq" if "(mcq)" in line else "true_false"

            marks = 1
            marks_match = re.search(r'\[(\d+(?:\.\d+)?)\]', line)
            if marks_match:
                marks = float(marks_match.group(1))
                if marks == int(marks):
                    marks = int(marks)

            clean_text = re.sub(r'\(mcq\)|\(true_false\)', '', line).strip()

            current_q = {
                "question_id": qid,
                "type": qtype,
                "text": clean_text,
                "marks": marks,
                "options": [],
                "correct_answer": None,
                "page_number": 1
            }

        elif line.startswith(("a)", "b)", "c)", "d)")) and current_q:
            current_q["options"].append(line[2:].strip())

        elif "Correct Answer" in line and current_q:
            current_q["correct_answer"] = line.split(":", 1)[-1].strip().upper()

    if current_q:
        exam["questions"].append(current_q)

    mcq_qs = [q for q in exam["questions"] if q["type"] == "mcq"]
    tf_qs = [q for q in exam["questions"] if q["type"] == "true_false"]

    sorted_qs = mcq_qs + tf_qs

    for i, q in enumerate(sorted_qs):
        q["question_id"] = i + 1

    exam["questions"] = sorted_qs
    exam["total_marks"] = sum(q["marks"] for q in sorted_qs)

    return exam


# ===============================
# JSON to DB (Supabase ONLY)
# ===============================
def exam_json_to_db(data):

    # check if exists
    existing = supabase.table("Exam") \
        .select("*") \
        .eq("exam_id", data["exam_id"]) \
        .execute().data

    if existing:
        return existing[0]["exam_id"]

    # insert exam
    supabase.table("Exam").insert({
        "exam_id": data["exam_id"],
        "title": data["title"],"course_code": data["course_code"],
        "instructor": data["instructor"],
        "duration_minutes": data["duration_minutes"],
        "total_marks": data["total_marks"],
        "created_at": data["created_at"]
    }).execute()

    # insert questions
    for q in data["questions"]:
        supabase.table("Question").insert({
            "exam_id": data["exam_id"],
            "question_id": q["question_id"],
            "type": q["type"],
            "text": q["text"],
            "marks": q["marks"],
            "options": q.get("options"),
            "correct_answer": q.get("correct_answer"),
            "page_number": q.get("page_number")
        }).execute()

    return data["exam_id"]