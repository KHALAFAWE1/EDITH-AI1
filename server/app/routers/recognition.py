import logging
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.recognition import recognize_all_faces

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recognition", tags=["Recognition"])

UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "temp")
)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# الأنواع المسموحة فقط، والامتداد بنحدده احنا مش اسم الملف اللي بيبعته المستخدم
ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 ميجا


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _face_area(face: dict) -> int:
    box = face.get("bbox") or {}
    return box.get("width", 0) * box.get("height", 0)


# def عادية (مش async) عشان FastAPI يشغّلها في thread منفصل ومتوقفش السيرفر
@router.post("/identify")
def identify_person(
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ext = ALLOWED_TYPES.get(photo.content_type)
    if ext is None:
        raise HTTPException(status_code=415, detail="Unsupported image type. Use JPEG, PNG or WEBP.")

    data = photo.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large (max 5 MB).")

    file_path = os.path.join(UPLOAD_DIR, f"capture_{uuid.uuid4().hex}{ext}")
    with open(file_path, "wb") as buffer:
        buffer.write(data)

    try:
        face_results = recognize_all_faces(file_path, db)
    except Exception:
        logger.exception("Face recognition failed")
        raise HTTPException(status_code=500, detail="Face recognition failed.")
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass

    if not face_results:
        return {
            "found": False,
            "message": "No face detected",
            "faces_count": 0,
            "faces": [],
        }

    # الوجه الأساسي = أكبر وجه في الصورة
    face_results.sort(key=_face_area, reverse=True)
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
        "faces": face_results,
    }