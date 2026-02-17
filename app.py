import streamlit as st
import sqlite3
import qrcode
from datetime import datetime, timedelta
from io import BytesIO

# ---------------- DATABASE ----------------

conn = sqlite3.connect("attendance.db", check_same_thread=False)
cursor = conn.cursor()

# Admin
cursor.execute("""
CREATE TABLE IF NOT EXISTS admin(
    username TEXT,
    password TEXT
)
""")

# Teachers
cursor.execute("""
CREATE TABLE IF NOT EXISTS teachers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    username TEXT UNIQUE,
    password TEXT
)
""")

# Students
cursor.execute("""
CREATE TABLE IF NOT EXISTS students(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE,
    student_name TEXT
)
""")

# Subjects
cursor.execute("""
CREATE TABLE IF NOT EXISTS subjects(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)
""")

# QR Session
cursor.execute("""
CREATE TABLE IF NOT EXISTS qr_session(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    created_at TEXT,
    is_active INTEGER
)
""")

# Attendance
cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT,
    student_name TEXT,
    subject TEXT,
    date TEXT,
    time TEXT
)
""")

conn.commit()

# Default Admin
cursor.execute("SELECT * FROM admin")
if not cursor.fetchone():
    cursor.execute("INSERT INTO admin VALUES('admin','admin')")
    conn.commit()

# ---------------- LOGIN ----------------

def login_page():
    st.title("🔐 Login")

    role = st.selectbox("Login As", ["Admin", "Teacher"])

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if role == "Admin":
            cursor.execute("SELECT * FROM admin WHERE username=? AND password=?",
                           (username,password))
            if cursor.fetchone():
                st.session_state.role = "admin"
                st.session_state.user = username
                st.rerun()
            else:
                st.error("Invalid Admin Credentials")

        if role == "Teacher":
            cursor.execute("SELECT * FROM teachers WHERE username=? AND password=?",
                           (username,password))
            if cursor.fetchone():
                st.session_state.role = "teacher"
                st.session_state.user = username
                st.rerun()
            else:
                st.error("Invalid Teacher Credentials")

# ---------------- DASHBOARD ----------------

def dashboard():

    st.title(f"📊 {st.session_state.role.upper()} Dashboard")

    if st.session_state.role == "admin":
        menu = st.sidebar.selectbox("Menu",
            ["Add Student","Add Teacher","Add Subject",
             "Generate QR","View Report","Logout"])

    else:
        menu = st.sidebar.selectbox("Menu",
            ["Generate QR","View Report","Logout"])

    # -------- Add Student --------
    if menu == "Add Student":
        sid = st.text_input("Student ID")
        name = st.text_input("Student Name")

        if st.button("Add Student"):
            try:
                cursor.execute("INSERT INTO students(student_id,student_name) VALUES(?,?)",
                               (sid,name))
                conn.commit()
                st.success("Student Added")
            except:
                st.error("Student ID exists")

    # -------- Add Teacher --------
    elif menu == "Add Teacher":
        name = st.text_input("Teacher Name")
        username = st.text_input("Username")
        password = st.text_input("Password")

        if st.button("Add Teacher"):
            try:
                cursor.execute("INSERT INTO teachers(name,username,password) VALUES(?,?,?)",
                               (name,username,password))
                conn.commit()
                st.success("Teacher Added")
            except:
                st.error("Username already exists")

    # -------- Add Subject --------
    elif menu == "Add Subject":
        subject = st.text_input("Subject Name")

        if st.button("Add Subject"):
            try:
                cursor.execute("INSERT INTO subjects(name) VALUES(?)",(subject,))
                conn.commit()
                st.success("Subject Added")
            except:
                st.error("Subject already exists")

    # -------- Generate QR --------
    elif menu == "Generate QR":

        st.subheader("Generate QR")

        cursor.execute("SELECT name FROM subjects")
        subject_list = [x[0] for x in cursor.fetchall()]

        subject = st.selectbox("Select Subject", subject_list)

        if st.button("Generate QR"):

            created = datetime.now().isoformat()

            cursor.execute("""
            INSERT INTO qr_session(subject,created_at,is_active)
            VALUES(?,?,1)
            """,(subject,created))
            conn.commit()

            session_id = cursor.lastrowid

            BASE_URL = "https://smart-test0.streamlit.app"
            qr_link = f"{BASE_URL}?scan={session_id}"

            qr = qrcode.make(qr_link)
            buffer = BytesIO()
            qr.save(buffer)

            st.image(buffer.getvalue())
            st.success("QR valid for 1 minute")

    # -------- View Report --------
    elif menu == "View Report":

        cursor.execute("SELECT name FROM subjects")
        subject_list = [x[0] for x in cursor.fetchall()]

        subject = st.selectbox("Subject", subject_list)
        date = st.date_input("Select Date")

        if st.button("View"):

            cursor.execute("""
            SELECT student_id FROM attendance
            WHERE subject=? AND date=?
            """,(subject,str(date)))

            present_ids = [x[0] for x in cursor.fetchall()]

            cursor.execute("SELECT student_id,student_name FROM students")
            students = cursor.fetchall()

            report = []
            for s in students:
                status = "Present" if s[0] in present_ids else "Absent"
                report.append([s[0],s[1],status])

            st.table(report)

    # -------- Logout --------
    elif menu == "Logout":
        st.session_state.clear()
        st.rerun()

# ---------------- MARK ATTENDANCE ----------------

def mark_attendance(session_id):

    cursor.execute("""
    SELECT subject,created_at,is_active
    FROM qr_session WHERE id=?
    """,(session_id,))
    qr = cursor.fetchone()

    if not qr:
        st.error("Invalid QR")
        return

    subject,created,active = qr

    if active == 0:
        st.error("QR Expired")
        return

    created_time = datetime.fromisoformat(created)

    if datetime.now() > created_time + timedelta(minutes=1):
        cursor.execute("UPDATE qr_session SET is_active=0 WHERE id=?",
                       (session_id,))
        conn.commit()
        st.error("QR Expired")
        return

    st.title("📘 Mark Attendance")
    st.write("Subject:", subject)

    sid = st.text_input("Enter Student ID")

    if st.button("Submit"):

        cursor.execute("SELECT student_name FROM students WHERE student_id=?",
                       (sid,))
        stu = cursor.fetchone()

        if not stu:
            st.error("Student not registered")
            return

        today = str(datetime.now().date())

        cursor.execute("""
        SELECT * FROM attendance
        WHERE student_id=? AND subject=? AND date=?
        """,(sid,subject,today))

        if cursor.fetchone():
            st.warning("Already Marked")
            return

        cursor.execute("""
        INSERT INTO attendance(student_id,student_name,subject,date,time)
        VALUES(?,?,?,?,?)
        """,(sid,stu[0],subject,today,str(datetime.now().time())))

        conn.commit()

        st.success("Attendance Marked Successfully")

# ---------------- MAIN ----------------

params = st.query_params

if "scan" in params:
    mark_attendance(params["scan"])
else:
    if "role" not in st.session_state:
        login_page()
    else:
        dashboard()