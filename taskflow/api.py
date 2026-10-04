"""Small JSON REST API (JWT Bearer token) - handy for automated testing."""
from flask import Blueprint, jsonify, request, g

from .models import db, User, Project, Task
from .utils import create_token, api_login_required, visible_project_ids

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or request.form
    user = User.query.filter_by(username=(data.get("username") or "").strip()).first()
    if not user or not user.check_password(data.get("password") or "") or not user.is_active:
        return jsonify(error="Invalid credentials"), 401
    return jsonify(token=create_token(user), user=user.to_dict())


@bp.route("/me")
@api_login_required
def me():
    return jsonify(g.user.to_dict())


@bp.route("/projects")
@api_login_required
def projects():
    items = Project.query.filter(Project.id.in_(visible_project_ids(g.user) or [-1])).all()
    return jsonify([p.to_dict() for p in items])


@bp.route("/tasks", methods=["GET"])
@api_login_required
def tasks():
    query = Task.query.filter(Task.project_id.in_(visible_project_ids(g.user) or [-1]))
    if request.args.get("status"):
        query = query.filter_by(status=request.args["status"])
    return jsonify([t.to_dict() for t in query.order_by(Task.id.desc()).all()])


@bp.route("/tasks", methods=["POST"])
@api_login_required
def create_task():
    data = request.get_json(silent=True) or {}
    project = db.session.get(Project, data.get("project_id") or 0)
    if not project or not project.is_member(g.user):
        return jsonify(error="Project not found"), 404
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify(error="Title is required"), 400
    priority = data.get("priority", "Medium")
    if priority not in Task.PRIORITIES:
        return jsonify(error="Invalid priority"), 400
    task = Task(project_id=project.id, title=title[:200], description=data.get("description", ""),
                priority=priority, created_by=g.user.id)
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@bp.route("/stats")
@api_login_required
def stats():
    query = Task.query.filter(Task.project_id.in_(visible_project_ids(g.user) or [-1]))
    return jsonify({s: query.filter_by(status=s).count() for s in Task.STATUSES})
