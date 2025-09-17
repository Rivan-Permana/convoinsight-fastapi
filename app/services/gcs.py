import io
import json
import time
import base64
from typing import Optional, List, Tuple
from google.cloud import storage
from google.oauth2 import service_account
import pandas as pd

class GCSClient:
    def __init__(self, bucket: str):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket)

    def sign_url_v4(self, blob_name: str, content_type: str, method: str = "PUT", expires: int = 15*60) -> str:
        blob = self.bucket.blob(blob_name)
        return blob.generate_signed_url(
            version="v4",
            expiration=expires,
            method=method,
            content_type=content_type,
        )

    def list_prefix(self, prefix: str, max_results: int = 100) -> List[str]:
        return [b.name for b in self.client.list_blobs(self.bucket.name, prefix=prefix, max_results=max_results)]

    def head_csv(self, blob_name: str, n: int = 20) -> Tuple[pd.DataFrame, dict]:
        blob = self.bucket.blob(blob_name)
        content = blob.download_as_bytes()
        buf = io.BytesIO(content)
        df = pd.read_csv(buf)
        schema = {c: str(t) for c, t in zip(df.columns, df.dtypes)}
        return df.head(n), schema

    def upload_bytes(self, blob_name: str, content: bytes, content_type: str = "text/html", make_public: bool = False) -> str:
        blob = self.bucket.blob(blob_name)
        blob.upload_from_string(content, content_type=content_type)
        if make_public:
            blob.make_public()
            return blob.public_url
        return f"gs://{self.bucket.name}/{blob_name}"

    def upload_file(self, local_path: str, blob_name: str, content_type: Optional[str] = None, make_public: bool = False) -> str:
        blob = self.bucket.blob(blob_name)
        blob.upload_from_filename(local_path, content_type=content_type)
        if make_public:
            blob.make_public()
            return blob.public_url
        return f"gs://{self.bucket.name}/{blob_name}"
