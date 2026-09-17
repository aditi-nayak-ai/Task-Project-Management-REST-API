from tests.conftest import auth_header


def test_only_admin_can_create_project(client, admin_user, manager_user):
    admin_headers = auth_header(client, "admin@test.com", "AdminPass1!")
    r = client.post("/projects/", json={"name": "Project A", "description": "desc"}, headers=admin_headers)
    assert r.status_code == 201

    manager_headers = auth_header(client, "manager@test.com", "ManagerPass1!")
    r = client.post("/projects/", json={"name": "Project B"}, headers=manager_headers)
    assert r.status_code == 403


def test_duplicate_project_name_returns_409_not_500(client, admin_user):
    admin_headers = auth_header(client, "admin@test.com", "AdminPass1!")
    project = client.post("/projects/", json={"name": "Visible Project"}, headers=admin_headers).json()
    # Manager must be explicitly scoped to this project before they can
    # act on it -- see _ensure_can_act_on_project in app/api/tasks.py.
    client.post(f"/projects/{project['id']}/managers/{manager_user.id}", headers=admin_headers)
    manager_headers = auth_header(client, "manager@test.com", "ManagerPass1!")

    r = client.post("/projects/", json={"name": "Unique Name"}, headers=admin_headers)
    # Regression test for the bug found in the original code: an unhandled
    # IntegrityError on the unique constraint used to propagate as a raw
    # 500. It must now be a clean 409.
    assert r.status_code == 409


def test_create_task_with_nonexistent_project_returns_404_not_500(client, manager_user):
    manager_headers = auth_header(client, "manager@test.com", "ManagerPass1!")
    r = client.post(
        "/tasks/",
        json={"title": "Orphan task", "project_id": 9999},
        headers=manager_headers,
    )
    # Regression test: previously this reached the DB, violated the FK
    # constraint, and surfaced as an unhandled 500.
    assert r.status_code == 404
    assert "Project" in r.json()["detail"]


def test_create_task_with_nonexistent_assignee_returns_404(client, admin_user, manager_user):
    admin_headers = auth_header(client, "admin@test.com", "AdminPass1!")
    project = client.post("/projects/", json={"name": "Real Project"}, headers=admin_headers).json()

    manager_headers = auth_header(client, "manager@test.com", "ManagerPass1!")
    r = client.post(
        "/tasks/",
        json={"title": "Task", "project_id": project["id"], "assigned_to": 9999},
        headers=manager_headers,
    )
    assert r.status_code == 404
    assert "User" in r.json()["detail"]


def test_regular_user_only_sees_assigned_tasks(client, admin_user, manager_user, regular_user):
    admin_headers = auth_header(client, "admin@test.com", "AdminPass1!")
    project = client.post("/projects/", json={"name": "Visible Project"}, headers=admin_headers).json()

    manager_headers = auth_header(client, "manager@test.com", "ManagerPass1!")
    client.post(
        "/tasks/",
        json={"title": "Assigned to user", "project_id": project["id"], "assigned_to": regular_user.id},
        headers=manager_headers,
    )
    client.post(
        "/tasks/",
        json={"title": "Not assigned to user", "project_id": project["id"]},
        headers=manager_headers,
    )

    user_headers = auth_header(client, "user@test.com", "UserPass1!")
    r = client.get("/tasks/", headers=user_headers)
    assert r.status_code == 200
    titles = [t["title"] for t in r.json()]
    assert titles == ["Assigned to user"]


def test_regular_user_cannot_create_task(client, regular_user):
    user_headers = auth_header(client, "user@test.com", "UserPass1!")
    r = client.post("/tasks/", json={"title": "Nope", "project_id": 1}, headers=user_headers)
    assert r.status_code == 403
