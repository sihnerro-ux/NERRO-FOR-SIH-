import ast
import os
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent / "validation-deps"))
source = Path(__file__).parent / "backend" / "app" / "evidence.py"
tree = ast.parse(source.read_text(encoding="utf-8-sig"))
storage_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "EvidenceStorage")
module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), storage_class], type_ignores=[])
namespace = {"os": os, "Path": Path, "BACKEND_DIR": Path(__file__).parent}
exec(compile(ast.fix_missing_locations(module), str(source), "exec"), namespace)
storage_type = namespace["EvidenceStorage"]
credentials = {"S3_ACCESS_KEY": "test-access", "S3_SECRET_KEY": "test-secret"}

with patch.dict(os.environ, {**credentials, "S3_ENDPOINT": "https://t3.storageapi.dev", "S3_BUCKET": "ner-evidence-test", "S3_REGION": "auto", "S3_ADDRESSING_STYLE": "virtual", "S3_AUTO_CREATE_BUCKET": "false"}, clear=True):
    storage = storage_type()
    client = storage._client()
    url = client.generate_presigned_url("get_object", Params={"Bucket": storage.bucket, "Key": "reports/test.png"})
    assert urlparse(url).hostname == "ner-evidence-test.t3.storageapi.dev"
    mocked_client = MagicMock()
    storage._ensure_bucket(mocked_client)
    assert not mocked_client.mock_calls

with patch.dict(os.environ, {**credentials, "S3_ENDPOINT": "minio:9000"}, clear=True):
    storage = storage_type()
    client = storage._client()
    url = client.generate_presigned_url("get_object", Params={"Bucket": storage.bucket, "Key": "reports/test.png"})
    assert urlparse(url).netloc == "minio:9000"
    assert urlparse(url).path == "/ner-field-evidence/reports/test.png"

with patch.dict(os.environ, {}, clear=True):
    assert storage_type()._client() is None

from datetime import UTC, datetime
from uuid import uuid4
import hashlib

namespace.update(datetime=datetime, UTC=UTC, uuid4=uuid4, hashlib=hashlib, EXTENSIONS={"image/png": "png"}, SessionLocal=MagicMock(), EvidenceRow=MagicMock(), EvidenceObject=MagicMock())
storage = storage_type()
storage.bucket = "ner-evidence-test"
mocked_client = MagicMock()
with patch.object(storage, "_client", return_value=mocked_client), patch.object(storage, "_ensure_bucket"), patch.object(storage, "_decode", return_value=("image/png", b"test-image")):
    storage.save("unused", "test-user", None)
    parameters = mocked_client.put_object.call_args.kwargs
    assert parameters["Bucket"] == storage.bucket
    assert parameters["Body"] == b"test-image"
    assert parameters["ContentType"] == "image/png"

row = MagicMock(storage_backend="S3", object_key="reports/test.png", content_type="image/png")
namespace["SessionLocal"].return_value.__enter__.return_value.get.return_value = row
body = MagicMock()
body.read.return_value = b"test-image"
mocked_client.get_object.return_value = {"Body": body}
with patch.object(storage, "_client", return_value=mocked_client):
    storage.read("test-id")
    mocked_client.get_object.assert_called_once_with(Bucket=storage.bucket, Key="reports/test.png")
    body.close.assert_called_once()

print("PASS: Railway virtual URLs, MinIO path URLs, managed bucket handling, local fallback, upload and download calls")
