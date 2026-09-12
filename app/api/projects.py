from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.utils.dependencies import require_role, get_current_user
from app.utils.pagination import get_pagination

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    # A duplicate `name` used to hit the unique constraint and bubble up
    # as an unhandled IntegrityError -> bare 500. app.core.errors now
    # catches IntegrityError globally and returns 409, so no try/except
    # is needed here -- that's the point of a global handler over
    # per-route boilerplate.
    new_project = Project(name=project.name, description=project.description, owner_id=current_user.id)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


@router.get("/", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    pagination: tuple = Depends(get_pagination),
):
    # Previously unbounded: db.query(Project).all() with no limit. Fine
    # at demo scale, a real liability once there are thousands of rows --
    # every call fetches the entire table into memory and serializes all
    # of it. tasks.py already paginated; this brings projects/users in
    # line with that pattern instead of leaving one inconsistent endpoint.
    offset, limit = pagination
    return db.query(Project).order_by(Project.id).offset(offset).limit(limit).all()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
