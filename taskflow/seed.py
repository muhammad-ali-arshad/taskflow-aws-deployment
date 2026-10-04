"""Demo data: run `flask --app application seed-demo` (or `python seed.py`)."""
import datetime
import random

from .models import utcnow, db, User, Project, ProjectMember, Task, Comment, ActivityLog


def seed_demo():
    if User.query.filter_by(username="admin").first():
        return "Demo data already present (user 'admin' exists)."
    random.seed(7)
    today = datetime.date.today()

    def make_user(username, name, role="member"):
        u = User(username=username, email=f"{username}@taskflow.local", full_name=name, role=role)
        u.set_password("Password123")
        db.session.add(u)
        return u

    admin = make_user("admin", "Admin User", "admin")
    ali = make_user("ali", "Muhammad Ali")
    sara = make_user("sara", "Sara Khan")
    usman = make_user("usman", "Usman Tariq")
    db.session.flush()

    plans = [
        ("Website Redesign", "Revamp the marketing site with a new design system.", "#4f46e5", admin,
         [ali, sara], ["Wireframes for home page", "Choose colour palette", "Build navbar component",
                       "Write landing copy", "Set up analytics", "Accessibility audit", "Mobile testing"]),
        ("Cloud Migration", "Move services from on-prem to AWS (EC2, RDS, S3).", "#0891b2", ali,
         [admin, usman], ["Provision EC2 instance", "Create RDS MySQL database", "Configure S3 bucket",
                          "Set up Elastic Beanstalk env", "Configure security groups", "Write runbook"]),
        ("Mobile App MVP", "First version of the companion mobile app.", "#059669", sara,
         [ali, usman], ["Login screen", "Push notifications", "Offline sync", "App store listing",
                        "Beta testing round"]),
    ]
    statuses = ["To Do", "In Progress", "In Review", "Done"]
    for name, desc, color, owner, members, titles in plans:
        p = Project(name=name, description=desc, color=color, owner_id=owner.id,
                    due_date=today + datetime.timedelta(days=random.randint(10, 40)))
        db.session.add(p)
        db.session.flush()
        db.session.add(ProjectMember(project_id=p.id, user_id=owner.id, role="owner"))
        for m in members:
            db.session.add(ProjectMember(project_id=p.id, user_id=m.id, role="member"))
        team = [owner] + members
        for title in titles:
            status = random.choice(statuses)
            t = Task(project_id=p.id, title=title, description=f"{title} for {name}.",
                     priority=random.choice(Task.PRIORITIES), assignee_id=random.choice(team).id,
                     created_by=owner.id, due_date=today + datetime.timedelta(days=random.randint(-5, 14)))
            t.set_status(status)
            if status == "Done":
                t.completed_at = utcnow() - datetime.timedelta(days=random.randint(0, 6))
            db.session.add(t)
            db.session.flush()
            if random.random() < 0.4:
                db.session.add(Comment(task_id=t.id, user_id=random.choice(team).id,
                                       body="Looks good, I'll pick this up next."))
            db.session.add(ActivityLog(user_id=owner.id, project_id=p.id, action=f"created task “{title}”"))
    for u in (admin, ali, sara, usman):
        p = Project(name="Personal", description="My personal tasks", owner_id=u.id)
        db.session.add(p)
        db.session.flush()
        db.session.add(ProjectMember(project_id=p.id, user_id=u.id, role="owner"))
    db.session.commit()
    return "Demo data created. Log in as admin / Password123 (also ali, sara, usman)."
