"""Database models (6 tables): users, projects, project_members, tasks, comments, activity_logs."""
import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False, default="")
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="member")   # admin | member
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_login = db.Column(db.DateTime)

    memberships = db.relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def display_name(self):
        return self.full_name or self.username

    @property
    def initials(self):
        parts = self.display_name.split()
        return "".join(p[0] for p in parts[:2]).upper() or "?"

    def to_dict(self):
        return {"id": self.id, "username": self.username, "email": self.email,
                "full_name": self.full_name, "role": self.role}


class Project(db.Model):
    __tablename__ = "projects"
    COLORS = ["#4f46e5", "#0891b2", "#059669", "#d97706", "#dc2626", "#db2777", "#7c3aed", "#475569"]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    color = db.Column(db.String(7), nullable=False, default="#4f46e5")
    status = db.Column(db.String(20), nullable=False, default="Active")    # Active | Archived
    due_date = db.Column(db.Date)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    owner = db.relationship("User")
    members = db.relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    tasks = db.relationship("Task", back_populates="project", cascade="all, delete-orphan",
                            order_by="Task.id.desc()")

    def member_role(self, user):
        for m in self.members:
            if m.user_id == user.id:
                return m.role
        return None

    def is_member(self, user):
        return user.is_admin or self.member_role(user) is not None

    def can_manage(self, user):
        return user.is_admin or self.member_role(user) == "owner"

    @property
    def progress(self):
        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t.status == "Done")
        return round(done * 100 / total) if total else 0

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description,
                "status": self.status, "owner": self.owner.username,
                "due_date": self.due_date.isoformat() if self.due_date else None,
                "progress": self.progress, "task_count": len(self.tasks)}


class ProjectMember(db.Model):
    __tablename__ = "project_members"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="member")   # owner | member
    added_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    __table_args__ = (db.UniqueConstraint("project_id", "user_id", name="uq_project_user"),)

    project = db.relationship("Project", back_populates="members")
    user = db.relationship("User", back_populates="memberships")


class Task(db.Model):
    __tablename__ = "tasks"
    STATUSES = ["To Do", "In Progress", "In Review", "Done"]
    PRIORITIES = ["Low", "Medium", "High", "Urgent"]

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(20), nullable=False, default="To Do")
    priority = db.Column(db.String(20), nullable=False, default="Medium")
    due_date = db.Column(db.Date)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    completed_at = db.Column(db.DateTime)

    project = db.relationship("Project", back_populates="tasks")
    assignee = db.relationship("User", foreign_keys=[assignee_id])
    creator = db.relationship("User", foreign_keys=[created_by])
    comments = db.relationship("Comment", back_populates="task", cascade="all, delete-orphan",
                               order_by="Comment.created_at")

    @property
    def is_overdue(self):
        return bool(self.due_date and self.status != "Done" and self.due_date < datetime.date.today())

    @property
    def slug(self):
        return self.status.lower().replace(" ", "-")

    def set_status(self, status):
        self.status = status
        self.completed_at = utcnow() if status == "Done" else None

    def to_dict(self):
        return {"id": self.id, "title": self.title, "description": self.description,
                "status": self.status, "priority": self.priority, "project_id": self.project_id,
                "project": self.project.name,
                "assignee": self.assignee.username if self.assignee else None,
                "due_date": self.due_date.isoformat() if self.due_date else None,
                "overdue": self.is_overdue, "created_at": self.created_at.isoformat()}


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    task = db.relationship("Task", back_populates="comments")
    author = db.relationship("User")


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"))
    action = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    user = db.relationship("User")
    project = db.relationship("Project")
