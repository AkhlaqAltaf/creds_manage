from pydantic import BaseModel
from typing import List, Optional
from src.core.models import UserRole


class CredentialResponse(BaseModel):
    id: int
    url: str
    user: str
    password: str
    is_accessed: bool
    is_admin: bool
    is_checked: bool
    status_id: Optional[int] = None
    status_name: Optional[str] = None
    
    class Config:
        from_attributes = True




class DomainResponse(BaseModel):
    id: int
    domain: str
    is_working: Optional[bool]
    is_important: bool
    is_checked: bool
    comment: Optional[str] = None  
    credentials: List[CredentialResponse]
    check_urls: Optional[List[str]] = None 
    total_credentials: int = 0  
    
    class Config:
        from_attributes = True




class StatsResponse(BaseModel):
    total_domains: int
    online_domains: int
    offline_domains: int
    total_credentials: int
    accessed_credentials: int
    unprocessed_files: int




class LoginRequest(BaseModel):
    username: str
    password: str
    captcha_id: str
    captcha_answer: str



class LoginResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None



class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole

class UserUpdate(BaseModel):
    username: str
    password: Optional[str] = None
    role: UserRole

class UserResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True

class DomainAssignmentCreate(BaseModel):
    user_id: int
    domain_id: int

class DomainAssignmentResponse(BaseModel):
    id: int
    user_id: int
    username: str
    domain_id: int
    domain_name: str
    assigned_at: str
    assigned_by: Optional[int] = None
    
    class Config:
        from_attributes = True

class CredentialStatusCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#667eea"

class CredentialStatusResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    color: str
    is_active: bool
    
    class Config:
        from_attributes = True

class ExportCredentialsRequest(BaseModel):
    domain_ids: List[int]




class BulkDeleteRequest(BaseModel):
    credential_ids: List[int] = []
    domain_ids: List[int] = []

class BulkCheckRequest(BaseModel):
    credential_ids: List[int] = []
    domain_ids: List[int] = []

class BulkExportRequest(BaseModel):
    credential_ids: List[int] = []
    domain_ids: List[int] = []
    format: str = "excel"


class ExportFilters(BaseModel):
    checked_filter: str = "not_checked"
    accessed_filter: str = "all"
    working_filter: str = "all"
    admin_filter: str = "all"
    domain_extensions: List[str] = []
    domain_contains: str = ""
    format: str = "excel"

class StatusProcessRequest(BaseModel):
    checked_filter: str = "not_checked"
    accessed_filter: str = "all"
    working_filter: str = "all"
    domain_extensions: List[str] = []
    domain_contains: str = ""
    batch_size: int = 25
