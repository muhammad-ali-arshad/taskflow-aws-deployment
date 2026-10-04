"""Module 2 - Projects & team collaboration (CRUD, members, archive, Kanban board)."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, g

from .models import db, User, Project, ProjectMember, Task, ActivityLog
from .utils import login_required, get_project_or_404, log_activity, parse_date

bp = Blueprint("projects", __name__, url_prefix="/projects")


def _project_from_form(project):
    name = request.form.get("name", "").strip()
    if not name:
        return "Project name is required."
    if len(name) > 120:
        return "Project name is too long (max 120 characters)."
    project.name = name
    project.description = request.form.get("description", "").strip()
    color = request.form.get("color", "#4f46e5")
    project.color = color if color in Project.COLORS else Project.COLORS[0]
    project.due_date = parse_date(request.form.get("due_date"))
    return None


@bp.route("/")
@login_required
def list_projects():
    show = request.args.get("show", "Active")
    if g.user.is_admin and request.args.get("scope") == "all":
        query = Project.query
    else:
        query = Project.query.join(ProjectMember).filter(ProjectMember.user_id == g.user.id)
    if show in ("Active", "Archived"):
        query = query.filter(Project.status == show)
    projects = query.order_by(Project.created_at.desc()).all()
    return render_template("projects/list.html", projects=projects, show=show)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create_project():
    project = Project(owner_id=g.user.id)
    if request.method == "POST":
        error = _project_from_form(project)
        if error:
            flash(error, "error")
            return render_template("projects/form.html", project=project, colors=Project.COLORS), 400
        db.session.add(project)
        db.session.flush()
        db.session.add(ProjectMember(project_id=project.id, user_id=g.user.id, role="owner"))
        log_activity(f"created project “{project.name}”", project.id)
        db.session.commit()
        flash("Project created.", "success")
        return redirect(url_for("projects.view_project", project_id=project.id))
    return render_template("projects/form.html", project=project, colors=Project.COLORS)


@bp.route("/<int:project_id>")
@login_required
def view_project(project_id):
    project = get_project_or_404(project_id)
    view = request.args.get("view", "board")
    columns = {s: [t for t in project.tasks if t.status == s] for s in Task.STATUSES}
    activity = (ActivityLog.query.filter_by(project_id=project.id)
                .order_by(ActivityLog.created_at.desc()).limit(10).all())
    member_ids = {m.user_id for m in project.members}
    candidates = (User.query.filter(~User.id.in_(member_ids), User.is_active.is_(True))
                  .order_by(User.username).all())
    return render_template("projects/view.html", project=project, columns=columns, view=view,
                           activity=activity, candidates=candidates,
                           can_manage=project.can_manage(g.user))


@bp.route("/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit_project(project_id):
    project = get_project_or_404(project_id, manage=True)
    if request.method == "POST":
        error = _project_from_form(project)
        if error:
            flash(error, "error")
            return render_template("projects/form.html", project=project, colors=Project.COLORS), 400
        log_activity(f"updated project “{project.name}”", project.id)
        db.session.commit()
        flash("Project updated.", "success")
        return redirect(url_for("projects.view_project", project_id=project.id))
    return render_template("projects/form.html", project=project, colors=Project.COLORS)


@bp.route("/<int:project_id>/archive", methods=["POST"])
@login_required
def toggle_archive(project_id):
    project = get_project_or_404(project_id, manage=True)
    project.status = "Active" if project.status == "Archived" else "Archived"
    log_activity(f"{'archived' if project.status == 'Archived' else 'restored'} project “{project.name}”",
                 project.id)
    db.session.commit()
    flash(f"Project {'archived' if project.status == 'Archived' else 'restored'}.", "success")
    return redirect(url_for("projects.view_project", project_id=project.id))


@bp.route("/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project(project_id):
    project = get_project_or_404(project_id, manage=True)
    name = project.name
    ActivityLog.query.filter_by(project_id=project.id).delete()
    db.session.delete(project)
    log_activity(f"deleted project “{name}”")
    db.session.commit()
    flash(f"Project “{name}” deleted.", "success")
    return redirect(url_for("projects.list_projects"))


@bp.route("/<int:project_id>/members", methods=["POST"])
@login_required
def add_member(project_id):
    project = get_project_or_404(project_id, manage=True)
    username = request.form.get("username", "").strip()
    user = User.query.filter_by(username=username).first()
    if not user:
        flash(f"No user named “{username}”.", "error")
    elif project.member_role(user):
        flash(f"{user.username} is already a member.", "warning")
    else:
        db.session.add(ProjectMember(project_id=project.id, user_id=user.id, role="member"))
        log_activity(f"added {user.username} to “{project.name}”", project.id)
        db.session.commit()
        flash(f"{user.username} added to the project.", "success")
    return redirect(url_for("projects.view_project", project_id=project.id, view="team"))


@bp.route("/<int:project_id>/members/<int:user_id>/remove", methods=["POST"])
@login_required
def remove_member(project_id, user_id):
    project = get_project_or_404(project_id, manage=True)
    member = ProjectMember.query.filter_by(project_id=project.id, user_id=user_id).first_or_404()
    if member.role == "owner":
        flash("The project owner cannot be removed.", "error")
    else:
        # unassign their tasks in this project
        Task.query.filter_by(project_id=project.id, assignee_id=user_id).update({"assignee_id": None})
        log_activity(f"removed {member.user.username} from “{project.name}”", project.id)
        db.session.delete(member)
        db.session.commit()
        flash("Member removed.", "success")
    return redirect(url_for("projects.view_project", project_id=project.id, view="team"))
