
import database
from fastapi import Depends, HTTPException, APIRouter, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status
from database import get_db
from pydantic import BaseModel, EmailStr, Field
from dependencies import get_user_from_session
from models import User, Session as SessionModel, Job
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import List, Dict, Any, Optional
from middleware import permission_required
from cv_processor import CVProcessor
from openai_utils import SkillAssessment
import re
import json
from fastapi import Query

router = APIRouter(
    prefix="/api/jobseeker",
    tags=["jobseeker"],
    responses={404: {"description": "Route not found"}},
)


class JobMatchResponse(BaseModel):
    job_id: int
    title: str
    company_name: str
    location: str
    salary: str
    match_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    description: Optional[str] = None


class JobMatchFilter(BaseModel):
    min_match_score: Optional[float] = Field(0.0, ge=0.0, le=1.0, description="Minimum match score (0.0 to 1.0)")
    location: Optional[str] = None
    include_description: Optional[bool] = False

class CurrentUserID(BaseModel):
    user_id: int




@router.get("/matchJob/{user_id}", response_model=List[JobMatchResponse])
async def match_job(
    user_id: int,
    db: Session = Depends(get_db)
):  
    """Match jobs with user's skills extracted from their CV"""
    # Get the current user from the database
    user = db.query(User).filter(User.id ==     user_id).first()
        
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user has uploaded a CV
    if not user.cv:
        raise HTTPException(status_code=400, detail="You need to upload your CV first to match jobs")
    
    # Process the CV to extract skills
    processor = CVProcessor()
    cv_text = processor.extract_text_from_pdf(user.cv)
    
    if not cv_text:
        raise HTTPException(status_code=400, detail="Could not extract text from your CV")
    
    # Extract key information including skills
    key_info = processor.extract_key_info(cv_text)
    user_skills = key_info.get('skills', [])
    
    # If no skills found, try to extract skills from the full text
    if not user_skills:
        # Simple skill extraction from full text as fallback
        common_tech_skills = [
            "python", "java", "javascript", "html", "css", "react", "angular", "vue", 
            "node", "express", "django", "flask", "spring", "hibernate", "sql", "nosql", 
            "mongodb", "postgresql", "mysql", "oracle", "aws", "azure", "gcp", "docker", 
            "kubernetes", "jenkins", "git", "ci/cd", "agile", "scrum", "rest", "graphql",
            "machine learning", "ai", "data science", "tensorflow", "pytorch", "nlp",
            "mobile", "android", "ios", "swift", "kotlin", "flutter", "react native"
        ]
        
        # Extract skills by looking for common tech keywords
        for skill in common_tech_skills:
            # Use word boundaries to find whole words
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, cv_text.lower()):
                user_skills.append(skill)
    
    # Normalize user skills (lowercase)
    user_skills = [skill.lower().strip() for skill in user_skills]
    user_skills = list(set(user_skills))  # Remove duplicates
    
    # Get all jobs
    jobs = db.query(Job).all()
    
    # Calculate match scores
    job_matches = []

    filter_params = JobMatchFilter()
    
    for job in jobs:
        # Get job skills and normalize
        job_skills = [skill.lower().strip() for skill in job.skills]
        
        # Find matching skills
        matched_skills = [skill for skill in user_skills if skill in job_skills]
        missing_skills = [skill for skill in job_skills if skill not in user_skills]
        
        # Calculate match score (percentage of job skills matched)
        match_score = len(matched_skills) / len(job_skills) if job_skills else 0
        
        # Apply filters
        if filter_params:
            # Filter by minimum match score
            if match_score < filter_params.min_match_score:
                continue
                
            # Filter by location if specified
            if filter_params.location and filter_params.location.lower() not in job.location.lower():
                continue
        
        # Create job match object
        job_match = {
            "job_id": job.id,
            "title": job.title,
            "company_name": job.company_name,
            "location": job.location,
            "salary": job.salary,
            "match_score": match_score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills
        }
        
        # Include description if requested
        if filter_params and filter_params.include_description:
            job_match["description"] = job.description
        
        job_matches.append(job_match)
    
    # Sort by match score (highest first)
    job_matches.sort(key=lambda x: x["match_score"], reverse=True)
    
    return job_matches


@router.get("/jobs", response_model=List[Dict[str, Any]])
async def get_all_jobs(db: Session = Depends(get_db)):
    """Get all available jobs"""
    jobs = db.query(Job).all()
    
    result = []
    for job in jobs:
        result.append({
            "id": job.id,
            "title": job.title,
            "company_name": job.company_name,
            "location": job.location,
            "salary": job.salary,
            "skills": job.skills,
            "experience": job.experience,
            "created_at": job.created_at.isoformat() if job.created_at else None
        })
    
    return result


class JobId(BaseModel):
    job_id: int
    
