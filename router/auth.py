import utils
import database
from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status
from database import get_db
from pydantic import BaseModel, EmailStr
from dependencies import get_user_from_session
from models import User, Session as SessionModel
from fastapi.responses import JSONResponse, Response
from datetime import datetime
from typing import List
import base64
import config
from models import (
    User,
    Session,
    Role,
    RolePermission,
    Permission,
    ForgotPassword
)
from cv_processor import CVProcessor
from uuid import uuid4
from passlib.context import CryptContext




settings = config.Settings()

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
    responses={404: {"description": "Route not found"}},
)


class LoginRequest(BaseModel):
    email: str
    password: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    # Check user credentials
    user = db.query(User).filter(User.email == request.email).first()
    if user is None:
        return JSONResponse(status_code=401, content={"message": "Invalid credentials"})

    if not pwd_context.verify(request.password, user.password):
        return JSONResponse(status_code=401, content={"message": "Invalid credentials"})

    # Check if already logged in
    session = db.query(Session).filter(Session.user_id == user.id).first()
    expires = datetime.now().timestamp() + 86400 * 30  # 30 days
    if session is not None:
        # Update session expiration
        session.expires = expires
        session_token = session.id  # Use existing session token
    else:
        # Create session token
        session_token = str(uuid4())
        session = Session(id=session_token, user_id=user.id, expires=expires)
        db.add(session)

    db.commit()

    # Fetch role and permissions
    role = db.query(Role).filter(Role.id == user.role_id).first()
    role_permissions = (
        db.query(RolePermission).filter(RolePermission.role_id == role.id).all()
    )
    permissions = [
        db.query(Permission).filter(Permission.id == rp.permission_id).first().name
        for rp in role_permissions
    ]

    # No room data needed

    # Encode CV as base64 if it exists
    cv_base64 = None
    cv_summary = None
    cv_key_info = None
    
    if user.cv:
        cv_base64 = base64.b64encode(user.cv).decode('utf-8')
        
        # Process the CV to get summary and key info
        try:
            processor = CVProcessor()
            cv_text = processor.extract_text_from_pdf(user.cv)
            
            if cv_text:
                cv_summary = processor.generate_summary(cv_text)
                cv_key_info = processor.extract_key_info(cv_text)
        except Exception as e:
            print(f"Error processing CV: {e}")
            # Continue without summary if there's an error
    
    # Craft response
    response = JSONResponse(
        status_code=200,
        content={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": {"id": role.id, "name": role.name, "permissions": permissions},
            "username": user.username,
            "contact": user.contact,
            "company_name": user.company_name,
            "job_title": user.job_title,
            "message": user.message,
            "has_cv": user.cv is not None,
            # "cv_summary": cv_summary,  # Include CV summary if available
            "cv_key_info": cv_key_info,  # Include key info extracted from CV
            "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else None,
        },
    )

    response.set_cookie("SESSION", session_token)
    return response


@router.get("/me")
async def get_profile(user: User = Depends(get_user_from_session), db: Session = Depends(get_db)):
    # If user is a dictionary (from the session), fetch the complete user object
    if isinstance(user, dict):
        user = db.query(User).filter(User.id == user["id"]).first()

    # Encode CV as base64 if it exists
    cv_base64 = None
    cv_summary = None
    cv_key_info = None
    
    if user.cv:
        cv_base64 = base64.b64encode(user.cv).decode('utf-8')
        
        # Process the CV to get summary and key info
        try:
            processor = CVProcessor()
            cv_text = processor.extract_text_from_pdf(user.cv)
            
            if cv_text:
                cv_summary = processor.generate_summary(cv_text)
                cv_key_info = processor.extract_key_info(cv_text)
        except Exception as e:
            print(f"Error processing CV in get_profile: {e}")
            # Continue without summary if there's an error
    
    # Create a response that includes all user fields with CV as base64
    user_data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "username": user.username,
        "contact": user.contact,
        "company_name": user.company_name,
        "job_title": user.job_title,
        "message": user.message,
        "has_cv": user.cv is not None,
        # "cv_summary": cv_summary,  # Include CV summary if available
        "cv_key_info": cv_key_info,  # Include key info extracted from CV
        "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else None,
    }
    
    return user_data


@router.get("/logout")
async def logout(
    user: User = Depends(get_user_from_session), db: Session = Depends(get_db)
):
    session = db.query(Session).filter(Session.user_id == user["id"]).first()
    db.delete(session)
    db.commit()

    response = JSONResponse(status_code=200, content={"message": "Logged out"})
    response.delete_cookie("SESSION")

    return response


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(get_user_from_session),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user["id"]).first()
    if not pwd_context.verify(request.old_password, user.password):
        return JSONResponse(status_code=401, content={"message": "Invalid credentials"})

    user.password = pwd_context.hash(request.new_password)
    db.commit()

    utils.sendEmail("Password changed", "Your password has been changed", user.email)

    return JSONResponse(status_code=200, content={"message": "Password changed"})


class ForgotPasswordRequest(BaseModel):
    email: str


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == request.email).first()
    if user is None:
        return JSONResponse(status_code=400, content={"message": "Invalid email"})

    token = str(uuid4().int)[:4]
    forgot_password = ForgotPassword(
        user_id=user.id,
        token=token,
        expires=datetime.now().timestamp() + 60 * 60,  # 1 hour
    )
    db.add(forgot_password)
    db.commit()

    utils.sendEmail("Forgot password", f"Your token is {token}", user.email)

    return JSONResponse(status_code=200, content={"message": "Otp sent"})


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    forgot_password = (
        db.query(ForgotPassword).filter(ForgotPassword.token == request.token).first()
    )
    if forgot_password is None:
        return JSONResponse(status_code=400, content={"message": "Invalid Otp"})

    if forgot_password.expires < datetime.now().timestamp():
        return JSONResponse(status_code=400, content={"message": "Otp expired"})

    user = db.query(User).filter(User.id == forgot_password.user_id).first()
    user.password = pwd_context.hash(request.new_password)
    db.delete(forgot_password)
    db.commit()

    return JSONResponse(status_code=200, content={"message": "Password reset"})

