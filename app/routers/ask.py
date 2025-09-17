from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
import pandas as pd
from urllib.parse import unquote
from app.core.config import settings
from app.services.gcs import GCSClient
from app.services.pipeline_runner import InferenceEngine
from app.utils.sse import sse_event

router = APIRouter(prefix="/ask", tags=["ask"])

gcs = GCSClient(settings.GCS_BUCKET)
engine = InferenceEngine(
    model=settings.LLM_MODEL,
    api_key=(settings.GEMINI_API_KEY),
    pipeline_path=settings.PIPELINE_PATH
)

@router.get("/stream")
def ask_stream(gcs_uri: str, q: str):
    """
    SSE endpoint (GET) agar gampang dipakai FE (EventSource).
    Param:
      - gcs_uri (contoh: gs://<bucket>/datasets/<filename>.csv) ATAU dataset_id (= path di bucket)
      - q (pertanyaan user)
    """
    bucket_prefix = f"gs://{settings.GCS_BUCKET}/"
    if gcs_uri.startswith(bucket_prefix):
        blob_name = gcs_uri[len(bucket_prefix):]
    else:
        blob_name = gcs_uri  # kalau user kirim dataset_id langsung

    def _gen():
        # Step 0: status
        yield sse_event("status", {"stage": "load", "message": "Loading dataset from GCS..."})
        # Load dataframe
        df, _ = gcs.head_csv(blob_name, n=1000000)  # load all for analysis (MVP)
        yield sse_event("status", {"stage": "orchestrate", "message": "Planning with Orchestrator..."})

        # Jalankan engine
        result = engine.infer(df, q)

        # Kirim chart (kalau ada)
        chart_url = None
        if result.get("chart_html"):
            # Simpan sebagai HTML ke GCS
            html_bytes = result["chart_html"].encode("utf-8", errors="ignore")
            chart_blob = f'{settings.GCS_CHARTS_PREFIX}chart_{abs(hash(q))}.html'
            chart_gs = gcs.upload_bytes(chart_blob, html_bytes, content_type="text/html", make_public=True)
            # kalau make_public=True -> public_url, kalau tidak -> gs://
            chart_url = chart_gs

        # Stream compiled text (simulate streaming potong kalimat)
        compiled = result.get("compiled", "")
        yield sse_event("status", {"stage": "stream", "message": "Streaming answer..."})
        chunk = 40
        for i in range(0, len(compiled), chunk):
            yield sse_event("answer", {"text": compiled[i:i+chunk]})

        # Final meta untuk FE simpan ke Firebase (historysidebar/usechathistory)
        yield sse_event("meta", {
            "question": q,
            "chart_url": chart_url,
            "plan": result.get("plan", {}),
        })
        yield sse_event("done", {"ok": True})

    return StreamingResponse(_gen(), media_type="text/event-stream")
