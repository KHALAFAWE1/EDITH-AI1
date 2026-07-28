import os
import shutil

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.person import Person

router = APIRouter(
    prefix="/people",
    tags=["People"]
)

UPLOAD_DIR = "faces"

os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def get_people(db: Session = Depends(get_db)):
    return db.query(Person).all()


@router.post("/register")
async def register_person(
    full_name: str = Form(...),
    person_type: str = Form("Student"),
    department: str = Form(""),
    position: str = Form(""),
    subjects: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    office: str = Form(""),
    notes: str = Form(""),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    file_path = os.path.join(
        UPLOAD_DIR,
        photo.filename
    )

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    person = Person(
        full_name=full_name,
        person_type=person_type,
        department=department,
        position=position,
        subjects=subjects,
        phone=phone,
        email=email,
        office=office,
        notes=notes,
        photo_path=file_path
    )

    db.add(person)
    db.commit()
    db.refresh(person)

    return person