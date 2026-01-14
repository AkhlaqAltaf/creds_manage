from fastapi.responses import RedirectResponse
from h11 import Request
from sqlalchemy import desc
from src.core.auth import get_current_user_from_session
from src.core.models import Credential, Domain, DomainAssignment, UserRole
from src.core.schemas import CredentialResponse, DomainResponse

from sqlalchemy.orm import Session

async def index_view(request: Request, page: int, per_page: int, status_filter: str, checked_filter: str, accessed_only: bool, domain_filter: str, search: str, db: Session, templates):
    
     
    """Main page showing credentials grouped by domain"""    
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    query = db.query(Domain).outerjoin(Credential)
    
    if current_user.role != UserRole.ADMIN:
        assigned_domain_ids = db.query(DomainAssignment.domain_id).filter(
            DomainAssignment.user_id == current_user.id
        ).all()
        assigned_ids = [row[0] for row in assigned_domain_ids]
        if assigned_ids:
            query = query.filter(Domain.id.in_(assigned_ids))
        else:
            query = query.filter(Domain.id == -1)  
    
    # Note: For "online" filter, we'll do real-time checking on frontend
    if status_filter == "offline":
        query = query.filter(Domain.is_working == False)
    
    # Filter by checked status
    if checked_filter == "checked":
        query = query.filter(Domain.is_checked == True)
    elif checked_filter == "not_checked":
        query = query.filter(Domain.is_checked == False)
    elif checked_filter == "checked_and_working":
        query = query.filter(Domain.is_checked == True, Domain.is_working == True)
    
    if accessed_only:
        query = query.filter(Credential.is_accessed == True)
    
    # Filter by domain TLD
    if domain_filter != "all":
        if domain_filter == ".gov.in":
            # Match .gov.in specifically
            query = query.filter(Domain.domain.like("%.gov.in"))
        elif domain_filter == ".gov":
            # Match .gov but not .gov.in (to avoid duplicates)
            query = query.filter(Domain.domain.like("%.gov")).filter(not_(Domain.domain.like("%.gov.%")))
        elif domain_filter == ".in":
            # Match .in but not .gov.in (to avoid duplicates)
            query = query.filter(Domain.domain.like("%.in")).filter(not_(Domain.domain.like("%.gov.in")))
    
    # Filter by search term (domain contains search)
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        query = query.filter(Domain.domain.ilike(search_term))
    
    # Get total count
    total = query.distinct().count()
    
    # Paginate
    offset = (page - 1) * per_page
    domains = query.distinct().order_by(desc(Domain.is_working), Domain.domain).offset(offset).limit(per_page).all()
    
    # Load credentials for each domain (limit to first 50 for initial load)
    INITIAL_CREDS_LIMIT = 50
    domain_responses = []
    for domain in domains:
        creds_query = db.query(Credential).filter(Credential.domain_id == domain.id)
        if accessed_only:
            creds_query = creds_query.filter(Credential.is_accessed == True)
        
        # Filter credentials by checked filter if needed (at query level for efficiency)
        if checked_filter == "checked":
            creds_query = creds_query.filter(Credential.is_checked == True)
        elif checked_filter == "not_checked":
            creds_query = creds_query.filter(Credential.is_checked == False)
        elif checked_filter == "checked_and_working":
            # For checked_and_working, domain filter already handles it, but we can still filter credentials
            creds_query = creds_query.filter(Credential.is_checked == True)
        
        # Get total count for pagination info
        total_creds = creds_query.count()
        
        # Load only first batch
        credentials = creds_query.limit(INITIAL_CREDS_LIMIT).all()
        
        # Get credential URLs for domain checking (use accessed ones first if available)
        check_urls = [cred.url for cred in credentials if cred.is_accessed]
        if not check_urls:
            check_urls = [cred.url for cred in credentials[:3]]  # Try first 3 URLs
        check_urls = check_urls[:3]  # Limit to 3 URLs
        
        domain_responses.append(DomainResponse(
            id=domain.id,
            domain=domain.domain,
            is_working=domain.is_working,
            is_important=domain.is_important,
            is_checked=domain.is_checked,
            comment=domain.comment,
            credentials=[CredentialResponse(
                id=cred.id,
                url=cred.url,
                user=cred.user,
                password=cred.password,
                is_accessed=cred.is_accessed,
                is_admin=cred.is_admin,
                is_checked=cred.is_checked,
                status_id=cred.status_id,
                status_name=cred.status.name if cred.status else None
            ) for cred in credentials],
            check_urls=check_urls,
            total_credentials=total_creds  # Add total count
        ))
    
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "domains": domain_responses,
        "current_page": page,
        "total_pages": total_pages,
        "per_page": per_page,
        "total": total,
        "status_filter": status_filter,
        "checked_filter": checked_filter,
        "accessed_only": accessed_only,
        "domain_filter": domain_filter,
        "search": search,
        "current_user": current_user
    })