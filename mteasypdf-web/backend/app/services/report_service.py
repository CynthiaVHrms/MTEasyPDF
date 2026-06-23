from pathlib import Path

from app.pdf_engine.generator import generate_report
from app.pdf_engine.models import ReportGenerationRequest
from app.services.storage_service import StorageService

class ReportService:
    
    def __init__(self):
        self.storage = StorageService()
        
    def generate_sync(
        self,
        zip_path: Path,
        project_data: dict,
        usa_ubicacion: bool = True,
    ):
        job_id = self.storage.create_job_id()
        dirs = self.storage.prepare_job_dirs(job_id)
        
        request = ReportGenerationRequest(
            job_id=job_id,
            zip_path=zip_path,
            output_dir=dirs["output_dir"],
            temp_dir=dirs["temp_dir"],
            project_data=project_data,
            usa_ubicacion=usa_ubicacion,
        )
        
        return generate_report(request)
    
        
        
