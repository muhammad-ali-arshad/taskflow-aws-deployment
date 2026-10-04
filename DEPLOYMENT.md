# TaskFlow: AWS Deployment Guide

This guide covers both deployments the assignment requires:

- **Part I (IaaS):** EC2 Ubuntu VM + MySQL server + gunicorn + nginx
- **Part II (PaaS):** S3 (holds the code bundle) + Elastic Beanstalk + RDS MySQL

Take a screenshot at every 📸 marker. Those screenshots go in your report.

> **Region:** pick one region (e.g. `us-east-1`) and use it for everything.
> **Free tier:** use `t2.micro` / `t3.micro` and `db.t3.micro` / `db.t4g.micro`, and stop or delete resources after grading.

---

## Part I: Deploy on Amazon EC2 (IaaS)

### 1. Launch an Ubuntu EC2 instance
1. AWS Console → **EC2** → **Launch instance**.
2. Name: `taskflow-ec2`.
3. AMI: **Ubuntu Server 24.04 LTS** (or 22.04).
4. Instance type: **t2.micro** or **t3.micro** (free tier).
5. **Key pair** → *Create new key pair* → name `taskflow-key`, type RSA, format **.pem** (OpenSSH) or **.ppk** (for PuTTY). Download it and keep it safe. 📸
6. **Network settings → Edit → Create security group** `taskflow-ec2-sg` with these inbound rules:

| Type | Port | Source | Why |
|---|---|---|---|
| SSH | 22 | My IP | Your SSH access |
| HTTP | 80 | 0.0.0.0/0 | The website |
| MYSQL/Aurora | 3306 | 0.0.0.0/0 | Lets the grader's read-only account connect to the database |

7. Storage: 8–10 GB gp3 is enough → **Launch instance**. 📸
8. Copy the instance's **Public IPv4 address**. 📸

> Optional: allocate an **Elastic IP** and associate it with the instance, so the IP doesn't change if you stop and start it. Do this before submitting the form.

### 2. Connect with SSH
On Windows PowerShell or Mac/Linux:
```bash
# Windows only: restrict the key's permissions first
icacls taskflow-key.pem /inheritance:r /grant:r "%USERNAME%:R"
# Mac/Linux only:
chmod 400 taskflow-key.pem

ssh -i taskflow-key.pem ubuntu@<PUBLIC_IP>
```
📸 (terminal showing `ubuntu@ip-...:~$`)

### 3. Upload the application code
**Option A: scp from your laptop.** Run this in the folder that *contains* the `task-manager` project folder:
```bash
scp -i taskflow-key.pem -r task-manager ubuntu@<PUBLIC_IP>:/home/ubuntu/taskflow
```
Don't upload `.venv`. Delete it first or use Option B.

**Option B: GitHub.** Push the project to a GitHub repo, then on the server run:
```bash
git clone https://github.com/<you>/<repo>.git ~/taskflow
```
📸 (`ls ~/taskflow` on the server)

### 4. Run the setup script (installs and configures everything)
```bash
cd ~/taskflow
nano deploy/ec2_setup.sh      # change APP_DB_PASS and READONLY_DB_PASS at the top
bash deploy/ec2_setup.sh
```
The script does the following. Each step is a "micro step" you can describe in the report:

| Step | What it does | Manual equivalent |
|---|---|---|
| 1 | Installs packages | `sudo apt update && sudo apt install -y python3-venv python3-pip mysql-server nginx` |
| 2 | Starts MySQL | `sudo systemctl enable --now mysql` |
| 3 | Creates the schema and DB users | `sudo mysql < deploy/schema.sql` then `sudo mysql < deploy/create_users.sql` |
| 4 | Allows remote MySQL access | sets `bind-address = 0.0.0.0` in `/etc/mysql/mysql.conf.d/mysqld.cnf` and restarts MySQL |
| 5 | Sets up the Python env and `.env`, loads demo data | `python3 -m venv venv`, `pip install -r requirements.txt`, `python seed.py` |
| 6 | Sets permissions, starts gunicorn as a service | `chown ubuntu:www-data`, `chmod 640 .env`, copies `deploy/taskflow.service` to systemd |
| 7 | Configures nginx as a reverse proxy | copies `deploy/nginx-taskflow.conf` to `/etc/nginx/sites-available/` and enables it |

