# Task Management REST API
 
A production-style backend REST API built with **FastAPI**, **PostgreSQL**, **JWT authentication**, and **role-based access control**. Fully deployed on Render with an interactive Streamlit dashboard.
 
---
 
## Live Demo
 
| Service | URL |
|---|---|
| Streamlit Dashboard | https://task-project-management-rest-api-utec6jmyj7yg22w7pfpyha.streamlit.app |
| Swagger API Docs | https://task-project-management-rest-api.onrender.com/docs |
| Base API URL | https://task-project-management-rest-api.onrender.com |
 
> **Note:** Render free-tier instances spin down after inactivity. First request may take 30–60 seconds to cold-start.
 
### Demo Credentials
 
| Role | Email | Password | Access |
|---|---|---|---|
| Admin | admin@taskdemo.com | K#9v!mX7$zP2*qLt | Full access — users, projects, tasks, role management |
| Manager | manager@taskdemo.com | Manager@1234 | Create and update tasks across all projects |
| Viewer | viewer@taskdemo.com | Viewer@1234 | Read-only access to assigned tasks |
 
---
 
## Tech Stack
 
| Layer | Technology |
|---|---|
| Framework | FastAPI (Python 3.13) |
| Database | PostgreSQL (production) / SQLite (local dev) |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| Authentication | JWT via python-jose (OAuth2 Password Flow) |
| Password Hashing | bcrypt via passlib |
| Server | Gunicorn + Uvicorn workers |
| Deployment | Render (Web Service + PostgreSQL) |
| Dashboard | Streamlit |
| Testing | pytest + httpx |
 
---
 
## Features
 
- User registration and login with bcrypt password hashing
- JWT-based authentication (OAuth2 Password Flow)
- Role-based access control with three roles: `admin`, `manager`, `user`
- Full CRUD for projects and tasks
- Task assignment to users
- Task filtering by status and priority
- Pagination on task listing (`?page=1&limit=10`)
- Cascade deletes — deleting a project removes all its tasks
- Auto-generated Swagger UI and OpenAPI schema
- Streamlit dashboard with role-aware UI
---
 
## Project Structure
 
```
app/
├── api/
│   ├── auth.py          # Register and login endpoints
│   ├── users.py         # User profile and role management
│   ├── projects.py      # Project CRUD
│   └── tasks.py         # Task CRUD with RBAC and pagination
├── models/
│   ├── user.py          # User ORM model
│   ├── project.py       # Project ORM model
│   └── task.py          # Task ORM model
├── schemas/
│   ├── user.py          # Pydantic schemas for users
│   ├── project.py       # Pydantic schemas for projects
│   └── task.py          # Pydantic schemas for tasks
├── db/
│   ├── base.py          # SQLAlchemy declarative base
│   ├── session.py       # Engine and session factory
│   └── init_db.py       # Dev-only table creation
├── core/
│   ├── config.py        # pydantic-settings environment config
│   └── security.py      # Password hashing and JWT creation
└── utils/
    ├── dependencies.py  # Auth and RBAC FastAPI dependencies
    └── pagination.py    # Page/limit query parameter helper
alembic/                 # Database migration scripts
dashboard.py             # Streamlit frontend
```
 
---
 
## Authentication Flow
 
```
POST /auth/register  →  create account (bcrypt hashed password)
POST /auth/login     →  validate credentials, receive JWT token
                        Authorization: Bearer <token>
GET  /users/me       →  token decoded, user loaded via dependency
```
 
Every protected route runs through `get_current_user`, which decodes the JWT, validates the signature, and loads the user from the database. Role enforcement sits on top via `require_role(*roles)`.
 
---
 
## Role-Based Access Control
 
| Role | Permissions |
|---|---|
| `user` | Read own profile, view tasks assigned to them only |
| `manager` | Everything `user` can do + create and update tasks |
| `admin` | Full access — manage users, projects, tasks, assign roles |
 
