"""
Filter helper for building queries with various filters
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Query
from sqlalchemy import and_, or_, not_
from src.core.models import Domain, Credential


class FilterHelper:
    """Helper class for building filtered queries"""
    
    @staticmethod
    def build_domain_query(
        query: Query,
        checked_filter: str = "all",
        working_filter: str = "all",
        accessed_filter: Optional[str] = None,
        domain_extensions: Optional[List[str]] = None,
        domain_contains: Optional[str] = None,
        admin_filter: Optional[str] = None
    ) -> Query:
        """Build domain query with filters"""
        
        # Checked filter
        if checked_filter == "checked":
            query = query.filter(Domain.is_checked == True)
        elif checked_filter == "not_checked":
            query = query.filter(Domain.is_checked == False)
        
        # Working filter
        if working_filter == "working":
            query = query.filter(Domain.is_working == True)
        elif working_filter == "not_working":
            query = query.filter(Domain.is_working == False)
        elif working_filter == "unknown":
            query = query.filter(Domain.is_working == None)
        
        # Domain extensions filter
        if domain_extensions:
            extension_conditions = []
            for ext in domain_extensions:
                extension_conditions.append(Domain.domain.like(f"%{ext}"))
            if extension_conditions:
                query = query.filter(or_(*extension_conditions))
        
        # Domain contains filter
        if domain_contains:
            query = query.filter(Domain.domain.ilike(f"%{domain_contains}%"))
        
        # Note: accessed_filter and admin_filter are for credentials, not domains
        # They are included here for API consistency but won't be applied to domain query
        
        return query
    
    @staticmethod
    def build_credential_query(
        query: Query,
        checked_filter: str = "all",
        accessed_filter: str = "all",
        admin_filter: str = "all",
        domain_id: Optional[int] = None
    ) -> Query:
        """Build credential query with filters"""
        
        # Domain filter
        if domain_id:
            query = query.filter(Credential.domain_id == domain_id)
        
        # Checked filter
        if checked_filter == "checked":
            query = query.filter(Credential.is_checked == True)
        elif checked_filter == "not_checked":
            query = query.filter(Credential.is_checked == False)
        
        # Accessed filter
        if accessed_filter == "accessed":
            query = query.filter(Credential.is_accessed == True)
        elif accessed_filter == "not_accessed":
            query = query.filter(Credential.is_accessed == False)
        
        # Admin filter
        if admin_filter == "admin":
            query = query.filter(Credential.is_admin == True)
        elif admin_filter == "not_admin":
            query = query.filter(Credential.is_admin == False)
        
        return query
    
    @staticmethod
    def apply_user_access_control(
        query: Query,
        current_user,
        model,
        join_model=None
    ) -> Query:
        """Apply user access control based on role and assignments"""
        from src.core.models import UserRole, DomainAssignment
        
        if current_user.role != UserRole.ADMIN:
            if model == Domain:
                assigned_domain_ids = DomainAssignment.get_user_domain_ids(current_user.id)
                if assigned_domain_ids:
                    query = query.filter(Domain.id.in_(assigned_domain_ids))
                else:
                    query = query.filter(Domain.id == -1)  # No access
            elif model == Credential:
                # Join with Domain and DomainAssignment
                query = query.join(Domain).join(DomainAssignment)
                query = query.filter(DomainAssignment.user_id == current_user.id)
        
        return query
    
    @staticmethod
    def get_export_filters_description(filters: Dict[str, Any]) -> str:
        """Get human-readable description of applied filters"""
        descriptions = []
        
        if filters.get('checked_filter') and filters['checked_filter'] != 'all':
            descriptions.append(f"Checked: {filters['checked_filter']}")
        
        if filters.get('accessed_filter') and filters['accessed_filter'] != 'all':
            descriptions.append(f"Accessed: {filters['accessed_filter']}")
        
        if filters.get('working_filter') and filters['working_filter'] != 'all':
            descriptions.append(f"Working: {filters['working_filter']}")
        
        if filters.get('admin_filter') and filters['admin_filter'] != 'all':
            descriptions.append(f"Admin: {filters['admin_filter']}")
        
        if filters.get('domain_extensions'):
            extensions = ', '.join(filters['domain_extensions'])
            descriptions.append(f"Extensions: {extensions}")
        
        if filters.get('domain_contains'):
            descriptions.append(f"Contains: {filters['domain_contains']}")
        
        return ' | '.join(descriptions) if descriptions else 'No filters applied'