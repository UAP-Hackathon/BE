from sqlalchemy.orm import Session
from dependencies import get_user_from_session
from models import User  # Adjust the import path as necessary
from database import get_db
from fastapi import HTTPException, Depends


def permission_required(permission: str, roomNumber: list[int] = None):
    def permission_checker(
        user: User = Depends(get_user_from_session), db: Session = Depends(get_db)
    ):
        if not roomNumber:
            if permission not in user["role"]["permissions"]:
                raise HTTPException(status_code=403, detail="Not enough permissions")
        if roomNumber is not None:
            if not user["room"]:
                raise HTTPException(status_code=403, detail="No room assigned to user")
            assigned_rooms = [
                room["room_number"]
                for room_group in user["room"]
                for room in room_group["room_numbers"]
            ]

            # Check if the requested roomNumber is in the user's assigned rooms
            for r in roomNumber:
                if r not in assigned_rooms:
                    raise HTTPException(
                        status_code=403,
                        detail=f"User does not have access to room number {r}",
                    )

        return user

    return permission_checker
