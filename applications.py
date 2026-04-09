from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import Application, Job
from jobs import get_current_user

router = APIRouter(prefix="/applications", tags=["Applications"])

class ApplicationRequest(BaseModel):
    job_id: int
    cover_letter: str

@router.post("/")
def apply_for_job(req: ApplicationRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.owner_id == user_id:
        raise HTTPException(status_code=400, detail="You cannot apply to your own job")
    existing = db.query(Application).filter(
        Application.job_id == req.job_id,
        Application.applicant_id == user_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already applied for this job")
    application = Application(
        job_id=req.job_id,
        applicant_id=user_id,
        cover_letter=req.cover_letter
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return {"message": "Applied successfully", "application_id": application.id}

@router.get("/job/{job_id}")
def get_applications_for_job(job_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    applications = db.query(Application).filter(Application.job_id == job_id).all()
    return applications

@router.get("/my")
def my_applications(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    applications = db.query(Application).filter(Application.applicant_id == user_id).all()
    return applications