import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import qrcode
from io import BytesIO
import pandas as pd
import time

# ---------------- DB ----------------
conn = sqlite3.connect("attendance.db", check_same_thread=False)
cursor = conn.cursor()

# Tables
cursor.execute("""CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS students(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE,
    student_name TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS subjects(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS qr_session(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    created_at TEXT,
    is_active INTEGER
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS attendance(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT,
    subject TEXT,
    date TEXT
)""")

conn.commit()

# Default Admin
cursor.execute("SELECT * FROM users WHERE role='admin'")
if not cursor.fetchone():
    cursor.execute("INSERT INTO users VALUES (NULL,'Admin','admin','admin','admin')")
    conn.commit()

# ---------------- SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None

st.set_page_config(page_title="Smart Attendance Pro")

# ---------------- LOGIN ----------------
if not st.session_state.user:

    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?",
                       (username, password))
        user = cursor.fetchone()
        if user:
            st.session_state.user = user
            st.success("Login Successful ✅")
            st.rerun()
        else:
            st.error("Invalid Credentials ❌")

# ---------------- DASHBOARD ----------------
else:
    role = st.session_state.user[4]

    st.sidebar.title("📚 Smart Attendance Pro")
    menu = st.sidebar.selectbox("Menu", [
        "Dashboard",
        "Add Student",
        "Add Teacher",
        "Manage Subjects",
        "Generate QR",
        "Mark Attendance",
        "Report",
        "Logout"
    ])

    # ---------------- DASHBOARD ----------------
    if menu == "Dashboard":
        st.header("📊 Dashboard")

        cursor.execute("SELECT COUNT(*) FROM students")
        total_students = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM attendance")
        total_attendance = cursor.fetchone()[0]

        st.metric("Total Students", total_students)
        st.metric("Total Attendance Records", total_attendance)

    # ---------------- ADD STUDENT ----------------
    elif menu == "Add Student":
        st.header("➕ Add Student")

        sid = st.text_input("Student ID")
        name = st.text_input("Student Name")

        if st.button("Add"):
            try:
                cursor.execute("INSERT INTO students VALUES (NULL,?,?)",
                               (sid, name))
                conn.commit()
                st.success("Student Added ✅")
            except:
                st.warning("Student ID Exists ⚠")

        st.subheader("Student List")
        cursor.execute("SELECT student_id, student_name FROM students")
        st.table(cursor.fetchall())

    # ---------------- ADD TEACHER ----------------
    elif menu == "Add Teacher":
        if role != "admin":
            st.warning("Admin Only Feature ❌")
        else:
            st.header("👨‍🏫 Add Teacher")

            name = st.text_input("Name")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            if st.button("Add Teacher"):
                cursor.execute(
                    "INSERT INTO users VALUES (NULL,?,?,?,?)",
                    (name, username, password, "teacher")
                )
                conn.commit()
                st.success("Teacher Added ✅")

    # ---------------- SUBJECTS ----------------
    elif menu == "Manage Subjects":
        st.header("📘 Subjects")

        subject = st.text_input("Add Subject")

        if st.button("Add Subject"):
            try:
                cursor.execute("INSERT INTO subjects VALUES (NULL,?)",
                               (subject,))
                conn.commit()
                st.success("Subject Added ✅")
            except:
                st.warning("Subject Exists ⚠")

        cursor.execute("SELECT name FROM subjects")
        st.table(cursor.fetchall())

    # ---------------- GENERATE QR ----------------
    elif menu == "Generate QR":
        st.header("📌 Generate QR (Valid 1 Min)")

        cursor.execute("SELECT name FROM subjects")
        subjects = [s[0] for s in cursor.fetchall()]

        subject = st.selectbox("Select Subject", subjects)

        if st.button("Generate QR"):
            now = datetime.now()
            cursor.execute("INSERT INTO qr_session VALUES (NULL,?,?,?)",
                           (subject, str(now), 1))
            conn.commit()

            qr_id = cursor.lastrowid
            data = f"QR_ID:{qr_id}"
            img = qrcode.make(data)

            buf = BytesIO()
            img.save(buf)

            st.image(buf)
            st.success("QR Generated ✅")

    # ---------------- MARK ATTENDANCE ----------------
    elif menu == "Mark Attendance":
        st.header("📝 Mark Attendance")

        qr_id = st.text_input("Enter QR ID")
        sid = st.text_input("Student ID")

        if st.button("Submit"):
            cursor.execute("SELECT subject,created_at,is_active FROM qr_session WHERE id=?",
                           (qr_id,))
            qr = cursor.fetchone()

            if not qr:
                st.error("Invalid QR ❌")
            else:
                subject, created, active = qr
                created = datetime.strptime(created, "%Y-%m-%d %H:%M:%S.%f")

                if active == 0 or datetime.now() > created + timedelta(minutes=1):
                    st.error("QR Expired ❌")
                else:
                    today = str(datetime.now().date())

                    cursor.execute("""
                        SELECT * FROM attendance
                        WHERE student_id=? AND subject=? AND date=?
                    """, (sid, subject, today))

                    if cursor.fetchone():
                        st.warning("Already Marked ⚠")
                    else:
                        cursor.execute("""
                            INSERT INTO attendance VALUES (NULL,?,?,?)
                        """, (sid, subject, today))
                        conn.commit()
                        st.success("Attendance Marked ✅")

    # ---------------- REPORT ----------------
    elif menu == "Report":
        st.header("📊 Attendance Report")

        cursor.execute("""
            SELECT student_id, subject, date
            FROM attendance
        """)

        df = pd.DataFrame(cursor.fetchall(),
                          columns=["Student ID", "Subject", "Date"])

        st.dataframe(df)

        if not df.empty:
            st.subheader("Attendance Chart")
            chart = df["Subject"].value_counts()
            st.bar_chart(chart)

    # ---------------- LOGOUT ----------------
    elif menu == "Logout":
        st.session_state.user = None
        st.success("Logged Out 👋")
        st.rerun()