@router.post("/jobs", response_model=Dict[str, Any])
async def get_job(job_id: JobId, db: Session = Depends(get_db)):
    """Get a specific job by ID"""
    job = db.query(Job).filter(Job.id == job_id.job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "company_name": job.company_name,
        "location": job.location,
        "salary": job.salary,
        "skills": job.skills,
        "experience": job.experience,
        "created_at": job.created_at.isoformat() if job.created_at else None
    }


class SkillAssessmentRequest(BaseModel):
    skills: Optional[List[str]] = None
    job_id: Optional[int] = None
    num_questions: Optional[int] = Field(5, ge=1, le=10)
    question_type: Optional[str] = Field("mixed", description="Type of questions: mcq, short_answer, or mixed")

class ReactUIRequest(BaseModel):
    ui_type: str = Field(..., description="Type of UI to generate (e.g., 'landing-page', 'dashboard', 'form', 'e-commerce', 'social-media', 'admin-panel')")
    features: Optional[List[str]] = Field(["responsive", "dark-mode"], description="Features to include in the UI")
    difficulty: Optional[str] = Field("medium", description="Difficulty level: easy, medium, hard")
    description: Optional[str] = Field(None, description="Additional description of what the UI should do")


class ReactExamSubmission(BaseModel):
    exam_id: str
    answers: List[Dict[str, Any]]


@router.get("/generate-assessment")
async def generate_assessment(
    skills: Optional[List[str]] = Query(None),
    job_id: Optional[int] = None,
    num_questions: Optional[int] = Query(5, ge=1, le=10),
    question_type: Optional[str] = Query("mixed"),
    db: Session = Depends(get_db)
):

    
    skills_to_assess = []
    
    # If skills are provided directly, use those
    if skills and len(skills) > 0:
        skills_to_assess = skills
    
    # If job_id is provided, get skills from the job
    elif job_id is not None:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        skills_to_assess = job.skills
    
    # If neither skills nor job_id is provided, extract skills from user's CV
    else:
        if not user.cv:
            raise HTTPException(status_code=400, detail="You need to upload your CV or specify skills to assess")
        
        # Process the CV to extract skills
        processor = CVProcessor()
        cv_text = processor.extract_text_from_pdf(user.cv)
        
        if not cv_text:
            raise HTTPException(status_code=400, detail="Could not extract text from your CV")
        
        # Extract key information including skills
        key_info = processor.extract_key_info(cv_text)
        user_skills = key_info.get('skills', [])
        
        # If no skills found, try to extract skills from the full text
        if not user_skills:
            # Simple skill extraction from full text as fallback
            common_tech_skills = [
                "python", "java", "javascript", "html", "css", "react", "angular", "vue", 
                "node", "express", "django", "flask", "spring", "hibernate", "sql", "nosql", 
                "mongodb", "postgresql", "mysql", "oracle", "aws", "azure", "gcp", "docker", 
                "kubernetes", "jenkins", "git", "ci/cd", "agile", "scrum", "rest", "graphql",
                "machine learning", "ai", "data science", "tensorflow", "pytorch", "nlp",
                "mobile", "android", "ios", "swift", "kotlin", "flutter", "react native"
            ]
            
            # Extract skills by looking for common tech keywords
            for skill in common_tech_skills:
                # Use word boundaries to find whole words
                pattern = r'\b' + re.escape(skill) + r'\b'
                if re.search(pattern, cv_text.lower()):
                    user_skills.append(skill)
        
        skills_to_assess = user_skills
    
    # Ensure we have skills to assess
    if not skills_to_assess:
        raise HTTPException(status_code=400, detail="No skills found to assess")
    
    # Generate questions using OpenAI
    questions = SkillAssessment.generate_questions(
        skills=skills_to_assess,
        num_questions=num_questions,
        question_type=question_type
    )
    
    if not questions:
        raise HTTPException(status_code=500, detail="Failed to generate assessment questions")
    
    return {
        "skills_assessed": skills_to_assess,
        "questions": questions
    }


class AnswerSubmission(BaseModel):
    question: Dict[str, Any]
    answer: str


@router.post("/evaluate-answer")
async def evaluate_answer(
    submission: AnswerSubmission,
    db: Session = Depends(get_db)
):
    """Evaluate a user's answer to an assessment question"""
    # Get the current user from the database
    if isinstance(current_user, dict):
        user = db.query(User).filter(User.id == current_user["id"]).first()
    else:
        user = current_user
        
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate the question format
    required_fields = ["question", "type"]
    if submission.question["type"] == "mcq":
        required_fields.extend(["options", "correct_answer"])
    elif submission.question["type"] == "short_answer":
        required_fields.extend(["sample_answer", "key_points"])
    
    for field in required_fields:
        if field not in submission.question:
            raise HTTPException(status_code=400, detail=f"Question is missing required field: {field}")
    
    # Evaluate the answer
    evaluation = SkillAssessment.evaluate_answer(submission.question, submission.answer)
    
    return {
        "question": submission.question["question"],
        "user_answer": submission.answer,
        "evaluation": evaluation
    }


