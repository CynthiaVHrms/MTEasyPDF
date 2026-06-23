from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

ProgressCallback = Optional[Callable[[int], None]]

@dataclass
class ReportGenerationRequest:
    job_id: str
    zip_path: Path
    output_dir: Path
    temp_dir: Path
    project_data: dict
    usa_ubicacion: bool = True
    progress_callback: ProgressCallback = None


@dataclass
class ReportGenerationResult:
    job_id: str
    main_pdf_path: Path
    final_zip_path: Path
    success: bool = True



    


