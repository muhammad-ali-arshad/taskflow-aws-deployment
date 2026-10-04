"""
Entry point.
  - Local:              python application.py      -> http://127.0.0.1:5000
  - EC2 (gunicorn):     gunicorn -w 3 -b 127.0.0.1:8000 application:application
  - Elastic Beanstalk:  looks for the `application` object in application.py automatically
"""
from taskflow import create_app

application = create_app()
app = application  # alias so `flask --app application ...` also works

if __name__ == "__main__":
    application.run(debug=True)
