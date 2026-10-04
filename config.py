"""
Application configuration.

The database is picked in this order:
  1. DATABASE_URL            e.g. mysql+pymysql://user:pass@host:3306/taskflow
  2. RDS_* variables         set automatically by Elastic Beanstalk when an RDS DB is attached
                             (RDS_HOSTNAME, RDS_PORT, RDS_DB_NAME, RDS_USERNAME, RDS_PASSWORD)
  3. DB_HOST/DB_USER/...     handy on EC2 with a local MySQL server
  4. SQLite file             fallback for running on your own laptop
"""
import os
from urllib.parse import quote_plus

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _mysql_url(host, port, name, user, password):
    return (f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}"
            f"@{host}:{port}/{name}?charset=utf8mb4")


def build_database_url():
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    if os.environ.get("RDS_HOSTNAME"):
        return _mysql_url(os.environ["RDS_HOSTNAME"], os.environ.get("RDS_PORT", "3306"),
                          os.environ.get("RDS_DB_NAME", "ebdb"), os.environ["RDS_USERNAME"],
                          os.environ["RDS_PASSWORD"])
    if os.environ.get("DB_HOST"):
        return _mysql_url(os.environ["DB_HOST"], os.environ.get("DB_PORT", "3306"),
                          os.environ.get("DB_NAME", "taskflow"), os.environ.get("DB_USER", "taskflow"),
                          os.environ.get("DB_PASSWORD", ""))
    return "sqlite:///" + os.path.join(BASE_DIR, "taskflow.db")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-taskflow-dev-secret-2026")
    SQLALCHEMY_DATABASE_URI = build_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "8"))
    COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
    TASKS_PER_PAGE = 15


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
