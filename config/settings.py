"""
Application configuration settings
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/data/credentials.db")

# Security settings
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# Application settings
APP_NAME = "Credential Manager"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Directory paths
CREDS_DIR = BASE_DIR / "creds"
PROCESSED_CREDS_DIR = BASE_DIR / "processed_creds"
NOT_USEFUL_DIR = BASE_DIR / "not_useful"
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Ensure directories exist
CREDS_DIR.mkdir(exist_ok=True)
PROCESSED_CREDS_DIR.mkdir(exist_ok=True)
NOT_USEFUL_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)














