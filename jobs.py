from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import Job
from auth import SECRET_KEY, ALGORITHM
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/jobs", tags=["Jobs"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class JobRequest(BaseModel):
    title: str
    description: str
    budget: float
    category: str

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return int(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/")
def create_job(req: JobRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    job = Job(
        title=req.title,
        description=req.description,
        budget=req.budget,
        category=req.category,
        owner_id=user_id
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"message": "Job posted successfully", "job_id": job.id}

@router.get("/")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).all()
    return jobs

@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job