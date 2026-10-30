# TaskFlow - Assignment 2, Part II

`docker-compose.part2.yml` uses `python:3.12-slim` and mounts the checked-out
application code into the app container. There is no Part II Dockerfile. The
Part II containers have separate names, database volume, and host ports from
Part I:

| Component | Container | Container port | EC2 host port |
|---|---|---:|---:|
| TaskFlow app | `taskflow-p2-app` | 8000 | 8082 |
| MySQL | `taskflow-p2-db` | 3306 | 3308 |

Keep Part II down until a GitHub push triggers the Jenkins pipeline. A manual
first run validates the source inside a Python Docker container but leaves
Part II down. A GitHub push run copies the current app source to Jenkins'
stable code directory, starts the Compose services, and waits for `/health` to
report a connected database. The Compose project has a separate named MySQL
volume.

On EC2, create `/etc/taskflow-part2.env` with real values from
`part2.env.example`; set its owner to `root:jenkins` and mode to `0640`. Do not
commit real credentials to GitHub.

Jenkins sends post-build email through the Email Extension plugin to Git
commit authors. Configure the SMTP server and sender address in Jenkins' global
email settings, then test email delivery with a push. The GitHub webhook must
point to `http://<EC2-IP>:8080/github-webhook/` and trigger the taskflow job.
