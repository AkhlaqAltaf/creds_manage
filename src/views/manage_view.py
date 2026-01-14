
from config.settings import CREDS_DIR
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.core.models import Domain, Credential, UserRole
from src.core.schemas import StatsResponse
from src.core.auth import get_current_user_from_session



async def manage_view(request: Request, db: Session, templates):
    """Management page with statistics and process button"""

    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.CREATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    total_domains = db.query(func.count(Domain.id)).scalar() or 0
    online_domains = db.query(func.count(Domain.id)).filter(Domain.is_working == True).scalar() or 0
    offline_domains = db.query(func.count(Domain.id)).filter(Domain.is_working == False).scalar() or 0
    total_credentials = db.query(func.count(Credential.id)).scalar() or 0
    accessed_credentials = db.query(func.count(Credential.id)).filter(Credential.is_accessed == True).scalar() or 0
    unprocessed_files = len([f for f in CREDS_DIR.iterdir() if f.is_file() and f.suffix == ".txt"])
    
    stats = StatsResponse(
        total_domains=total_domains,
        online_domains=online_domains,
        offline_domains=offline_domains,
        total_credentials=total_credentials,
        accessed_credentials=accessed_credentials,
        unprocessed_files=unprocessed_files
    )
    
    return templates.TemplateResponse("manage.html", {
        "request": request,
        "stats": stats,
        "current_user": current_user
    })