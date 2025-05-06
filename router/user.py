import utils
import database
from fastapi import Depends, HTTPException, APIRouter, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status
from database import get_db
from pydantic import BaseModel, EmailStr
from dependencies import get_user_from_session
from models import User, Session as SessionModel
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import List
from middleware import permission_required
from models import Role, RolePermission, Permission
from cv_processor import CVProcessor
import base64


router = APIRouter(
    prefix="/api/user",
    tags=["user"],
    responses={404: {"description": "Route not found"}},
)


class NewUserRequest(BaseModel):
    name: str
    email: str
    password: str
    contact: str = None
    username: str = None
    role_id: int


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    contact: str = None
    username: str = None
    company_name: str = None
    job_title: str = None
    message: str = None


@router.get("/allUsers")
async def all_users(
    user: User = Depends(permission_required("LIST_ALL_USERS")),
    db: Session = Depends(get_db),
):
    # Query all users and roles in a more optimized way
    users = db.query(User).all()

    response = []

    for user in users:
        role = db.query(Role).filter(Role.id == user.role_id).first()

        # Fetch permissions in a single query
        role_permissions = (
            db.query(Permission)
            .join(RolePermission)
            .filter(RolePermission.role_id == role.id)
            .all()
        )
        permissions = [permission.name for permission in role_permissions]

        # Room data removed as Room model is no longer available
        cv_base64 = None
        cv_summary = None
        cv_key_info = None
        
        if user.cv:
            cv_base64 = base64.b64encode(user.cv).decode('utf-8')
            
            # Process the CV to get summary and key info
            processor = CVProcessor()
            cv_text = processor.extract_text_from_pdf(user.cv)
            
            if cv_text:
                cv_summary = processor.generate_summary(cv_text)
                cv_key_info = processor.extract_key_info(cv_text)

        # Construct the response for each user
        user_response = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": {"id": role.id, "name": role.name, "permissions": permissions},
            "username": user.username,
            "contact": user.contact,
            "company_name": user.company_name,
            "job_title": user.job_title,
            "message": user.message,
          
            "has_cv": user.cv is not None,  # Only indicate if CV exists, don't return binary data
            "cv_data": cv_base64,  # Include CV as base64 string
            "cv_summary": cv_summary,  # Include CV summary if available
            "cv_key_info": cv_key_info,  # Include key info extracted from CV
            "created_at": user.created_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            ) if user.created_at else None  # Convert datetime to string
        }

        # Append the user response to the list
        response.append(user_response)

    # Return the final response as JSON
    return JSONResponse(status_code=200, content={"users": response})



@router.post("/signup")
async def signup(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    username: str = Form(None),
    contact: str = Form(None),
    company_name: str = Form(None),
    job_title: str = Form(None),
    message: str = Form(None),
    role_id: int = Form(None),  # Added role_id parameter
    cv: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    # Check if email already exists
    user = db.query(User).filter(User.email == email).first()
    if user is not None:
        return JSONResponse(
            status_code=400, content={"message": "Email already exists"}
        )
    
    # Get the latest user ID
    latest_user_id = (
        0
        if db.query(User).count() == 0
        else db.query(User).order_by(User.id.desc()).first().id
    )
    
    # Determine role_id to use
    user_role_id = None
    if role_id is not None:
        # Use provided role_id if it exists
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            return JSONResponse(
                status_code=400, content={"message": "Invalid role ID"}
            )
        user_role_id = role.id
    else:
        # Default to JOB_SEEKER role if no role_id provided
        job_seeker_role = db.query(Role).filter(Role.name == "JOB_SEEKER").first()
        if not job_seeker_role:
            return JSONResponse(
                status_code=500, content={"message": "JOB_SEEKER role not found"}
            )
        user_role_id = job_seeker_role.id
    
    # Process CV file if provided
    cv_data = None
    if cv:
        # Check if file is a PDF
        if not cv.content_type == "application/pdf":
            return JSONResponse(
                status_code=400, content={"message": "CV file must be a PDF"}
            )
        
        # Read the file content
        cv_data = await cv.read()
    
    # Create new user with JOB_SEEKER role
    newUser = User(
        id=latest_user_id + 1,
        name=name,
        email=email,
        password=utils.hash(password),
        role_id=user_role_id,  # Use the determined role_id
        username=username,
        contact=contact,
        company_name=company_name,
        job_title=job_title,
        message=message,
        created_at=datetime.utcnow(),
        cv=cv_data  # Save CV data if provided
    )
    
    db.add(newUser)
    db.commit()
    
    # Send welcome email
    utils.sendEmail(
        "Welcome to our platform",
        f"Hello {name},\n\nWelcome to our platform. You have successfully registered.\n\nBest Regards,\nTeam",
        email,
    )
    
    return JSONResponse(status_code=201, content={"message": "Signup successful"})


class CVSummaryRequest(BaseModel):
    user_id: int

@router.post("/cv-summary")
async def get_cv_summary(
    request: CVSummaryRequest,
    current_user: User = Depends(permission_required("VIEW_USER")),
    db: Session = Depends(get_db),
):
    # Check if user exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user has a CV
    if not user.cv:
        raise HTTPException(status_code=404, detail="CV not found for this user")
    
    # Process the CV
    processor = CVProcessor()
    
    # Extract text from PDF
    cv_text = processor.extract_text_from_pdf(user.cv)
    if not cv_text:
        return JSONResponse(
            status_code=400, 
            content={"message": "Could not extract text from the PDF"}
        )
    
    # Generate summary
    summary = processor.generate_summary(cv_text)
    
    # Extract key information
    key_info = processor.extract_key_info(cv_text)
    
    return JSONResponse(
        status_code=200,
        content={
            "user_id": request.user_id,
            "summary": summary,
            "key_info": key_info,
            "full_text": cv_text[:1000] + "..." if len(cv_text) > 1000 else cv_text  # Truncate long text
        }
    )


@router.get("/my-cv-summary")
async def get_my_cv_summary(
    current_user: User = Depends(get_user_from_session),
    db: Session = Depends(get_db),
):
    # Get the user from the database
    if isinstance(current_user, dict):
        user = db.query(User).filter(User.id == current_user["id"]).first()
    else:
        user = current_user
        
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user has a CV
    if not user.cv:
        raise HTTPException(status_code=404, detail="You haven't uploaded a CV yet")
    
    # Process the CV
    processor = CVProcessor()
    
    # Extract text from PDF
    cv_text = processor.extract_text_from_pdf(user.cv)
    if not cv_text:
        return JSONResponse(
            status_code=400, 
            content={"message": "Could not extract text from your PDF"}
        )
    
    # Generate summary
    summary = processor.generate_summary(cv_text)
    
    # Extract key information
    key_info = processor.extract_key_info(cv_text)
    
    return JSONResponse(
        status_code=200,
        content={
            "summary": summary,
            "key_info": key_info,
            "full_text": cv_text[:1000] + "..." if len(cv_text) > 1000 else cv_text  # Truncate long text
        }
    )

