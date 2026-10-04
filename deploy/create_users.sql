-- =====================================================================
-- Database accounts for TaskFlow
--   taskflow_app      -> used by the web application (read + write)
--   taskflow_readonly -> READ-ONLY account for the automated grading script
-- Change the passwords before running!  Replace `taskflow` with `ebdb`
-- if you are using the database Elastic Beanstalk created.
-- Run as root (EC2) or as the RDS master user.
-- =====================================================================

-- Application user (EC2 only - on RDS the app normally uses the master user)
CREATE USER IF NOT EXISTS 'taskflow_app'@'localhost' IDENTIFIED BY 'ChangeMe_App#2026';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES ON taskflow.* TO 'taskflow_app'@'localhost';
CREATE USER IF NOT EXISTS 'taskflow_app'@'127.0.0.1' IDENTIFIED BY 'ChangeMe_App#2026';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES ON taskflow.* TO 'taskflow_app'@'127.0.0.1';

-- Read-only user that the evaluation script will use (can connect from anywhere: '%')
CREATE USER IF NOT EXISTS 'taskflow_readonly'@'%' IDENTIFIED BY 'ChangeMe_Read#2026';
GRANT SELECT ON taskflow.* TO 'taskflow_readonly'@'%';

FLUSH PRIVILEGES;

-- Check:
-- SHOW GRANTS FOR 'taskflow_readonly'@'%';
