import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ConvoInsight API"
    VERSION: str = "0.1.0"

    # GCP
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    GCS_BUCKET: str = os.getenv("GCS_BUCKET", "convoinsight-assets")
    GCS_DATASETS_PREFIX: str = os.getenv("GCS_DATASETS_PREFIX", "datasets/")
    GCS_CHARTS_PREFIX: str = os.getenv("GCS_CHARTS_PREFIX", "charts/")

    # LLM via LiteLLM ('gemini/gemini-2.5-pro')
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini/gemini-2.5-pro")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Path ke file pipeline (harus sama namanya)
    PIPELINE_PATH: str = os.getenv(
        "PIPELINE_PATH",
        "pipeline/4th_copy_of_ml_bi_pipeline_a0_0_5.py"
    )

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",  # Vite
        "http://localhost:3000",
        os.getenv("FE_ORIGIN", "")
    ]

settings = Settings()
