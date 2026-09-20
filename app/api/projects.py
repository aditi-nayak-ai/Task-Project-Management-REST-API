from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.project import Project
from app.models.project_manager import ProjectManager
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.schemas.project_manager import ProjectManagerResponse
from app.utils.dependencies import require_role, get_current_user
from app.utils.pagination import get_pagination
from app.core.audit import record_audit
 
router = APIRouter()
 
 
@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    new_project = Project(name=project.name, description=project.description, owner_id=current_user.id)
    db.add(new_project)
    db.flush()  # assigns new_project.id without ending the transaction, so the audit row below can reference it
    record_audit(db, current_user, "project.create", "project", new_project.id, detail={"name": project.name})
    db.commit()
    db.refresh(new_project)
    return new_project
 
 
@router.get("/", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    pagination: tuple = Depends(get_pagination),
):
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
    current_user: User = Depends(require_role("admin")),
):
    # FOR UPDATE row lock: see update_task -- serializes concurrent edits so the
    # version check below can't be raced.
    project = db.query(Project).filter(Project.id == project_id).with_for_update().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
 
    if payload.version != project.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Version conflict: you sent version {payload.version}, current version is {project.version}. Re-fetch and retry.",
        )
 
    changes = payload.model_dump(exclude_unset=True, exclude={"version"})
    for field, value in changes.items():
        setattr(project, field, value)
    project.version += 1
 
    record_audit(db, current_user, "project.update", "project", project.id, detail=changes)
    db.commit()
    db.refresh(project)
    return project
 
 
@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin"))):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    record_audit(db, current_user, "project.delete", "project", project.id, detail={"name": project.name})
    db.delete(project)
    db.commit()
 
 
# ── Manager scoping ──────────────────────────────────────────────────────
# A `manager` role by itself doesn't say *which* projects they can act on
# (see ProjectManager model). These endpoints are how an admin grants or
# revokes that scope. Deliberately admin-only: a manager cannot add
# themselves, or another manager, to a project.
 
@router.get("/{project_id}/managers", response_model=list[ProjectManagerResponse])
def list_project_managers(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(ProjectManager).filter(ProjectManager.project_id == project_id).all()
 
 
@router.post("/{project_id}/managers/{user_id}", response_model=ProjectManagerResponse, status_code=status.HTTP_201_CREATED)
def add_project_manager(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
 
    existing = db.query(ProjectManager).filter(
        ProjectManager.project_id == project_id, ProjectManager.user_id == user_id
    ).first()
    if existing:
        return existing
 
    link = ProjectManager(project_id=project_id, user_id=user_id)
    db.add(link)
    db.flush()
    record_audit(db, current_user, "project.manager.add", "project", project_id, detail={"user_id": user_id})
    db.commit()
    db.refresh(link)
    return link
 
 
@router.delete("/{project_id}/managers/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_manager(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    link = db.query(ProjectManager).filter(
        ProjectManager.project_id == project_id, ProjectManager.user_id == user_id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="This user is not a manager of this project")
    record_audit(db, current_user, "project.manager.remove", "project", project_id, detail={"user_id": user_id})
    db.delete(link)
    db.commit()
