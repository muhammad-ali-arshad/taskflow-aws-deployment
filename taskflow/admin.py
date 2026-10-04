"""Module 5 - Administration (manage users, roles, activation, system overview)."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort
from sqlalchemy import func

from .models import db, User, Project, Task, Comment, ActivityLog
from .utils import admin_required, log_activity

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@admin_required
def index():
    q = request.args.get("q", "").strip()
    users_q = User.query
    if q:
        users_q = users_q.filter((User.username.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%")) |
                                 (User.full_name.ilike(f"%{q}%")))
    users = users_q.order_by(User.created_at.desc()).all()
    task_counts = dict(db.session.query(Task.assignee_id, func.count(Task.id))
                       .group_by(Task.assignee_id).all())
    overview = {
        "users": User.query.count(),
        "active_users": User.query.filter_by(is_active=True).count(),
        "projects": Project.query.count(),
        "tasks": Task.query.count(),
        "comments": Comment.query.count(),
        "engine": db.engine.dialect.name,
    }
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(15).all()
    return render_template("admin/index.html", users=users, task_counts=task_counts,
                           overview=overview, logs=logs, q=q)


def _target_user(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.id == g.user.id:
        flash("You can't change your own admin account here.", "error")
        return None
    return user


@bp.route("/users/<int:user_id>/role", methods=["POST"])
@admin_required
def change_role(user_id):
    user = _target_user(user_id)
    if user:
        role = request.form.get("role")
        if role not in ("admin", "member"):
            flash("Invalid role.", "error")
        else:
            user.role = role
            log_activity(f"changed role of {user.username} to {role}")
            db.session.commit()
            flash(f"{user.username} is now {role}.", "success")
    return redirect(url_for("admin.index"))


@bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_active(user_id):
    user = _target_user(user_id)
    if user:
        user.is_active = not user.is_active
        log_activity(f"{'activated' if user.is_active else 'deactivated'} {user.username}")
        db.session.commit()
        flash(f"{user.username} {'activated' if user.is_active else 'deactivated'}.", "success")
    return redirect(url_for("admin.index"))


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = _target_user(user_id)
    if user:
        if Project.query.filter_by(owner_id=user.id).count():
            # hand their projects over to the admin doing the delete
            for p in Project.query.filter_by(owner_id=user.id):
                p.owner_id = g.user.id
                if not p.member_role(g.user):
                    from .models import ProjectMember
                    db.session.add(ProjectMember(project_id=p.id, user_id=g.user.id, role="owner"))
        Task.query.filter_by(assignee_id=user.id).update({"assignee_id": None})
        Task.query.filter_by(created_by=user.id).update({"created_by": None})
        Comment.query.filter_by(user_id=user.id).delete()
        ActivityLog.query.filter_by(user_id=user.id).delete()
        name = user.username
        db.session.delete(user)
        log_activity(f"deleted user {name}")
        db.session.commit()
        flash(f"User {name} deleted.", "success")
    return redirect(url_for("admin.index"))
