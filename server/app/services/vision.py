import cv2
import os
import ollama

OUTPUT_FOLDER = "captures"


def analyze_scene():

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        return {
            "success": False,
            "message": "Camera not found"
        }

    success, frame = camera.read()

    camera.release()

    if not success:
        return {
            "success": False,
            "message": "Cannot capture image"
        }

    image_path = os.path.join(
        OUTPUT_FOLDER,
        "capture.jpg"
    )

    cv2.imwrite(image_path, frame)

    response = ollama.chat(
        model="moondream",
        messages=[
            {
                "role": "user",
                "content": "Describe everything you see in this image.",
                "images": [image_path]
            }
        ]
    )

    return {
        "success": True,
        "image": image_path,
        "description": response["message"]["content"]
    }