# Task Management REST API
 
![CI/CD](https://github.com/aditi-nayak-ai/Task-Project-Management-REST-API/actions/workflows/ci-cd.yml/badge.svg)
 
A production-style backend REST API built with **FastAPI**, **PostgreSQL**, **JWT authentication** (access + refresh tokens), and **role-based access control**. Containerized with Docker, tested and deployed automatically via GitHub Actions CI/CD, and paired with an interactive Streamlit dashboard.
 
---
 
## Live Demo
 
| Service | URL |
|---|---|
| Streamlit Dashboard | https://task-project-management-rest-api.onrender.com |
| Swagger API Docs | https://task-project-management-rest-api-1.onrender.com/docs |
| Base API URL | https://task-project-management-rest-api-1.onrender.com |
 
> **Note:** Both services run on free tiers and spin down after inactivity. The first request after idle time may take 30–60 seconds to cold-start — this is expected, not a bug.
 
### Demo Credentials
 
| Role | Email | Password | Access |
|---|---|---|---|
| Admin | admin@taskdemo.com | *(rotate before sharing publicly — see Security Notes)* | Full access — users, projects, tasks, role management, audit log |
| Manager | manager@taskdemo.com | *(rotate before sharing publicly)* | Create and update tasks on projects they're scoped to |
| Viewer | viewer@taskdemo.com | *(rotate before sharing publicly)* | Read-only access to tasks assigned to them |
 
> Demo credentials are seeded/updated directly in the database, not committed to source control. See **Security Notes** below for why, and how to rotate them.
 
---
 
## Tech Stack
 
| Layer | Technology |
|---|---|
| Framework | FastAPI (Python 3.13) |
| Database | PostgreSQL (production) / SQLite (local dev & tests) |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic — run automatically at startup via the app's lifespan |
| Authentication | JWT access tokens (python-jose) + hashed, revocable refresh tokens |
| Password Hashing | bcrypt via passlib |
| Rate Limiting | slowapi (per-route limits on auth endpoints) |
| Server | Gunicorn + Uvicorn workers |
| Containerization | Docker (multi-stage build) + docker-compose for local dev |
| CI/CD | GitHub Actions — lint → test → build/push image → deploy |
| Deployment | Render (Web Service + PostgreSQL) |
| Dashboard | Streamlit |
| Testing | pytest + httpx, with coverage reporting |
| Linting | ruff |
 
---
 
## Features
 
- User registration and login with bcrypt password hashing
- JWT access tokens **and** hashed refresh tokens with server-side revocation (`/auth/refresh`, `/auth/logout`)
- Rate limiting on auth endpoints (register, login, refresh) to slow brute-force attempts
- Role-based access control with three roles: `admin`, `manager`, `user`
- Per-project manager scoping — a manager must be explicitly assigned to a project before they can create or edit its tasks
- Full CRUD for projects and tasks, with optimistic concurrency control (`version` field) to prevent silent overwrite on concurrent edits
- Task assignment to users; a `user`-role account only sees tasks assigned to them
- Task filtering by status and priority, pagination on tasks/projects/users (`?page=1&limit=10`)
- Cascade deletes — deleting a project removes all its tasks
- Audit log of sensitive actions (task/project changes, role updates) queryable by admins (`/audit-logs/`)
- Structured logging and a dedicated `/health/db` endpoint that actually round-trips the database (not just "process is up")
- Auto-generated Swagger UI and OpenAPI schema
- Streamlit dashboard with role-aware UI (different views/actions for admin, manager, viewer)
---
 
## Screenshots
 
| | |
|---|---|
| **Login** | <img width="1920" height="1080" alt="Screenshot (431)" src="https://github.com/user-attachments/assets/ec2b7df0-6541-4ce4-a619-301ccd83ef2e" />|
| **Admin Dashboard** | <img width="1920" height="1080" alt="Admin Dashboard" src="https://github.com/user-attachments/assets/2937a320-5dbf-4046-bea4-d1644604358c" />|
| **Users & Roles** | <img width="1920" height="1080" alt="User   Role" src="https://github.com/user-attachments/assets/463752f9-4f3b-446a-8bff-409cd54ce6a0" />|
| **Tasks** | <img width="1920" height="1080" alt="Task" src="https://github.com/user-attachments/assets/83848064-ed62-44cd-ba65-acc41c06112e" />|
 
---
 
## Project Structure
 
```
app/
├── api/
│   ├── auth.py           # Register, login, refresh, logout
│   ├── users.py          # User profile and role management
│   ├── projects.py       # Project CRUD + project-manager scoping
│   ├── tasks.py          # Task CRUD with RBAC, scoping, pagination
│   └── audit.py          # Admin-only audit log queries
├── models/                # SQLAlchemy ORM models (user, project, task,
│                          # project_manager, refresh_token, audit_log)
├── schemas/               # Pydantic request/response schemas
├── db/
│   ├── base.py            # SQLAlchemy declarative base
│   ├── session.py         # Engine and session factory
│   └── seed.py            # Seeds the first admin account on startup
├── core/
│   ├── config.py          # pydantic-settings environment config
│   ├── security.py        # Password hashing, JWT + refresh token logic
│   ├── audit.py            # record_audit() helper used across routers
│   ├── errors.py           # Centralized exception handlers
│   └── limiter.py          # slowapi rate limiter instance
└── utils/
    ├── dependencies.py     # Auth and RBAC FastAPI dependencies
    └── pagination.py       # Page/limit query parameter helper
 
alembic/                    # Database migration scripts
tests/                      # pytest suite (auth, RBAC, rate limiting, security)
scripts/                    # One-off maintenance scripts (e.g. backfill)
dashboard.py                # Streamlit frontend
Dockerfile                  # Multi-stage production image
docker-compose.yml          # Local dev: API + Postgres + Redis + dashboard
.github/workflows/ci-cd.yml # Lint, test, build/push image, deploy
```
 
---
 
## Authentication Flow
 
```
POST /auth/register  →  create account (bcrypt hashed password)
POST /auth/login     →  validate credentials, receive access + refresh token
                         Authorization: Bearer <access_token>
POST /auth/refresh   →  exchange a valid refresh token for a new access token
POST /auth/logout    →  revoke a refresh token server-side
GET  /users/me       →  token decoded, user loaded via dependency
```
 
Every protected route runs through `get_current_user`, which decodes the JWT, validates the signature, and loads the user from the database. Role enforcement sits on top via `require_role(*roles)`. Refresh tokens are never stored in plaintext — only a SHA-256 hash is persisted, and revoking one (logout) does not retroactively invalidate access tokens already issued (a documented, deliberate tradeoff of stateless JWTs — see the comment in `app/api/auth.py`).
 
---
 
## Role-Based Access Control
 
| Role | Permissions |
|---|---|
| `user` | Read own profile, view only tasks assigned to them |
| `manager` | Everything `user` can do + create/update/delete tasks on projects they're scoped to via `/projects/{id}/managers` |
| `admin` | Full access — manage users, projects, tasks, project-manager assignments, role changes, and the audit log |
 
New accounts default to the `user` role. Admins can promote any user via `PATCH /users/{user_id}/role`.
 
---
 
## API Endpoints
 
### Auth
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Register a new user (rate limited: 10/min) |
| POST | `/auth/login` | No | Login, receive access + refresh token (rate limited: 5/min) |
| POST | `/auth/refresh` | No (valid refresh token) | Exchange refresh token for new access token (rate limited: 30/min) |
| POST | `/auth/logout` | No (valid refresh token) | Revoke a refresh token |
 
### Users
| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/users/me` | Any | Get current user profile |
| GET | `/users/` | admin | List all users (paginated) |
| PATCH | `/users/{user_id}/role` | admin | Change a user's role |
 
### Projects
| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/projects/` | Any | List all projects (paginated) |
| POST | `/projects/` | admin | Create a project |
| GET | `/projects/{project_id}` | Any | Get a specific project |
| PATCH | `/projects/{project_id}` | admin | Update a project (requires current `version`) |
| DELETE | `/projects/{project_id}` | admin | Delete a project (cascades to tasks) |
| GET | `/projects/{project_id}/managers` | admin | List managers scoped to a project |
| POST | `/projects/{project_id}/managers/{user_id}` | admin | Scope a manager to a project |
| DELETE | `/projects/{project_id}/managers/{user_id}` | admin | Remove a manager's scope on a project |
 
### Tasks
| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/tasks/` | admin, scoped manager | Create a task |
| GET | `/tasks/` | Any | List tasks (`user` role sees only tasks assigned to them) |
| GET | `/tasks/{task_id}` | Any | Get a task (same visibility rule as above) |
| PATCH | `/tasks/{task_id}` | admin, scoped manager | Update a task (requires current `version`) |
| DELETE | `/tasks/{task_id}` | admin, scoped manager | Delete a task |
 
### Audit Log
| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/audit-logs/` | admin | List audit log entries, filterable by `resource_type` and `action`, paginated |
 
### Health
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | No | Liveness check |
| GET | `/health/db` | No | Confirms the app can actually reach and query the database |
 
---
 
## Data Models
 
### Task Fields
| Field | Type | Values |
|---|---|---|
| `status` | Enum | `todo` / `in_progress` / `done` |
| `priority` | Enum | `low` / `medium` / `high` |
| `due_date` | datetime (optional) | ISO 8601 |
| `project_id` | integer | Required — foreign key to projects |
| `assigned_to` | integer (optional) | Foreign key to users |
| `version` | integer | Incremented on update; required on `PATCH` for optimistic concurrency |
 
### Relationships
- One User → Many Projects (via `owner_id`)
- One Project → Many Tasks (cascade delete)
- One Project → Many scoped Managers (via `project_manager` join table)
- One User → Many Tasks (via `assigned_to`, nullable)
- One User → Many Refresh Tokens (revocable independently)
---
 
## Local Development
 
### Option A — Docker (recommended, matches production)
 
```bash
git clone https://github.com/aditi-nayak-ai/Task-Project-Management-REST-API.git
cd Task-Project-Management-REST-API
cp .env.example .env
# generate a real SECRET_KEY and put it in .env:
python -c "import secrets; print(secrets.token_urlsafe(48))"
 
docker compose up --build
```
 
This starts Postgres, Redis, the FastAPI service (with migrations run automatically), and the Streamlit dashboard together. API: `http://localhost:8000`, docs: `http://localhost:8000/docs`, dashboard: `http://localhost:8501`.
 
### Option B — Local Python environment
 
**Prerequisites:** Python 3.13+, PostgreSQL running locally (or SQLite for quick dev)
 
```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
 
Copy `.env.example` to `.env` and fill in real values (a generated `SECRET_KEY` at minimum). For quick local dev without Postgres, set:
```
DATABASE_URL=sqlite:///./test.db
```
 
Run:
```bash
uvicorn app.main:app --reload
```
Migrations run automatically at startup (`RUN_MIGRATIONS_ON_STARTUP=true` by default). Swagger UI: `http://127.0.0.1:8000/docs`.
 
Run the dashboard separately:
```bash
streamlit run dashboard.py
```
 
### Run tests
 
```bash
pytest --cov=app --cov-report=term-missing
```
 
---
 
## Environment Variables
 
See `.env.example` for the full list with descriptions. Key ones:
 
| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy connection string (Postgres in prod, SQLite for quick local dev) |
| `SECRET_KEY` | JWT signing secret — **must** be 32+ characters, never committed |
| `ALGORITHM` | JWT algorithm (default `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime |
| `CORS_ORIGINS` | Comma-separated list of allowed browser origins |
| `RUN_MIGRATIONS_ON_STARTUP` | Whether Alembic migrations run at boot — set `false` in multi-replica deployments and run migrations as a separate release step instead |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Optional — auto-seeds a first admin account on startup |
 
---
 
## CI/CD Pipeline
 
Every push to `main` (and every PR) runs through GitHub Actions:
 
1. **Lint** — `ruff check app tests`
2. **Test** — full pytest suite against an in-memory SQLite DB, with coverage
3. **Build & push** *(main branch only, after tests pass)* — multi-stage Docker image built and pushed to GitHub Container Registry (`ghcr.io`)
4. **Deploy** *(main branch only, after image push)* — triggers a Render deploy hook, which pulls the new build and runs migrations
See `.github/workflows/ci-cd.yml`. `pyproject.toml` scopes ruff to real-bug checks (`F` rules) rather than style opinions, so the pipeline fails on actual problems, not formatting preference.
 
---
 
## Deployment on Render
 
1. Create a Render PostgreSQL database — copy its **internal** connection string
2. Create a Render Web Service connected to this GitHub repository (or configured to deploy the image built by CI)
3. Set environment variables in the Render dashboard (Environment tab) — see the list above; `DATABASE_URL` should use the `postgresql+psycopg2://` scheme
4. Start command:
```
   gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```
5. Create a Deploy Hook (Settings → Deploy Hook) and store its URL as the `RENDER_DEPLOY_HOOK_URL` GitHub Actions repo secret, so CI can trigger deploys automatically
Migrations run automatically on startup via the app's `lifespan` (`RUN_MIGRATIONS_ON_STARTUP=true`). For a multi-replica deployment, set that to `false` and run `alembic upgrade head` as a separate release-phase step instead, so replicas don't race on DDL at boot.
 
---
 
## Example Requests
 
### Register
```bash
curl -X POST https://task-project-management-rest-api-1.onrender.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "yourpassword"}'
```
 
### Login
```bash
curl -X POST https://task-project-management-rest-api-1.onrender.com/auth/login \
  -d "username=user@example.com&password=yourpassword"
```
 
### Refresh an access token
```bash
curl -X POST https://task-project-management-rest-api-1.onrender.com/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token from login>"}'
```
 
### Create Project (admin only)
```bash
curl -X POST https://task-project-management-rest-api-1.onrender.com/projects/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Sprint 1", "description": "Core API development"}'
```
 
### Create Task (admin or a manager scoped to the project)
```bash
curl -X POST https://task-project-management-rest-api-1.onrender.com/tasks/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Implement JWT refresh tokens",
    "status": "todo",
    "priority": "high",
    "project_id": 1,
    "assigned_to": 2
  }'
```
 
---
 
## Security Notes
 
- `.env` is git-ignored; only `.env.example` (with placeholder values) is committed
- `SECRET_KEY` and demo account passwords are rotated periodically and stored only in Render's environment variables and the production database — never in source control
- Refresh tokens are stored as SHA-256 hashes, never in plaintext
- Rate limiting on `/auth/*` routes mitigates brute-force login attempts
- `pre-commit` hooks (`ruff`, `gitleaks`, `detect-private-key`) run locally to catch secrets before they're ever committed — see `.pre-commit-config.yaml`
If you fork this repo, rotate `SECRET_KEY` and any demo credentials before deploying your own instance.
 
---
 
## Known Limitations
 
| Item | Notes |
|---|---|
| Access token revocation | Access tokens remain valid until expiry even after logout — only refresh tokens are revocable. A short access-token TTL is the current mitigation. |
| Email verification | Registration does not send a verification email; any syntactically valid email is accepted |
| Test coverage | Core auth/RBAC/security paths are covered; some routers (projects, users, audit) have lower line coverage — see `pytest --cov` output |
| Multi-replica migrations | `RUN_MIGRATIONS_ON_STARTUP` is convenient for a single instance but should be disabled in favor of a release-phase migration step once this runs on more than one replica |
 
