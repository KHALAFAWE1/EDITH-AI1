import ast
import numpy as np
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.person import Person
from app.models.face_embedding import FaceEmbedding
from app.services.face_service import get_all_faces, get_face_embedding

# الحد الأدنى للتشابه لتأكيد هوية الشخص (Cosine Similarity Threshold)
SIMILARITY_THRESHOLD = 0.70

# ذاكرة تخزين مؤقت للـ Embeddings لتفادي استدعاء قاعدة البيانات مع كل لقطة كاميرا
_EMBEDDING_CACHE = {
    "is_valid": False,
    "embeddings": [],      # مصفوفة الـ embeddings المطبّعة (N x 512)
    "person_records": []   # بيانات كل شخص مرتبطة بالـ embedding
}


def invalidate_embeddings_cache():
    """إلغاء صلاحية الكاش لإعادة تحميله عند إضافة أو تعديل أو حذف شخص"""
    global _EMBEDDING_CACHE
    _EMBEDDING_CACHE["is_valid"] = False


def _load_cache(db: Session):
    """تحميل جميع بصمات الوجوه وتجهيز مصفوفة NumPy للمطابقة السريعة"""
    global _EMBEDDING_CACHE

    people = db.query(Person).all()
    emb_list = []
    records = []

    for person in people:
        for emb_obj in person.embeddings:
            try:
                raw_emb = ast.literal_eval(emb_obj.embedding)
                vec = np.array(raw_emb, dtype=np.float32).flatten()
                if vec.shape[0] != 512:
                    print(f"[TARS Biometric Cache] Skipping embedding with non-512 dimension ({vec.shape[0]}) for {person.full_name}")
                    continue
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm  # تطبيع المتجه (L2 normalization)
                    emb_list.append(vec)
                    records.append({
                        "person_id": person.id,
                        "id": person.id,
                        "full_name": person.full_name,
                        "person_type": person.person_type,
                        "department": person.department,
                        "position": person.position,
                        "subjects": person.subjects,
                        "phone": person.phone,
                        "email": person.email,
                        "office": person.office,
                        "notes": person.notes,
                        "photo_path": person.photo_path,
                        "embeddings_count": len(person.embeddings)
                    })
            except Exception as e:
                print(f"[TARS Biometric Cache Warning] Error parsing embedding for person {person.full_name}: {e}")

    if len(emb_list) > 0:
        _EMBEDDING_CACHE["embeddings"] = np.vstack(emb_list)
    else:
        _EMBEDDING_CACHE["embeddings"] = np.empty((0, 512), dtype=np.float32)

    _EMBEDDING_CACHE["person_records"] = records
    _EMBEDDING_CACHE["is_valid"] = True


def recognize_person(image_path: str, db: Session) -> Optional[Dict[str, Any]]:
    """التعرف على الوجه الرئيسي في الصورة بأقصى سرعة"""
    all_results = recognize_all_faces(image_path, db)
    if not all_results:
        return None
    return all_results[0]


def recognize_all_faces(image_path: str, db: Session) -> List[Dict[str, Any]]:
    """اكتشاف والتعرف على جميع الوجوه الظاهرة في الصورة (Multi-Face Tracking)"""
    global _EMBEDDING_CACHE

    faces = get_all_faces(image_path)
    if not faces:
        return []

    if not _EMBEDDING_CACHE["is_valid"]:
        _load_cache(db)

    cached_matrix = _EMBEDDING_CACHE["embeddings"]
    records = _EMBEDDING_CACHE["person_records"]

    results = []

    for face in faces:
        query_vec = np.array(face["embedding"], dtype=np.float32).flatten()
        if query_vec.shape[0] != 512:
            continue
        q_norm = np.linalg.norm(query_vec)
        if q_norm > 0:
            query_vec = query_vec / q_norm

        best_score = 0.0
        best_person = None

        if len(cached_matrix) > 0:
            similarities = np.dot(cached_matrix, query_vec)
            max_idx = int(np.argmax(similarities))
            best_score = float(similarities[max_idx])

            if best_score >= SIMILARITY_THRESHOLD:
                best_person = records[max_idx]

        if best_score >= 0.82:
            confidence = "High"
        elif best_score >= SIMILARITY_THRESHOLD:
            confidence = "Medium"
        else:
            confidence = "Low"

        results.append({
            "found": best_person is not None,
            "score": round(best_score, 4),
            "confidence": confidence,
            "bbox": face["bbox"],
            "age": face.get("age"),
            "gender": face.get("gender"),
            "det_score": face.get("det_score"),
            "person": best_person
        })

    return results
