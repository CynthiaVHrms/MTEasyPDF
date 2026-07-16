from __future__ import annotations

import json
import os
import re
import threading

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


JOB_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
STATUS_FILENAME = "estado_generacion.json"

_WRITE_LOCK = threading.RLock()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_job_id(job_id: str) -> str:
    normalized_job_id = job_id.strip().lower()

    if not JOB_ID_PATTERN.fullmatch(normalized_job_id):
        raise ValueError("El identificador del proceso no es válido.")

    return normalized_job_id


def get_job_status_path(status_root: Path, job_id: str) -> Path:
    normalized_job_id = validate_job_id(job_id)
    return Path(status_root) / normalized_job_id / STATUS_FILENAME


def create_job_status(
    status_root: Path,
    job_id: str,
    *,
    message: str = "El proceso está en espera de iniciar.",
) -> dict[str, Any]:
    normalized_job_id = validate_job_id(job_id)
    now = _utc_now_iso()

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "job_id": normalized_job_id,
        "status": "queued",
        "stage": "queued",
        "percentage": 0,
        "message": message,
        "current_site": 0,
        "total_sites": 0,
        "current_site_name": "",
        "processed_images": 0,
        "total_images": 0,
        "detected_images": 0,
        "download_ready": False,
        "diagnostics_ready": False,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }

    _write_status(status_root, normalized_job_id, payload)
    return payload


def update_job_status(
    status_root: Path,
    job_id: str,
    **changes: Any,
) -> dict[str, Any]:
    normalized_job_id = validate_job_id(job_id)

    with _WRITE_LOCK:
        current = read_job_status(status_root, normalized_job_id)

        if current is None:
            current = create_job_status(status_root, normalized_job_id)

        if "percentage" in changes:
            try:
                changes["percentage"] = max(
                    0,
                    min(100, int(changes["percentage"])),
                )
            except (TypeError, ValueError):
                changes["percentage"] = current.get("percentage", 0)

        current.update(changes)
        current["updated_at"] = _utc_now_iso()

        _write_status(status_root, normalized_job_id, current)
        return current


def read_job_status(
    status_root: Path,
    job_id: str,
) -> dict[str, Any] | None:
    normalized_job_id = validate_job_id(job_id)
    status_path = get_job_status_path(status_root, normalized_job_id)

    if not status_path.exists() or not status_path.is_file():
        return None

    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    return payload


def _write_status(
    status_root: Path,
    job_id: str,
    payload: dict[str, Any],
) -> None:
    status_path = get_job_status_path(status_root, job_id)
    status_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = status_path.with_name(
        f".{status_path.name}.{uuid4().hex}.tmp"
    )

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )

    with _WRITE_LOCK:
        temporary_path.write_text(serialized, encoding="utf-8")
        os.replace(temporary_path, status_path)