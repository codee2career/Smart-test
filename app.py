import streamlit as st
import mysql.connector
from datetime import datetime
import qrcode
from io import BytesIO

# ---------------- DATABASE CONNECTION ----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="attendance_db"
)
cursor = db.cursor()

st.set_page_config(page_title="Smart Attendance", layout="centered")

# ---------------- SESSION LOGIN ----------------
if "admin" not in st.session_state:
    st.session_state.admin = False

# ---------------- LOGIN PAGE ----------------
if not st.session_state.admin:
    st.title("🔐 Admin Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        cursor.execute(
            "SELECT * FROM admin WHERE username=%s AND password=%s",
            (username, password)
        )
        if cursor.fetchone():
            st.session_state.admin = True
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
            cursor.execute(
                "INSERT INTO students(student_id, student_name) VALUES(%s,%s)",
                (sid, name)
            )
            db.commit()
            st.success("Student Added Successfully ✅")

    # ---------------- GENERATE QR ----------------
    elif menu == "Generate QR":
        st.header("📌 Generate QR")
        subject = st.text_input("Enter Subject Name")

        if st.button("Generate QR"):
            data = f"Subject: {subject} | Time: {datetime.now()}"
            img = qrcode.make(data)

            buf = BytesIO()
            img.save(buf)
            st.image(buf)
            st.success("QR Generated ✅")

    # ---------------- MARK ATTENDANCE ----------------
    elif menu == "Mark Attendance":
        st.header("📝 Mark Attendance")

        sid = st.text_input("Student ID")
        subject = st.text_input("Subject")

        if st.button("Submit"):
            today = datetime.now().date()

            cursor.execute("""
            SELECT * FROM attendance
            WHERE student_id=%s AND subject=%s AND date=%s
            """, (sid, subject, today))

            if cursor.fetchone():
                st.warning("Attendance already marked ⚠")
            else:
                cursor.execute("""
                INSERT INTO attendance(student_id, subject, date)
                VALUES(%s,%s,%s)
                """, (sid, subject, today))
                db.commit()
                st.success("Attendance Marked Successfully ✅")

    # ---------------- VIEW REPORT ----------------
    elif menu == "View Report":
        st.header("📊 Attendance Report")

        cursor.execute("SELECT * FROM attendance")
        data = cursor.fetchall()

        st.table(data)

    # ---------------- LOGOUT ----------------
    elif menu == "Logout":
        st.session_state.admin = False
        st.success("Logged out successfully")
        st.rerun()
