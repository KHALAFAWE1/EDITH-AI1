from fastapi import APIRouter

router = APIRouter(
    prefix="/devices",
    tags=["Devices"]
)


@router.get("/")
def get_devices():
    return {
        "message": "EDITH AI Device API is working"
    }