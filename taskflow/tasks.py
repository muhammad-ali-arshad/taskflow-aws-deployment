"""Module 3 - Task management (CRUD, assign, priority, due dates, search/filter, comments, CSV export)."""
import csv
import io
import datetime

from flask import (Blueprint, render_template, request, redirect, url_for, flash, g, abort,
                   jsonify, Response, current_app)
from sqlalchemy import or_

from .models import db, User, Project, ProjectMember, Task, Comment
from .utils import login_required, get_project_or_404, visible_project_ids, log_activity, parse_date

bp = Blueprint("tasks", __name__, url_prefix="/tasks")


def get_task_or_404(task_id):
    task = db.session.get(Task, task_id) or abort(404)
    if not task.project.is_member(g.user):
        abort(403)
    return task


def can_edit_task(task):
    return (task.project.can_manage(g.user) or task.created_by == g.user.id
            or task.assignee_id == g.user.id)


def _writable_projects():
    if g.user.is_admin:
        return Project.query.filter_by(status="Active").order_by(Project.name).all()
    return (Project.query.join(ProjectMember).filter(ProjectMember.user_id == g.user.id,
                                                     Project.status == "Active")
            .order_by(Project.name).all())


def filtered_query():
    """Builds the task query from the ?q=&status=&priority=&project=&assignee=&due=&sort= filters."""
    args = request.args
    query = Task.query.filter(Task.project_id.in_(visible_project_ids(g.user) or [-1]))
    if args.get("q"):
        like = f"%{args['q'].strip()}%"
        query = query.filter(or_(Task.title.ilike(like), Task.description.ilike(like)))
    if args.get("status") in Task.STATUSES:
        query = query.filter(Task.status == args["status"])
    elif args.get("status") == "open":
        query = query.filter(Task.status != "Done")
    if args.get("priority") in Task.PRIORITIES:
        query = query.filter(Task.priority == args["priority"])
    if args.get("project", "").isdigit():
        query = query.filter(Task.project_id == int(args["project"]))
    if args.get("assignee") == "me":
        query = query.filter(Task.assignee_id == g.user.id)
    elif args.get("assignee") == "none":
        query = query.filter(Task.assignee_id.is_(None))
    today = datetime.date.today()
    if args.get("due") == "overdue":
        query = query.filter(Task.due_date < today, Task.status != "Done")
    elif args.get("due") == "week":
        query = query.filter(Task.due_date >= today, Task.due_date <= today + datetime.timedelta(days=7))

    sort = args.get("sort", "newest")
    if sort == "due":
        query = query.order_by(Task.due_date.is_(None), Task.due_date.asc())
    elif sort == "priority":
        order = db.case({p: i for i, p in enumerate(reversed(Task.PRIORITIES))}, value=Task.priority)
        query = query.order_by(order, Task.id.desc())
    elif sort == "title":
        query = query.order_by(Task.title.asc())
    else:
        query = query.order_by(Task.id.desc())
    return query


@bp.route("/")
@login_required
def list_tasks():
    page = request.args.get("page", 1, type=int)
    pagination = filtered_query().paginate(page=page, per_page=current_app.config["TASKS_PER_PAGE"],
                                           error_out=False)
    projects = Project.query.filter(Project.id.in_(visible_project_ids(g.user) or [-1])) \
        .order_by(Project.name).all()
    args = {k: v for k, v in request.args.items() if k != "page"}
    return render_template("tasks/list.html", pagination=pagination, tasks=pagination.items,
                           projects=projects, args=args)


@bp.route("/export.csv")
@login_required
def export_csv():
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "Title", "Project", "Status", "Priority", "Assignee", "Due date",
                     "Created", "Completed"])
    for t in filtered_query().all():
        writer.writerow([t.id, t.title, t.project.name, t.status, t.priority,
                         t.assignee.username if t.assignee else "",
                         t.due_date.isoformat() if t.due_date else "",
                         t.created_at.strftime("%Y-%m-%d %H:%M"),
                         t.completed_at.strftime("%Y-%m-%d %H:%M") if t.completed_at else ""])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=tasks.csv"})


