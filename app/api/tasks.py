from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.task import Task
from app.models.project import Project
from app.models.project_manager import ProjectManager
from app.models.user import User, UserRole
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.utils.dependencies import get_current_user, require_role
from app.utils.pagination import get_pagination
from app.core.audit import record_audit

router = APIRouter()


def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_assignee_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _ensure_can_act_on_project(db: Session, current_user: User, project_id: int) -> None:
    """
    Resource-level RBAC check. `require_role("admin", "manager")` on the
    route only confirms the caller holds one of those roles -- it says
    nothing about *which* project they may act on. Admins bypass this
    check entirely; managers must have an explicit ProjectManager row
    for this specific project, otherwise this is a 403, not a silent
    pass-through.
    """
    if current_user.role == UserRole.admin:
        return
    is_scoped = db.query(ProjectManager).filter(
        ProjectManager.project_id == project_id,
        ProjectManager.user_id == current_user.id,
    ).first()
    if not is_scoped:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a manager of this project",
        )


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "manager"))):
    # Existence checks first (404s), then scope check (403) -- a manager
    # probing for project IDs shouldn't be able to distinguish "doesn't
    # exist" from "exists but isn't yours" via the create endpoint, but
    # can via 403 on an update/delete they can at least see the ID of.
    # Ordering here keeps 404 authoritative over 403 for unknown IDs.
    _get_project_or_404(db, task.project_id)
    if task.assigned_to is not None:
        _get_assignee_or_404(db, task.assigned_to)
    _ensure_can_act_on_project(db, current_user, task.project_id)

    new_task = Task(
        title=task.title, description=task.description, status=task.status, priority=task.priority,
        due_date=task.due_date, project_id=task.project_id, assigned_to=task.assigned_to,
    )
    db.add(new_task)
    db.flush()
    record_audit(db, current_user, "task.create", "task", new_task.id, detail={"project_id": task.project_id, "title": task.title})
    db.commit()
    db.refresh(new_task)
    return new_task


@router.get("/", response_model=list[TaskResponse])
def list_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), pagination: tuple = Depends(get_pagination)):
    offset, limit = pagination
    query = db.query(Task)
    if current_user.role == UserRole.user:
        query = query.filter(Task.assigned_to == current_user.id)
    # Deliberately NOT scoping manager reads to their own projects here:
    # write actions are the resource-level RBAC boundary (see
    # _ensure_can_act_on_project); read visibility for admin/manager
    # stays broad so a manager can still see cross-project context
    # (e.g. checking assignee workload) even on projects they can't edit.
    return query.offset(offset).limit(limit).all()


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current_user.role == UserRole.user and task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "manager"))):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    _ensure_can_act_on_project(db, current_user, task.project_id)

    if payload.version != task.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Version conflict: you sent version {payload.version}, current version is {task.version}. Re-fetch and retry.",
        )

    changes = payload.model_dump(exclude_unset=True, exclude={"version"})
    if "assigned_to" in changes and changes["assigned_to"] is not None:
        _get_assignee_or_404(db, changes["assigned_to"])

    for field, value in changes.items():
        setattr(task, field, value)
    task.version += 1

    record_audit(db, current_user, "task.update", "task", task.id, detail=changes)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "manager"))):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    _ensure_can_act_on_project(db, current_user, task.project_id)

    record_audit(db, current_user, "task.delete", "task", task.id, detail={"project_id": task.project_id, "title": task.title})
    db.delete(task)
    db.commit()