📸 the "Done!" message at the end.

### 5. Verify
```bash
sudo systemctl status taskflow     # should say active (running)   📸
sudo systemctl status nginx        # 📸
curl http://localhost/health       # {"database":"connected","engine":"mysql",...}
sudo mysql -e "USE taskflow; SHOW TABLES; SELECT username, role FROM users;"   # 📸
```
In your browser, open `http://<PUBLIC_IP>/`, log in as **admin / Password123**, then create a project and a task. 📸 Take screenshots of the dashboard, the Kanban board and the admin panel.

Test the read-only account **from your laptop** (MySQL Workbench, or the `mysql` CLI):
```
Host: <PUBLIC_IP>   Port: 3306   Database: taskflow
User: taskflow_readonly   Password: <READONLY_DB_PASS>
```
`SELECT * FROM tasks;` should work, and `INSERT ...` should be denied. 📸

**Part I URL:** `http://<PUBLIC_IP>/`

### Troubleshooting (EC2)
- `502 Bad Gateway`: gunicorn isn't running. Check `sudo journalctl -u taskflow -n 50`.
- Site not loading at all: check the security group allows HTTP on port 80.
- Remote MySQL refused: check the security group allows port 3306, then run `sudo ss -tlnp | grep 3306` (it should show `0.0.0.0:3306`).
- After changing code: `sudo systemctl restart taskflow`.

---

## Part II: Deploy on Elastic Beanstalk + S3 + RDS (PaaS)

### 1. Create the RDS MySQL database
1. Console → **RDS** → **Create database** → **Standard create** → **MySQL** (8.0 or later).
2. Template: **Free tier**.
3. DB instance identifier: `taskflow-db`. Master username: `admin`. Set a master password and **save it**.
4. Instance class: `db.t3.micro` or `db.t4g.micro`. Storage: 20 GB.
5. Connectivity: **Public access: Yes**. The grader needs to reach it with the read-only account.
   VPC security group: **Create new** → `taskflow-rds-sg`.
6. Additional configuration → **Initial database name: `taskflow`**.
7. Click **Create database** and wait until the status is *Available* (5–10 min). 📸
8. Copy the **Endpoint**, e.g. `taskflow-db.xxxxxx.us-east-1.rds.amazonaws.com`. 📸
9. Open `taskflow-rds-sg` → **Edit inbound rules** → add **MYSQL/Aurora 3306 from 0.0.0.0/0** (needed for the grader). 📸

### 2. Create the tables and the read-only user on RDS
From your EC2 instance (it already has the mysql client) or from MySQL Workbench on your laptop:
```bash
cd ~/taskflow
mysql -h <RDS_ENDPOINT> -u admin -p < deploy/schema.sql
mysql -h <RDS_ENDPOINT> -u admin -p -e "
  CREATE USER 'taskflow_readonly'@'%' IDENTIFIED BY '<READONLY_PASS>';
  GRANT SELECT ON taskflow.* TO 'taskflow_readonly'@'%';
  FLUSH PRIVILEGES;"
mysql -h <RDS_ENDPOINT> -u admin -p -e "SHOW TABLES FROM taskflow;"     # 📸
```

### 3. Build the source bundle and upload it to S3
On your laptop, inside the project folder:
```bash
python make_bundle.py        # creates taskflow-eb.zip
```
1. Console → **S3** → **Create bucket** → name e.g. `taskflow-code-<yourname>` (names must be globally unique), same region → Create. 📸
2. Open the bucket → **Upload** → `taskflow-eb.zip` → Upload. 📸
3. Click the uploaded file and copy its **S3 URI / Object URL**. 📸

