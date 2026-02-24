import streamlit as st
import sqlite3
import io
from github import Github
import os


def backup_to_github():

    token = st.secrets["GITHUB_TOKEN"]
    repo_name = st.secrets["REPO_NAME"]

    g = Github(token)
    repo = g.get_repo(repo_name)

    file_path = "courses.db"

    with open(file_path, "rb") as f:
        content = f.read()

    try:
        contents = repo.get_contents(file_path)

        repo.update_file(
            contents.path,
            "Backup automatico database",
            content,
            contents.sha
        )

    except:
        repo.create_file(
            file_path,
            "Backup iniziale database",
            content
        )
        
conn = sqlite3.connect("courses.db", check_same_thread=False)
c = conn.cursor()
c.execute("PRAGMA foreign_keys = ON")

# Tabelle
c.execute("""CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
username TEXT,
password TEXT,
role TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS courses(
id INTEGER PRIMARY KEY,
title TEXT
)""")

c.execute("""
CREATE TABLE IF NOT EXISTS enrollments(
id INTEGER PRIMARY KEY,
user_id INTEGER,
course_id INTEGER,
UNIQUE(user_id,course_id),
FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
)
""")

conn.commit()

st.title("Portale di iscrizione ai corsi")

# LOGIN
if "user" not in st.session_state:

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        user = c.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username,password)).fetchone()

        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Credenziali errate")

else:

    user = st.session_state.user
    role = user[3]

    st.sidebar.write("Utente:", user[1])

    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.rerun()

    menu = ["Corsi disponibili","Iscrizioni attivate"]

    if role == "admin":
        menu += ["Gestione corsi", "Lista iscritti", "Gestione utenti"]

    choice = st.sidebar.selectbox("Menu", menu)

    # ----------------------

    if choice == "Corsi disponibili":
        st.subheader("CORSI DISPONIBILI")
        courses = c.execute("SELECT * FROM courses").fetchall()

        for course in courses:

            st.subheader(course[1])

            already = c.execute("""
            SELECT * FROM enrollments
            WHERE user_id=? AND course_id=?
            """, (user[0], course[0])).fetchone()

            if already:
                st.info("Sei già iscritto")
            else:
                if st.button("Iscriviti", key=course[0]):
                    c.execute(
                        "INSERT INTO enrollments(user_id,course_id) VALUES (?,?)",
                        (user[0], course[0])
                    )

                    conn.commit()
                    backup_to_github()
                    st.success("Iscritto")

    # ----------------------

    if choice == "Iscrizioni attivate":
        st.subheader("ISCRIZIONI ATTIVATE")
        courses = c.execute("""
        SELECT courses.id, courses.title
        FROM courses
        JOIN enrollments
        ON courses.id=enrollments.course_id
        WHERE enrollments.user_id=?
        """,(user[0],)).fetchall()

        for course in courses:

            st.write(course[1])

            if st.button("Cancella iscrizione", key="del"+str(course[0])):

                c.execute("""
                DELETE FROM enrollments
                WHERE user_id=? AND course_id=?
                """,(user[0],course[0]))

                conn.commit()
                backup_to_github()
                st.success("Iscrizione cancellata")

    # ----------------------

    if choice == "Gestione corsi":
        st.subheader("Crea corso")
        
        title = st.text_input("Titolo corso")

        if st.button("Salva"):
            c.execute("INSERT INTO courses(title) VALUES (?)",(title,))
            conn.commit()
            backup_to_github()
            st.success("Corso creato")

        st.subheader("Elimina corso")

        corsi = c.execute("SELECT id,title FROM courses").fetchall()

        courses_dict = {u[1]:u[0] for u in corsi}

        selected = st.selectbox("Seleziona corso",courses_dict.keys())
        
        if st.button("Elimina corso"):
            
            c.execute("DELETE FROM courses WHERE id=?",(courses_dict[selected],))
            #c.execute("DELETE FROM enrollments WHERE course_id=?", courses_dict[selected])
                        
            conn.commit()
            backup_to_github()

            st.warning("Corso eliminato")

    # ----------------------

    if choice == "Lista iscritti":

        courses = c.execute("SELECT * FROM courses").fetchall()

        for course in courses:

            st.subheader(course[1])

            users = c.execute("""
            SELECT users.username
            FROM enrollments
            JOIN users ON users.id=enrollments.user_id
            WHERE enrollments.course_id=?
            """, (course[0],)).fetchall()

            if users:
                for u in users:
                    st.write("-", u[0])
            else:
                st.write("--- Nessun iscritto ---")


    if choice == "Gestione utenti":

        st.subheader("Crea nuovo utente")

        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")

        role_user = st.selectbox("Ruolo", ["user", "admin"])

        if st.button("Crea utente"):
            c.execute(
                "INSERT INTO users(username,password,role) VALUES (?,?,?)",
                (new_user, new_pass, role_user)
            )

            conn.commit()
            backup_to_github()
            st.success("Utente creato")

        st.subheader("Elimina utente")

        users = c.execute("SELECT id,username FROM users").fetchall()

        user_dict = {u[1]:u[0] for u in users}

        selected = st.selectbox("Seleziona utente",user_dict.keys())

        if st.button("Elimina utente"):

            c.execute("DELETE FROM users WHERE id=?",(user_dict[selected],))
            conn.commit()
            backup_to_github()

            st.warning("Utente eliminato")

        # Pulsante per scaricare il database
        if role == "admin":
            st.subheader("Gestione database")

            # apriamo il file in modalità binaria
            with open("courses.db", "rb") as f:
                db_bytes = f.read()

            st.download_button(
                label="Scarica database",
                data=db_bytes,
                file_name="courses.db",
                mime="application/octet-stream"
            )

        if st.button("Backup manuale su Github"):
            backup_to_github()

        
       







