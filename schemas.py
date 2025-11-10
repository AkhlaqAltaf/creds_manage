from pydantic import BaseModel
from typing import List, Optional

class CredentialResponse(BaseModel):
    id: int
    url: str
    user: str
    password: str
    is_accessed: bool
    is_admin: bool
    is_checked: bool
    
    class Config:
        from_attributes = True

class DomainResponse(BaseModel):
    id: int
    domain: str
    is_working: Optional[bool]
    is_important: bool
    is_checked: bool
    credentials: List[CredentialResponse]
    check_urls: Optional[List[str]] = None  # URLs to use for domain checking
    total_credentials: int = 0  # Total credentials count for this domain
    
    class Config:
        from_attributes = True

class StatsResponse(BaseModel):
    total_domains: int
    online_domains: int
    offline_domains: int
    total_credentials: int
    accessed_credentials: int
    unprocessed_files: int

