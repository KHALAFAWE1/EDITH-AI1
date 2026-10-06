import os
import shutil
import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from app.services.vision import (
    analyze_scene,
    analyze_image_file,
    detect_objects_in_image,
    ocr_read_document,
    structured_scene_understanding
)

router = APIRouter(
    prefix="/vision",
    tags=["Multi-Modal Vision, OCR & Object Intelligence"]
)

TEMP_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "temp")
)
os.makedirs(TEMP_DIR, exist_ok=True)


def _save_temp_upload(photo: UploadFile) -> str:
    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    unique_name = f"vision_{uuid.uuid4().hex}{ext}"
    path = os.path.join(TEMP_DIR, unique_name)
    with open(path, "wb") as f:
        shutil.copyfileobj(photo.file, f)
    return path


@router.get("/analyze")
def analyze():
    """التقاط لقطة مباشرة من الكاميرا المتصلة بالسيرفر وتحليلها"""
    return analyze_scene()


@router.post("/analyze-image")
async def analyze_uploaded_image(
    photo: UploadFile = File(...),
    prompt: str = Form("قم بوصف محتويات هذه الصورة بالتفصيل واشرح ما تراه باللغة العربية.")
):
    """تحليل صورة مرفوعة بالذكاء الاصطناعي البصري"""
    path = _save_temp_upload(photo)
    try:
        res = analyze_image_file(path, prompt)
        return res
    finally:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


@router.post("/detect-objects")
async def detect_objects(photo: UploadFile = File(...)):
    """اكتشاف وتصنيف الكائنات والأجهزة في الصورة (Objects Detection)"""
    path = _save_temp_upload(photo)
    try:
        return detect_objects_in_image(path)
    finally:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


@router.post("/ocr")
async def read_document_ocr(photo: UploadFile = File(...)):
    """قراءة النصوص والمستندات واللافتات وأرقام الأجهزة (OCR Document Intelligence)"""
    path = _save_temp_upload(photo)
    try:
        return ocr_read_document(path)
    finally:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


@router.post("/scene-understanding")
async def get_scene_understanding(photo: UploadFile = File(...)):
    """تحليل المشهد التكتيكي واستخراج بنية أمنية مهيكلة (Scene, People, Objects, Anomalies, Risk)"""
    path = _save_temp_upload(photo)
    try:
        return structured_scene_understanding(path)
    finally:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass