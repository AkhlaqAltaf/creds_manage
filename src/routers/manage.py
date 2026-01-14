"""
Clean and optimized manage.py with helper classes
"""
from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from config.settings import CREDS_DIR
from src.core.database import get_db
from src.core.models import Domain, Credential, User, UserRole, DomainAssignment, CredentialStatus
from src.core.schemas import (
    ExportCredentialsRequest, ExportFilters, StatusProcessRequest,
    BulkDeleteRequest, BulkCheckRequest, BulkExportRequest
)
from src.core.auth import get_current_user_from_session, require_admin_or_creator_from_session
from src.utils.credential_processor import (
    process_credentials_background, processing_status, processing_lock
)
from src.utils.export_helper import ExportHelper
from src.utils.filter_helper import FilterHelper
from src.utils.status_processor import StatusProcessor
from src.utils.bulk_operations import BulkOperations

router = APIRouter(prefix="/api", tags=["manage"])


@router.post("/process")
async def process_credentials(
    request: Request,
    background_tasks: BackgroundTasks, 
    current_user: User = Depends(require_admin_or_creator_from_session)
):
    """Process credential files in background"""
    with processing_lock:
        if processing_status["is_processing"]:
            return JSONResponse({
                "success": False,
                "message": "Processing already in progress"
            })
        
        processing_status["is_processing"] = True
        processing_status["progress"] = 0
        processing_status["total"] = len(list(CREDS_DIR.glob("*.txt")))
        processing_status["processed_count"] = 0
        processing_status["errors"] = []
        processing_status["start_time"] = datetime.now()
        processing_status["current_file"] = None
    
    background_tasks.add_task(process_credentials_background)
    
    return JSONResponse({
        "success": True,
        "message": "Processing started in background",
        "total_files": processing_status["total"]
    })


@router.get("/process-status")
async def get_process_status():
    """Get current processing status"""
    with processing_lock:
        status = {
            "is_processing": processing_status["is_processing"],
            "progress": processing_status["progress"],
            "total": processing_status["total"],
            "processed_count": processing_status["processed_count"],
            "errors": processing_status["errors"][-10:],  # Last 10 errors
            "current_file": processing_status["current_file"]
        }
        
        if processing_status["start_time"]:
            elapsed = (datetime.now() - processing_status["start_time"]).total_seconds()
            status["elapsed_seconds"] = int(elapsed)
            if status["progress"] > 0:
                remaining = (elapsed / status["progress"]) * (status["total"] - status["progress"])
                status["estimated_remaining_seconds"] = int(remaining)
    
    return JSONResponse(status)


@router.post("/update-working-status")
async def update_working_status(domain_statuses: dict, db: Session = Depends(get_db)):
    """Update is_working status for domains"""
    updated = 0
    for domain_id, is_working in domain_statuses.items():
        try:
            domain = db.query(Domain).filter(Domain.id == int(domain_id)).first()
            if domain:
                domain.is_working = bool(is_working)
                updated += 1
        except:
            continue
    
    db.commit()
    return JSONResponse({"success": True, "updated": updated})


@router.post("/credential/{credential_id}/toggle-accessed")
async def toggle_accessed(credential_id: int, db: Session = Depends(get_db)):
    """Toggle is_accessed status for a credential"""
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    credential.is_accessed = not credential.is_accessed
    db.commit()
    return JSONResponse({"success": True, "is_accessed": credential.is_accessed})


@router.post("/credential/{credential_id}/toggle-checked")
async def toggle_credential_checked(credential_id: int, db: Session = Depends(get_db)):
    """Toggle is_checked status for a credential"""
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    credential.is_checked = True
    db.commit()
    return JSONResponse({"success": True, "is_checked": credential.is_checked})


@router.post("/credential/{credential_id}/update-status")
async def update_credential_status(
    request: Request,
    credential_id: int,
    status_id: int = Query(...),
    current_user: User = Depends(require_admin_or_creator_from_session),
    db: Session = Depends(get_db)
):
    """Update status of a credential"""
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    status = db.query(CredentialStatus).filter(CredentialStatus.id == status_id).first()
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
    
    credential.status_id = status_id
    db.commit()
    return JSONResponse({"success": True, "status_id": credential.status_id, "status_name": status.name})


