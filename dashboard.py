
import os
import streamlit as st
import requests
import pandas as pd
 
API_URL = os.environ.get("API_URL", "https://task-project-management-rest-api-1.onrender.com")
 
st.set_page_config(page_title="Task Manager", layout="wide", page_icon="✅")
 
# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: #f8fafc; }
    [data-testid="stAppViewContainer"] * { color: #1e293b; }
    [data-testid="stSidebar"] { background: #1e293b; }
    [data-testid="stSidebar"] * { color: #f1f5f9 !important; }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px 24px;
        border-left: 4px solid #0d9488;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        margin-bottom: 8px;
    }
    .metric-card .label { font-size: 13px; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-card .value { font-size: 32px; font-weight: 700; color: #1e293b; margin-top: 4px; }
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 99px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-todo { background: #f1f5f9; color: #475569; }
    .badge-in_progress { background: #fef9c3; color: #92400e; }
    .badge-done { background: #dcfce7; color: #166534; }
    .badge-low { background: #f0fdf4; color: #166534; }
    .badge-medium { background: #fff7ed; color: #9a3412; }
    .badge-high { background: #fef2f2; color: #991b1b; }
    .demo-box {
        background: #f0fdfa;
        border: 1px solid #99f6e4;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 16px;
    }
    .demo-box b { color: #0d9488; }
    .section-title {
        font-size: 20px;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 2px solid #e2e8f0;
    }
    div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
    .stButton > button {
        background: #0d9488;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 600;
    }
    .stButton > button:hover { background: #0f766e; }
</style>
""", unsafe_allow_html=True)
 
 
# ── Helpers ───────────────────────────────────────────────────────────────────
 
def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}
 
 
def extract_error_detail(response):
    """
    Safely pull an error message out of a response. Render's free tier can
    return an HTML error page (e.g. during a cold start / 502) instead of
    JSON -- calling .json() on that raises "Expecting value: line 1 column
    1", which is confusing to see as a user-facing error. This gives a
    clear message in that case instead of crashing the parse.
 
    FastAPI validation errors (422) return `detail` as a list of dicts, so
    that case is flattened into a readable string too.
    """
    try:
        detail = response.json().get("detail", f"Request failed with status {response.status_code}.")
        if isinstance(detail, list):
            parts = []
            for item in detail:
                loc = ".".join(str(x) for x in item.get("loc", []))
                parts.append(f"{loc}: {item.get('msg', 'invalid')}")
            return "; ".join(parts)
        return detail
    except Exception:
        return (
            f"Server returned an unexpected response (status {response.status_code}). "
            "It may be waking up from sleep -- wait a moment and try again."
        )
 
 
def try_refresh_token():
    """
    Uses the stored refresh token to get a new access token without
    forcing the user to log in again. Added alongside the backend's
    /auth/refresh endpoint -- without this, issuing a refresh token from
    the API was pointless because nothing in the client ever used it.
    """
    if not st.session_state.get("refresh_token"):
        return False
    try:
        r = requests.post(
            f"{API_URL}/auth/refresh",
            json={"refresh_token": st.session_state.refresh_token},
            timeout=15,
        )
        if r.status_code == 200:
            st.session_state.token = r.json()["access_token"]
            return True
    except Exception:
        pass
    return False
 
 
def api_get(endpoint, params=None):
    try:
        r = requests.get(f"{API_URL}{endpoint}", headers=auth_headers(), params=params, timeout=15)
        if r.status_code == 401:
            if try_refresh_token():
                r = requests.get(f"{API_URL}{endpoint}", headers=auth_headers(), params=params, timeout=15)
            else:
                st.session_state.token = None
                st.session_state.refresh_token = None
                st.warning("Session expired. Please log in again.")
                st.rerun()
        if r.status_code == 403:
            return []
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else [data]
    except Exception:
        return []
 
 
def api_post(endpoint, payload=None, form_data=None):
    try:
        kwargs = {"headers": auth_headers(), "timeout": 15}
        if form_data:
            kwargs["data"] = form_data
        else:
            kwargs["json"] = payload
        r = requests.post(f"{API_URL}{endpoint}", **kwargs)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"Error: {extract_error_detail(e.response)}")
    except Exception as e:
        st.error(f"Connection error: {e}")
    return None
 
 
def api_delete(endpoint):
    try:
        r = requests.delete(f"{API_URL}{endpoint}", headers=auth_headers(), timeout=15)
        return r.status_code == 204
    except Exception:
        return False
 
 
def api_patch(endpoint, payload):
    try:
        r = requests.patch(f"{API_URL}{endpoint}", json=payload, headers=auth_headers(), timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 409:
            st.error(
                f"{extract_error_detail(e.response)} "
                "Someone else changed this item. Reload the page and try again."
            )
        else:
            st.error(f"Error: {extract_error_detail(e.response)}")
    except Exception as e:
        st.error(f"Connection error: {e}")
    return None
 
 
# ── Session init ──────────────────────────────────────────────────────────────
 
for key, default in [("token", None), ("refresh_token", None), ("user", None)]:
    if key not in st.session_state:
        st.session_state[key] = default
 
 
# ── Login / Register ──────────────────────────────────────────────────────────
 
if not st.session_state.token:
    st.markdown("<h1 style='color:#0d9488;margin-bottom:4px'>✅ Task Manager</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#64748b;margin-bottom:24px'>A production-style REST API with JWT auth and role-based access control.</p>",
        unsafe_allow_html=True,
    )
 
    st.markdown("""
    <div class="demo-box">
        <b>🔑 Demo Credentials</b><br><br>
        <b>Admin</b> — full access (create projects, manage users, assign roles)<br>
        &nbsp;&nbsp;Email: <b>admin@taskdemo.com</b> &nbsp;|&nbsp; Password: <b>81iBtLus8J@</b><br><br>
        <b>Manager</b> — create and manage tasks<br>
        &nbsp;&nbsp;Email: <b>manager@taskdemo.com</b> &nbsp;|&nbsp; Password: <b>muQ9OLT1ZZ!</b><br><br>
        <b>Viewer</b> — see only tasks assigned to them<br>
        &nbsp;&nbsp;Email: <b>viewer@taskdemo.com</b> &nbsp;|&nbsp; Password: <b>bQ3wJlNj9N$</b>
    </div>
    """, unsafe_allow_html=True)
 
    tab_login, tab_register = st.tabs(["Login", "Register"])
 
    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", key="btn_login"):
            if not email or not password:
                st.warning("Enter both email and password.")
            else:
                try:
                    r = requests.post(
                        f"{API_URL}/auth/login",
                        data={"username": email, "password": password},
                        timeout=20,
                    )
                    if r.status_code == 200:
                        payload = r.json()
                        st.session_state.token = payload["access_token"]
                        st.session_state.refresh_token = payload["refresh_token"]
                        st.rerun()
                    elif r.status_code == 429:
                        st.error("Too many login attempts. Wait a minute and try again.")
                    else:
                        st.error(extract_error_detail(r))
                except Exception as e:
                    st.error(f"Could not reach server: {e}")
 
    with tab_register:
        st.caption("Register a new account. New users get 'viewer' role by default — an admin can promote you. Password must be 8–72 characters.")
        reg_email = st.text_input("Email", key="reg_email")
        reg_pass = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Register", key="btn_register"):
            if not reg_email or not reg_pass:
                st.warning("Fill in both fields.")
            elif not 8 <= len(reg_pass) <= 72:
                st.warning("Password must be between 8 and 72 characters.")
            else:
                try:
                    r = requests.post(
                        f"{API_URL}/auth/register",
                        json={"email": reg_email, "password": reg_pass},
                        timeout=20,
                    )
                    if r.status_code == 201:
                        st.success("Account created! Switch to the Login tab.")
                    else:
                        st.error(extract_error_detail(r))
                except Exception as e:
                    st.error(f"Could not reach server: {e}")
 
    st.stop()
 
 
# ── Load current user ─────────────────────────────────────────────────────────
 
if not st.session_state.user:
    me = api_get("/users/me")
    st.session_state.user = me[0] if me else {}
 
user = st.session_state.user
role = user.get("role", "user")
is_admin = role == "admin"
is_manager = role in ("admin", "manager")
 
 
# ── Sidebar ───────────────────────────────────────────────────────────────────
 
with st.sidebar:
    st.markdown(
        "<div style='font-size:22px;font-weight:700;margin-bottom:4px'>✅ Task Manager</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:13px;color:#94a3b8;margin-bottom:20px'>{user.get('email', '')}</div>",
        unsafe_allow_html=True,
    )
 
    role_colors = {"admin": "#f59e0b", "manager": "#60a5fa", "user": "#34d399"}
    st.markdown(
        f"<span style='background:{role_colors.get(role, '#94a3b8')};color:#1e293b;padding:3px 12px;"
        f"border-radius:99px;font-size:12px;font-weight:700;text-transform:uppercase'>{role}</span>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)
 
    pages = ["Dashboard", "Projects", "Tasks"]
    if is_admin:
        pages.append("Users")
    menu = st.selectbox("Navigate", pages)
 
    st.markdown("<br>" * 6, unsafe_allow_html=True)
    if st.button("Logout"):
        if st.session_state.get("refresh_token"):
            try:
                requests.post(
                    f"{API_URL}/auth/logout",
                    json={"refresh_token": st.session_state.refresh_token},
                    timeout=5,
                )
            except Exception:
                pass  # best-effort revoke; don't block logout on it
        st.session_state.token = None
        st.session_state.refresh_token = None
        st.session_state.user = None
        st.rerun()
 
    st.markdown("""
    <div style='font-size:11px;color:#475569;margin-top:8px'>
    Built with FastAPI · PostgreSQL<br>JWT Auth · RBAC · Deployed on Render
    </div>
    """, unsafe_allow_html=True)
 
 
# ── Dashboard ─────────────────────────────────────────────────────────────────
 
if menu == "Dashboard":
    st.markdown("<div class='section-title'>📊 Overview</div>", unsafe_allow_html=True)
 
    projects = api_get("/projects/", params={"limit": 100})
    tasks = api_get("/tasks/", params={"limit": 100})
    users = api_get("/users/", params={"limit": 100}) if is_admin else []
 
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""<div class='metric-card'>
            <div class='label'>{'Total Users' if is_admin else 'My Role'}</div>
            <div class='value'>{'👥 ' + str(len(users)) if is_admin else role.title()}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='metric-card'>
            <div class='label'>Projects</div>
            <div class='value'>📁 {len(projects)}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class='metric-card'>
            <div class='label'>{'All Tasks' if is_manager else 'My Tasks'}</div>
            <div class='value'>✅ {len(tasks)}</div>
        </div>""", unsafe_allow_html=True)
 
    if tasks:
        df = pd.DataFrame(tasks)
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Tasks by Status**")
            st.bar_chart(df["status"].value_counts(), color="#0d9488")
        with col_b:
            st.markdown("**Tasks by Priority**")
            st.bar_chart(df["priority"].value_counts(), color="#f59e0b")
 
        st.markdown("**Recent Tasks**")
        display = df[["title", "status", "priority", "due_date"]].head(5).copy()
        display.columns = ["Title", "Status", "Priority", "Due Date"]
        st.dataframe(display, use_container_width=True, hide_index=True)
 
 
# ── Projects ──────────────────────────────────────────────────────────────────
 
elif menu == "Projects":
    st.markdown("<div class='section-title'>📁 Projects</div>", unsafe_allow_html=True)
 
    if is_admin:
        with st.expander("➕ Create New Project"):
            p_name = st.text_input("Project Name", key="proj_name")
            p_desc = st.text_area("Description", key="proj_desc")
            if st.button("Create Project"):
                if not p_name.strip():
                    st.warning("Project name is required.")
                else:
                    result = api_post("/projects/", {"name": p_name, "description": p_desc})
                    if result:
                        st.success(f"Project '{result['name']}' created.")
                        st.rerun()
 
    projects = api_get("/projects/", params={"limit": 100})
    if projects:
        df = pd.DataFrame(projects)[["id", "name", "description", "owner_id", "created_at"]]
        df.columns = ["ID", "Name", "Description", "Owner ID", "Created At"]
        df["Created At"] = pd.to_datetime(df["Created At"]).dt.strftime("%d %b %Y")
        st.dataframe(df, use_container_width=True, hide_index=True)
 
        if is_admin:
            project_options = {p["name"]: p["id"] for p in projects}
 
            st.markdown("---")
            st.markdown("**Project Managers**")
            st.caption(
                "A manager can create and update tasks only in projects they are assigned to here. "
                "Admins can act on every project, so they never need to be added."
            )
 
            all_users = api_get("/users/", params={"limit": 100})
            email_by_id = {u["id"]: u["email"] for u in all_users}
            manager_users = [u for u in all_users if u["role"] == "manager"]
 
            mgr_project = st.selectbox("Project", list(project_options.keys()), key="mgr_proj")
            mgr_pid = project_options[mgr_project]
            current_links = api_get(f"/projects/{mgr_pid}/managers")
 
            if current_links:
                st.dataframe(
                    pd.DataFrame(
                        [{"User ID": m["user_id"], "Email": email_by_id.get(m["user_id"], "unknown")} for m in current_links]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No managers are assigned to this project yet.")
 
            if not manager_users:
                st.info("No user has the 'manager' role yet. Promote a user on the Users page first.")
            else:
                assigned_ids = {m["user_id"] for m in current_links}
                add_options = {u["email"]: u["id"] for u in manager_users if u["id"] not in assigned_ids}
                remove_options = {
                    email_by_id.get(uid, f"user {uid}"): uid for uid in assigned_ids
                }
 
                col_add, col_remove = st.columns(2)
                with col_add:
                    if add_options:
                        add_pick = st.selectbox("Add manager", list(add_options.keys()), key="mgr_add")
                        if st.button("Add to project", key="btn_mgr_add"):
                            if api_post(f"/projects/{mgr_pid}/managers/{add_options[add_pick]}"):
                                st.success(f"{add_pick} can now manage '{mgr_project}'.")
                                st.rerun()
                    else:
                        st.caption("Every manager is already assigned to this project.")
                with col_remove:
                    if remove_options:
                        remove_pick = st.selectbox("Remove manager", list(remove_options.keys()), key="mgr_remove")
                        if st.button("Remove from project", key="btn_mgr_remove"):
                            if api_delete(f"/projects/{mgr_pid}/managers/{remove_options[remove_pick]}"):
                                st.success(f"Removed {remove_pick} from '{mgr_project}'.")
                                st.rerun()
 
            st.markdown("---")
            st.markdown("**Delete Project**")
            selected = st.selectbox("Select project", list(project_options.keys()), key="del_proj")
            if st.button("🗑️ Delete Selected Project"):
                if api_delete(f"/projects/{project_options[selected]}"):
                    st.success(f"Deleted '{selected}'")
                    st.rerun()
    else:
        st.info("No projects found.")
 
 
# ── Tasks ─────────────────────────────────────────────────────────────────────
 
elif menu == "Tasks":
    st.markdown("<div class='section-title'>✅ Tasks</div>", unsafe_allow_html=True)
 
    projects = api_get("/projects/", params={"limit": 100})
    project_map = {p["name"]: p["id"] for p in projects}
 
    # Only admins may list users, so only admins get an assignee dropdown.
    # Managers can still assign by typing a user ID.
    task_users = api_get("/users/", params={"limit": 100}) if is_admin else []
    email_by_id = {u["id"]: u["email"] for u in task_users}
    assignee_ids = {u["email"]: u["id"] for u in task_users}
    UNASSIGNED = "— Unassigned —"
    KEEP_CURRENT = "— Keep current —"
 
    if is_manager:
        with st.expander("➕ Create New Task"):
            t_title = st.text_input("Title", key="task_title")
            t_desc = st.text_area("Description", key="task_desc")
            t_status = st.selectbox("Status", ["todo", "in_progress", "done"], key="task_status")
            t_priority = st.selectbox("Priority", ["low", "medium", "high"], key="task_priority")
            t_due = st.date_input("Due Date (optional)", value=None, key="task_due")
 
            if project_map:
                t_proj = st.selectbox("Project", list(project_map.keys()), key="task_proj")
            else:
                st.warning("No projects available. An admin must create a project first.")
                t_proj = None
 
            if not is_admin:
                st.caption("You can only create tasks in projects an admin has assigned you to.")
 
            if is_admin:
                t_assignee = st.selectbox(
                    "Assign to (optional)", [UNASSIGNED] + list(assignee_ids.keys()), key="task_assignee"
                )
                t_assigned_to = assignee_ids.get(t_assignee)
            else:
                t_assigned_id = st.number_input(
                    "Assign to user ID (optional, 0 = nobody)", min_value=0, step=1, value=0, key="task_assignee_id"
                )
                t_assigned_to = int(t_assigned_id) or None
 
            if st.button("Create Task"):
                if not t_title.strip():
                    st.warning("Title is required.")
                elif not t_proj:
                    st.warning("Select a project.")
                else:
                    payload = {
                        "title": t_title,
                        "description": t_desc,
                        "status": t_status,
                        "priority": t_priority,
                        "project_id": project_map[t_proj],
                    }
                    if t_due:
                        payload["due_date"] = t_due.isoformat() + "T00:00:00"
                    if t_assigned_to:
                        payload["assigned_to"] = t_assigned_to
                    result = api_post("/tasks/", payload)
                    if result:
                        st.success(f"Task '{result['title']}' created.")
                        st.rerun()
 
    tasks = api_get("/tasks/", params={"limit": 100})
    if tasks:
        df = pd.DataFrame(tasks)
 
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            status_filter = st.multiselect("Filter by Status", ["todo", "in_progress", "done"])
        with col_f2:
            priority_filter = st.multiselect("Filter by Priority", ["low", "medium", "high"])
        with col_f3:
            sort_col = st.selectbox("Sort by", ["created_at", "priority", "status", "title"])
 
        if status_filter:
            df = df[df["status"].isin(status_filter)]
        if priority_filter:
            df = df[df["priority"].isin(priority_filter)]
        df = df.sort_values(sort_col)
 
        display_cols = ["id", "title", "status", "priority", "due_date", "project_id", "assigned_to"]
        display_cols = [c for c in display_cols if c in df.columns]
        display = df[display_cols].copy()
 
        if is_admin and "assigned_to" in display.columns:
            display["assigned_to"] = display["assigned_to"].apply(
                lambda v: "—" if pd.isna(v) else email_by_id.get(int(v), f"user {int(v)}")
            )
        display.columns = [c.replace("_", " ").title() for c in display_cols]
 
        if "Due Date" in display.columns:
            display["Due Date"] = pd.to_datetime(display["Due Date"], errors="coerce").dt.strftime("%d %b %Y")
 
        st.dataframe(display, use_container_width=True, hide_index=True)
 
        if is_manager:
            st.markdown("---")
            st.markdown("**Update Task**")
 
            # Each task carries a `version` that the backend uses for
            # optimistic concurrency. `tasks` is re-fetched on every Streamlit
            # rerun, so this map always holds the latest version at click time.
            task_options = {f"#{t['id']} — {t['title']}": t["id"] for t in tasks}
            task_versions = {t["id"]: t["version"] for t in tasks}
 
            selected_task = st.selectbox("Select Task", list(task_options.keys()), key="upd_task")
            new_status = st.selectbox("New Status", ["todo", "in_progress", "done"], key="upd_status")
            new_priority = st.selectbox("New Priority", ["low", "medium", "high"], key="upd_priority")
            if is_admin:
                new_assignee = st.selectbox(
                    "Assign to", [KEEP_CURRENT, UNASSIGNED] + list(assignee_ids.keys()), key="upd_assignee"
                )
 
            if st.button("Update Task"):
                task_id = task_options[selected_task]
                update_payload = {
                    "status": new_status,
                    "priority": new_priority,
                    "version": task_versions[task_id],
                }
                if is_admin and new_assignee != KEEP_CURRENT:
                    update_payload["assigned_to"] = None if new_assignee == UNASSIGNED else assignee_ids[new_assignee]
                result = api_patch(f"/tasks/{task_id}", update_payload)
                if result:
                    st.success("Task updated.")
                    st.rerun()
    else:
        st.info("No tasks found." if is_manager else "No tasks assigned to you yet.")
 
 
# ── Users (admin only) ────────────────────────────────────────────────────────
 
elif menu == "Users":
    st.markdown("<div class='section-title'>👥 Users</div>", unsafe_allow_html=True)
 
    users = api_get("/users/", params={"limit": 100})
    if users:
        df = pd.DataFrame(users)[["id", "email", "role", "is_active"]]
        df.columns = ["ID", "Email", "Role", "Active"]
        st.dataframe(df, use_container_width=True, hide_index=True)
 
        st.markdown("---")
        st.markdown("**Change User Role**")
        user_options = {u["email"]: u["id"] for u in users if u["email"] != user.get("email")}
        if user_options:
            selected_user = st.selectbox("Select User", list(user_options.keys()), key="role_user")
            new_role = st.selectbox("Assign Role", ["user", "manager", "admin"], key="role_val")
            if st.button("Update Role"):
                r = requests.patch(
                    f"{API_URL}/users/{user_options[selected_user]}/role",
                    params={"role": new_role},
                    headers=auth_headers(),
                    timeout=15,
                )
                if r.status_code == 200:
                    st.success(f"Role updated to '{new_role}'.")
                    st.rerun()
                else:
                    st.error(extract_error_detail(r))
        else:
            st.info("No other users to manage.")
    else:
        st.info("No users found.")
