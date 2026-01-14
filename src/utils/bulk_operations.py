"""
Bulk operations helper for handling bulk actions
"""
from typing import List
from sqlalchemy.orm import Session
from src.core.models import Domain, Credential, DomainAssignment, UserRole


class BulkOperations:
    """Helper class for bulk operations"""
    
    @staticmethod
    def delete_selected(
        db: Session,
        current_user,
        credential_ids: List[int],
        domain_ids: List[int]
    ) -> dict:
        """Bulk delete selected items"""
        deleted_credentials = 0
        deleted_domains = 0
        
        try:
            # Delete selected credentials
            if credential_ids:
                if current_user.role != UserRole.ADMIN:
                    # Verify access
                    accessible_creds = BulkOperations._get_accessible_credentials(
                        db, current_user.id, credential_ids
                    )
                    cred_ids = [c.id for c in accessible_creds]
                    deleted = db.query(Credential).filter(Credential.id.in_(cred_ids)).delete(synchronize_session=False)
                    deleted_credentials = deleted
                else:
                    deleted = db.query(Credential).filter(Credential.id.in_(credential_ids)).delete(synchronize_session=False)
                    deleted_credentials = deleted
            
            # Delete selected domains
            if domain_ids:
                if current_user.role != UserRole.ADMIN:
                    # Verify access
                    accessible_domains = BulkOperations._get_accessible_domains(
                        db, current_user.id, domain_ids
                    )
                    dom_ids = [d.id for d in accessible_domains]
                    deleted = db.query(Domain).filter(Domain.id.in_(dom_ids)).delete(synchronize_session=False)
                    deleted_domains = deleted
                else:
                    deleted = db.query(Domain).filter(Domain.id.in_(domain_ids)).delete(synchronize_session=False)
                    deleted_domains = deleted
            
            db.commit()
            
            return {
                "success": True,
                "deleted_credentials": deleted_credentials,
                "deleted_domains": deleted_domains
            }
            
        except Exception as e:
            db.rollback()
            raise e
    
    @staticmethod
    def mark_as_checked(
        db: Session,
        current_user,
        credential_ids: List[int],
        domain_ids: List[int]
    ) -> dict:
        """Bulk mark items as checked"""
        checked_credentials = 0
        checked_domains = 0
        
        try:
            # Mark credentials as checked
            if credential_ids:
                if current_user.role != UserRole.ADMIN:
                    accessible_creds = BulkOperations._get_accessible_credentials(
                        db, current_user.id, credential_ids
                    )
                    cred_ids = [c.id for c in accessible_creds]
                    updated = db.query(Credential).filter(Credential.id.in_(cred_ids)).update(
                        {Credential.is_checked: True},
                        synchronize_session=False
                    )
                    checked_credentials = updated
                else:
                    updated = db.query(Credential).filter(Credential.id.in_(credential_ids)).update(
                        {Credential.is_checked: True},
                        synchronize_session=False
                    )
                    checked_credentials = updated
            
            # Mark domains as checked
            if domain_ids:
                if current_user.role != UserRole.ADMIN:
                    accessible_domains = BulkOperations._get_accessible_domains(
                        db, current_user.id, domain_ids
                    )
                    dom_ids = [d.id for d in accessible_domains]
                    updated = db.query(Domain).filter(Domain.id.in_(dom_ids)).update(
                        {Domain.is_checked: True},
                        synchronize_session=False
                    )
                    checked_domains = updated
                else:
                    updated = db.query(Domain).filter(Domain.id.in_(domain_ids)).update(
                        {Domain.is_checked: True},
                        synchronize_session=False
                    )
                    checked_domains = updated
            
            db.commit()
            
            return {
                "success": True,
                "checked_credentials": checked_credentials,
                "checked_domains": checked_domains
            }
            
        except Exception as e:
            db.rollback()
            raise e
    
    @staticmethod
    def _get_accessible_credentials(db: Session, user_id: int, credential_ids: List[int]) -> List[Credential]:
        """Get credentials accessible to the user"""
        return db.query(Credential).join(Domain).join(DomainAssignment).filter(
            Credential.id.in_(credential_ids),
            DomainAssignment.user_id == user_id
        ).all()
    
    @staticmethod
    def _get_accessible_domains(db: Session, user_id: int, domain_ids: List[int]) -> List[Domain]:
        """Get domains accessible to the user"""
        return db.query(Domain).join(DomainAssignment).filter(
            Domain.id.in_(domain_ids),
            DomainAssignment.user_id == user_id
        ).all()