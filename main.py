from fastapi import FastAPI, Request, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, not_
import os
from pathlib import Path
from typing import Optional, List, Dict
import shutil
from urllib.parse import urlparse
from collections import defaultdict
import threading
from datetime import datetime

from database import get_db, init_db, SessionLocal
from models import Domain, Credential
from schemas import CredentialResponse, DomainResponse, StatsResponse

app = FastAPI(title="Credential Manager")

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add JSON filter for templates
import json
def tojson_filter(obj):
    return json.dumps(obj)

templates.env.filters["tojson"] = tojson_filter

# Ensure directories exist
Path("creds").mkdir(exist_ok=True)
Path("processed_creds").mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)
Path("templates").mkdir(exist_ok=True)
Path("not_useful").mkdir(exist_ok=True)

# Processing status tracking
processing_status = {
    "is_processing": False,
    "progress": 0,
    "total": 0,
    "processed_count": 0,
    "errors": [],
    "start_time": None,
    "current_file": None
}
processing_lock = threading.Lock()

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, 
                page: int = Query(1, ge=1),
                per_page: int = Query(20, ge=1, le=100),
                status_filter: str = Query("online", regex="^(all|online|offline)$"),
                checked_filter: str = Query("not_checked", regex="^(all|checked|not_checked|checked_and_working)$"),
                accessed_only: bool = Query(False),
                domain_filter: str = Query("all", regex="^(all|\\.in|\\.gov|\\.gov\\.in)$"),
                search: str = Query("", max_length=100),
                db: Session = Depends(get_db)):
    """Main page showing credentials grouped by domain"""
    
    # Build query
    query = db.query(Domain).outerjoin(Credential)
    
    if status_filter == "online":
        query = query.filter(Domain.is_working == True)
    elif status_filter == "offline":
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
            credentials=[CredentialResponse(
                id=cred.id,
                url=cred.url,
                user=cred.user,
                password=cred.password,
                is_accessed=cred.is_accessed,
                is_admin=cred.is_admin,
                is_checked=cred.is_checked
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
        "search": search
    })

@app.get("/manage", response_class=HTMLResponse)
async def manage(request: Request, db: Session = Depends(get_db)):
    """Management page with statistics and process button"""
    
    # Get statistics
    total_domains = db.query(func.count(Domain.id)).scalar() or 0
    online_domains = db.query(func.count(Domain.id)).filter(Domain.is_working == True).scalar() or 0
    offline_domains = db.query(func.count(Domain.id)).filter(Domain.is_working == False).scalar() or 0
    total_credentials = db.query(func.count(Credential.id)).scalar() or 0
    accessed_credentials = db.query(func.count(Credential.id)).filter(Credential.is_accessed == True).scalar() or 0
    unprocessed_files = len([f for f in Path("creds").iterdir() if f.is_file() and f.suffix == ".txt"])
    
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
        "stats": stats
    })

def parse_credential_line(line: str) -> Optional[tuple]:
    """Parse a credential line, return (url, user, password) or None"""
    line = line.strip()
    if not line:
        return None
    
    # Split from right to left: url:user:password
    parts = line.rsplit(':', 2)
    if len(parts) != 3:
        return None
    
    url, user, password = parts
    url = url.strip()
    user = user.strip()
    password = password.strip()
    
    if not url or not user or not password:
        return None
    
    return (url, user, password)

def extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL"""
    try:
        if not url or not isinstance(url, str):
            return None
        
        url = url.strip()
        if not url:
            return None
        
        # Skip if it's just a protocol
        if url.lower() in ('http://', 'https://', 'http:', 'https:'):
            return None
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        
        parsed = urlparse(url)
        domain_str = parsed.netloc or parsed.path.split('/')[0]
        
        if domain_str:
            domain_str = domain_str.lower().strip()
            
            # Filter out invalid domains
            # Skip if it's just a protocol or empty
            if not domain_str or domain_str in ('http:', 'https:', 'http://', 'https://'):
                return None
            
            # Skip if it doesn't look like a valid domain (no dots or just numbers/special chars)
            if '.' not in domain_str or len(domain_str) < 3:
                return None
            
            # Remove port if present
            if ':' in domain_str:
                domain_str = domain_str.split(':')[0]
            
            # Basic validation - should have at least one dot and be alphanumeric with dots and hyphens
            if not all(c.isalnum() or c in '.-' for c in domain_str):
                return None
            
            return domain_str
    except Exception:
        pass
    return None

def process_credentials_background():
    """Background task to process credential files efficiently"""
    creds_dir = Path("creds")
    processed_dir = Path("processed_creds")
    not_useful_dir = Path("not_useful")
    
    # Get all files to process
    files = list(creds_dir.glob("*.txt"))
    
    with processing_lock:
        processing_status["is_processing"] = True
        processing_status["progress"] = 0
        processing_status["total"] = len(files)
        processing_status["processed_count"] = 0
        processing_status["errors"] = []
        processing_status["start_time"] = datetime.now()
        processing_status["current_file"] = None
    
    # Create database session for this thread
    db = SessionLocal()
    
    try:
        # Process files
        for file_idx, file_path in enumerate(files):
            with processing_lock:
                processing_status["current_file"] = file_path.name
                processing_status["progress"] = file_idx + 1
            
            try:
                # Read all lines at once
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                # Batch collect all credentials
                credentials_batch = []
                domains_map = {}  # domain_str -> domain_id
                domains_to_create = set()
                invalid_line_info = None
                
                # Parse all lines first
                for line_num, line in enumerate(lines, 1):
                    try:
                        parsed = parse_credential_line(line)
                        if not parsed:
                            if line.strip():
                                invalid_line_info = line_num
                                break
                            else:
                                invalid_line_info = line_num
                                break
                        
                        url, user, password = parsed
                        domain_str = extract_domain(url)
                        
                        if not domain_str:
                            invalid_line_info = line_num
                            break
                        
                        # Validate domain string
                        if len(domain_str) < 3 or '.' not in domain_str:
                            invalid_line_info = line_num
                            break
                        
                        # Collect domain
                        if domain_str not in domains_map and domain_str not in domains_to_create:
                            domains_to_create.add(domain_str)
                        
                        # Determine if admin
                        is_admin = 'admin' in url.lower() or 'admin' in user.lower() or 'administrator' in url.lower()
                        
                        credentials_batch.append({
                            'domain': domain_str,
                            'url': url,
                            'user': user,
                            'password': password,
                            'is_admin': is_admin
                        })
                    except Exception as e:
                        invalid_line_info = line_num
                        with processing_lock:
                            processing_status["errors"].append(f"{file_path.name}:{line_num} - {str(e)}")
                        break
                
                if invalid_line_info or not credentials_batch:
                    # Move invalid or empty files to not_useful directory
                    try:
                        shutil.move(str(file_path), str(not_useful_dir / file_path.name))
                    except Exception as e:
                        with processing_lock:
                            processing_status["errors"].append(f"{file_path.name} - Move to not_useful error: {str(e)}")
                    else:
                        if invalid_line_info:
                            with processing_lock:
                                processing_status["errors"].append(
                                    f"{file_path.name} - Invalid format at line {invalid_line_info}"
                                )
                    continue
                
                # Bulk fetch/create domains
                if domains_to_create:
                    # Filter out invalid domains before processing
                    valid_domains_to_create = [d for d in domains_to_create if d and len(d) >= 3 and '.' in d]
                    
                    if valid_domains_to_create:
                        existing_domains = db.query(Domain).filter(Domain.domain.in_(valid_domains_to_create)).all()
                        existing_domain_map = {d.domain: d.id for d in existing_domains}
                        
                        new_domains = []
                        for domain_str in valid_domains_to_create:
                            if domain_str not in existing_domain_map:
                                new_domains.append(Domain(domain=domain_str, is_working=None, is_important=False))
                        
                        if new_domains:
                            # Use individual inserts to ensure IDs are populated
                            for domain_obj in new_domains:
                                db.add(domain_obj)
                            db.flush()
                            
                            # Refresh to get IDs (bulk_save_objects doesn't populate IDs)
                            # Query back the newly created domains to get their IDs
                            new_domain_names = [d.domain for d in new_domains]
                            if new_domain_names:
                                # Handle large lists by batching
                                BATCH_SIZE_DOMAINS = 500
                                refreshed_domains = []
                                for i in range(0, len(new_domain_names), BATCH_SIZE_DOMAINS):
                                    batch = new_domain_names[i:i + BATCH_SIZE_DOMAINS]
                                    batch_domains = db.query(Domain).filter(Domain.domain.in_(batch)).all()
                                    refreshed_domains.extend(batch_domains)
                            else:
                                refreshed_domains = []
                        else:
                            refreshed_domains = []
                        
                        # Update domains map with all domain IDs
                        for domain in existing_domains:
                            domains_map[domain.domain] = domain.id
                        for domain in refreshed_domains:
                            domains_map[domain.domain] = domain.id
                
                # Process credentials in batches by domain
                if credentials_batch:
                    # Group credentials by domain for efficient processing
                    creds_by_domain = defaultdict(list)
                    for cred_data in credentials_batch:
                        if cred_data['domain'] in domains_map:
                            creds_by_domain[cred_data['domain']].append(cred_data)
                    
                    # Process each domain's credentials in batches to avoid SQLite parameter limit
                    # SQLite has limit of ~999 variables, so we batch in chunks of 300
                    # (300 urls + 300 users = 600 variables, safe margin)
                    BATCH_SIZE = 300
                    
                    for domain_str, cred_list in creds_by_domain.items():
                        # Skip if domain not in map (shouldn't happen, but safety check)
                        if domain_str not in domains_map:
                            with processing_lock:
                                processing_status["errors"].append(f"{file_path.name} - Domain '{domain_str}' not found in domains map")
                            continue
                        
                        domain_id = domains_map[domain_str]
                        
                        if not domain_id:
                            with processing_lock:
                                processing_status["errors"].append(f"{file_path.name} - Invalid domain_id for domain '{domain_str}'")
                            continue
                        
                        # Process credentials in batches
                        total_new_credentials = []
                        
                        for i in range(0, len(cred_list), BATCH_SIZE):
                            batch = cred_list[i:i + BATCH_SIZE]
                            
                            # Get URLs and users for this batch
                            urls = [c['url'] for c in batch]
                            users = [c['user'] for c in batch]
                            
                            # Query existing credentials for this batch
                            existing = db.query(Credential).filter(
                                Credential.domain_id == domain_id,
                                Credential.url.in_(urls),
                                Credential.user.in_(users)
                            ).all()
                            
                            # Create set of existing (url, user) pairs for fast lookup
                            existing_set = {(c.url, c.user) for c in existing}
                            
                            # Filter out duplicates and create new credentials for this batch
                            new_credentials = []
                            for cred_data in batch:
                                if (cred_data['url'], cred_data['user']) not in existing_set:
                                    new_credentials.append(Credential(
                                        domain_id=domain_id,
                                        url=cred_data['url'],
                                        user=cred_data['user'],
                                        password=cred_data['password'],
                                        is_accessed=False,
                                        is_admin=cred_data['is_admin']
                                    ))
                            
                            # Collect all new credentials
                            total_new_credentials.extend(new_credentials)
                        
                        # Bulk insert all new credentials for this domain at once
                        if total_new_credentials:
                            # Split into smaller bulk insert batches if needed
                            INSERT_BATCH_SIZE = 500
                            for j in range(0, len(total_new_credentials), INSERT_BATCH_SIZE):
                                insert_batch = total_new_credentials[j:j + INSERT_BATCH_SIZE]
                                db.bulk_save_objects(insert_batch)
                            
                            with processing_lock:
                                processing_status["processed_count"] += len(total_new_credentials)
                
                # Commit after each file for safety
                db.commit()
                
                # Move file to processed folder
                try:
                    shutil.move(str(file_path), str(processed_dir / file_path.name))
                except Exception as e:
                    with processing_lock:
                        processing_status["errors"].append(f"{file_path.name} - Move error: {str(e)}")
                
            except Exception as e:
                with processing_lock:
                    processing_status["errors"].append(f"{file_path.name} - Error: {str(e)}")
        
    except Exception as e:
        with processing_lock:
            processing_status["errors"].append(f"Processing error: {str(e)}")
    finally:
        db.close()
        with processing_lock:
            processing_status["is_processing"] = False
            processing_status["current_file"] = None

@app.post("/api/process")
async def process_credentials(background_tasks: BackgroundTasks):
    """Start processing credential files in background"""
    
    with processing_lock:
        if processing_status["is_processing"]:
            return JSONResponse({
                "success": False,
                "message": "Processing already in progress"
            })
        
        # Reset status
        processing_status["is_processing"] = True
        processing_status["progress"] = 0
        processing_status["total"] = len(list(Path("creds").glob("*.txt")))
        processing_status["processed_count"] = 0
        processing_status["errors"] = []
        processing_status["start_time"] = datetime.now()
    
    # Start background task
    background_tasks.add_task(process_credentials_background)
    
    return JSONResponse({
        "success": True,
        "message": "Processing started in background",
        "total_files": processing_status["total"]
    })

@app.get("/api/process-status")
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

@app.post("/api/update-working-status")
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

@app.post("/api/credential/{credential_id}/toggle-accessed")
async def toggle_accessed(credential_id: int, db: Session = Depends(get_db)):
    """Toggle is_accessed status for a credential"""
    
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    credential.is_accessed = not credential.is_accessed
    db.commit()
    
    return JSONResponse({"success": True, "is_accessed": credential.is_accessed})

@app.post("/api/credential/{credential_id}/toggle-checked")
async def toggle_credential_checked(credential_id: int, db: Session = Depends(get_db)):
    """Toggle is_checked status for a credential"""
    
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    credential.is_checked = True  # Set to True when checked
    db.commit()
    
    return JSONResponse({"success": True, "is_checked": credential.is_checked})

@app.post("/api/domain/{domain_id}/toggle-checked")
async def toggle_domain_checked(domain_id: int, db: Session = Depends(get_db)):
    """Toggle is_checked status for a domain"""
    
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    domain.is_checked = True  # Set to True when checked
    db.commit()
    
    return JSONResponse({"success": True, "is_checked": domain.is_checked})

@app.post("/api/check-all")
async def check_all(db: Session = Depends(get_db)):
    """Check all domains and credentials (set is_checked to True)"""
    
    try:
        # Update all domains
        domains_updated = db.query(Domain).filter(Domain.is_checked == False).update({Domain.is_checked: True})
        
        # Update all credentials
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

@app.get("/api/domain/{domain_id}/credentials")
async def get_domain_credentials(
    domain_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    accessed_only: bool = Query(False),
    checked_filter: str = Query("all", regex="^(all|checked|not_checked|checked_and_working)$"),
    db: Session = Depends(get_db)
):
    """Get paginated credentials for a domain"""
    
    # Verify domain exists
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    # Build query
    creds_query = db.query(Credential).filter(Credential.domain_id == domain_id)
    if accessed_only:
        creds_query = creds_query.filter(Credential.is_accessed == True)
    
    # Filter by checked status
    if checked_filter == "checked":
        creds_query = creds_query.filter(Credential.is_checked == True)
    elif checked_filter == "not_checked":
        creds_query = creds_query.filter(Credential.is_checked == False)
    elif checked_filter == "checked_and_working":
        creds_query = creds_query.filter(Credential.is_checked == True)
    
    # Get total count
    total = creds_query.count()
    
    # Get paginated credentials
    credentials = creds_query.offset(offset).limit(limit).all()
    
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

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get database statistics"""
    
    total_domains = db.query(func.count(Domain.id)).scalar() or 0
    online_domains = db.query(func.count(Domain.id)).filter(Domain.is_working == True).scalar() or 0
    offline_domains = db.query(func.count(Domain.id)).filter(Domain.is_working == False).scalar() or 0
    total_credentials = db.query(func.count(Credential.id)).scalar() or 0
    accessed_credentials = db.query(func.count(Credential.id)).filter(Credential.is_accessed == True).scalar() or 0
    
    return JSONResponse({
        "total_domains": total_domains,
        "online_domains": online_domains,
        "offline_domains": offline_domains,
        "total_credentials": total_credentials,
        "accessed_credentials": accessed_credentials
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

