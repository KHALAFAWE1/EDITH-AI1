import os
import cv2
import insightface

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.person import Person
from app.models.face_embedding import FaceEmbedding

face_app = insightface.app.FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=-1, det_size=(640, 640))

PEOPLE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "uploads",
        "people"
    )
)

db: Session = SessionLocal()

people = db.query(Person).all()

print("=" * 60)
print("Building Face Embeddings")
print("=" * 60)

for person in people:

    folder = os.path.join(
        PEOPLE_DIR,
        person.full_name
    )

    if not os.path.exists(folder):
        print(f"Folder not found -> {person.full_name}")
        continue

    db.query(FaceEmbedding).filter(
        FaceEmbedding.person_id == person.id
    ).delete()

    images = [
        f for f in os.listdir(folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    images = images[:5]

    loaded = 0

    for image_name in images:

        image_path = os.path.join(folder, image_name)

        image = cv2.imread(image_path)

        if image is None:
            continue

        faces = face_app.get(image)

        if len(faces) == 0:
            print(f"No face -> {image_name}")
            continue

        embedding = faces[0].embedding.tolist()

        db.add(
            FaceEmbedding(
                person_id=person.id,
                embedding=str(embedding)
            )
        )

        loaded += 1

        print(f"Loaded -> {image_name}")

    db.commit()

    print(f"Saved {loaded} embeddings for {person.full_name}")

db.close()

print("=" * 60)
print("Finished Successfully")
print("=" * 60)