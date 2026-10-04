#!/usr/bin/env bash
# =====================================================================
# One-shot setup for TaskFlow on an Ubuntu 22.04/24.04 EC2 instance.
# Upload the project to /home/ubuntu/taskflow first, then:
#     cd ~/taskflow && bash deploy/ec2_setup.sh
# Edit the three passwords below BEFORE running.
# =====================================================================
set -e
APP_DB_PASS='ChangeMe_App#2026'
READONLY_DB_PASS='ChangeMe_Read#2026'
SECRET_KEY="$(openssl rand -hex 32)"
APP_DIR=/home/ubuntu/taskflow

echo ">>> 1/7 Installing packages (python, mysql, nginx)"
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip mysql-server nginx

echo ">>> 2/7 Starting MySQL"
sudo systemctl enable --now mysql

echo ">>> 3/7 Creating database, tables and users"
sudo mysql < "$APP_DIR/deploy/schema.sql"
sed -e "s/ChangeMe_App#2026/${APP_DB_PASS}/" -e "s/ChangeMe_Read#2026/${READONLY_DB_PASS}/" \
    "$APP_DIR/deploy/create_users.sql" | sudo mysql

echo ">>> 4/7 Allowing remote connections to MySQL (needed for the read-only grader account)"
sudo sed -i 's/^bind-address.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf
sudo sed -i 's/^mysqlx-bind-address.*/mysqlx-bind-address = 127.0.0.1/' /etc/mysql/mysql.conf.d/mysqld.cnf
sudo systemctl restart mysql

echo ">>> 5/7 Python virtualenv + requirements"
cd "$APP_DIR"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
cat > .env <<ENV
SECRET_KEY=${SECRET_KEY}
DB_HOST=localhost
DB_PORT=3306
DB_NAME=taskflow
DB_USER=taskflow_app
DB_PASSWORD=${APP_DB_PASS}
ENV
set -a; source .env; set +a
./venv/bin/python seed.py      # demo data (admin / Password123)

echo ">>> 6/7 Permissions + gunicorn service"
sudo chown -R ubuntu:www-data "$APP_DIR"
chmod 750 "$APP_DIR"; chmod 640 "$APP_DIR/.env"
chmod 711 /home/ubuntu
sudo cp deploy/taskflow.service /etc/systemd/system/taskflow.service
sudo systemctl daemon-reload
sudo systemctl enable --now taskflow

echo ">>> 7/7 nginx reverse proxy"
sudo cp deploy/nginx-taskflow.conf /etc/nginx/sites-available/taskflow
sudo ln -sf /etc/nginx/sites-available/taskflow /etc/nginx/sites-enabled/taskflow
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

IP=$(curl -s http://checkip.amazonaws.com || echo "<your-public-ip>")
echo ""
echo "======================================================"
echo " Done!  Open:  http://${IP}/        Health: http://${IP}/health"
echo " Login: admin / Password123"
echo " Read-only DB: host=${IP} port=3306 db=taskflow user=taskflow_readonly"
echo "======================================================"
