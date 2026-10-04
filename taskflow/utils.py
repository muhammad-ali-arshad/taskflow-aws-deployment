"""JWT helpers, login decorators and small shared helpers."""
import datetime
from functools import wraps

import jwt
from flask import current_app, request, g, redirect, url_for, flash, abort, jsonify

from .models import db, User, Project, ActivityLog


# ---------------- JWT ----------------
def create_token(user):
    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "exp": datetime.datetime.now(datetime.timezone.utc)
               + datetime.timedelta(hours=current_app.config["JWT_EXPIRY_HOURS"]),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def decode_token(token):
    return jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])


def load_current_user():
    """Runs before every request: reads the JWT from the cookie (or Authorization header)."""
    g.user = None
    g.token_error = None
    token = request.cookies.get("token")
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        return
    try:
        data = decode_token(token)
    except jwt.ExpiredSignatureError:
        g.token_error = "Session expired. Please log in again."
        return
    except jwt.InvalidTokenError:
        g.token_error = "Invalid session. Please log in again."
        return
    user = db.session.get(User, data.get("user_id"))
    if user and user.is_active:
        g.user = user


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if g.user is None:
            flash(g.get("token_error") or "Please log in first.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not g.user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def api_login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return jsonify(error=g.get("token_error") or "Authentication required"), 401
        return f(*args, **kwargs)
    return wrapper


# ---------------- helpers ----------------
def get_project_or_404(project_id, manage=False):
    project = db.session.get(Project, project_id) or abort(404)
    if not project.is_member(g.user):
        abort(403)
    if manage and not project.can_manage(g.user):
        abort(403)
    return project


def visible_project_ids(user):
    """Projects shown in the user's dashboard / task lists (the ones they belong to).
    Admins can still open any project directly, and manage everything from the Admin panel."""
    return [m.project_id for m in user.memberships]


def log_activity(action, project_id=None):
    db.session.add(ActivityLog(user_id=g.user.id if g.get("user") else None,
                               project_id=project_id, action=action[:255]))


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
