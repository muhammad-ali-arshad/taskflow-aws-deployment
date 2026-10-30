# Jenkins and GitHub pipeline for TaskFlow

## Pipeline flow

A push to `main` triggers Jenkins through the GitHub webhook. Jenkins checks out
this repository, runs the existing pytest suite inside a Python Docker
container, builds and health-checks the app image, then deploys Part II with
`docker-compose.part2.yml`. Part II uses a code bind mount and its own MySQL
container and named volume on EC2 host port `8082`.

A manual first build checks out, tests, builds, and verifies the image. It does
not start Part II. The Compose deployment stage runs only for a GitHub webhook
push. Part I remains separate on host port `8081`.

## Jenkins prerequisites

Install or enable these plugins in **Manage Jenkins -> Plugins**:

| Plugin | ID | Use |
| --- | --- | --- |
| Pipeline | `workflow-aggregator` | Jenkinsfile pipeline |
| Git | `git` | Checkout the public GitHub repository |
| GitHub | `github` | GitHub push trigger |
| Docker Pipeline | `docker-workflow` | Run tests inside Python container |
| JUnit | `junit` | Display pytest results |
| Email Extension | `email-ext` | Optional build notification |

The Jenkins built-in node must be online with at least one executor. Jenkins'
service user must be able to run Docker and Docker Compose. This EC2 uses a
rootless Docker daemon; do not add Jenkins to the rootful `docker` group. Keep
the rootless daemon available to the Jenkins service after a reboot.

## Jenkins job

Create **New Item -> Pipeline**, then configure:

- Definition: **Pipeline script from SCM**
- SCM: **Git**
- Repository URL: `https://github.com/muhammad-ali-arshad/taskflow-aws-deployment.git`
- Credentials: none while the repository is public
- Branch specifier: `*/main`
- Script path: `Jenkinsfile`
- Build trigger: **GitHub hook trigger for GITScm polling**

Save the job and click **Build Now** once. The manual build should pass the
checkout, test, image-build, and image-health stages. It intentionally leaves
Part II down until a webhook-triggered push arrives.

## Part II environment on EC2

Create `/etc/taskflow-part2.env` from the sanitized variable names in
`.env.part2.example`. Generate private values for both database passwords and
the application secret. Do not commit the real env file or put secrets in
Jenkinsfile or GitHub.

```bash
sudo chown root:jenkins /etc/taskflow-part2.env
sudo chmod 0640 /etc/taskflow-part2.env
```

The pipeline deploys Compose project `taskflow-part2`, app container
`taskflow-p2-app`, and database container `taskflow-p2-db`. Database data lives
in its own named Docker volume. The health check runs on EC2 at
`http://127.0.0.1:8082/health`; the browser URL is
`http://<EC2-public-IP>:8082/` if the EC2 security group allows that port.

## GitHub webhook

In the repository, open **Settings -> Webhooks -> Add webhook**:

- Payload URL: `http://<EC2-public-IP>:8080/github-webhook/`
- Content type: `application/json`
- Events: **Just the push event**
- Active: checked

The Jenkins endpoint must be reachable from GitHub. The EC2 security group
currently restricts port `8080` to the administrator's client IP, so GitHub
cannot deliver webhooks until inbound access is configured for the webhook
source ranges. Do not expose Jenkins or its Docker API indiscriminately. After
adding the webhook, inspect **Recent Deliveries**, push a commit to `main`, and
confirm Jenkins runs the Compose deployment and reports a healthy app.

## Optional email notification

The Jenkinsfile accepts a `NOTIFY_EMAIL` build parameter. Configure the SMTP
server and sender under **Manage Jenkins -> System -> Extended E-mail
Notification** before setting the parameter. Leave it blank until SMTP works.
Never put a mailbox password or app password in the repository.

## Assignment files

- Part I app image: `Dockerfile`
- Part I services: `docker-compose.yml` (host ports `8081` and `3307`)
- Part II code-mount deployment: `docker-compose.part2.yml` (host ports `8082`
  and `3308`)
- Jenkins pipeline: `Jenkinsfile`
- Part I notes: `DOCKER-PART1.md`
- Part II notes: `JENKINS-PART2.md`
