"""
Authentication API routes
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.models import User
from src.core.schemas import LoginRequest, LoginResponse
from src.core.auth import (
    verify_password, create_access_token,
    generate_captcha, verify_captcha
)

router = APIRouter(prefix="/api", tags=["auth"])



@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token"""
    if not verify_captcha(login_data.captcha_id, login_data.captcha_answer):
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "Invalid CAPTCHA"}
        )
    
    # Verify user credentials
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "Invalid username or password"}
        )
    
    if not user.is_active:
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "User account is inactive"}
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.username})
    
    response = JSONResponse({
        "success": True,
        "message": "Login successful",
        "access_token": access_token
    })
    
    # Set cookie for session-based auth
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=28800  # 8 hours
    )
    
    return response


@router.get("/captcha")
async def get_captcha():
    """Generate a new CAPTCHA challenge"""
    captcha_id, challenge = generate_captcha()
    return JSONResponse({
        "captcha_id": captcha_id,
        "challenge": challenge
    })


@router.get("/logout")
async def logout():
    """Logout user"""
    response = RedirectResponse(url="/login", status_code=303)
    return response
