import streamlit as st
import sqlite3
import qrcode
from datetime import datetime
from io import BytesIO
import pandas as pd

# ---------------- DATABASE ----------------
conn = sqlite3.connect("attendance.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
username TEXT UNIQUE,
password TEXT,
role TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS students(
id INTEGER PRIMARY KEY AUTOINCREMENT,
student_id TEXT,
student_name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS subjects(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT UNIQUE
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

conn.commit()

# Default Admin
cursor.execute("SELECT * FROM users WHERE username='admin'")
if not cursor.fetchone():
    cursor.execute("INSERT INTO users(name,username,password,role) VALUES(?,?,?,?)",
                   ("Admin","admin","admin123","admin"))
    conn.commit()

# ---------------- SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- LOGIN ----------------
if not st.session_state.user:

    st.title("🔐 Smart Attendance Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?",
                       (username,password))
        user = cursor.fetchone()
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Invalid Credentials ❌")

else:

    role = st.session_state.user[4]
    st.sidebar.title("📚 Smart Attendance")

    menu = st.sidebar.selectbox("Menu",[
        "Dashboard",
        "Add Student",
        "Add Teacher",
        "Add Subject",
        "Generate QR",
        "Mark Attendance",
        "Report",
        "Logout"
    ])

    # ---------------- DASHBOARD ----------------
    if menu == "Dashboard":
        st.title("📊 Dashboard")
        st.write("Welcome,", st.session_state.user[1])

    # ---------------- ADD STUDENT ----------------
    elif menu == "Add Student":
        st.title("➕ Add Student")

        sid = st.text_input("Student ID")
        name = st.text_input("Student Name")

        if st.button("Add"):
            cursor.execute("INSERT INTO students(student_id,student_name) VALUES(?,?)",
                           (sid,name))
            conn.commit()
            st.success("Student Added ✅")

        df = pd.read_sql("SELECT * FROM students", conn)
        st.dataframe(df)

    # ---------------- ADD TEACHER ----------------
    elif menu == "Add Teacher":
        if role != "admin":
            st.warning("Only Admin Allowed")
        else:
            st.title("👩‍🏫 Add Teacher")

            name = st.text_input("Teacher Name")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            if st.button("Create"):
                cursor.execute("INSERT INTO users(name,username,password,role) VALUES(?,?,?,?)",
                               (name,username,password,"teacher"))
                conn.commit()
                st.success("Teacher Created ✅")

            df = pd.read_sql("SELECT id,name,username,role FROM users WHERE role='teacher'", conn)
            st.dataframe(df)

    # ---------------- ADD SUBJECT ----------------
    elif menu == "Add Subject":
        st.title("📘 Add Subject")

        sub = st.text_input("Subject Name")
        if st.button("Add Subject"):
            cursor.execute("INSERT OR IGNORE INTO subjects(name) VALUES(?)",(sub,))
            conn.commit()
            st.success("Subject Added ✅")

        df = pd.read_sql("SELECT * FROM subjects", conn)
        st.dataframe(df)

    # ---------------- GENERATE QR ----------------
    elif menu == "Generate QR":
        st.title("🔳 Generate QR")

        subjects = pd.read_sql("SELECT name FROM subjects", conn)

        if len(subjects) == 0:
            st.warning("Add Subject First")
        else:
            subject = st.selectbox("Select Subject", subjects["name"])

            if st.button("Generate"):
                data = f"{subject}-{datetime.now()}"
                img = qrcode.make(data)
                buffer = BytesIO()
                img.save(buffer)
                st.image(buffer.getvalue())
                st.success("QR Generated ✅")

    # ---------------- MARK ATTENDANCE ----------------
    elif menu == "Mark Attendance":
        st.title("📝 Mark Attendance")

        sid = st.text_input("Student ID")
        subject = st.text_input("Subject")

        if st.button("Submit"):
            cursor.execute("SELECT student_name FROM students WHERE student_id=?",(sid,))
            stu = cursor.fetchone()

            if stu:
                cursor.execute("INSERT INTO attendance(student_id,student_name,subject,date,time) VALUES(?,?,?,?,?)",
                               (sid,stu[0],subject,
                                datetime.now().date(),
                                datetime.now().time()))
                conn.commit()
                st.success("Attendance Marked ✅")
            else:
                st.error("Student Not Found ❌")

    # ---------------- REPORT ----------------
    elif menu == "Report":
        st.title("📑 Attendance Report")

        df = pd.read_sql("SELECT * FROM attendance", conn)
        st.dataframe(df)

    # ---------------- LOGOUT ----------------
    elif menu == "Logout":
        st.session_state.user = None
        st.rerun()