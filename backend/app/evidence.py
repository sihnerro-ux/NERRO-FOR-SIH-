from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import os
from pathlib import Path
import re
from uuid import uuid4

from sqlalchemy import select

from app.db.database import BACKEND_DIR, SessionLocal
from app.db.tables import EvidenceRow


MAX_EVIDENCE_BYTES = 1_500_000
DATA_URL_PATTERN = re.compile(r"^data:(image/(?:jpeg|png|webp));base64,(.+)$", re.DOTALL)
EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _matches_image_signature(content_type: str, content: bytes) -> bool:
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    return len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"


@dataclass(frozen=True)
class EvidenceObject:
    id: str
    content_type: str
    content: bytes


class EvidenceStorage:
    def __init__(self) -> None:
        self.endpoint = os.getenv("S3_ENDPOINT")
        self.bucket = os.getenv("S3_BUCKET", "ner-field-evidence")
        self.local_directory = Path(os.getenv("EVIDENCE_LOCAL_DIR", BACKEND_DIR / "data" / "evidence"))

    def _client(self):
        if not self.endpoint:
            return None
        import boto3
        from botocore.config import Config

        endpoint = self.endpoint
        if "://" not in endpoint:
            scheme = "https" if os.getenv("S3_SECURE", "false").lower() == "true" else "http"
            endpoint = f"{scheme}://{endpoint}"
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=os.getenv("S3_ACCESS_KEY", ""),
            aws_secret_access_key=os.getenv("S3_SECRET_KEY", ""),
            region_name=os.getenv("S3_REGION", "us-east-1"),
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": os.getenv("S3_ADDRESSING_STYLE", "path")},
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        )

    def _ensure_bucket(self, client) -> None:
        if os.getenv("S3_AUTO_CREATE_BUCKET", "true").lower() != "true":
            return
        from botocore.exceptions import ClientError

        try:
            client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            if str(exc.response.get("Error", {}).get("Code")) not in {"404", "NoSuchBucket", "NotFound"}:
                raise
            region = os.getenv("S3_REGION", "us-east-1")
            options = {} if region == "us-east-1" else {"CreateBucketConfiguration": {"LocationConstraint": region}}
            client.create_bucket(Bucket=self.bucket, **options)

    @staticmethod
    def _decode(data_url: str) -> tuple[str, bytes]:
        match = DATA_URL_PATTERN.fullmatch(data_url)
        if not match:
            raise ValueError("Evidence must be a JPEG, PNG or WebP image.")
        try:
            content = base64.b64decode(match.group(2), validate=True)
        except ValueError as exc:
            raise ValueError("Evidence image encoding is invalid.") from exc
        if not content or len(content) > MAX_EVIDENCE_BYTES:
            raise ValueError("Evidence image must be between 1 byte and 1.5 MB.")
        if not _matches_image_signature(match.group(1), content):
            raise ValueError("Evidence content does not match its declared image type.")
        return match.group(1), content

    def save(self, data_url: str, uploaded_by: str, client_report_id: str | None) -> str:
        if client_report_id:
            with SessionLocal() as session:
                existing = session.scalar(select(EvidenceRow).where(EvidenceRow.client_report_id == client_report_id))
                if existing:
                    return existing.id

        content_type, content = self._decode(data_url)
        evidence_id = f"EVD-{uuid4()}"
        date_path = datetime.now(UTC).strftime("%Y/%m/%d")
        object_key = f"{date_path}/{evidence_id}.{EXTENSIONS[content_type]}"
        client = self._client()
        if client:
            self._ensure_bucket(client)
            client.put_object(Bucket=self.bucket, Key=object_key, Body=content, ContentType=content_type)
            storage_backend = "S3"
        else:
            target = self.local_directory / object_key
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            storage_backend = "LOCAL"

        with SessionLocal.begin() as session:
            session.add(EvidenceRow(
                id=evidence_id,
                client_report_id=client_report_id,
                object_key=object_key,
                content_type=content_type,
                size_bytes=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                storage_backend=storage_backend,
                uploaded_by=uploaded_by,
                created_at=datetime.now(UTC),
            ))
        return evidence_id

    def read(self, evidence_id: str) -> EvidenceObject | None:
        with SessionLocal() as session:
            row = session.get(EvidenceRow, evidence_id)
            if not row:
                return None
            object_key, content_type, storage_backend = row.object_key, row.content_type, row.storage_backend

        if storage_backend == "S3":
            client = self._client()
            if not client:
                return None
            response = client.get_object(Bucket=self.bucket, Key=object_key)["Body"]
            try:
                content = response.read()
            finally:
                response.close()
        else:
            target = (self.local_directory / object_key).resolve()
            if self.local_directory.resolve() not in target.parents or not target.is_file():
                return None
            content = target.read_bytes()
        return EvidenceObject(id=evidence_id, content_type=content_type, content=content)


evidence_storage = EvidenceStorage()
