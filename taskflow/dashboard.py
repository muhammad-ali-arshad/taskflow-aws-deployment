"""Module 4 - Dashboard & reports (stats, workload, overdue, project progress, activity feed)."""
import datetime

from flask import Blueprint, render_template, g, redirect, url_for
from sqlalchemy import func

from .models import db, Project, Task, ActivityLog, User
from .utils import login_required, visible_project_ids

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def home():
    return redirect(url_for("dashboard.index") if g.user else url_for("auth.login"))


@bp.route("/dashboard")
@login_required
def index():
    ids = visible_project_ids(g.user) or [-1]
    today = datetime.date.today()
    base = Task.query.filter(Task.project_id.in_(ids))

    status_counts = dict(db.session.query(Task.status, func.count(Task.id))
                         .filter(Task.project_id.in_(ids)).group_by(Task.status).all())
    priority_counts = dict(db.session.query(Task.priority, func.count(Task.id))
                           .filter(Task.project_id.in_(ids), Task.status != "Done")
                           .group_by(Task.priority).all())
    total = sum(status_counts.values())
    done = status_counts.get("Done", 0)

    stats = {
        "total": total,
        "done": done,
        "open": total - done,
        "overdue": base.filter(Task.due_date < today, Task.status != "Done").count(),
        "mine": base.filter(Task.assignee_id == g.user.id, Task.status != "Done").count(),
        "completion": round(done * 100 / total) if total else 0,
        "projects": Project.query.filter(Project.id.in_(ids), Project.status == "Active").count(),
    }

    my_tasks = (base.filter(Task.assignee_id == g.user.id, Task.status != "Done")
                .order_by(Task.due_date.is_(None), Task.due_date.asc()).limit(8).all())
    upcoming = (base.filter(Task.status != "Done", Task.due_date >= today,
                            Task.due_date <= today + datetime.timedelta(days=7))
                .order_by(Task.due_date.asc()).limit(6).all())
    overdue = (base.filter(Task.due_date < today, Task.status != "Done")
               .order_by(Task.due_date.asc()).limit(6).all())
    projects = (Project.query.filter(Project.id.in_(ids), Project.status == "Active")
                .order_by(Project.created_at.desc()).limit(6).all())
    activity = (ActivityLog.query.filter((ActivityLog.project_id.in_(ids)) |
                                         (ActivityLog.user_id == g.user.id))
                .order_by(ActivityLog.created_at.desc()).limit(12).all())

    # completed per day for the last 7 days
    week = []
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        start = datetime.datetime.combine(day, datetime.time.min)
        end = start + datetime.timedelta(days=1)
        count = base.filter(Task.completed_at >= start, Task.completed_at < end).count()
        week.append((day.strftime("%a"), count))

    # workload per team member (open tasks)
    workload = (db.session.query(User, func.count(Task.id))
                .join(Task, Task.assignee_id == User.id)
                .filter(Task.project_id.in_(ids), Task.status != "Done")
                .group_by(User.id).order_by(func.count(Task.id).desc()).limit(6).all())

    return render_template("dashboard.html", stats=stats, status_counts=status_counts,
                           priority_counts=priority_counts, my_tasks=my_tasks, upcoming=upcoming,
                           overdue=overdue, projects=projects, activity=activity, week=week,
                           week_max=max([c for _, c in week] + [1]), workload=workload,
                           workload_max=max([c for _, c in workload] + [1]))
