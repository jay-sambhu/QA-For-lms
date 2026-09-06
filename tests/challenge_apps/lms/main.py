"""
Challenge App C — LMS (Learning Management System) Application.
Defects:
1. Student role can access /instructor/grades without authorization (Security Authorization Bypass)
2. Lesson 3 link /courses/1/lessons/3 returns HTTP 404 (Dead Link / Navigation)
3. POST /quiz/submit with empty answer raises HTTP 500 (API Error)
"""
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="Challenge LMS App")


@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>EduPortal LMS - Home</title></head>
    <body>
        <h1>EduPortal Learning Platform</h1>
        <p><a href="/courses" id="nav-courses">Browse Courses</a></p>
        <p><a href="/login" id="nav-login">User Login</a></p>
        <p><a href="/instructor/grades" id="nav-grades">Instructor Grade Portal (Unprotected)</a></p>
    </body>
    </html>
    """


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>EduPortal - Login</title></head>
    <body>
        <h1>Student & Instructor Login</h1>
        <form action="/login" method="post">
            <input type="text" name="username" placeholder="Username" required /><br/>
            <input type="password" name="password" placeholder="Password" required /><br/>
            <button type="submit" id="btn-login">Login</button>
        </form>
    </body>
    </html>
    """


@app.post("/login")
def login_submit(username: str = Form(...), password: str = Form(...)):
    return RedirectResponse(url="/courses", status_code=303)


@app.get("/courses", response_class=HTMLResponse)
def course_list():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>EduPortal - Available Courses</title></head>
    <body>
        <h1>Available Courses</h1>
        <ul>
            <li><strong>Python Software Testing 101</strong> - <a href="/courses/1" id="course-1">View Course</a></li>
            <li><strong>Advanced QA Automation</strong> - <a href="/courses/2" id="course-2">View Course</a></li>
        </ul>
    </body>
    </html>
    """


@app.get("/courses/1", response_class=HTMLResponse)
def course_detail():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Python Software Testing 101</title></head>
    <body>
        <h1>Python Software Testing 101</h1>
        <h3>Syllabus Lessons</h3>
        <ul>
            <li><a href="/courses/1/lessons/1">Lesson 1: Introduction</a></li>
            <li><a href="/courses/1/lessons/2">Lesson 2: Unit Testing</a></li>
            <li><a href="/courses/1/lessons/3" id="broken-lesson">Lesson 3: Integration Testing (Dead Link)</a></li>
        </ul>
        <br/>
        <a href="/courses/1/quiz" id="take-quiz">Take Module Quiz</a>
    </body>
    </html>
    """


@app.get("/courses/1/lessons/1", response_class=HTMLResponse)
def lesson_one():
    return "<h1>Lesson 1: Introduction to Testing</h1><p>Content for lesson 1.</p>"


@app.get("/courses/1/lessons/2", response_class=HTMLResponse)
def lesson_two():
    return "<h1>Lesson 2: Unit Testing Fundamentals</h1><p>Content for lesson 2.</p>"


@app.get("/courses/1/lessons/3")
def lesson_three_broken():
    # DEFECT: Dead link returns 404!
    raise HTTPException(status_code=404, detail="Lesson Resource Not Found")


@app.get("/courses/1/quiz", response_class=HTMLResponse)
def quiz_page():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Module 1 Quiz</title></head>
    <body>
        <h1>Module 1 Quiz</h1>
        <form action="/quiz/submit" method="post">
            <p>Question 1: What command runs pytest?</p>
            <input type="text" id="answer" name="answer" />
            <button type="submit" id="submit-quiz">Submit Answers</button>
        </form>
    </body>
    </html>
    """


@app.post("/quiz/submit")
def quiz_submit(answer: str = Form("")):
    # DEFECT: Empty answer string raises HTTP 500!
    if not answer or answer.strip() == "":
        raise HTTPException(status_code=500, detail="Quiz Engine Exception: Null Answer Provided")
    return HTMLResponse("<h1>Quiz Passed! Score: 100%</h1>", status_code=200)


@app.get("/instructor/grades", response_class=HTMLResponse)
def instructor_grades():
    # DEFECT: Missing authorization check! Accessible by anyone!
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Instructor Portal - Student Grades</title></head>
    <body>
        <h1>Instructor Grade Management (Unprotected Access)</h1>
        <table border="1">
            <tr><th>Student</th><th>Score</th></tr>
            <tr><td>Alice Smith</td><td>98%</td></tr>
            <tr><td>Bob Jones</td><td>85%</td></tr>
        </table>
    </body>
    </html>
    """
