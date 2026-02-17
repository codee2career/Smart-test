import streamlit as st
import sqlite3
import qrcode
from datetime import datetime, timedelta
import os
from io import BytesIO

# ---------------- DATABASE ----------------
conn = sqlite3.connect("attendance.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS admin(
    username TEXT,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS students(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE,
    student_name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS qr_session(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    created_at TEXT,
    is_active INTEGER
)
""")

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

# Default admin
cursor.execute("SELECT * FROM admin")
if not cursor.fetchone():
    cursor.execute("INSERT INTO admin VALUES('admin','admin')")
    conn.commit()

# ---------------- FUNCTIONS ----------------

def login_page():
    st.title("🔐 Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        cursor.execute("SELECT * FROM admin WHERE username=? AND password=?", (username,password))
        if cursor.fetchone():
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid credentials")


def dashboard():
    st.title("📊 Dashboard")

    menu = st.sidebar.selectbox("Menu",
        ["Add Student","Generate QR","View Report","Logout"])

    if menu == "Add Student":
        st.subheader("Add Student")
        sid = st.text_input("Student ID")
        name = st.text_input("Student Name")

        if st.button("Add"):
            try:
                cursor.execute("INSERT INTO students(student_id,student_name) VALUES(?,?)",(sid,name))
                conn.commit()
                st.success("Student Added")
            except:
                st.error("Student ID already exists")

        st.subheader("Student List")
        cursor.execute("SELECT * FROM students")
        st.dataframe(cursor.fetchall())

    elif menu == "Generate QR":
        st.subheader("Generate QR")
        subject = st.text_input("Enter Subject")

        if st.button("Generate"):
            created = datetime.now().isoformat()
            cursor.execute("INSERT INTO qr_session(subject,created_at,is_active) VALUES(?,?,1)",
                           (subject,created))
            conn.commit()
            session_id = cursor.lastrowid

            BASE_URL = "https://smart-test0.streamlit.app"
            qr_data = f"{BASE_URL}?scan={session_id}"

            qr = qrcode.make(qr_data)
            buffer = BytesIO()
            qr.save(buffer)
            st.image(buffer.getvalue())

            st.success("QR valid for 1 minute")

    elif menu == "View Report":
        st.subheader("Attendance Report")

        subject = st.text_input("Subject")
        date = st.date_input("Select Date")

        if st.button("View"):
            cursor.execute("SELECT student_id FROM attendance WHERE subject=? AND date=?",
                           (subject,str(date)))
            present = [x[0] for x in cursor.fetchall()]

            cursor.execute("SELECT student_id,student_name FROM students")
            students = cursor.fetchall()

            report = []
            for s in students:
                status = "Present" if s[0] in present else "Absent"
                report.append([s[0],s[1],status])

            st.table(report)

    elif menu == "Logout":
        st.session_state.logged_in = False
        st.rerun()


def mark_attendance(session_id):
    cursor.execute("SELECT subject,created_at,is_active FROM qr_session WHERE id=?",
                   (session_id,))
    qr = cursor.fetchone()

    if not qr:
        st.error("Invalid QR")
        return

    subject, created, active = qr

    if not active:
        st.error("QR Expired")
        return

    created_time = datetime.fromisoformat(created)

    if datetime.now() > created_time + timedelta(minutes=1):
        cursor.execute("UPDATE qr_session SET is_active=0 WHERE id=?",(session_id,))
        conn.commit()
        st.error("QR Expired")
        return

    st.title("📘 Mark Attendance")
    st.write("Subject:", subject)

    sid = st.text_input("Enter Student ID")

    if st.button("Submit"):
        cursor.execute("SELECT student_name FROM students WHERE student_id=?",(sid,))
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
    session_id = params["scan"]
    mark_attendance(session_id)
else:
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_page()
    else:
        dashboard()