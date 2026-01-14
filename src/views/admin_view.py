from fastapi.responses import RedirectResponse
from src.core.auth import get_current_user_from_session
from src.core.models import CredentialStatus, Domain, DomainAssignment, User, UserRole
from sqlalchemy.orm import Session


async def admin_access_view(request, db: Session,templates):
    current_user = await get_current_user_from_session(request, db)
    if not current_user or current_user.role != UserRole.ADMIN:
        return RedirectResponse(url="/login", status_code=303)    
    users = db.query(User).all()
    domains = db.query(Domain).order_by(Domain.domain).all()
    assignments = db.query(DomainAssignment).join(
        User, DomainAssignment.user_id == User.id
    ).join(Domain).order_by(DomainAssignment.assigned_at.desc()).all()
    statuses = db.query(CredentialStatus).filter(CredentialStatus.is_active == True).all()
    
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "current_user": current_user,
        "users": users,
        "domains": domains,
        "assignments": assignments,
        "statuses": statuses
    })
