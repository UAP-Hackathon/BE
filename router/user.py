import utils
import database
from fastapi import Depends, HTTPException, APIRouter
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

        # Construct the response for each user
        user_response = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": {"id": role.id, "name": role.name, "permissions": permissions},
            "username": user.username,
            "contact": user.contact,
            "created_at": user.created_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),  # Convert datetime to string
        }

        # Append the user response to the list
        response.append(user_response)

    # Return the final response as JSON
    return JSONResponse(status_code=200, content={"users": response})


@router.post("/createUser")
async def create_user(
    userRequest: NewUserRequest,
    user: User = Depends(permission_required("CREATE_USER")),
    db: Session = Depends(get_db),
):
    latest_user_id = (
        0
        if db.query(User).count() == 0
        else db.query(User).order_by(User.id.desc()).first().id
    )

    # check if email already exists
    user = db.query(User).filter(User.email == userRequest.email).first()
    if user is not None:
        return JSONResponse(
            status_code=400, content={"message": "Email already exists"}
        )

    newUser = User(
        id=latest_user_id + 1,
        name=userRequest.name,
        email=userRequest.email,
        password=utils.hash(userRequest.password),
        role_id=userRequest.role_id,  # role id from path parameter
        # 0 - > ADMIN
        # 1 - > CHAIRMAN
        # 2 - > TEACHER
        username=userRequest.username,
        contact=userRequest.contact,
    )
    db.add(newUser)
    db.commit()
    utils.sendEmail(
        "Welcome to our platform",
        f"Hello {userRequest.name},\n\nWelcome to our platform. You have successfully registered.\n\nBest Regards,\nTeam",
        userRequest.email,
    )

    return JSONResponse(status_code=201, content={"message": "User created"})
