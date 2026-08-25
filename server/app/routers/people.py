import os
import shutil
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.person import Person
from app.models.face_embedding import FaceEmbedding
from app.services.face_service import get_face_embedding
from app.services.recognition import invalidate_embeddings_cache

router = APIRouter(
    prefix="/people",
    tags=["People"]
)

# مسار حفظ الصور الخاص بالأشخاص
BASE_UPLOAD_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "uploads",
        "people"
    )
)
os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def get_people(db: Session = Depends(get_db)):
    """جلب جميع الأشخاص المسجلين في النظام مع عدد بصمات الوجه الخاصة بهم"""
    people = db.query(Person).all()
    result = []
    for p in people:
        result.append({
            "id": p.id,
            "full_name": p.full_name,
            "person_type": p.person_type,
            "department": p.department,
            "position": p.position,
            "subjects": p.subjects,
            "phone": p.phone,
            "email": p.email,
            "office": p.office,
            "photo_path": p.photo_path,
            "notes": p.notes,
            "created_at": p.created_at,
            "embeddings_count": len(p.embeddings) if p.embeddings else 0
        })
    return result


@router.get("/{person_id}")
def get_person_by_id(person_id: int, db: Session = Depends(get_db)):
    """جلب بيانات شخص محدد بواسطة المعرف ID"""
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    return {
        "id": person.id,
        "full_name": person.full_name,
        "person_type": person.person_type,
        "department": person.department,
        "position": person.position,
        "subjects": person.subjects,
        "phone": person.phone,
        "email": person.email,
        "office": person.office,
        "photo_path": person.photo_path,
        "notes": person.notes,
        "created_at": person.created_at,
        "embeddings_count": len(person.embeddings) if person.embeddings else 0
    }


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
    """تسجيل شخص جديد واستخراج بصمة الوجه وتخزينها في قاعدة البيانات"""

    person_name_clean = full_name.strip()
    person_dir = os.path.join(BASE_UPLOAD_DIR, person_name_clean)
    os.makedirs(person_dir, exist_ok=True)

    file_path = os.path.join(person_dir, photo.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    face_data = get_face_embedding(file_path)

    if face_data is None:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لم يتم اكتشاف أي وجه في الصورة المرفوعة. يرجى اختيار صورة واضحة الملامح."
        )

    relative_photo_path = f"uploads/people/{person_name_clean}/{photo.filename}"

    new_person = Person(
        full_name=person_name_clean,
        person_type=person_type.strip(),
        department=department.strip(),
        position=position.strip(),
        subjects=subjects.strip(),
        phone=phone.strip(),
        email=email.strip(),
        office=office.strip(),
        notes=notes.strip(),
        photo_path=relative_photo_path
    )

    db.add(new_person)
    db.commit()
    db.refresh(new_person)

    new_embedding = FaceEmbedding(
        person_id=new_person.id,
        embedding=str(face_data["embedding"])
    )

    db.add(new_embedding)
    db.commit()

    # تحديث كاش الوجوه تلقائياً
    invalidate_embeddings_cache()

    return {
        "success": True,
        "message": f"تم تسجيل {new_person.full_name} بنجاح وحفظ بصمة الوجه.",
        "person": {
            "id": new_person.id,
            "full_name": new_person.full_name,
            "person_type": new_person.person_type,
            "department": new_person.department,
            "position": new_person.position,
            "phone": new_person.phone,
            "email": new_person.email,
            "photo_path": new_person.photo_path
        }
    }


@router.delete("/{person_id}")
def delete_person(person_id: int, db: Session = Depends(get_db)):
    """حذف شخص وجميع بصمات وجهه ومجلده من النظام"""
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )

    person_dir = os.path.join(BASE_UPLOAD_DIR, person.full_name)
    if os.path.exists(person_dir):
        try:
            shutil.rmtree(person_dir)
        except Exception:
            pass

    db.delete(person)
    db.commit()

    # تحديث كاش الوجوه تلقائياً
    invalidate_embeddings_cache()

    return {
        "success": True,
        "message": f"تم حذف الشخص {person.full_name} وبصماته بنجاح."
    }