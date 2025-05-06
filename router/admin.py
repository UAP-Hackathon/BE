
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
from models import Job

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    responses={404: {"description": "Route not found"}},
)

class JobPost(BaseModel):
    title: str
    description: str
    company_name: str
    location: str
    salary: float
    skills: List[str]
    experience: int


@router.post("/postJob")
async def post_job(job: JobPost, user: User = Depends(permission_required("POST_JOB")), db: Session = Depends(get_db)):
    latest_id = db.query(Job).order_by(Job.id.desc()).first()
    
    db.add(Job(id=latest_id.id + 1 if latest_id else 1, title=job.title, description=job.description, company_name=job.company_name, location=job.location, salary=job.salary, skills=job.skills, experience=job.experience))
    db.commit()
    return JSONResponse(status_code=201, content={"message": "Job posted successfully"})
    

