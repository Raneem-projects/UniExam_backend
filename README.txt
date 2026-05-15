UniExam System — Secure E-Ink Digital Examination Device


Overview:
UniExam is a smart exam management system that converts traditional PDF exams into a fully 
digital experience. The system supports uploading exam, generating a unique session PIN, 
automatic grading for MCQ, and PDF report generation.

----------------------------------------

Features:
- User authentication 
- Upload exam as PDF
- Automatic parsing (PDF → Questions)
- Generate unique exam session PIN
- Student exam submission via API
- Auto grading for MCQ questions
- Generate PDF report per student
- Dashboard for instructors
- Secure data handling using HTTPS 

----------------------------------------

Technologies Used:
- Backend: Flask (Python)
- Database: SQLite
- Database Management: Flask-SQLAlchemy 
- PyMuPDF for processing PDF files 
- Frontend: HTML, CSS, JavaScript
- PDF Processing: Custom Parser
- PDF Generation: ReportLab
- HTTPS protocol for secure communication 

----------------------------------------

Project Structure:
- app.py → Main server file
- models.py → Database models
- templates/ → HTML pages
- static/ → Images & uploads
- parser.py → PDF to JSON logic

----------------------------------------

How to Run:
1. Install dependencies:
   pip install requirements.txt

2. Run the server:
   python app.py

3. Open in browser:
   https://localhost:5000/login

----------------------------------------

Default Web Login:
Username: admin
Password: 1234

----------------------------------------

Main APIs:
- POST /api/create-session 
- POST /api/doctor/upload-pdf 
- GET /api/doctor/exams 
- GET /api/doctor/exam/<exam_id>/submissions 
- GET /api/doctor/export_pdf/<submission_id> 
- GET /api/student/result/<submission_id> 
- POST /api/student/verify-pin 
- GET /api/student/get_exam/<exam_id> 
- POST /api/student/submit_exam 

----------------------------------------

Security:
- Secure communication using HTTPS.
- Data encryption during data transmission.
- User authentication 
- Protection against unauthorized access 

----------------------------------------

Notes:
- MCQ questions are graded automatically.
- PDF format must follow a structured pattern for parsing.

----------------------------------------

Contributors:
UniExam Team (Raneem Alateeq, Layan Quplan, Shmail Aloqaily)

-------------------------------------