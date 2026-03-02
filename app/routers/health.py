from fastapi import APIRouter

router = APIRouter()

@router.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"ok": True}
