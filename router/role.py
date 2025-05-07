from models import Role, User, RolePermission, Permission
import database
from fastapi import Depends, APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from typing import List
from middleware import permission_required

router = APIRouter(
    prefix="/api/rbac",
    tags=["role"],
    responses={404: {"description": "Route not found"}},
)


class RoleRequest(BaseModel):
    name: str


@router.post("/createRole")
async def create_role(
    role: RoleRequest,
    user: User = Depends(permission_required("CREATE_ROLE")),
    db: Session = Depends(database.get_db),
):
    latest_id = db.query(Role).order_by(Role.id.desc()).first()
    db.add(Role(id=latest_id.id + 1, name=role.name))
    db.commit()
    return JSONResponse(
        status_code=201, content={"message": "Role created successfully"}
    )


@router.put("/updateRole/{role_id}")
async def update_role(
    role_id: int,
    role: RoleRequest,
    user: User = Depends(permission_required("UPDATE_ROLE")),
    db: Session = Depends(database.get_db),
):
    db.query(Role).filter(Role.id == role_id).update({"name": role.name})
    db.commit()
    return JSONResponse(
        status_code=200, content={"message": "Role updated successfully"}
    )


class DeleteRoleRequest(BaseModel):
    role_id: int


@router.delete("/deleteRole")
async def delete_role(
    role: DeleteRoleRequest,
    user: User = Depends(permission_required("DELETE_ROLE")),
    db: Session = Depends(database.get_db),
):
    role_id = role.role_id
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
    db.query(User).filter(User.role_id == role_id).update({"role_id": 0})
    db.query(Role).filter(Role.id == role_id).delete()
    db.commit()
    return JSONResponse(
        status_code=200, content={"message": "Role deleted successfully"}
    )


class PermissionRequest(BaseModel):
    name: str
    category: str


@router.post("/createPermission")
async def create_permission(
    permission: PermissionRequest,
    user: User = Depends(permission_required("CREATE_PERMISSION")),
    db: Session = Depends(database.get_db),
):
    latest_id = db.query(Permission).order_by(Permission.id.desc()).first()

    db.add(
        Permission(
            id=latest_id.id + 1, name=permission.name, category=permission.category
        )
    )
    db.commit()
    return JSONResponse(
        status_code=201, content={"message": "Permission created successfully"}
    )


class RolePermissionRequest(BaseModel):
    role_id: int
    permissions: List[int]


@router.put("/permissions")
async def edit_role_permissions(
    role_permissions: RolePermissionRequest,
    user: User = Depends(permission_required("ASSIGN_ROLE_PERMISSION")),
    db: Session = Depends(database.get_db),
):
    already_assigned_ids = set(
        rp.permission_id
        for rp in db.query(RolePermission.permission_id)
        .filter(RolePermission.role_id == role_permissions.role_id)
        .all()
    )

    # Get permissions for validation
    db.query(Permission.name)\
        .filter(Permission.id.in_(role_permissions.permissions))\
        .all()

    max_id = db.query(RolePermission.id).order_by(RolePermission.id.desc()).first()
    next_id = max_id.id + 1 if max_id else 1

    new_permissions = []
    for permission_id in role_permissions.permissions:
        if permission_id not in already_assigned_ids:
            new_permissions.append(
                RolePermission(
                    id=next_id,
                    role_id=role_permissions.role_id,
                    permission_id=permission_id,
                )
            )
            next_id += 1

    if new_permissions:
        db.bulk_save_objects(new_permissions)
        db.commit()

    return JSONResponse(
        status_code=200, content={"message": "Role permissions updated successfully"}
    )


@router.get("/listAllRoles")
async def get_roles(
    user: User = Depends(permission_required("LIST_ALL_ROLES")),
    db: Session = Depends(database.get_db),
):
    roles = db.query(Role).all()
    response = []
    for role in roles:
        role_permissions = (
            db.query(RolePermission).filter(RolePermission.role_id == role.id).all()
        )
        permissions = []
        for rp in role_permissions:
            permission = (
                db.query(Permission).filter(Permission.id == rp.permission_id).first()
            )
            permissions.append(permission.name)

        response.append({"id": role.id, "name": role.name, "permissions": permissions})

    return JSONResponse(status_code=200, content=response)


@router.get("/listAllPermissions")
async def list_permissions(
    user: User = Depends(permission_required("LIST_ALL_PERMISSIONS")),
    db: Session = Depends(database.get_db),
):
    permissions = db.query(Permission).all()
    response = []
    for permission in permissions:
        response.append(
            {
                "id": permission.id,
                "name": permission.name,
                "category": permission.category,
            }
        )

    categories = set([p.category for p in permissions])
    category_response = []
    for category in categories:
        category_permission = []
        for p in permissions:
            if p.category == category:
                category_permission.append({"id": p.id, "name": p.name})

        category_response.append(
            {"category": category, "permissions": category_permission}
        )

    return JSONResponse(status_code=200, content=category_response)