class BatchAnswerSubmission(BaseModel):
    questions_and_answers: List[AnswerSubmission]


@router.post("/react-ui-task")
async def get_react_ui_task(
    request: ReactUIRequest,
    db: Session = Depends(get_db)
):
    """Generate a React UI development task using AI"""

    
    # Set task difficulty
    difficulty_level = request.difficulty.lower()
    
    # Generate a dynamic UI task using OpenAI
    ui_task = SkillAssessment.generate_react_ui_task(
        ui_type=request.ui_type,
        difficulty=difficulty_level,
        features=request.features,
        description=request.description
    )
    
    # Generate a unique task ID
    task_id = f"react-ui-{datetime.now().timestamp()}"    
    return {
        "task_id": task_id,
        "ui_type": request.ui_type,
        "difficulty": difficulty_level,
        "task": ui_task,
        "submission_instructions": "Create a React application implementing this UI. Submit a GitHub repository link with your solution."
    }


@router.post("/evaluate-react-exam")
async def evaluate_react_exam(
    submission: ReactExamSubmission,
    current_user: CurrentUserID,
    db: Session = Depends(get_db)
):
    """Evaluate a React frontend exam submission"""
    # Get the user from the database
    user = db.query(User).filter(User.id == current_user.user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    results = []
    total_score = 0
    max_possible_score = len(submission.answers) * 10  # Each question is worth 10 points
    
    for answer in submission.answers:
        # Evaluate the answer based on its type
        if answer.get("type") == "mcq":
            # For MCQs, check if the answer matches exactly
            is_correct = answer.get("user_answer", "") == answer.get("correct_answer", "")
            score = 10 if is_correct else 0
            
            results.append({
                "question": answer.get("question"),
                "user_answer": answer.get("user_answer"),
                "correct_answer": answer.get("correct_answer"),
                "score": score,
                "feedback": "Correct!" if is_correct else "Incorrect. The correct answer is: " + answer.get("correct_answer", "")
            })
            
            total_score += score
        else:  # short_answer
            # For short answers, check for key points
            user_answer = answer.get("user_answer", "").lower()
            key_points = answer.get("key_points", [])
            matched_points = [point for point in key_points if point.lower() in user_answer]
            
            # Calculate score based on percentage of key points covered
            point_score = len(matched_points) / len(key_points) if key_points else 0
            score = round(point_score * 10)
            
            results.append({
                "question": answer.get("question"),
                "user_answer": answer.get("user_answer"),
                "score": score,
                "feedback": f"You covered {len(matched_points)} out of {len(key_points)} key points.",
                "key_points_covered": matched_points,
                "key_points_missed": [point for point in key_points if point.lower() not in user_answer]
            })
            
            total_score += score
    
    # Calculate overall percentage
    percentage = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0
    
    return {
        "exam_id": submission.exam_id,
        "results": results,
        "summary": {
            "total_score": total_score,
            "max_possible_score": max_possible_score,
            "percentage": round(percentage, 2),
            "pass": percentage >= 70,  # Consider 70% as passing score
            "grade": "A" if percentage >= 90 else "B" if percentage >= 80 else "C" if percentage >= 70 else "D" if percentage >= 60 else "F"
        }
    }


@router.post("/evaluate-assessment")
async def evaluate_assessment(
    submission: BatchAnswerSubmission,
    db: Session = Depends(get_db)
):
    """Evaluate all answers in a skill assessment"""
    # Get the current user from the database
    if isinstance(current_user, dict):
        user = db.query(User).filter(User.id == current_user["id"]).first()
    else:
        user = current_user
        
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    results = []
    total_score = 0
    max_possible_score = 0
    
    for qa_pair in submission.questions_and_answers:
        # Evaluate each answer
        evaluation = SkillAssessment.evaluate_answer(qa_pair.question, qa_pair.answer)
        
        result = {
            "question": qa_pair.question["question"],
            "user_answer": qa_pair.answer,
            "evaluation": evaluation
        }
        
        results.append(result)
        
        # Calculate scores for summary
        if qa_pair.question["type"] == "mcq":
            max_possible_score += 10
            if evaluation.get("is_correct", False):
                total_score += 10
        else:  # short_answer
            max_possible_score += 10
            total_score += evaluation.get("score", 0)
    
    # Calculate overall percentage
    percentage = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0
    
    return {
        "results": results,
        "summary": {
            "total_score": total_score,
            "max_possible_score": max_possible_score,
            "percentage": round(percentage, 2),
            "pass": percentage >= 70  # Consider 70% as passing score
        }
    }
    