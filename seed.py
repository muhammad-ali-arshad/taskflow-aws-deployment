"""Load demo users/projects/tasks:  python seed.py"""
from application import application
from taskflow.seed import seed_demo

with application.app_context():
    print(seed_demo())