@router.post("/domain/{domain_id}/toggle-checked")
async def toggle_domain_checked(domain_id: int, db: Session = Depends(get_db)):
    """Toggle is_checked status for a domain"""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    domain.is_checked = not domain.is_checked
    db.commit()
    return JSONResponse({"success": True, "is_checked": domain.is_checked})


@router.post("/domain/{domain_id}/comment")
async def update_domain_comment(domain_id: int, request: Request, db: Session = Depends(get_db)):
    """Update comment for a domain"""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    data = await request.json()
    comment = data.get("comment", "")
    
    if comment and len(comment) > 50:
        comment = comment[:50]
    
    domain.comment = comment if comment else None
    db.commit()
    return JSONResponse({"success": True, "comment": domain.comment})


@router.post("/check-all")
async def check_all(db: Session = Depends(get_db)):
    """Check all domains and credentials (set is_checked to True)"""
    try:
        domains_updated = db.query(Domain).filter(Domain.is_checked == False).update({Domain.is_checked: True})
        credentials_updated = db.query(Credential).filter(Credential.is_checked == False).update({Credential.is_checked: True})
        
        db.commit()
        
        return JSONResponse({
            "success": True,
            "domains_updated": domains_updated,
            "credentials_updated": credentials_updated
        })
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error checking all: {str(e)}")


