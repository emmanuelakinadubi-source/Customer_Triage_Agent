-- AWS RDS PostgreSQL verification queries for VS Code.
--
-- VS Code connection settings:
-- Host: db-dev-traige-agent-ds-may.c1i4cqwu4kdd.eu-west-2.rds.amazonaws.com
-- Port: 5432
-- Database: postgres
-- Username: postgres
-- SSL: require
--
-- If using a connection string in VS Code, use:
-- postgresql://postgres:YOUR_PASSWORD@db-dev-traige-agent-ds-may.c1i4cqwu4kdd.eu-west-2.rds.amazonaws.com:5432/postgres?sslmode=require
--
-- Do not use the app-only SQLAlchemy prefix "postgresql+psycopg2://" in VS Code.

SELECT current_database(), current_schema();

SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_name = 'triage_records';

SELECT COUNT(*) AS triage_record_count
FROM public.triage_records;

SELECT *
FROM public.triage_records
ORDER BY created_at DESC;
