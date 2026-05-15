import fitz
import uuid
import re
from datetime import datetime
from models import Exam, Question
from extensions import db


# ===============================
# PDF to JSON
# ===============================
def parse_exam_pdf_to_json(pdf_path):

    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"

    lines = text.splitlines()

    # ── دمج السطور: كل سؤال يُجمع حتى نجد (mcq) أو (true_false) ──────────
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
                    combined = combined + " " + next_line
            # إذا وجدنا (mcq) أو (true_false) لكن لا يوجد [...] بعد — نضم السطر التالي
            if re.search(r'\(mcq\)|\(true_false\)', combined) and not re.search(r'\[\d+(?:\.\d+)?\]', combined):
                if i + 1 < len(lines):
                    i += 1
                    next_line = lines[i].strip()
                    if next_line:
                        combined = combined + " " + next_line
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
            parts = line.split(":", 1)
            if len(parts) > 1:
                exam["title"] = parts[1].strip()

        elif line.startswith("Course Code"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                exam["course_code"] = parts[1].strip()

        elif line.startswith("Instructor"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                exam["instructor"] = parts[1].strip()

        elif line.startswith("Duration"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                exam["duration_minutes"] = int(parts[1].strip())

        elif line.startswith("Q") and len(line) > 1 and line[1].isdigit():
            if current_q:
                exam["questions"].append(current_q)

            qid = int(line.split(".")[0][1:])
            qtype = "mcq" if "(mcq)" in line else ("true_false" if "(true_false)" in line else "mcq")

            marks = 1
            marks_match = re.search(r'\[(\d+(?:\.\d+)?)\]', line)
            if marks_match:
                marks = float(marks_match.group(1))
                if marks == int(marks): marks = int(marks)

            m = re.search(r'\(mcq\)|\(true_false\)', line)
            clean_text = line[:m.start()].strip() if m else line.strip()

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
            parts = line.split(":", 1)
            if len(parts) > 1:
                current_q["correct_answer"] = parts[1].strip().upper()

    if current_q:
        exam["questions"].append(current_q)

    mcq_qs = [q for q in exam["questions"] if q["type"] == "mcq"]
    tf_qs  = [q for q in exam["questions"] if q["type"] == "true_false"]
    sorted_qs = mcq_qs + tf_qs
    for i, q in enumerate(sorted_qs):
        q["question_id"] = i + 1
    exam["questions"] = sorted_qs
    exam["total_marks"] = sum(q["marks"] for q in exam["questions"])

    return exam


# ===============================
# JSON to DB
# ===============================
def exam_json_to_db(data):

    existing_exam = Exam.query.filter_by(exam_id=data["exam_id"]).first()
    if existing_exam:
        return existing_exam.exam_id

    exam = Exam(
        exam_id=data["exam_id"],
        title=data["title"],
        course_code=data["course_code"],
        instructor=data["instructor"],
        duration_minutes=data["duration_minutes"],
        total_marks=data["total_marks"],
        created_at=datetime.utcnow()
    )
    db.session.add(exam)

    for q in data["questions"]:
        question = Question(
            exam_id=data["exam_id"],
            question_id=q["question_id"],
            type=q["type"],
            text=q["text"],
            marks=q["marks"],
            options=q.get("options"),
            correct_answer=q.get("correct_answer"),
            page_number=q.get("page_number")
        )
        db.session.add(question)

    db.session.commit()
    return data["exam_id"]
