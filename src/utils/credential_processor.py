"""
Background credential processing utilities
"""
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import shutil
import threading

from src.core.database import SessionLocal
from src.core.models import Domain, Credential
from src.utils.credential_parser import parse_credential_line, extract_domain, parse_multi_line_credential_block

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


def process_credentials_background():
    """
    Background task to process credential files efficiently.
    Reads files from creds/ folder, parses credentials, and imports into database.
    """
    from config.settings import CREDS_DIR, PROCESSED_CREDS_DIR, NOT_USEFUL_DIR
    
    creds_dir = CREDS_DIR
    processed_dir = PROCESSED_CREDS_DIR
    not_useful_dir = NOT_USEFUL_DIR    
    files = list(creds_dir.glob("*.txt"))
    
    with processing_lock:
        processing_status["is_processing"] = True
        processing_status["progress"] = 0
        processing_status["total"] = len(files)
        processing_status["processed_count"] = 0
        processing_status["errors"] = []
        processing_status["start_time"] = datetime.now()
        processing_status["current_file"] = None
    db = SessionLocal()
    
    try:
        for file_idx, file_path in enumerate(files):
            with processing_lock:
                processing_status["current_file"] = file_path.name
                processing_status["progress"] = file_idx + 1
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                credentials_batch = []
                domains_map = {} 
                domains_to_create = set()
                has_valid_credentials = False
        
                is_multi_line_format = any(
                    line.strip().startswith(('SEARCH ->', 'URL ->', 'LOGIN ->', 'PASSWORD ->'))
                    for line in lines[:20]  # Check first 20 lines
                )
                
                line_idx = 0
                while line_idx < len(lines):
                    try:
                        parsed = None
                        next_idx = line_idx + 1
                        
                        if is_multi_line_format:
                            result = parse_multi_line_credential_block(lines, line_idx)
                            if result:
                                parsed, next_idx = result
                        else:
                            parsed = parse_credential_line(lines[line_idx])
                        
                        if not parsed:
                            line_idx = next_idx
                            continue  
                        url, user, password = parsed
                        domain_str = extract_domain(url)
                        
                        if not domain_str:
                            line_idx = next_idx
                            continue                          
                        if len(domain_str) < 3 or '.' not in domain_str:
                            line_idx = next_idx
                            continue
                
                        has_valid_credentials = True
                        
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
                        
                        line_idx = next_idx
                    except Exception as e:
                        # Log error but continue processing other lines
                        with processing_lock:
                            processing_status["errors"].append(f"{file_path.name}:{line_idx+1} - {str(e)}")
                        line_idx += 1
                        continue
                
                # If no valid credentials found, move to not_useful
                if not has_valid_credentials:
                    try:
                        shutil.move(str(file_path), str(not_useful_dir / file_path.name))
                        with processing_lock:
                            processing_status["errors"].append(f"{file_path.name} - No valid credentials found")
                    except Exception as e:
                        with processing_lock:
                            processing_status["errors"].append(f"{file_path.name} - Move to not_useful error: {str(e)}")
                    continue
                
                # If we have valid credentials but the batch is empty due to filtering, still process
                if not credentials_batch:
                    try:
                        shutil.move(str(file_path), str(processed_dir / file_path.name))
                    except Exception as e:
                        with processing_lock:
                            processing_status["errors"].append(f"{file_path.name} - Move error: {str(e)}")
                    continue
                
                # Bulk fetch/create domains
                if domains_to_create:
                    # Filter out invalid domains before processing
                    valid_domains_to_create = [d for d in domains_to_create if d and len(d) >= 3 and '.' in d]
                    
                    if valid_domains_to_create:
                        existing_domains = db.query(Domain).filter(
                            Domain.domain.in_(valid_domains_to_create)
                        ).all()
                        existing_domain_map = {d.domain: d.id for d in existing_domains}
                        
                        new_domains = []
                        for domain_str in valid_domains_to_create:
                            if domain_str not in existing_domain_map:
                                new_domains.append(Domain(
                                    domain=domain_str,
                                    is_working=None,
                                    is_important=False,
                                    is_checked=False  # New domains should be unchecked
                                ))
                        
                        if new_domains:
                            # Use individual inserts to ensure IDs are populated
                            for domain_obj in new_domains:
                                db.add(domain_obj)
                            db.flush()
                            
                            # Query back the newly created domains to get their IDs
                            new_domain_names = [d.domain for d in new_domains]
                            if new_domain_names:
                                # Handle large lists by batching
                                BATCH_SIZE_DOMAINS = 500
                                refreshed_domains = []
                                for i in range(0, len(new_domain_names), BATCH_SIZE_DOMAINS):
                                    batch = new_domain_names[i:i + BATCH_SIZE_DOMAINS]
                                    batch_domains = db.query(Domain).filter(
                                        Domain.domain.in_(batch)
                                    ).all()
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
                    
                    # Process each domain's credentials
                    for domain_str, cred_list in creds_by_domain.items():
                        # Skip if domain not in map (shouldn't happen, but safety check)
                        if domain_str not in domains_map:
                            with processing_lock:
                                processing_status["errors"].append(
                                    f"{file_path.name} - Domain '{domain_str}' not found in domains map"
                                )
                            continue
                        
                        domain_id = domains_map[domain_str]
                        
                        if not domain_id:
                            with processing_lock:
                                processing_status["errors"].append(
                                    f"{file_path.name} - Invalid domain_id for domain '{domain_str}'"
                                )
                            continue
                        
                        # Fetch domain object
                        domain_obj = db.query(Domain).filter(Domain.id == domain_id).first()
                        if not domain_obj:
                            with processing_lock:
                                processing_status["errors"].append(
                                    f"{file_path.name} - Domain object not found for id '{domain_id}'"
                                )
                            continue
                        
                        # Get all existing credentials for this domain
                        existing_credentials = db.query(Credential).filter(
                            Credential.domain_id == domain_id
                        ).all()
                        
                        # Create sets for fast lookup of existing credentials
                        existing_triples = {(cred.url, cred.user, cred.password) for cred in existing_credentials}
                        existing_urls = {cred.url for cred in existing_credentials}
                        existing_users = {cred.user for cred in existing_credentials}
                        existing_passwords = {cred.password for cred in existing_credentials}
                        
                        # Flag to track if we find any new/different credential
                        has_new_or_different_credential = False
                        new_credentials_to_add = []
                        
                        # Check each credential from the file
                        for cred_data in cred_list:
                            url = cred_data['url']
                            user = cred_data['user']
                            password = cred_data['password']
                            
                            # Check if this exact combination (url, user, password) already exists
                            if (url, user, password) in existing_triples:
                                # Exact match exists, skip
                                continue
                            
                            # Check if any of the three fields is different from existing ones
                            # We need to check if this represents a new credential pattern
                            is_different = False
                            
                            # If this URL doesn't exist in any existing credential for this domain
                            if url not in existing_urls:
                                is_different = True
                            # If this user doesn't exist in any existing credential for this domain  
                            elif user not in existing_users:
                                is_different = True
                            # If this password doesn't exist in any existing credential for this domain
                            elif password not in existing_passwords:
                                is_different = True
                            # Even if all three exist separately, they might not be combined in the same way
                            # So we should still add it if the combination is new
                            else:
                                # Check if this specific combination exists
                                if (url, user, password) not in existing_triples:
                                    # Check if there's any existing credential with the same URL and user
                                    same_url_user_exists = any(
                                        cred.url == url and cred.user == user 
                                        for cred in existing_credentials
                                    )
                                    
                                    # If same URL and user exists with different password, this is a new credential
                                    if same_url_user_exists:
                                        is_different = True
                                    else:
                                        # This is a new combination of existing values
                                        is_different = True
                            
                            if is_different:
                                has_new_or_different_credential = True
                                new_credentials_to_add.append(Credential(
                                    domain_id=domain_id,
                                    url=url,
                                    user=user,
                                    password=password,
                                    is_accessed=False,
                                    is_admin=cred_data['is_admin'],
                                    is_checked=False  # New credentials should be unchecked
                                ))
                        
                        # Add new credentials if any
                        if new_credentials_to_add:
                            # Insert in batches to avoid SQLite parameter limit
                            BATCH_SIZE = 500
                            for i in range(0, len(new_credentials_to_add), BATCH_SIZE):
                                batch = new_credentials_to_add[i:i + BATCH_SIZE]
                                db.bulk_save_objects(batch)
                            
                            with processing_lock:
                                processing_status["processed_count"] += len(new_credentials_to_add)
                        
                        # Update domain checked status if any new/different credential was found
                        if has_new_or_different_credential:
                            domain_obj.is_checked = False
                
                # Commit after each file for safety
                db.commit()
                
                # Move file to processed folder (since it has valid credentials)
                try:
                    shutil.move(str(file_path), str(processed_dir / file_path.name))
                except Exception as e:
                    with processing_lock:
                        processing_status["errors"].append(f"{file_path.name} - Move error: {str(e)}")
                
            except Exception as e:
                with processing_lock:
                    processing_status["errors"].append(f"{file_path.name} - Error: {str(e)}")
                # Rollback transaction for this file on error
                db.rollback()
        
    except Exception as e:
        with processing_lock:
            processing_status["errors"].append(f"Processing error: {str(e)}")
    finally:
        db.close()
        with processing_lock:
            processing_status["is_processing"] = False
            processing_status["current_file"] = None