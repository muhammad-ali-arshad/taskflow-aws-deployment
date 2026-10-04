"""Module 1 - Authentication & user profile (signup, login with JWT, logout, profile, password)."""
import re

from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app

from .models import db, User, Project, ProjectMember, Task, utcnow
from .utils import create_token, login_required, log_activity

bp = Blueprint("auth", __name__)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_password(pw):
    if len(pw) < 6:
        return "Password must be at least 6 characters."
    if not re.search(r"\d", pw) or not re.search(r"[A-Za-z]", pw):
        return "Password must contain at least one letter and one number."
    return None


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if g.user:
        return redirect(url_for("dashboard.index"))
    form = request.form
    if request.method == "POST":
        username = form.get("username", "").strip()
        email = form.get("email", "").strip().lower()
        full_name = form.get("full_name", "").strip()
        password = form.get("password", "")
        confirm = form.get("confirm_password", "")

        error = None
        if not USERNAME_RE.match(username):
            error = "Username must be 3-30 characters (letters, numbers, _ or .)."
        elif not EMAIL_RE.match(email):
            error = "Please enter a valid email address."
        elif validate_password(password):
            error = validate_password(password)
        elif password != confirm:
            error = "Passwords do not match."
        elif User.query.filter_by(username=username).first():
            error = "Username already exists."
        elif User.query.filter_by(email=email).first():
            error = "Email is already registered."

        if error:
            flash(error, "error")
            return render_template("auth/signup.html", form=form), 400

        is_first_user = User.query.count() == 0
        user = User(username=username, email=email, full_name=full_name,
                    role="admin" if is_first_user else "member")
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # every new user gets a personal project to start with
        personal = Project(name="Personal", description="My personal tasks", owner_id=user.id,
                           color="#4f46e5")
        db.session.add(personal)
        db.session.flush()
        db.session.add(ProjectMember(project_id=personal.id, user_id=user.id, role="owner"))
        db.session.commit()

        msg = "Account created! Please log in."
        if is_first_user:
            msg += " As the first user you are the administrator."
        flash(msg, "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/signup.html", form={})


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        login_id = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter((User.username == login_id) | (User.email == login_id.lower())).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash("Your account has been deactivated. Contact the administrator.", "error")
                return render_template("auth/login.html"), 403
            user.last_login = utcnow()
            g.user = user
            log_activity("logged in")
            db.session.commit()
            nxt = request.args.get("next", "")
            resp = redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard.index"))
            resp.set_cookie("token", create_token(user), httponly=True, samesite="Lax",
                            secure=current_app.config["COOKIE_SECURE"],
                            max_age=current_app.config["JWT_EXPIRY_HOURS"] * 3600)
            flash(f"Welcome back, {user.display_name}!", "success")
            return resp
        flash("Wrong username or password.", "error")
        return render_template("auth/login.html"), 401
    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    resp = redirect(url_for("auth.login"))
    resp.delete_cookie("token")
    flash("You have been logged out.", "info")
    return resp


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = g.user
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        if not EMAIL_RE.match(email):
            flash("Please enter a valid email address.", "error")
        elif User.query.filter(User.email == email, User.id != user.id).first():
            flash("That email is used by another account.", "error")
        else:
            user.full_name = full_name
            user.email = email
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("auth.profile"))
    stats = {
        "projects": len(user.memberships),
        "assigned": Task.query.filter_by(assignee_id=user.id).count(),
        "completed": Task.query.filter_by(assignee_id=user.id, status="Done").count(),
    }
    return render_template("auth/profile.html", user=user, stats=stats)


@bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")
    if not g.user.check_password(current):
        flash("Current password is incorrect.", "error")
    elif validate_password(new):
        flash(validate_password(new), "error")
    elif new != confirm:
        flash("New passwords do not match.", "error")
    else:
        g.user.set_password(new)
        db.session.commit()
        flash("Password changed successfully.", "success")
    return redirect(url_for("auth.profile"))
