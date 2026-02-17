import streamlit as st
import sqlite3
from datetime import datetime
import qrcode
from io import BytesIO

# ---------------- DATABASE CONNECTION ----------------
conn = sqlite3.connect("attendance.db", check_same_thread=False)
cursor = conn.cursor()

# ---------------- CREATE TABLES ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS admin (
    username TEXT,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE,
    student_name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT,
    subject TEXT,
    date TEXT
)
""")

# Insert default admin if not exists
cursor.execute("SELECT * FROM admin")
if not cursor.fetchone():
    cursor.execute("INSERT INTO admin VALUES ('admin','admin')")
    conn.commit()

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Smart Attendance System")

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------- LOGIN ----------------
if not st.session_state.logged_in:

    st.title("🔐 Admin Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        cursor.execute(
            "SELECT * FROM admin WHERE username=? AND password=?",
            (username, password)
        )
        if cursor.fetchone():
            st.session_state.logged_in = True
            st.success("Login Successful ✅")
            st.rerun()
        else:
            st.error("Invalid Credentials ❌")

# ---------------- DASHBOARD ----------------
else:

    st.sidebar.title("📚 Smart Attendance")
    menu = st.sidebar.selectbox("Menu", [
        "Add Student",
        "Generate QR",
        "Mark Attendance",
        "View Report",
        "Logout"
    ])

    # ---------------- ADD STUDENT ----------------
    if menu == "Add Student":

        st.header("➕ Add Student")

        sid = st.text_input("Student ID")
        name = st.text_input("Student Name")

        if st.button("Add Student"):
            try:
                cursor.execute(
                    "INSERT INTO students (student_id, student_name) VALUES (?,?)",
                    (sid, name)
                )
                conn.commit()
                st.success("Student Added Successfully ✅")
            except:
                st.warning("Student ID already exists ⚠")

        st.subheader("📋 Student List")
        cursor.execute("SELECT student_id, student_name FROM students")
        students = cursor.fetchall()
        st.table(students)

    # ---------------- GENERATE QR ----------------
    elif menu == "Generate QR":

        st.header("📌 Generate QR Code")

        subject = st.text_input("Enter Subject Name")

        if st.button("Generate QR"):
            data = f"Subject: {subject} | Time: {datetime.now()}"
            img = qrcode.make(data)

            buf = BytesIO()
            img.save(buf)

            st.image(buf)
            st.success("QR Generated Successfully ✅")

    # ---------------- MARK ATTENDANCE ----------------
    elif menu == "Mark Attendance":

        st.header("📝 Mark Attendance")

        sid = st.text_input("Enter Student ID")
        subject = st.text_input("Enter Subject Name")

        if st.button("Submit Attendance"):

            today = str(datetime.now().date())

            cursor.execute("""
                SELECT * FROM attendance
                WHERE student_id=? AND subject=? AND date=?
            """, (sid, subject, today))

            if cursor.fetchone():
                st.warning("Attendance already marked ⚠")
            else:
                cursor.execute("""
                    INSERT INTO attendance (student_id, subject, date)
                    VALUES (?,?,?)
                """, (sid, subject, today))
                conn.commit()
                st.success("Attendance Marked Successfully ✅")

    # ---------------- VIEW REPORT ----------------
    elif menu == "View Report":

        st.header("📊 Attendance Report")

        cursor.execute("""
            SELECT s.student_id, s.student_name, a.subject, a.date
            FROM students s
            LEFT JOIN attendance a
            ON s.student_id = a.student_id
        """)

        report = cursor.fetchall()
        st.table(report)

    # ---------------- LOGOUT ----------------
    elif menu == "Logout":
        st.session_state.logged_in = False
        st.success("Logged Out Successfully 👋")
        st.rerun()