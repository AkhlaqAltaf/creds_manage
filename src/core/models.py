from typing import List
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base
import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CREATOR = "creator"
    VIEWER = "viewer"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    domain_assignments = relationship("DomainAssignment", back_populates="user", foreign_keys=lambda: [DomainAssignment.user_id], cascade="all, delete-orphan")

class Domain(Base):
    __tablename__ = "domains"
    
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, unique=True, index=True, nullable=False)
    is_working = Column(Boolean, default=None, nullable=True)  
    is_important = Column(Boolean, default=False)
    is_checked = Column(Boolean, default=False)
    comment = Column(String, nullable=True)  
    
    credentials = relationship("Credential", back_populates="domain", cascade="all, delete-orphan")
    domain_assignments = relationship("DomainAssignment", back_populates="domain", cascade="all, delete-orphan")
    


class DomainAssignment(Base):
    __tablename__ = "domain_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)  
    
    user = relationship("User", back_populates="domain_assignments", foreign_keys=[user_id])
    domain = relationship("Domain", back_populates="domain_assignments")
    assigner = relationship("User", foreign_keys=[assigned_by])
    
    @staticmethod
    def get_user_domain_ids(user_id: int) -> List[int]:
        """Get domain IDs assigned to a user"""
        from src.core.database import SessionLocal
        db = SessionLocal()
        try:
            assigned_domains = db.query(DomainAssignment.domain_id).filter(
                DomainAssignment.user_id == user_id 
            ).all()
            return [row[0] for row in assigned_domains]
        finally:
            db.close()

class CredentialStatus(Base):
    __tablename__ = "credential_statuses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    color = Column(String, default="#667eea")  
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, nullable=False)

class Credential(Base):
    __tablename__ = "credentials"
    
    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    url = Column(String, nullable=False)
    user = Column(String, nullable=False)
    password = Column(String, nullable=False)
    is_accessed = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_checked = Column(Boolean, default=False)
    status_id = Column(Integer, ForeignKey("credential_statuses.id"), nullable=True)
    
    domain = relationship("Domain", back_populates="credentials")
    status = relationship("CredentialStatus")


