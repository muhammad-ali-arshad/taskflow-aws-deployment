# TaskFlow: Ubuntu EC2, Jenkins, Docker agent and GitHub webhook

This pipeline adapts the containerized build idea to this Python/Flask app.
The original lab separately asks for Java and LAMP examples; using this app
does not demonstrate those language-specific examples. Confirm substitution
with your instructor if those are required for grading.

Flow: GitHub push -> webhook -> Jenkins -> checkout -> tests inside a Python
Docker agent -> application image build -> running-container health check.
The pipeline then removes its temporary container and image. This is build
automation; it does not replace an existing live deployment.

## 1. Check Ubuntu and available resources

Run every Linux command below in your EC2 SSH terminal, not Windows PowerShell.

```bash
cat /etc/os-release
free -h
df -h /
```

These installation instructions are for Ubuntu. Skip a component's install if
it is already configured and working. Jenkins recommends 4 GB+ RAM for a small
team; small EC2 instances can run out of memory while Jenkins and Docker work.

## 2. Install Java and Jenkins LTS

```bash
sudo apt-get update
sudo apt-get install -y fontconfig openjdk-21-jre git curl ca-certificates
java -version
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key -o /etc/apt/keyrings/jenkins-keyring.asc
echo 'deb [signed-by=/etc/apt/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/' | sudo tee /etc/apt/sources.list.d/jenkins.list
sudo apt-get update
sudo apt-get install -y jenkins
sudo systemctl enable --now jenkins
sudo systemctl status jenkins --no-pager
curl -I http://127.0.0.1:8080/login
```

Java is needed to run Jenkins itself. You do not install Flask or your app's
Python dependencies on EC2; the pipeline installs those inside containers.

If Jenkins fails:

```bash
sudo journalctl -u jenkins -n 60 --no-pager
sudo ss -ltnp | grep ':8080'
```

## 3. Open Jenkins and complete setup

In EC2 -> instance -> Security -> security group -> Edit inbound rules, allow
TCP 8080 from your current public IP (/32) for browser access. Keep SSH TCP 22
restricted to your IP. Do not add an inbound Docker API port.

Open `http://YOUR_EC2_PUBLIC_IP:8080` in your browser. Get the initial password:

```bash
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

Enter it only in Jenkins. Choose Install suggested plugins, create your admin
account, and set Jenkins URL to the address you use to reach it. For ongoing
internet access, use HTTPS through a properly configured reverse proxy.

## 4. Install Docker Engine

If Docker already works, go to step 5. If existing Docker/containerd packages
conflict with Docker CE, follow Docker's Ubuntu conflict instructions rather
than removing packages from an existing deployment blindly.

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run --rm hello-world
```

Compose is installed for future multi-container work; this Python build pipeline
uses Docker directly and does not need a Compose file or Docker Hub login.

## 5. Give Jenkins Docker access

```bash
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
sudo -u jenkins -H docker version
sudo -u jenkins -H docker run --rm python:3.12-slim python --version
sudo -u jenkins -H git --version
```

Docker group access gives powerful control over this host. This single-machine
setup is for your own trusted lab code. Use a dedicated execution agent for
untrusted code or a shared production Jenkins system. You do not need to create
a second EC2 instance for this lab.

## 6. Jenkins plugins and node label

Manage Jenkins -> Plugins -> Available plugins. Install any missing plugins:

| Display name | Plugin ID | Purpose |
| --- | --- | --- |
| Pipeline | workflow-aggregator | Jenkinsfile pipelines |
| Pipeline: Declarative | pipeline-model-definition | Declarative pipeline syntax; usually a dependency |
| Git | git | Repository checkout |
| GitHub | github | GitHub push webhook trigger |
| Docker Pipeline | docker-workflow | Docker agent syntax |
| JUnit | junit | Publish pytest reports |
| Email Extension | email-ext | Optional result email |

Let Jenkins install dependencies and restart when no job is running.
The plugin named simply Docker is not needed for this pipeline.

Manage Jenkins -> Nodes -> Built-In Node -> Configure:

- Labels: append `docker` to any existing labels.
- Number of executors: 1 for this small, single-machine lab.
- Save.

The top-level `agent { label 'docker' }` chooses this execution node. The test
stage's Docker agent starts a temporary Python container on the same node.

## 7. Create the Pipeline job

Keep your old Freestyle job. Create New Item -> `taskflow-container-build` ->
Pipeline -> OK. If the old job has a GitHub push trigger, disable that trigger
if you only want the new Pipeline job to run on pushes.

Under Pipeline:

- Definition: Pipeline script from SCM.
- SCM: Git.
- Repository URL: `https://github.com/muhammad-ali-arshad/taskflow-aws-deployment.git`
- Credentials: none for public repositories. For a private repository, add a
  Jenkins username/password credential with your GitHub username and a token
  that can read this repository. Do not put the token in the repository URL.
- Branch Specifier: `*/ci/jenkins-docker` for the prepared branch.
- Script Path: `Jenkinsfile` (case sensitive).
- Save -> Build Now.

The first manual run loads the Jenkinsfile and registers its `githubPush()`
trigger. It also creates the NOTIFY_EMAIL parameter for subsequent runs.

