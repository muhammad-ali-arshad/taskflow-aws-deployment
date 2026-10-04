"""Automated tests:  pytest -q"""
import datetime
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TestConfig  # noqa: E402
from taskflow import create_app  # noqa: E402
from taskflow.models import db, User, Project, Task, Comment  # noqa: E402


@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def signup(client, username="alice", password="Secret123", email=None):
    return client.post("/signup", data={"username": username, "email": email or f"{username}@x.com",
                                        "full_name": username.title(), "password": password,
                                        "confirm_password": password}, follow_redirects=True)


def login(client, username="alice", password="Secret123"):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


def make_project(client, name="Apollo"):
    client.post("/projects/new", data={"name": name, "description": "d", "color": "#4f46e5"})
    return Project.query.filter_by(name=name).first()


# ---------------- Module 1: authentication ----------------
def test_signup_creates_user_and_first_is_admin(client, app):
    r = signup(client)
    assert b"Account created" in r.data
    with app.app_context():
        u = User.query.filter_by(username="alice").one()
        assert u.is_admin and u.password_hash != "Secret123"


def test_second_user_is_member(client, app):
    signup(client, "alice")
    signup(client, "bob")
    with app.app_context():
        assert User.query.filter_by(username="bob").one().role == "member"


def test_signup_rejects_duplicate_username(client):
    signup(client)
    r = signup(client, email="other@x.com")
    assert r.status_code == 400 and b"Username already exists" in r.data


def test_signup_rejects_weak_password(client):
    r = signup(client, password="abc")
    assert r.status_code == 400 and b"at least 6" in r.data


def test_login_success_sets_jwt_cookie(client):
    signup(client)
    r = client.post("/login", data={"username": "alice", "password": "Secret123"})
    assert r.status_code == 302 and "token=" in r.headers.get("Set-Cookie", "")


def test_login_wrong_password(client):
    signup(client)
    r = login(client, password="Wrong999")
    assert r.status_code == 401 and b"Wrong username or password" in r.data


def test_protected_page_redirects_when_logged_out(client):
    r = client.get("/dashboard")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_logout_clears_session(client):
    signup(client); login(client)
    client.get("/logout")
    assert client.get("/dashboard").status_code == 302


def test_change_password(client):
    signup(client); login(client)
    client.post("/profile/password", data={"current_password": "Secret123", "new_password": "Newpass456",
                                           "confirm_password": "Newpass456"})
    client.get("/logout")
    assert b"Hello" in login(client, password="Newpass456").data


# ---------------- Module 2: projects ----------------
def test_personal_project_created_on_signup(client, app):
    signup(client)
    with app.app_context():
        assert Project.query.filter_by(name="Personal").count() == 1


def test_create_edit_and_delete_project(client, app):
    signup(client); login(client)
    with app.app_context():
        p = make_project(client)
        assert p is not None
        client.post(f"/projects/{p.id}/edit", data={"name": "Apollo 2", "color": "#059669"})
        assert db.session.get(Project, p.id).name == "Apollo 2"
        client.post(f"/projects/{p.id}/delete")
        assert db.session.get(Project, p.id) is None


def test_add_member_and_non_member_forbidden(client, app):
    signup(client, "alice"); signup(client, "bob"); signup(client, "carol")
    login(client, "alice")
    with app.app_context():
        p = make_project(client)
        client.post(f"/projects/{p.id}/members", data={"username": "bob"})
        client.get("/logout")
        login(client, "bob")
        assert client.get(f"/projects/{p.id}").status_code == 200
        client.get("/logout")
        login(client, "carol")
        assert client.get(f"/projects/{p.id}").status_code == 403


def test_archive_project(client, app):
    signup(client); login(client)
    with app.app_context():
        p = make_project(client)
        client.post(f"/projects/{p.id}/archive")
        assert db.session.get(Project, p.id).status == "Archived"


# ---------------- Module 3: tasks ----------------
def test_create_task_and_view(client, app):
    signup(client); login(client)
    with app.app_context():
        p = make_project(client)
        client.post("/tasks/new", data={"project_id": p.id, "title": "Write tests", "status": "To Do",
                                        "priority": "High", "due_date": "2030-01-01"})
        t = Task.query.filter_by(title="Write tests").one()
        assert t.priority == "High" and t.due_date == datetime.date(2030, 1, 1)
        assert b"Write tests" in client.get(f"/tasks/{t.id}").data


def test_task_requires_title(client, app):
    signup(client); login(client)
    with app.app_context():
        p = make_project(client)
        r = client.post("/tasks/new", data={"project_id": p.id, "title": "  "})
        assert r.status_code == 400 and Task.query.count() == 0


def test_status_change_sets_completed_at(client, app):
    signup(client); login(client)
    with app.app_context():
        p = make_project(client)
        client.post("/tasks/new", data={"project_id": p.id, "title": "T1"})
        t = Task.query.one()
        r = client.post(f"/tasks/{t.id}/status", json={"status": "Done"})
        assert r.get_json()["progress"] == 100
        assert db.session.get(Task, t.id).completed_at is not None


def test_search_and_filter_tasks(client, app):
    signup(client); login(client)
    with app.app_context():
        p = make_project(client)
        for title, pr in [("Fix login bug", "Urgent"), ("Design logo", "Low")]:
            client.post("/tasks/new", data={"project_id": p.id, "title": title, "priority": pr})
        r = client.get("/tasks/?q=login")
        assert b"Fix login bug" in r.data and b"Design logo" not in r.data
        r = client.get("/tasks/?priority=Low")
        assert b"Design logo" in r.data and b"Fix login bug" not in r.data


def test_comment_and_delete_task(client, app):
    signup(client); login(client)
    with app.app_context():
        p = make_project(client)
        client.post("/tasks/new", data={"project_id": p.id, "title": "T1"})
        t = Task.query.one()
        client.post(f"/tasks/{t.id}/comments", data={"body": "Nice work"})
        assert Comment.query.count() == 1
        client.post(f"/tasks/{t.id}/delete")
        assert Task.query.count() == 0 and Comment.query.count() == 0


def test_export_csv(client, app):
    signup(client); login(client)
    with app.app_context():
        p = make_project(client)
        client.post("/tasks/new", data={"project_id": p.id, "title": "CSV task"})
        r = client.get("/tasks/export.csv")
        assert r.mimetype == "text/csv" and b"CSV task" in r.data


# ---------------- Module 4/5: dashboard, admin, API, health ----------------
def test_dashboard_loads(client):
    signup(client); login(client)
    r = client.get("/dashboard")
    assert r.status_code == 200 and b"Completion rate" in r.data


def test_admin_panel_only_for_admin(client):
    signup(client, "alice"); signup(client, "bob")
    login(client, "bob")
    assert client.get("/admin/").status_code == 403
    client.get("/logout")
    login(client, "alice")
    assert client.get("/admin/").status_code == 200


def test_api_login_and_tasks(client):
    signup(client)
    token = client.post("/api/login", json={"username": "alice", "password": "Secret123"}).get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    pid = client.get("/api/projects", headers=headers).get_json()[0]["id"]
    r = client.post("/api/tasks", json={"project_id": pid, "title": "From API"}, headers=headers)
    assert r.status_code == 201
    assert client.get("/api/tasks", headers=headers).get_json()[0]["title"] == "From API"
    assert client.get("/api/tasks").status_code == 401


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json()["database"] == "connected"


def test_404_page(client):
    assert client.get("/does-not-exist").status_code == 404