def _task_from_form(task, project):
    title = request.form.get("title", "").strip()
    if not title:
        return "Task title is required."
    if len(title) > 200:
        return "Task title is too long (max 200 characters)."
    status = request.form.get("status", task.status or "To Do")
    priority = request.form.get("priority", task.priority or "Medium")
    if status not in Task.STATUSES or priority not in Task.PRIORITIES:
        return "Invalid status or priority."
    assignee_id = request.form.get("assignee_id", type=int)
    if assignee_id:
        assignee = db.session.get(User, assignee_id)
        if not assignee or not project.member_role(assignee):
            return "Assignee must be a member of the project."
    task.title = title
    task.description = request.form.get("description", "").strip()
    task.priority = priority
    task.due_date = parse_date(request.form.get("due_date"))
    task.assignee_id = assignee_id or None
    if task.status != status or task.id is None:
        task.set_status(status)
    return None


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create_task():
    projects = _writable_projects()
    if not projects:
        flash("Create a project first.", "warning")
        return redirect(url_for("projects.create_project"))
    project_id = request.values.get("project_id", type=int) or projects[0].id
    project = get_project_or_404(project_id)
    if project.status == "Archived":
        flash("You can't add tasks to an archived project.", "error")
        return redirect(url_for("projects.view_project", project_id=project.id))
    task = Task(project_id=project.id, status=request.args.get("status", "To Do"))
    if request.method == "POST":
        error = _task_from_form(task, project)
        if error:
            flash(error, "error")
            return render_template("tasks/form.html", task=task, project=project, projects=projects), 400
        task.created_by = g.user.id
        db.session.add(task)
        log_activity(f"created task “{task.title}”", project.id)
        db.session.commit()
        flash("Task created.", "success")
        if request.form.get("next") == "project":
            return redirect(url_for("projects.view_project", project_id=project.id))
        return redirect(url_for("tasks.view_task", task_id=task.id))
    return render_template("tasks/form.html", task=task, project=project, projects=projects)


@bp.route("/<int:task_id>")
@login_required
def view_task(task_id):
    task = get_task_or_404(task_id)
    return render_template("tasks/view.html", task=task, can_edit=can_edit_task(task))


@bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = get_task_or_404(task_id)
    if not can_edit_task(task):
        abort(403)
    if request.method == "POST":
        error = _task_from_form(task, task.project)
        if error:
            flash(error, "error")
            return render_template("tasks/form.html", task=task, project=task.project, projects=None), 400
        log_activity(f"updated task “{task.title}”", task.project_id)
        db.session.commit()
        flash("Task updated.", "success")
        return redirect(url_for("tasks.view_task", task_id=task.id))
    return render_template("tasks/form.html", task=task, project=task.project, projects=None)


@bp.route("/<int:task_id>/status", methods=["POST"])
@login_required
def update_status(task_id):
    """Quick status change - used by the Kanban drag & drop and the status buttons."""
    task = get_task_or_404(task_id)
    status = request.form.get("status") or (request.get_json(silent=True) or {}).get("status")
    if status not in Task.STATUSES:
        if request.is_json:
            return jsonify(error="Invalid status"), 400
        flash("Invalid status.", "error")
        return redirect(request.referrer or url_for("tasks.view_task", task_id=task.id))
    old = task.status
    task.set_status(status)
    log_activity(f"moved “{task.title}” from {old} to {status}", task.project_id)
    db.session.commit()
    if request.is_json:
        return jsonify(ok=True, task=task.to_dict(), progress=task.project.progress)
    flash(f"Status changed to {status}.", "success")
    return redirect(request.referrer or url_for("tasks.view_task", task_id=task.id))


@bp.route("/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    task = get_task_or_404(task_id)
    if not (task.project.can_manage(g.user) or task.created_by == g.user.id):
        abort(403)
    project_id = task.project_id
    log_activity(f"deleted task “{task.title}”", project_id)
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "success")
    if request.form.get("next") == "project":
        return redirect(url_for("projects.view_project", project_id=project_id))
    return redirect(url_for("tasks.list_tasks"))


@bp.route("/<int:task_id>/comments", methods=["POST"])
@login_required
def add_comment(task_id):
    task = get_task_or_404(task_id)
    body = request.form.get("body", "").strip()
    if not body:
        flash("Comment can't be empty.", "error")
    else:
        db.session.add(Comment(task_id=task.id, user_id=g.user.id, body=body[:2000]))
        log_activity(f"commented on “{task.title}”", task.project_id)
        db.session.commit()
        flash("Comment added.", "success")
    return redirect(url_for("tasks.view_task", task_id=task.id) + "#comments")


@bp.route("/comments/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = db.session.get(Comment, comment_id) or abort(404)
    task = get_task_or_404(comment.task_id)
    if comment.user_id != g.user.id and not task.project.can_manage(g.user):
        abort(403)
    db.session.delete(comment)
    db.session.commit()
    flash("Comment deleted.", "success")
    return redirect(url_for("tasks.view_task", task_id=task.id) + "#comments")