Open the build -> Console Output. Expect Checkout, Test inside Docker agent,
Build application image, Verify running container, and final SUCCESS. Test
Results should show the pytest results. The image tag includes the build
number and commit ID. Images are removed after the job to avoid accumulating
disk usage. Dependencies are currently minimum-version ranges, as in the
existing app, so future package updates can change the resolved environment.

## 8. Configure the GitHub push webhook

The webhook requires a Jenkins endpoint reachable from GitHub. A security group
allowing only your laptop cannot receive GitHub requests. Prefer an HTTPS
endpoint exposing `/github-webhook/`; if using EC2 port 8080 for the lab, allow
GitHub's current webhook IP ranges to that port as well as your own IP. Obtain
current ranges from https://api.github.com/meta under `hooks`; do not copy stale
ranges from a tutorial. Account for any Ubuntu firewall and reverse proxy too.

On GitHub, open the repository -> Settings -> Webhooks -> Add webhook:

- Payload URL: `https://YOUR_JENKINS_HOST/github-webhook/`, or for the initial
  lab `http://YOUR_EC2_PUBLIC_IP:8080/github-webhook/`.
- Content type: application/json.
- Events: Just the push event.
- Active: checked.
- If configuring a webhook secret, configure the matching validation secret in
  your installed Jenkins GitHub plugin first; do not set mismatched secrets.
- Keep SSL verification enabled when using HTTPS.

Jenkins job -> Configure -> Triggers should show GitHub hook trigger for GITScm
polling after the first Jenkinsfile run. The `githubPush()` directive sets it.
This is event-driven polling initiated by a webhook, not a scheduled poll.

On the new webhook, inspect Recent Deliveries. A successful ping alone does not
prove the build trigger works. Push a real change to the branch this job watches
and confirm a new Jenkins build starts. A push to main will not build the
`ci/jenkins-docker` branch when that branch has no changes. After merging these
files into main, change the job's branch specifier to `*/main`.

In your existing Windows project folder, fetch the prepared branch before making
changes. These are PowerShell commands:

```powershell
git fetch origin
git switch --track origin/ci/jenkins-docker
```

If the local branch already exists, use `git switch ci/jenkins-docker` instead.
Change a README sentence, then:

```powershell
git add README.md
git commit -m "Verify Jenkins webhook build"
git push origin ci/jenkins-docker
```

## 9. Optional result email

Manage Jenkins -> System -> Extended E-mail Notification: configure your SMTP
host, port, TLS/SSL settings, authentication using Jenkins credentials, and an
allowed sender address according to your email provider. Use its supported
SMTP credential method; your normal mailbox password may not work.

Run Build with Parameters and set NOTIFY_EMAIL to your own address. Leave it
blank until SMTP is ready. The post block sends the whole pipeline result after
success or failure. It uses an explicit recipient instead of assuming a commit
author's address is a deliverable mailbox. Do not send to someone else's
address without authorization.

## 10. Optional: run the built application manually

This is separate from CI. In a fresh EC2 working directory after Docker setup:

```bash
git clone --branch ci/jenkins-docker https://github.com/muhammad-ali-arshad/taskflow-aws-deployment.git taskflow-container-lab
cd taskflow-container-lab
sudo docker build -t taskflow:lab .
sudo docker volume create taskflow-lab-data
TASKFLOW_SECRET=$(openssl rand -hex 32)
sudo docker run -d --name taskflow-container-lab \
  --restart unless-stopped \
  -p 127.0.0.1:8001:8000 \
  -e SECRET_KEY="$TASKFLOW_SECRET" \
  -v taskflow-lab-data:/data \
  taskflow:lab
unset TASKFLOW_SECRET
curl http://127.0.0.1:8001/health
```

This creates a new SQLite database inside a persistent named volume. It does
not copy your existing database. The secret is stored in the container's
configuration; preserve it securely if recreating the container. The app binds
to localhost on port 8001 to avoid your existing deployment's port 8000. Use
your existing SSH connection command with `-L 8001:127.0.0.1:8001` added to open
http://127.0.0.1:8001 locally. The first signup becomes this fresh app's admin.

## Troubleshooting and evidence

- Waiting for an executor: check the `docker` label and one available executor.
- Invalid agent type docker: install Docker Pipeline and restart Jenkins.
- Docker socket permission denied: repeat step 5 and restart Jenkins.
- Checkout failure: check repository read credentials and branch specifier.
- Webhook timeout: check public endpoint, security group, proxy and firewall.
- Webhook succeeds but no build: check first manual build, trigger and branch.
- Process killed / exit 137: check RAM and Docker/Jenkins logs.
- SMTP failure: leave NOTIFY_EMAIL empty while fixing provider settings.

For your lab evidence, capture the Jenkinsfile, successful stage view, test
results, Console Output showing Docker execution, successful GitHub push
delivery, resulting automatic build, and email if configured.

## Official references

- https://www.jenkins.io/doc/book/installing/linux/
- https://www.jenkins.io/doc/book/pipeline/docker/
- https://docs.docker.com/engine/install/ubuntu/
- https://plugins.jenkins.io/github/
- https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks
- https://plugins.jenkins.io/email-ext/
