# Customer Support Triage Agent

An AI-powered triage system that reads a customer message, classifies it, decides who should handle it, and generates a safe draft reply — all in one API call.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Create the .env File](#2-create-the-env-file)
3. [Run with Docker](#3-run-with-docker)
4. [URLs](#4-urls)
5. [How the App Works](#5-how-the-app-works)
6. [What to Expect (Output Fields)](#6-what-to-expect-output-fields)
7. [Running the Tests](#7-running-the-tests)
8. [Project Structure](#8-project-structure)
9. [Tools Used](#9-tools-used)

---

## 1. Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Git

### Pull the main branch

```bash
git clone https://github.com/<your-org>/customer-triage-agent.git
cd customer-triage-agent

# If the repo is already cloned, pull the latest main
git checkout main
git pull origin main
```

---

## 2. Create the .env File

The API reads credentials from `api/.env`. This file is **not committed** (it is in `.gitignore`). You must create it manually.

```bash
# From the project root
cp api/.env.example api/.env   # if an example file exists, otherwise create it manually
```

Create `api/.env` with the following content:

```env
# AWS Secrets Manager source for Azure OpenAI credentials
AWS_SECRET_NAME=dev-mayds-triage-agent
AWS_REGION=eu-west-2
AWS_SECRETS_REQUIRED=true
AWS_SECRETS_OVERRIDE_ENV=true

# Azure OpenAI model settings
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1-mini

# AWS RDS PostgreSQL database
POSTGRES_HOST=db-dev-traige-agent-ds-may.c1i4cqwu4kdd.eu-west-2.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your-rds-password>
```

The AWS secret named by `AWS_SECRET_NAME` must contain:

```json
{
  "AZURE_OPENAI_ENDPOINT": "https://<your-resource>.openai.azure.com/",
  "AZURE_OPENAI_API_KEY": "<your-api-key>"
}
```

You can also put `AZURE_OPENAI_API_VERSION` and
`AZURE_OPENAI_DEPLOYMENT_NAME` in the secret. When
`AWS_SECRETS_OVERRIDE_ENV=true`, Azure OpenAI values from AWS Secrets Manager
override matching local environment values.

Docker Compose passes AWS credentials into the API container from the
project-root `.env` file. Database settings live in `api/.env`.
Set these before starting Docker:

```env
AWS_ACCESS_KEY_ID=<your-aws-access-key-id>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-access-key>
AWS_SESSION_TOKEN=<your-session-token-if-using-temporary-credentials>
AWS_REGION=eu-west-2
```


---

## 3. Run with Docker

```bash
# Build images and start both services (API + UI)
docker compose up --build

# To run in the background
docker compose up --build -d

# Stop everything
docker compose down
```

The first build downloads base images and installs dependencies — this takes a few minutes. Subsequent starts are much faster.

---

## 4. URLs

| Service | URL | Description |
|---|---|---|
| Streamlit UI | http://localhost:8501 | Main user interface |
| FastAPI (backend) | http://localhost:8000 | REST API |
| Swagger / API docs | http://localhost:8000/docs | Interactive API documentation |

Open **http://localhost:8501** in your browser to use the app.

---

## 5. How the App Works

### Overview

Every message goes through a three-stage pipeline before the result is saved:

```
Customer message
      │
      ▼
 Input Guard          ← strips whitespace, checks length, blocks prompt injection
      │
      ▼
 Azure OpenAI         ← GPT-4.1-mini classifies and generates a draft reply
      │
      ▼
 Output Guard         ← validates routing rules, checks for hallucinated values,
      │                  runs a second LLM pass for consistency
      ▼
 SQLite Database      ← result is persisted
      │
      ▼
  UI / API response
```

---

### Single Message (Triage tab)

1. Open the **Triage** tab.
2. In the **Single Message** panel (left column), type or paste a customer message.
3. Click **Send**.
4. The result appears below — category, urgency, sentiment, suggested owner, and a draft reply.

**Example input:**
```
I ordered a jacket two weeks ago and it still hasn't arrived.
My order number is 78432.
```

**What happens internally:**
- The input guard checks the message is safe and within length limits.
- GPT-4.1-mini classifies it as a Delivery Issue, assigns Medium urgency, and writes a draft reply that does not invent any new order numbers or amounts.
- The output guard confirms the routing (Delivery Issue must go to Logistics Team or Customer Service Agent) and checks the draft for hallucinated values.
- The result is saved to the database.

---

### Batch Upload (Triage tab)

1. Open the **Triage** tab.
2. In the **Batch Upload** panel (right column), upload a **CSV** or **Excel** file.
3. The file must contain a column named `message`. Each row is one customer message.
4. A preview of the file is shown. Click **Send** to process all rows.
5. Results appear in a table — one row per input message, with success/failure per row.

**CSV format:**
```csv
message
I need a refund for order 12345
My account is locked
Great service, thank you!
```

**Limits:**
- Maximum **20 messages** per batch submission (the first 20 rows are used if the file is larger).
- Supported formats: `.csv`, `.xlsx`.
- The file encoding can be UTF-8 or Windows-1252 (latin-1) — both are handled automatically.

---

### History tab

- Click **Load / Refresh** to pull all saved triage records from the database.
- Use the slider to control how many records are returned (up to 200).
- Click **Download History CSV** to export the full table.

---

### Abusive messages

If the message contains offensive or abusive content, the LLM sets `abusive_flag = true`. In that case:
- No draft reply is generated.
- The record is flagged for human review.
- The UI displays a red warning banner instead of the draft.

---

## 6. What to Expect (Output Fields)

| Field | Type | Possible Values | Meaning |
|---|---|---|---|
| `category` | string | Refund Request, Delivery Issue, Product Complaint, Account Problem, General Enquiry, Compliment, Other | The topic of the customer message |
| `urgency` | string | High, Medium, Low | How urgently the issue needs attention |
| `urgency_reason` | string | free text | One sentence explaining the urgency level |
| `sentiment` | string | Positive, Negative, Neutral, Mixed | Emotional tone of the message |
| `suggested_owner` | string | Customer Service Agent, Billing Team, Logistics Team, Escalate to Manager | The team or role that should handle it |
| `draft_response` | string / null | free text | A suggested reply (null if the message was flagged as abusive) |
| `confidence` | string | High, Medium, Low | How confident the model is in its classification |
| `abusive_flag` | boolean | true / false | True if offensive or abusive language was detected |

**Routing rules enforced by the output guard:**

| Category | Allowed owners |
|---|---|
| Refund Request | Billing Team, Customer Service Agent |
| Delivery Issue | Logistics Team, Customer Service Agent |
| Product Complaint | Customer Service Agent, Escalate to Manager |
| Account Problem | Billing Team, Customer Service Agent |
| General Enquiry | Customer Service Agent |
| Compliment | Customer Service Agent |
| Other | Any |
| Any category — High urgency | Escalate to Manager (for Refund Request, Product Complaint, Account Problem) |

If the LLM output violates any rule, the request is rejected with HTTP 422 and the reason is returned.

---

## 7. Running the Tests

Tests run locally using the project's virtual environment. No running containers or real Azure credentials are required — the LLM is fully mocked.

```bash
# Install test dependencies (once)
pip install -r api/requirements-test.txt

# Run all 93 tests
python -m pytest api/tests/ -v

# Run a specific file
python -m pytest api/tests/test_output_guard.py -v

# Run a specific class
python -m pytest api/tests/test_input_guard.py::TestCheckInput -v
```

---

## 8. Project Structure

Only active files are listed below. Scaffold-only placeholder files (`review_service.py`, `json_helpers.py`, `validators.py`, unused prompt files) are omitted.

```
customer-triage-agent/
│
├── docker-compose.yml          Defines and links the API and UI containers
├── pyproject.toml              Python project metadata + pytest configuration
├── .gitignore                  Excludes .env, __pycache__, venv,  files, etc.
├── README.md                   This file
│
├── api/                        FastAPI backend
│   ├── Dockerfile              Builds the API container image (Python 3.11-slim)
│   ├── requirements.txt        Runtime dependencies (FastAPI, SQLAlchemy, OpenAI, etc.)
│   ├── requirements-test.txt   Test-only dependencies (pytest, httpx, pytest-asyncio)
│   ├── .env                    Credentials — NOT committed, must be created manually
│   ├── .env.example            Template showing which variables are required
│   │
│   ├── data/
│   │   └── triage.db           SQLite database (volume-mounted; survives restarts)
│   │
│   └── app/
│       ├── main.py             FastAPI app factory — registers routers, CORS, lifespan
│       │
│       ├── api/routes/
│       │   ├── triage.py       POST /triage, POST /triage/batch,
│       │   │                   GET  /triage/history, POST /triage/upload
│       │   └── health.py       GET  /health — liveness check
│       │
│       ├── core/
│       │   ├── config.py       Pydantic Settings — reads all values from api/.env
│       │   └── constants.py    Allowed categories, urgency levels, owners,
│       │                       and the category → owner routing rules table
│       │
│       ├── db/
│       │   ├── models.py       SQLAlchemy TriageRecord model (one row per message)
│       │   ├── session.py      Database session factory + get_db() dependency
│       │   └── init_db.py      Calls Base.metadata.create_all() on app startup
│       │
│       ├── guards/
│       │   ├── input_guard.py  Pre-LLM check: strips whitespace, enforces 5k char
│       │   │                   limit, blocks prompt injection patterns (Pydantic model)
│       │   ├── output_guard.py Post-LLM Pydantic interface — wraps routing_guard and
│       │   │                   returns a typed GuardrailResult model
│       │   └── routing_guard.py Deterministic routing rules + hallucination detection
│       │                        + second LLM consistency check
│       │
│       ├── prompts/
│       │   └── system_prompt.py System prompt sent to GPT-4.1-mini and
│       │                        build_user_message() helper
│       │
│       ├── schemas/
│       │   ├── triage.py       All Pydantic request/response models with Literal types
│       │   │                   (TriageRequest, TriageResponse, BatchTriageRequest,
│       │   │                   BatchItemResponse, TriageHistoryItem, etc.)
│       │   └── common.py       HealthResponse schema
│       │
│       ├── services/
│       │   ├── triage_service.py  Orchestrates the full pipeline:
│       │   │                      input guard → LLM → output guard → DB persist
│       │   └── llm_service.py     Azure OpenAI client; calls GPT-4.1-mini with
│       │                          structured output (response_format=TriageResponse)
│       │
│       └── utils/
│           └── text_cleaning.py  clean_text() — normalises whitespace and line breaks
│
├── api/tests/                  Pytest test suite (93 tests, no real LLM calls)
│   ├── conftest.py             Fixtures: in-memory SQLite (StaticPool), TestClient,
│   │                           sample_triage_response
│   ├── test_triage_api.py      API route tests (POST /triage, GET /history, upload)
│   ├── test_input_guard.py     check_input() unit tests + schema + route validation
│   ├── test_output_guard.py    guardrail_check() + check_output() tests
│   └── test_batch_triage.py    Batch endpoint + CSV/JSON file extraction tests
│
├── ui/                         Streamlit frontend
│   ├── Dockerfile              Builds the UI container image
│   ├── requirements.txt        UI dependencies (Streamlit, pandas, requests)
│   ├── app.py                  Entry point — page config, sidebar, Triage + History tabs
│   │
│   ├── pages/
│   │   └── batch_triage.py     Renders the single-message input and batch file uploader;
│   │                           calls the API and displays results
│   │
│   ├── components/
│   │   └── batch_table.py      Flattens batch API results into a DataFrame, renders
│   │                           the results table, and provides CSV download
│   │
│   └── utils/
│       └── api_client.py       HTTP helper — wraps POST /triage, POST /triage/batch,
│                               GET /triage/history calls to the FastAPI backend
│
├── notebooks/
│   └── triage_demo.ipynb       Interactive demo notebook for exploring the triage pipeline
│
└── scripts/
    └── sample_messages.py      Sample customer messages for manual testing
```

---

## 9. Tools Used

| Tool | Role in this project |
|---|---|
| **Azure OpenAI (GPT-4.1-mini)** | Core LLM: classifies the message, determines urgency and sentiment, identifies the right owner, and writes a safe draft reply. Structured output mode (`response_format=TriageResponse`) is used so the model returns valid JSON that maps directly to a Pydantic model. |
| **FastAPI** | REST API framework for the backend. Handles routing, dependency injection (database sessions), request parsing, and response serialization. |
| **Pydantic** | Data validation at every boundary. `TriageRequest` enforces message constraints and strips whitespace via a field validator. `TriageResponse` uses `Literal` types for all enum fields (category, urgency, sentiment, owner, confidence) so the LLM output is validated against the exact allowed values. `InputGuardResult` and `OutputGuardInput` provide typed interfaces for the guard layer. |
| **Input Guard** | Pre-LLM deterministic check. Strips whitespace, enforces the 5,000-character limit, and blocks prompt injection patterns (e.g. "ignore previous instructions") before any API call is made. |
| **Output Guard / Routing Guard** | Post-LLM validation. Checks owner-to-category routing rules, the high-urgency escalation rule, hallucination patterns (fabricated order numbers, monetary amounts), and runs a second LLM call to verify consistency. |
| **SQLAlchemy + SQLite** | ORM for persisting every triage result to a SQLite database. The database file lives in `api/data/triage.db` and is volume-mounted so records survive container restarts. |
| **Streamlit** | Web UI. Provides the single-message input, batch CSV/Excel upload, history table, and CSV export — no frontend framework or JavaScript required. |
| **Docker / Docker Compose** | Packages the API and UI into isolated containers. `docker compose up --build` starts both services with a single command. |
| **pytest** | Test suite (93 tests across 4 files). Uses an in-memory SQLite database (`StaticPool`) and `AsyncMock` to test all layers — input guard, output guard, API routes, and batch processing — without any real LLM calls or running containers. |
| **uvicorn** | ASGI server that runs the FastAPI application inside the Docker container. |
| **httpx** | HTTP client used internally by FastAPI's `TestClient` to make requests against the app during tests. |