New accounts default to the `user` role. Admins can promote any user via `PATCH /users/{user_id}/role`.
 
---
 
## API Endpoints
 
### Auth
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Register a new user |
| POST | `/auth/login` | No | Login and receive JWT token |
 
### Users
| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/users/me` | Any | Get current user profile |
| GET | `/users/` | admin | List all users |
| PATCH | `/users/{user_id}/role` | admin | Change a user's role |
 
### Projects
| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/projects/` | Any | List all projects |
| POST | `/projects/` | admin | Create a project |
| GET | `/projects/{project_id}` | Any | Get a specific project |
| PATCH | `/projects/{project_id}` | admin | Update a project |
| DELETE | `/projects/{project_id}` | admin | Delete a project (cascades to tasks) |
 
### Tasks
| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/tasks/` | admin, manager | Create a task |
| GET | `/tasks/` | Any | List tasks (users see only assigned tasks) |
| GET | `/tasks/{task_id}` | Any | Get a task (users restricted to assigned) |
| PATCH | `/tasks/{task_id}` | admin, manager | Update a task |
| DELETE | `/tasks/{task_id}` | admin, manager | Delete a task |
 
Task listing supports pagination: `GET /tasks/?page=1&limit=10`
 
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
 
### Relationships
- One User → Many Projects (via `owner_id`)
- One Project → Many Tasks (cascade delete)
- One User → Many Tasks (via `assigned_to`, nullable)
---
 
## Local Development
 
### Prerequisites
- Python 3.13+
- PostgreSQL running locally (or use SQLite for quick dev)
### Setup
 
```bash
git clone https://github.com/aditi-nayak-ai/Task-Project-Management-REST-API.git
cd Task-Project-Management-REST-API
 
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
 
pip install -r requirements.txt
```
 
### Environment Variables
 
Create a `.env` file in the project root:
 
```
DATABASE_URL=postgresql://user:password@localhost/taskdb
SECRET_KEY=your-secret-key-minimum-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```
 
For local dev with SQLite:
 
```
DATABASE_URL=sqlite:///./test.db
```
 
### Run
 
```bash
alembic upgrade head
uvicorn app.main:app --reload
```
 
Swagger UI: http://127.0.0.1:8000/docs
 
### Run Streamlit Dashboard
 
```bash
streamlit run dashboard.py
```
 
---
 
## Deployment on Render
 
1. Create a Render PostgreSQL database — copy the internal connection string
2. Create a Render Web Service connected to this GitHub repository
3. Set environment variables in Render dashboard:
```
DATABASE_URL=<internal connection string from Render PostgreSQL>
SECRET_KEY=<your secret key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```
 
4. Set Start Command:
```
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```
 
Migrations run automatically on startup via `alembic upgrade head` called in `main.py`.
 
---
 
## Example Requests
 
### Register
```bash
curl -X POST https://task-project-management-rest-api.onrender.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "yourpassword"}'
```
 
### Login
```bash
curl -X POST https://task-project-management-rest-api.onrender.com/auth/login \
  -d "username=user@example.com&password=yourpassword"
```
 
### Create Project (admin only)
```bash
curl -X POST https://task-project-management-rest-api.onrender.com/projects/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Sprint 1", "description": "Core API development"}'
```
 
### Create Task (admin or manager)
```bash
curl -X POST https://task-project-management-rest-api.onrender.com/tasks/ \
  -H "Authorization: Bearer <token>" \
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
 
## Known Limitations
 
| Item | Notes |
|---|---|
| JWT refresh tokens | Not implemented — tokens expire after 60 minutes with no renewal path |
| Token revocation | Logout is client-side only — token remains valid until expiry |
| Rate limiting | No brute-force protection on auth endpoints |
| Pagination | Implemented on tasks only — projects and users return full lists |
| Test coverage | pytest + httpx configured — integration tests in progress |
 