@router.get("/domain/{domain_id}/credentials")
async def get_domain_credentials(
    domain_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    accessed_only: bool = Query(False),
    checked_filter: str = Query("all", pattern="^(all|checked|not_checked|checked_and_working)$"),
    db: Session = Depends(get_db)
):
    """Get paginated credentials for a domain"""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    # Build query with filters
    query = db.query(Credential).filter(Credential.domain_id == domain_id)
    
    if accessed_only:
        query = query.filter(Credential.is_accessed == True)
    
    if checked_filter == "checked":
        query = query.filter(Credential.is_checked == True)
    elif checked_filter == "not_checked":
        query = query.filter(Credential.is_checked == False)
    elif checked_filter == "checked_and_working":
        query = query.filter(Credential.is_checked == True)
    
    total = query.count()
    credentials = query.offset(offset).limit(limit).all()
    
    return JSONResponse({
        "total": total,
        "offset": offset,
        "limit": limit,
        "credentials": [{
            "id": cred.id,
            "url": cred.url,
            "user": cred.user,
            "password": cred.password,
            "is_accessed": cred.is_accessed,
            "is_admin": cred.is_admin,
            "is_checked": cred.is_checked
        } for cred in credentials]
    })


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get database statistics"""
    total_domains = db.query(func.count(Domain.id)).scalar() or 0
    online_domains = db.query(func.count(Domain.id)).filter(Domain.is_working == True).scalar() or 0
    offline_domains = db.query(func.count(Domain.id)).filter(Domain.is_working == False).scalar() or 0
    total_credentials = db.query(func.count(Credential.id)).scalar() or 0
    accessed_credentials = db.query(func.count(Credential.id)).filter(Credential.is_accessed == True).scalar() or 0
    
    # Count unprocessed files
    unprocessed_files = 0
    if CREDS_DIR.exists():
        unprocessed_files = len(list(CREDS_DIR.glob("*.txt")))
    
    return JSONResponse({
        "total_domains": total_domains,
        "online_domains": online_domains,
        "offline_domains": offline_domains,
        "total_credentials": total_credentials,
        "accessed_credentials": accessed_credentials,
        "unprocessed_files": unprocessed_files
    })


@router.post("/export-credentials")
async def export_credentials(
    request: Request,
    export_data: ExportCredentialsRequest,
    db: Session = Depends(get_db)
):
    """Export credentials for selected domains to Excel"""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    domain_ids = export_data.domain_ids
    
    # Apply user access control
    if current_user.role != UserRole.ADMIN:
        assigned_domain_ids = db.query(DomainAssignment.domain_id).filter(
            DomainAssignment.user_id == current_user.id
        ).all()
        assigned_ids = [row[0] for row in assigned_domain_ids]
        domain_ids = [did for did in domain_ids if did in assigned_ids]
    
    if not domain_ids:
        raise HTTPException(status_code=400, detail="No valid domains selected or no access to selected domains")
    
    # Get domains and credentials
    domains = db.query(Domain).filter(Domain.id.in_(domain_ids)).all()
    all_credentials = []
    
    for domain in domains:
        credentials = db.query(Credential).filter(Credential.domain_id == domain.id).all()
        all_credentials.extend(credentials)
    
    # Prepare export data
    export_data = ExportHelper.prepare_export_data(all_credentials, domains)
    
    # Export based on requested format
    if export_data.format == "xlsx":
        return ExportHelper.export_to_excel(export_data, "credentials_export")
    elif export_data.format == "csv":
        return ExportHelper.export_to_csv(export_data, "credentials_export")
    elif export_data.format == "txt":
        return ExportHelper.export_to_txt(export_data, "credentials_export")
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")


@router.post("/bulk-delete")
async def bulk_delete(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_creator_from_session)
):
    """Bulk delete domains and credentials"""
    try:
        result = BulkOperations.delete_selected(
            db, current_user, request.credential_ids, request.domain_ids
        )
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during bulk delete: {str(e)}")


@router.post("/bulk-check")
async def bulk_check(
    request: BulkCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_creator_from_session)
):
    """Bulk mark domains and credentials as checked"""
    try:
        result = BulkOperations.mark_as_checked(
            db, current_user, request.credential_ids, request.domain_ids
        )
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during bulk check: {str(e)}")


@router.post("/bulk-export")
async def bulk_export(
    request: BulkExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_creator_from_session)
):
    """Bulk export selected items in various formats"""
    # Get all credential IDs to export
    credential_ids_to_export = set(request.credential_ids)
    
    # Add all credentials from selected domains
    if request.domain_ids:
        # Verify access to domains
        if current_user.role != UserRole.ADMIN:
            accessible_domains = db.query(Domain).join(DomainAssignment).filter(
                Domain.id.in_(request.domain_ids),
                DomainAssignment.user_id == current_user.id
            ).all()
            domain_ids = [d.id for d in accessible_domains]
        else:
            domain_ids = request.domain_ids
        
        if domain_ids:
            domain_creds = db.query(Credential.id).filter(
                Credential.domain_id.in_(domain_ids)
            ).all()
            for cred in domain_creds:
                credential_ids_to_export.add(cred[0])
    
    # Verify access to individual credentials
    if current_user.role != UserRole.ADMIN:
        accessible_creds = db.query(Credential.id).join(Domain).join(DomainAssignment).filter(
            Credential.id.in_(list(credential_ids_to_export)),
            DomainAssignment.user_id == current_user.id
        ).all()
        accessible_ids = [c[0] for c in accessible_creds]
        credential_ids_to_export = set(accessible_ids)
    
    if not credential_ids_to_export:
        raise HTTPException(status_code=400, detail="No accessible items to export")
    
    # Get credentials with domain info
    credentials = db.query(Credential, Domain).join(Domain).filter(
        Credential.id.in_(list(credential_ids_to_export))
    ).all()
    
    # Prepare data
    data = []
    for cred, domain in credentials:
        data.append({
            "domain": domain.domain,
            "url": cred.url,
            "user": cred.user,
            "password": cred.password,
            "is_admin": "Yes" if cred.is_admin else "No",
            "is_accessed": "Yes" if cred.is_accessed else "No",
            "is_checked": "Yes" if cred.is_checked else "No",
            "status": cred.status.name if cred.status else "N/A"
        })
    
    # Export based on format
    if request.format == "xlsx":
        return ExportHelper.export_to_excel(data, "credentials_bulk_export")
    elif request.format == "csv":
        return ExportHelper.export_to_csv(data, "credentials_bulk_export")
    elif request.format == "txt":
        return ExportHelper.export_to_txt(data, "credentials_bulk_export")
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")


@router.post("/export-credentials-filtered")
async def export_credentials_filtered(
    request: ExportFilters,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_creator_from_session)
):
    """Export credentials with filters"""
    # Build query with filters
    query = db.query(Credential).join(Domain)
    
    # Apply user access control
    query = FilterHelper.apply_user_access_control(query, current_user, Credential)
    
    # Apply filters
    if request.checked_filter == "checked":
        query = query.filter(Credential.is_checked == True)
    elif request.checked_filter == "not_checked":
        query = query.filter(Credential.is_checked == False)
    
    if request.accessed_filter == "accessed":
        query = query.filter(Credential.is_accessed == True)
    elif request.accessed_filter == "not_accessed":
        query = query.filter(Credential.is_accessed == False)
    
    if request.working_filter == "working":
        query = query.filter(Domain.is_working == True)
    elif request.working_filter == "not_working":
        query = query.filter(Domain.is_working == False)
    elif request.working_filter == "unknown":
        query = query.filter(Domain.is_working == None)
    
    if request.admin_filter == "admin":
        query = query.filter(Credential.is_admin == True)
    elif request.admin_filter == "not_admin":
        query = query.filter(Credential.is_admin == False)
    
    # Domain extensions filter
    if request.domain_extensions:
        from sqlalchemy import or_
        extension_conditions = []
        for ext in request.domain_extensions:
            extension_conditions.append(Domain.domain.like(f"%{ext}"))
        if extension_conditions:
            query = query.filter(or_(*extension_conditions))
    
    # Domain contains filter
    if request.domain_contains:
        query = query.filter(Domain.domain.ilike(f"%{request.domain_contains}%"))
    
    # Get all matching credentials
    credentials = query.all()
    
    if not credentials:
        raise HTTPException(status_code=404, detail="No credentials found matching the filters")
    
    # Get unique domains for the credentials
    domain_ids = {cred.domain_id for cred in credentials}
    domains = db.query(Domain).filter(Domain.id.in_(domain_ids)).all()
    
    # Prepare data for export
    export_data = ExportHelper.prepare_export_data(credentials, domains)
    
    # Export based on format
    if request.format == "excel":
        return ExportHelper.export_to_excel(export_data, "credentials_filtered")
    elif request.format == "csv":
        return ExportHelper.export_to_csv(export_data, "credentials_filtered")
    elif request.format == "txt":
        return ExportHelper.export_to_txt(export_data, "credentials_filtered")
    elif request.format == "json":
        return ExportHelper.export_to_json(export_data, "credentials_filtered")
    else:
        raise HTTPException(status_code=400, detail="Unsupported export format")


@router.post("/process-working-status")
async def start_process_working_status(
    request: StatusProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_creator_from_session)
):
    """Start processing working status with filters"""
    # Generate a unique task ID
    task_id = str(datetime.now().timestamp()).replace('.', '')
    
    # Initialize task status
    StatusProcessor.create_task(task_id)
    
    # Build query for domains with filters
    query = db.query(Domain)
    query = FilterHelper.build_domain_query(
        query,
        checked_filter=request.checked_filter,
        working_filter=request.working_filter,
        domain_extensions=request.domain_extensions,
        domain_contains=request.domain_contains
    )
    
    # Apply user access control
    query = FilterHelper.apply_user_access_control(query, current_user, Domain)
    
    # Get domains to process
    domains = query.all()
    
    # Start background task
    background_tasks.add_task(
        StatusProcessor.process_domains_background,
        task_id,
        domains,
        db,
        request.batch_size
    )
    
    return JSONResponse({
        "success": True,
        "task_id": task_id,
        "message": "Working status processing started",
        "total_domains": len(domains)
    })


@router.get("/process-working-status/{task_id}")
async def get_working_status(task_id: str):
    """Get status of working status processing task"""
    task_status = StatusProcessor.get_task(task_id)
    
    if not task_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return JSONResponse(task_status)


@router.post("/process-working-status/stop")
async def stop_working_status_processing():
    """Stop all working status processing tasks"""
    StatusProcessor.stop_all_tasks()
    return JSONResponse({"success": True, "message": "All processing tasks stopped"})