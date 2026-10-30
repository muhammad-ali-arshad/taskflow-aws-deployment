# TaskFlow - Assignment 2, Part I

This folder is the **web app project root**. Keep `Dockerfile`, `docker-compose.yml`,
`application.py`, `config.py`, `requirements.txt`, and `taskflow/` together.
The Dockerfile builds the **app image**. The database uses the official MySQL
image, so there is no separate database Dockerfile.

## What runs where

| Component | Image | Container port | EC2 host port | Persistent data |
|---|---|---:|---:|---|
| TaskFlow app | `ali024024/taskflow:part1` | 8000 | 8081 | App data is in MySQL |
| MySQL database | `mysql:8.4` | 3306 | 3307 | Docker named volume `taskflow_mysql_data` |

The app connects to `db:3306` **inside** the Compose network. Its database is
separate from the MySQL server currently installed directly on the EC2 host.
The original TaskFlow records were copied into the container database: 6 users,
10 projects, and 18 tasks at migration time. The original host database was
left in place. The named volume keeps the container database data when
containers are recreated; this was verified after a Compose down/up cycle. Do
not run `docker compose down --volumes` if you want to retain it.

## 1. Build and push the app image

Use a computer with Docker Engine or Docker Desktop installed, or build on the
EC2 instance after installing Docker there. The build creates an image in the
Docker engine **on whichever machine runs the command**. Docker Hub receives
the image only after `docker push`.

Run these commands from this folder, replacing `<Docker Hub username>`:

```sh
docker login
docker build -t <Docker Hub username>/taskflow:part1 .
docker push <Docker Hub username>/taskflow:part1
```

You need a Docker Hub account and permission to push to that account's
`taskflow` repository. Use a Docker Hub access token for CLI login if your
account requires one. The image name and tag must exactly match the `app.image`
value produced by `docker-compose.yml` after `.env` substitution.

## 2. Start Part I on the TaskFlow EC2 instance

Install Docker Engine plus the Compose plugin on EC2, then copy this folder to
the instance. In this folder on EC2, create `.env` from `.env.part1.example` and set
real values. Keep `.env` private and out of GitHub and screenshots.

```sh
cp .env.example .env
# Edit .env: set Docker Hub username, two different DB passwords, and SECRET_KEY.
docker compose config
docker compose pull
docker compose up -d
docker compose ps
curl http://localhost:8081/health
```

The health response should include `"database":"connected"` and
`"engine":"mysql"`. If the Docker Hub repository is private, run `docker
login` on EC2 before `docker compose pull`. The read-only account is
`taskflow_readonly`; its password is stored on EC2 at
`/home/ubuntu/taskflow-readonly-password`. Retrieve it in your SSH terminal
with `cat /home/ubuntu/taskflow-readonly-password`.

The current TaskFlow instance already serves the original app through Nginx
on port 80. The new container uses host port 8081, so both can run during
verification. The database uses host port 3307, avoiding the host MySQL
service on 3306. The EC2 security group currently blocks direct external
database connections on 3307. If remote access is required, allow only the
evaluator's source IP. Publishing the port in Compose alone does not open the
EC2 security group.

## 3. Verify the assignment requirements

```sh
docker compose ps
docker volume ls
docker compose exec db mysql -u taskflow_app -p taskflow -e "SHOW TABLES;"
curl http://localhost:8081/health
```

Persistence was verified by recreating the containers while retaining the
named volume; the health endpoint still reported 6 users, 10 projects, and 18
tasks. Capture screenshots of the Docker Hub image, Compose services, health
response, database tables or records, and the browser app on EC2 for the report.

Part I submission should include the Dockerfile, Compose file, Docker Hub image
name, live app URL, database verification, and step-by-step report screenshots.
