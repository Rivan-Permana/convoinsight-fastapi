from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
from app.services.gcs import GCSClient

router = APIRouter(prefix="/datasets", tags=["datasets"])
gcs = GCSClient(settings.GCS_BUCKET)

class RegisterDataset(BaseModel):
    gcs_uri: str
    display_name: Optional[str] = None
    size_bytes: Optional[int] = None

@router.post("")
def register_dataset(body: RegisterDataset):
    # MVP: backend tidak menyimpan DB. FE simpan ke Firebase.
    # Kita kembalikan dataset_id deterministik dari blob path.
    if not body.gcs_uri.startswith("gs://"):
        raise HTTPException(400, "gcs_uri invalid")
    bucket = settings.GCS_BUCKET
    prefix = f"gs://{bucket}/"
    if not body.gcs_uri.startswith(prefix):
        raise HTTPException(400, f"gcs_uri bucket harus {prefix}")
    dataset_id = body.gcs_uri[len(prefix):]
    return {"dataset_id": dataset_id, "display_name": body.display_name or dataset_id, "gcs_uri": body.gcs_uri}

@router.get("")
def list_datasets():
    names = gcs.list_prefix(settings.GCS_DATASETS_PREFIX)
    return {"items": names}

@router.get("/{dataset_id}/preview")
def preview_dataset(dataset_id: str, limit: int = Query(20, ge=5, le=200)):
    df, schema = gcs.head_csv(dataset_id, n=limit)
    return {
        "schema": schema,
        "rows": df.to_dict(orient="records"),
        "row_count": len(df),
    }
