#!/usr/bin/env python3
"""
Script to create an admin user from the command line.
Usage: python create_admin.py [username] [password]
Or run without arguments for interactive mode.
"""

import sys
import getpass
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.database import SessionLocal, init_db
from src.core.models import User, UserRole
from src.core.auth import get_password_hash, verify_password

def create_admin_user(username: str = None, password: str = None):
    """Create an admin user"""
    # Initialize database
    init_db()
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Get username
        if not username:
            username = input("Enter username for admin: ").strip()
            if not username:
                print("❌ Username cannot be empty!")
                return False
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"❌ User '{username}' already exists!")
            response = input("Do you want to update the password? (y/n): ").strip().lower()
            if response == 'y':
                if not password:
                    password = getpass.getpass("Enter new password: ")
                    password_confirm = getpass.getpass("Confirm password: ")
                    if password != password_confirm:
                        print("❌ Passwords do not match!")
                        return False
                
                existing_user.password_hash = get_password_hash(password)
                existing_user.role = UserRole.ADMIN
                existing_user.is_active = True
                db.commit()
                print(f"✅ User '{username}' updated to admin with new password!")
                return True
            else:
                return False
        
        # Get password
        if not password:
            password = getpass.getpass("Enter password: ")
            password_confirm = getpass.getpass("Confirm password: ")
            if password != password_confirm:
                print("❌ Passwords do not match!")
                return False
        
        if len(password) < 6:
            print("⚠️  Warning: Password is less than 6 characters. Consider using a stronger password.")
            response = input("Continue anyway? (y/n): ").strip().lower()
            if response != 'y':
                return False
        
        # Create admin user
        admin_user = User(
            username=username,
            password_hash=get_password_hash(password),
            role=UserRole.ADMIN,
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        
        print(f"✅ Admin user '{username}' created successfully!")
        print(f"   You can now login at http://localhost:8000/login")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin user: {str(e)}")
        return False
    finally:
        db.close()

def main():
    """Main function"""
    print("=" * 50)
    print("  Create Admin User")
    print("=" * 50)
    print()
    
    # Check command line arguments
    if len(sys.argv) == 3:
        username = sys.argv[1]
        password = sys.argv[2]
        create_admin_user(username, password)
    elif len(sys.argv) == 2:
        username = sys.argv[1]
        create_admin_user(username, None)
    else:
        create_admin_user()

if __name__ == "__main__":
    main()