### 4. Create the Elastic Beanstalk environment
1. Console → **Elastic Beanstalk** → **Create application**.
2. Environment tier: **Web server environment**.
3. Application name: `taskflow`. Environment name: `taskflow-env`.
4. Platform: **Python**, newest branch (Python 3.11+ on Amazon Linux 2023).
5. Application code: **Upload your code** → version label `v1` → choose **Public S3 URL** and paste the S3 object URL from step 3. You can also upload the zip directly; EB stores it in its own S3 bucket. 📸
6. Presets: **Single instance (free tier eligible)** → Next.
7. Service access: create or use the **aws-elasticbeanstalk-service-role** and the EC2 instance profile **aws-elasticbeanstalk-ec2-role**. Optionally select your EC2 key pair. → Next.
8. Networking: default VPC, **Public IP address: enabled** → Next. Skip the *Database* section: we created RDS separately in step 1, which is the approach AWS recommends.
9. Instance traffic: defaults → Next.
10. **Environment properties** (Configure updates, monitoring and logging page → bottom). Add:

| Name | Value |
|---|---|
| `SECRET_KEY` | any long random string |
| `DB_HOST` | `<RDS_ENDPOINT>` |
| `DB_PORT` | `3306` |
| `DB_NAME` | `taskflow` |
| `DB_USER` | `admin` |
| `DB_PASSWORD` | your RDS master password |

📸 this page.

11. **Submit** and wait for health to turn **Green / OK** (around 5 min). 📸
12. Open the environment **Domain** URL, e.g. `taskflow-env.eba-xxxx.us-east-1.elasticbeanstalk.com`. 📸

> If health is red with database errors: the EB instance must be allowed to reach RDS. Open `taskflow-rds-sg` and make sure port 3306 allows `0.0.0.0/0`, or at least the EB instance's security group.

### 5. Verify
- `http://<EB_DOMAIN>/health` should return `"engine":"mysql","database":"connected"`. 📸
- Sign up. The **first account becomes admin**. Then create a project and tasks and drag cards on the board. 📸
- (Optional) Load demo data: set `DB_*` in your terminal and run `python seed.py` against the RDS database from EC2 or your laptop.
- Connect with `taskflow_readonly` to `<RDS_ENDPOINT>:3306/taskflow` and run `SELECT * FROM users;`. 📸

**Part II URL:** `http://<EB_DOMAIN>/`

### Deploying an update (new version)
Edit the code, run `python make_bundle.py`, upload the new zip to S3, then go to EB → **Upload and deploy** → paste the S3 URL → version `v2`.

---

## Google Form details (what to submit)

| Field | Part I (EC2) | Part II (Elastic Beanstalk) |
|---|---|---|
| App URL | `http://<EC2_PUBLIC_IP>/` | `http://<EB_DOMAIN>/` |
| DB host | `<EC2_PUBLIC_IP>` | `<RDS_ENDPOINT>` |
| DB port | 3306 | 3306 |
| DB name | `taskflow` | `taskflow` |
| DB user (read-only) | `taskflow_readonly` | `taskflow_readonly` |
| DB password | your read-only password | your read-only password |
| DB engine | MySQL 8 | MySQL 8 (RDS) |

## Suggested report outline
1. **Introduction**: what TaskFlow is, its 5 modules (copy from README), tech stack, ER diagram of the 6 tables.
2. **Service models**: IaaS (EC2: you manage the OS, packages, web server and DB) vs PaaS (EB + RDS: AWS manages servers, scaling and patching; S3 holds the code).
3. **Part I: EC2**: steps 1–5 above with screenshots.
4. **Part II: S3 + RDS + Elastic Beanstalk**: steps 1–5 with screenshots.
5. **URLs and DB details** (the table above).
6. **Challenges and fixes**, and **cleanup** (terminate EC2, delete the EB env, delete RDS, empty and delete the S3 bucket after grading).
