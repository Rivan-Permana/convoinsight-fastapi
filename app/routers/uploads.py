from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.core.config import settings
from app.services.gcs import GCSClient

router = APIRouter(prefix="/uploads", tags=["uploads"])

class SignURLRequest(BaseModel):
    filename: str
    content_type: str

@router.post("/sign-url")
def sign_url(req: SignURLRequest):
    gcs = GCSClient(settings.GCS_BUCKET)
    blob_name = f"{settings.GCS_DATASETS_PREFIX}{req.filename}"
    url = gcs.sign_url_v4(blob_name=blob_name, content_type=req.content_type, method="PUT")
    return {"upload_url": url, "blob_name": blob_name, "gcs_uri": f"gs://{settings.GCS_BUCKET}/{blob_name}"}
