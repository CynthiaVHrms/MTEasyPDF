import shutil
from pathlib import Path
from uuid import uuid4

from app.core.config import settings


class StorageService:
    
    def create_job_id(self) -> str:
        return uuid4().hex


    def get_job_dir(self, job_id: str) -> Path:
        return settings.storage_dir / job_id


    def prepare_job_dirs(self, job_id: str) -> dict:
        job_dir = self.get_job_dir(job_id)

        input_dir = job_dir / "input"
        temp_dir = job_dir / "temp"
        output_dir = job_dir / "output"

        input_dir.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        return {
            "job_dir": job_dir,
            "input_dir": input_dir,
            "temp_dir": temp_dir,
            "output_dir": output_dir,
        }

    def delete_job(self, job_id: str) -> None:
        job_dir = self.get_job_dir(job_id)

        if job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)