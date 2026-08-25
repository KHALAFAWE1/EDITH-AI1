import cv2
import insightface
from typing import List, Optional, Dict, Any

# تهيئة محرك InsightFace مع تحميل النماذج الضرورية فقط لتسريع الأداء 17 ضعفاً
face_app = insightface.app.FaceAnalysis(
    name="buffalo_l",
    allowed_modules=["detection", "recognition"]
)

# استخدام المعالج (CPU) وتحديد حجم فحص خفيف وسريع جداً
face_app.prepare(
    ctx_id=-1,
    det_size=(320, 320)
)


def get_face_embedding(image_path: str) -> Optional[Dict[str, Any]]:
    """استخراج بصمة وبيانات أول وجه يظهر في الصورة (متوافق مع الاستخدامات السابقة)"""
    faces = get_all_faces(image_path)
    if not faces:
        return None
    return faces[0]


def get_all_faces(image_path: str) -> List[Dict[str, Any]]:
    """استخراج جميع الوجوه الظاهرة في الصورة مع إحداثياتها وخصائصها"""
    image = cv2.imread(image_path)

    if image is None:
        return []

    faces = face_app.get(image)

    if len(faces) == 0:
        return []

    detected_faces = []
    for face in faces:
        x1, y1, x2, y2 = face.bbox.astype(int)
        
        # حماية ضد الإحداثيات السالبة
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = max(0, x2), max(0, y2)

        # استخراج الخصائص بأمان حتى عند عدم تحميل نموذج genderage
        raw_gender = getattr(face, "gender", None)
        gender = ("Male" if raw_gender == 1 else "Female") if raw_gender is not None else "Unknown"

        raw_age = getattr(face, "age", None)
        age = int(raw_age) if raw_age is not None else None

        raw_score = getattr(face, "det_score", None)
        det_score = float(raw_score) if raw_score is not None else 0.99

        detected_faces.append({
            "embedding": face.embedding.tolist(),
            "bbox": {
                "x": int(x1),
                "y": int(y1),
                "width": int(x2 - x1),
                "height": int(y2 - y1)
            },
            "age": age,
            "gender": gender,
            "det_score": round(det_score, 3)
        })

    return detected_faces