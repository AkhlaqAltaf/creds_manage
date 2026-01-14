"""
Admin routes for user management, domain assignment, and status management
"""
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List

from src.core.database import get_db
from src.core.models import User, Domain, DomainAssignment, CredentialStatus
from src.core.schemas import (
    UserCreate, UserUpdate, UserResponse, DomainAssignmentCreate,
    CredentialStatusCreate, CredentialStatusResponse
)
from src.core.auth import require_admin_from_session, get_password_hash
from config.settings import CREDS_DIR

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ==================== USER MANAGEMENT ====================

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    request: Request,
    current_user: User = Depends(require_admin_from_session),
    db: Session = Depends(get_db)
):
    """Create a new user (Admin only)"""
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at.isoformat()
    )


@router.get("/users")
async def get_users(
    request: Request,
    current_user: User = Depends(require_admin_from_session),
    db: Session = Depends(get_db)
):
    """Get all users (Admin only)"""
    users = db.query(User).all()
    return JSONResponse([{
        "id": u.id,
        "username": u.username,
        "role": u.role.value,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None
    } for u in users])


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    request: Request,
    current_user: User = Depends(require_admin_from_session),
    db: Session = Depends(get_db)
):
    """Update a user (Admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if username already exists (excluding current user)
    if user_data.username != user.username:
        existing = db.query(User).filter(User.username == user_data.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
    
    user.username = user_data.username
    # Only update password if a new one is provided
    if user_data.password and user_data.password.strip():
        user.password_hash = get_password_hash(user_data.password)
    user.role = user_data.role
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat()
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_admin_from_session),
    db: Session = Depends(get_db)
):
    """Delete a user (Admin only)"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    return JSONResponse({"success": True, "message": "User deleted successfully"})


# ==================== DOMAIN ASSIGNMENT ====================

@router.post("/assign-domain")
async def assign_domain(
    assignment: DomainAssignmentCreate,
    request: Request,
    current_user: User = Depends(require_admin_from_session),
    db: Session = Depends(get_db)
):
    """Assign a domain to a user (Admin only)"""
    existing = db.query(DomainAssignment).filter(
        DomainAssignment.user_id == assignment.user_id,
        DomainAssignment.domain_id == assignment.domain_id
    ).first()
    
    if existing:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Domain already assigned to this user"}
        )
    
    user = db.query(User).filter(User.id == assignment.user_id).first()
    domain = db.query(Domain).filter(Domain.id == assignment.domain_id).first()
    
    if not user or not domain:
        raise HTTPException(status_code=404, detail="User or domain not found")
    
    new_assignment = DomainAssignment(
        user_id=assignment.user_id,
        domain_id=assignment.domain_id,
        assigned_by=current_user.id
    )
    db.add(new_assignment)
    db.commit()
    
    return JSONResponse({
        "success": True,
        "message": f"Domain '{domain.domain}' assigned to user '{user.username}'"
    })


@router.get("/assignments")
async def get_assignments(
    request: Request,
    current_user: User = Depends(require_admin_from_session),
    db: Session = Depends(get_db)
):
    """Get all domain assignments (Admin only)"""
    assignments = db.query(DomainAssignment).join(
        User, DomainAssignment.user_id == User.id
    ).join(Domain).all()
    
    return JSONResponse([{
        "id": a.id,
        "user_id": a.user_id,
        "username": a.user.username,
        "domain_id": a.domain_id,
        "domain_name": a.domain.domain,
        "assigned_at": a.assigned_at.isoformat(),
        "assigned_by": a.assigned_by
    } for a in assignments])


@router.delete("/assignments/{assignment_id}")
async def remove_assignment(
    assignment_id: int,
    request: Request,
    current_user: User = Depends(require_admin_from_session),
    db: Session = Depends(get_db)
):
    """Remove a domain assignment (Admin only)"""
    assignment = db.query(DomainAssignment).filter(
        DomainAssignment.id == assignment_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    db.delete(assignment)
    db.commit()
    
    return JSONResponse({"success": True, "message": "Assignment removed"})


# ==================== CREDENTIAL STATUS MANAGEMENT ====================

@router.post("/statuses", response_model=CredentialStatusResponse)
async def create_status(
    status_data: CredentialStatusCreate,
    request: Request,
    current_user: User = Depends(require_admin_from_session),
    db: Session = Depends(get_db)
):
    """Create a new credential status (Admin only)"""
    existing = db.query(CredentialStatus).filter(
        CredentialStatus.name == status_data.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Status name already exists")
    
    new_status = CredentialStatus(
        name=status_data.name,
        description=status_data.description,
        color=status_data.color,
        is_active=True
    )
    db.add(new_status)
    db.commit()
    db.refresh(new_status)
    
    return CredentialStatusResponse(
        id=new_status.id,
        name=new_status.name,
        description=new_status.description,
        color=new_status.color,
        is_active=new_status.is_active
    )


@router.get("/statuses")
async def get_statuses(
    request: Request,
    current_user: User = Depends(require_admin_from_session),
    db: Session = Depends(get_db)
):
    """Get all credential statuses"""
    statuses = db.query(CredentialStatus).filter(
        CredentialStatus.is_active == True
    ).all()
    return JSONResponse([{
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "color": s.color,
        "is_active": s.is_active
    } for s in statuses])


@router.put("/statuses/{status_id}", response_model=CredentialStatusResponse)
async def update_status(
    status_id: int,
    status_data: CredentialStatusCreate,
    request: Request,
    current_user: User = Depends(require_admin_from_session),
    db: Session = Depends(get_db)
):
    """Update a credential status (Admin only)"""
    status = db.query(CredentialStatus).filter(
        CredentialStatus.id == status_id
    ).first()
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
    
    if status_data.name != status.name:
        existing = db.query(CredentialStatus).filter(
            CredentialStatus.name == status_data.name
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Status name already exists")
    
    status.name = status_data.name
    status.description = status_data.description
    status.color = status_data.color
    db.commit()
    db.refresh(status)
    
    return CredentialStatusResponse(
        id=status.id,
        name=status.name,
        description=status.description,
        color=status.color,
        is_active=status.is_active
    )


@router.delete("/statuses/{status_id}")
async def delete_status(
    status_id: int,
    request: Request,
    current_user: User = Depends(require_admin_from_session),
    db: Session = Depends(get_db)
):
    """Delete a credential status (Admin only) - soft delete"""
    status = db.query(CredentialStatus).filter(
        CredentialStatus.id == status_id
    ).first()
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
    status.is_active = False
    db.commit()
    
    return JSONResponse({"success": True, "message": "Status deactivated successfully"})


# ==================== FILE UPLOAD ====================

@router.post("/upload-files")
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(require_admin_from_session),
    db: Session = Depends(get_db)
):
    """Upload credential files (Admin only)"""
    uploaded_files = []
    errors = []
    
    for file in files:
        if not file.filename.endswith(('.txt', '.zip')):
            errors.append(
                f"{file.filename}: Invalid file type. Only .txt and .zip files are allowed."
            )
            continue
        
        try:
            file_path = CREDS_DIR / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            uploaded_files.append(file.filename)
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
    
    return JSONResponse({
        "success": True,
        "uploaded": uploaded_files,
        "errors": errors,
        "message": f"Uploaded {len(uploaded_files)} file(s)"
    })

