"""
Creates taskflow-eb.zip - the source bundle for Elastic Beanstalk / S3.
Run from this folder:   python make_bundle.py
(Zips the *contents* of the folder with forward-slash paths, which Elastic
Beanstalk on Linux needs; Windows' "Compress" sometimes gets this wrong.)
"""
import os
import zipfile

EXCLUDE_DIRS = {".venv", "venv", "__pycache__", ".pytest_cache", "tests", "_old_version", ".git"}
EXCLUDE_EXT = {".pyc", ".db", ".zip"}
EXCLUDE_FILES = {".env"}
OUT = "taskflow-eb.zip"

root = os.path.dirname(os.path.abspath(__file__))
count = 0
with zipfile.ZipFile(os.path.join(root, OUT), "w", zipfile.ZIP_DEFLATED) as zf:
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for name in files:
            if os.path.splitext(name)[1] in EXCLUDE_EXT or name in EXCLUDE_FILES:
                continue
            full = os.path.join(folder, name)
            arc = os.path.relpath(full, root).replace(os.sep, "/")
            zf.write(full, arc)
            count += 1
print(f"Created {OUT} with {count} files. Upload this file to S3 / Elastic Beanstalk.")
