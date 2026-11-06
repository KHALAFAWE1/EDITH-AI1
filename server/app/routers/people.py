import os
import re
import uuid
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
    tags=["People & Biometric Registry"]
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


def _safe_folder_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", name.strip())
    return cleaned or "person"


def _serialize_person(p: Person) -> dict:
    return {
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
    }


@router.get("")
@router.get("/")
def get_people(db: Session = Depends(get_db)):
    """جلب جميع الأشخاص المسجلين في النظام مع عدد بصمات الوجه الخاصة بهم"""
    people = db.query(Person).all()
    return [_serialize_person(p) for p in people]


@router.get("/{person_id}")
def get_person_by_id(person_id: int, db: Session = Depends(get_db)):
    """جلب بيانات شخص محدد بواسطة المعرف ID"""
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    return _serialize_person(person)


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
    """تسجيل شخص جديد واستخراج بصمة الوجه (512D ArcFace) وتخزينها في قاعدة البيانات"""
    person_name_clean = full_name.strip()
    if not person_name_clean:
        raise HTTPException(status_code=400, detail="Full name is required.")

    folder_slug = _safe_folder_name(person_name_clean)
    person_dir = os.path.join(BASE_UPLOAD_DIR, folder_slug)
    os.makedirs(person_dir, exist_ok=True)

    ext = os.path.splitext(photo.filename or "face.jpg")[1] or ".jpg"
    safe_filename = f"face_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(person_dir, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    face_data = get_face_embedding(file_path)

    if face_data is None:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لم يتم اكتشاف أي وجه واضح في الصورة المرفوعة. يرجى اختيار صورة واضحة الملامح."
        )

    relative_photo_path = f"uploads/people/{folder_slug}/{safe_filename}"

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
    db.refresh(new_person)

    invalidate_embeddings_cache()

    return {
        "success": True,
        "message": f"تم تسجيل {new_person.full_name} بنجاح وحفظ بصمة الوجه البيومترية.",
        "person": _serialize_person(new_person)
    }


@router.put("/{person_id}")
async def update_person(
    person_id: int,
    full_name: str = Form(...),
    person_type: str = Form("Student"),
    department: str = Form(""),
    position: str = Form(""),
    subjects: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    office: str = Form(""),
    notes: str = Form(""),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """تحديث بيانات شخص مسجل مع إمكانية تحديث صورته الشخصية وإضافة بصمة وجه جديدة"""
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    person_name_clean = full_name.strip()
    if not person_name_clean:
        raise HTTPException(status_code=400, detail="Full name cannot be empty.")

    person.full_name = person_name_clean
    person.person_type = person_type.strip()
    person.department = department.strip()
    person.position = position.strip()
    person.subjects = subjects.strip()
    person.phone = phone.strip()
    person.email = email.strip()
    person.office = office.strip()
    person.notes = notes.strip()

    if photo and photo.filename:
        folder_slug = _safe_folder_name(person_name_clean)
        person_dir = os.path.join(BASE_UPLOAD_DIR, folder_slug)
        os.makedirs(person_dir, exist_ok=True)

        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        safe_filename = f"face_{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(person_dir, safe_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

        face_data = get_face_embedding(file_path)
        if face_data is None:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لم يتم اكتشاف وجه واضح في الصورة الجديدة. لم يتم تغيير الصورة."
            )

        person.photo_path = f"uploads/people/{folder_slug}/{safe_filename}"
        new_emb = FaceEmbedding(
            person_id=person.id,
            embedding=str(face_data["embedding"])
        )
        db.add(new_emb)

    db.commit()
    db.refresh(person)
    invalidate_embeddings_cache()

    return {
        "success": True,
        "message": f"تم تحديث بيانات {person.full_name} بنجاح.",
        "person": _serialize_person(person)
    }


@router.post("/{person_id}/photos")
async def add_person_face_photo(
    person_id: int,
    set_as_primary: bool = Form(False),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """إضافة صورة وجه إضافية لشخص مسجل لتعزيز دقة المطابقة من زوايا وإضاءات متعددة"""
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    folder_slug = _safe_folder_name(person.full_name)
    person_dir = os.path.join(BASE_UPLOAD_DIR, folder_slug)
    os.makedirs(person_dir, exist_ok=True)

    ext = os.path.splitext(photo.filename or "angle.jpg")[1] or ".jpg"
    safe_filename = f"angle_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(person_dir, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    face_data = get_face_embedding(file_path)
    if face_data is None:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لم يتم اكتشاف أي وجه واضح في الصورة المضافة. يرجى رفع صورة واضحة للوجه."
        )

    new_embedding = FaceEmbedding(
        person_id=person.id,
        embedding=str(face_data["embedding"])
    )
    db.add(new_embedding)

    if set_as_primary or not person.photo_path:
        person.photo_path = f"uploads/people/{folder_slug}/{safe_filename}"

    db.commit()
    db.refresh(person)
    invalidate_embeddings_cache()

    return {
        "success": True,
        "message": f"تم إضافة بصمة وجه جديدة لـ {person.full_name} (إجمالي البصمات: {len(person.embeddings)}).",
        "embeddings_count": len(person.embeddings),
        "person": _serialize_person(person)
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

    for folder_candidate in [person.full_name, _safe_folder_name(person.full_name)]:
        person_dir = os.path.join(BASE_UPLOAD_DIR, folder_candidate)
        if os.path.exists(person_dir):
            try:
                shutil.rmtree(person_dir)
            except Exception:
                pass

    db.delete(person)
    db.commit()

    invalidate_embeddings_cache()

    return {
        "success": True,
        "message": f"تم حذف {person.full_name} وبصماته البيومترية بنجاح."
    }
