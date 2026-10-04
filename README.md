# TaskFlow — Project & Task Management System

A multi-user project and task management web app built with **Flask**, **SQLAlchemy** and **JWT authentication**.
It runs on **SQLite** on your laptop and on **MySQL** in the cloud: a MySQL server on **Amazon EC2** (IaaS), or **Amazon RDS** behind **AWS Elastic Beanstalk** (PaaS).

> DevOps for Cloud Computing, Assignment 1. Deployment steps are in **[DEPLOYMENT.md](DEPLOYMENT.md)**.

## Modules

| # | Module | Features |
|---|--------|----------|
| 1 | **Authentication & Profile** | Sign up with validation, login with a JWT in an HttpOnly cookie, logout, profile editing, password change. The first registered user becomes admin. |
| 2 | **Projects & Team** | Create, edit, archive and delete projects. Colour labels and target dates. Add or remove team members with owner/member roles. Per-project activity log. |
| 3 | **Task Management** | Task CRUD with status (To Do / In Progress / In Review / Done), priority, due date and assignee. **Kanban board with drag & drop**, comments, search, filters, sorting, pagination and **CSV export**. |
| 4 | **Dashboard & Reports** | KPI cards, my open tasks, overdue and due-this-week lists, tasks by status and priority, tasks completed in the last 7 days, team workload, project progress, activity feed. |
| 5 | **Admin Panel** | Manage all users (promote or demote, enable or disable, delete), system statistics, system-wide activity log. |
| + | **REST API & Health** | `POST /api/login` returns a JWT, plus `GET /api/me`, `/api/projects`, `/api/tasks`, `POST /api/tasks` and `/api/stats`. `GET /health` reports whether the database is connected. |

## Database (6 tables)

`users`, `projects`, `project_members`, `tasks`, `comments`, `activity_logs`. All foreign keys are enforced.
See `deploy/schema.sql`. The app also creates the tables automatically on first start.

## Run locally (Windows / Mac / Linux)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python seed.py                    # optional: loads demo data
python application.py             # opens on http://127.0.0.1:5000
```

Demo logins (after `seed.py`): **admin / Password123**, ali / Password123, sara / Password123, usman / Password123

Run the tests: `pip install pytest`, then `pytest -q` (24 tests).

## Configuration (environment variables)

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Signs the JWT tokens. Set a long random value in production. |
| `DATABASE_URL` | Full SQLAlchemy URL, e.g. `mysql+pymysql://user:pass@host:3306/taskflow` |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | MySQL connection, used on EC2 or when RDS is created separately |
| `RDS_HOSTNAME`, `RDS_PORT`, `RDS_DB_NAME`, `RDS_USERNAME`, `RDS_PASSWORD` | Set automatically by Elastic Beanstalk when RDS is attached to the environment |

If none of these are set, the app uses the local SQLite file `taskflow.db`.

## Project structure

```
application.py          entry point (Elastic Beanstalk looks for `application`)
config.py               settings and database selection
taskflow/
  __init__.py           app factory, /health, error pages
  models.py             SQLAlchemy models (6 tables)
  utils.py              JWT helpers, login/admin decorators
  auth.py               Module 1: auth & profile
  projects.py           Module 2: projects & team
  tasks.py              Module 3: tasks, comments, CSV
  dashboard.py          Module 4: dashboard & reports
  admin.py              Module 5: admin panel
  api.py                JSON REST API
  seed.py               demo data
  templates/, static/   UI (HTML, CSS, JS)
tests/test_app.py       24 automated tests
deploy/                 schema.sql, create_users.sql, ec2_setup.sh, nginx and systemd files
.ebextensions/          Elastic Beanstalk config
Procfile                gunicorn start command for Elastic Beanstalk
make_bundle.py          builds taskflow-eb.zip for S3 / Elastic Beanstalk
```
