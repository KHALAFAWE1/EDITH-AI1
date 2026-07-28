from fastapi import APIRouter
from app.services.vision import analyze_scene

router = APIRouter(
    prefix="/vision",
    tags=["Vision"]
)


@router.get("/analyze")
def analyze():

    return analyze_scene()