# Move from SQLite to AWS RDS PostgreSQL

This project now supports both local SQLite and AWS RDS PostgreSQL through the
same `DATABASE_URL` setting.

## 1. Get your RDS values

From AWS Console > RDS > Databases > your PostgreSQL database, collect:

- RDS endpoint, for example `customerreviews.xxxxxx.us-east-1.rds.amazonaws.com`
- Port, usually `5432`
- Database name, for example `customerreviews`
- Master username, for example `postgres`
- Password, stored safely outside Git

## 2. Allow network access

For local VS Code testing, the RDS security group must allow inbound PostgreSQL:

- Type: PostgreSQL
- Port: `5432`
- Source: your public IP only

For ECS later, restrict the source to the ECS service security group instead of
your public IP.

## 3. Update `api/.env`

Replace the SQLite value:

```env
DATABASE_URL=sqlite:///./data/triage.db
```

with your RDS PostgreSQL URL:

```env
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/postgres?sslmode=require
```

If your password contains special characters such as `@`, `#`, `/`, `:`, or
spaces, URL-encode it before putting it in the connection string.

Do not commit `api/.env`.

For VS Code SQL extensions, use the same values and set SSL explicitly:

```text
Host: YOUR_RDS_ENDPOINT
Port: 5432
Database: postgres
Username: postgres
SSL: require
```

If your VS Code extension asks for a connection string, use the standard
PostgreSQL URL format, not the SQLAlchemy application format:

```text
postgresql://postgres:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/postgres?sslmode=require
```

Do not use this SQLAlchemy-only prefix in VS Code:

```text
postgresql+psycopg2://
```

If VS Code shows `no pg_hba.conf entry ... no encryption`, the connection is
reaching RDS but SSL is disabled in the VS Code connection profile. Enable
SSL/Require SSL and reconnect.

## 4. Rebuild the API image

```powershell
docker compose build api
```

## 5. Test the database connection

```powershell
docker compose run --rm api python scripts/check_database.py
```

Expected result:

- It prints a masked PostgreSQL connection URL.
- It prints the PostgreSQL server version.
- It confirms the `triage_records` table exists.

The app creates the table automatically on startup through SQLAlchemy
`Base.metadata.create_all`.

## 6. Start the app

```powershell
docker compose up -d api ui
```

Then open:

```text
http://localhost:8501
```

Submit a customer message. If the response is saved successfully, the record is
now stored in AWS RDS PostgreSQL instead of local SQLite.
