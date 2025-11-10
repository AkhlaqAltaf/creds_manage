from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Domain(Base):
    __tablename__ = "domains"
    
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, unique=True, index=True, nullable=False)
    is_working = Column(Boolean, default=None, nullable=True)  # None = unknown, True = online, False = offline
    is_important = Column(Boolean, default=False)
    is_checked = Column(Boolean, default=False)
    
    credentials = relationship("Credential", back_populates="domain", cascade="all, delete-orphan")

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
    
    domain = relationship("Domain", back_populates="credentials")


