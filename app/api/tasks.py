from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.task import Task
from app.models.project import Project
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.utils.dependencies import get_current_user, require_role
from app.utils.pagination import get_pagination
 
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
 
 
@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "manager"))):
    # Previously this went straight to the DB and relied on the FK
    # constraint to reject a bad project_id/assigned_to -- which either
    # surfaced as a raw 500 (Postgres) or, worse, silently succeeded
    # (SQLite in this test setup, where FK enforcement isn't wired to
    # every engine instance). Look both up explicitly so a bad
    # reference is always a clean 404, never an orphaned row.
    _get_project_or_404(db, task.project_id)
    if task.assigned_to is not None:
        _get_assignee_or_404(db, task.assigned_to)
 
    new_task = Task(title=task.title, description=task.description, status=task.status, priority=task.priority, due_date=task.due_date, project_id=task.project_id, assigned_to=task.assigned_to)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task
 
@router.get("/", response_model=list[TaskResponse])
def list_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), pagination: tuple = Depends(get_pagination)):
    offset, limit = pagination
    query = db.query(Task)
    if current_user.role == "user":
        query = query.filter(Task.assigned_to == current_user.id)
    return query.offset(offset).limit(limit).all()
 
@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current_user.role == "user" and task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return task
 
@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db), _: User = Depends(require_role("admin", "manager"))):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
 
    payload_data = payload.model_dump(exclude_unset=True)
    if "assigned_to" in payload_data and payload_data["assigned_to"] is not None:
        _get_assignee_or_404(db, payload_data["assigned_to"])
 
    for field, value in payload_data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task
 
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db), _: User = Depends(require_role("admin", "manager"))):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
