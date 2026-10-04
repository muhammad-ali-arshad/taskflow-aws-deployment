-- =====================================================================
-- TaskFlow database schema (MySQL 8 / MariaDB / Amazon RDS for MySQL)
-- Run:   mysql -u root -p < deploy/schema.sql                  (EC2)
--        mysql -h <rds-endpoint> -u admin -p < deploy/schema.sql (RDS)
-- On RDS with Elastic Beanstalk the database is usually called `ebdb`;
-- change the two lines below if so.
-- NOTE: the app also creates these tables automatically on first start.
-- =====================================================================
CREATE DATABASE IF NOT EXISTS taskflow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE taskflow;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER NOT NULL AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(120) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    `role` VARCHAR(20) NOT NULL,
    is_active BOOL NOT NULL,
    created_at DATETIME NOT NULL,
    last_login DATETIME,
    PRIMARY KEY (id),
    UNIQUE (email),
    UNIQUE KEY ix_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER NOT NULL AUTO_INCREMENT,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    color VARCHAR(7) NOT NULL,
    status VARCHAR(20) NOT NULL,
    due_date DATE,
    owner_id INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER NOT NULL AUTO_INCREMENT,
    user_id INTEGER,
    project_id INTEGER,
    action VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    KEY ix_activity_logs_created_at (created_at),
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS project_members (
    id INTEGER NOT NULL AUTO_INCREMENT,
    project_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    `role` VARCHAR(20) NOT NULL,
    added_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_project_user UNIQUE (project_id, user_id),
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER NOT NULL AUTO_INCREMENT,
    project_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    due_date DATE,
    assignee_id INTEGER,
    created_by INTEGER,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    completed_at DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY(assignee_id) REFERENCES users (id) ON DELETE SET NULL,
    FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER NOT NULL AUTO_INCREMENT,
    task_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
