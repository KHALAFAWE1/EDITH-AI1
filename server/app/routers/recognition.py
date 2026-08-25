import os
import shutil
import uuid

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.recognition import recognize_all_faces

router = APIRouter(
    prefix="/recognition",
    tags=["Recognition"]
)

UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "temp")
)
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/identify")
async def identify_person(
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    التعرف على الوجوه الظاهرة في الصورة مع دعم الوجوه المتعددة والـ Bounding Boxes
    """
    # توليد اسم ملف مؤقت فريد لمنع تصادم الطلبات المتزامنة
    file_ext = os.path.splitext(photo.filename)[1] or ".jpg"
    unique_filename = f"capture_{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    try:
        face_results = recognize_all_faces(file_path, db)
    finally:
        # حذف الصورة المؤقتة فوراً لتوفير مساحة التخزين
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

    # لم يتم اكتشاف أي وجه في الصورة
    if not face_results:
        return {
            "found": False,
            "message": "No face detected",
            "faces_count": 0,
            "faces": []
        }

    # اختيار الوجه الأساسي (أكبر وجه أو الأعلى تطابقاً)
    primary = face_results[0]

    return {
        "found": primary["found"],
        "score": primary["score"],
        "confidence": primary["confidence"],
        "bbox": primary["bbox"],
        "age": primary.get("age"),
        "gender": primary.get("gender"),
        "person": primary.get("person"),
        "faces_count": len(face_results),
        "faces": face_results
    }