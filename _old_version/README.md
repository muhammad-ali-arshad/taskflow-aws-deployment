# Task Manager (Flask + SQLite + JWT)

A small web app where users sign up, log in with a JWT token, and manage their own tasks.

## Features
- Signup, Login, Logout (JWT token stored in an HttpOnly cookie)
- Passwords hashed with Werkzeug
- Full CRUD on tasks (Create, Read, Update, Delete)
- Local SQLite database (`database.db`, created automatically)
- Two entities: **Users** and **Tasks** (one user has many tasks)
- Pages: Login, Signup, Tasks dashboard, Edit task

## Run
```bash
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Structure
```
app.py            # backend: routes, JWT, database
templates/        # HTML pages (base, login, signup, tasks, edit)
requirements.txt
```
