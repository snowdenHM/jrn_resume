from typing import Dict, Any, Optional
from io import BytesIO
import logging
import uuid
from datetime import datetime, timedelta

from app.utils.pdf_generator import ResumePDFGenerator
from app.core.config import settings

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting resumes to various formats"""

    def __init__(self):
        self.pdf_generator = ResumePDFGenerator()
        self.export_cache = {}  # In production, use Redis

    def export_to_pdf(
            self,
            resume_content: Dict[str, Any],
            title: str = "Resume",
            template_id: str = "professional"
    ) -> BytesIO:
        """Export resume to PDF format"""
        try:
            logger.info(f"Starting PDF export for resume: {title}")

            # Generate PDF
            pdf_buffer = self.pdf_generator.generate_resume_pdf(
                resume_content=resume_content,
                title=title
            )

            logger.info(f"Successfully exported resume to PDF: {title}")
            return pdf_buffer

        except Exception as e:
            logger.error(f"Error exporting resume to PDF: {e}")
            raise

    def create_export_job(
            self,
            resume_content: Dict[str, Any],
            title: str = "Resume",
            export_format: str = "pdf",
            user_id: str = None
    ) -> Dict[str, Any]:
        """Create an asynchronous export job"""
        try:
            export_id = str(uuid.uuid4())

            job_data = {
                'export_id': export_id,
                'user_id': user_id,
                'resume_title': title,
                'export_format': export_format,
                'status': 'pending',
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(hours=24),
                'download_url': None,
                'file_size': None,
                'error_message': None
            }

            # Store job in cache (in production, use Redis with expiration)
            self.export_cache[export_id] = job_data

            # Process export immediately for PDF (for demo purposes)
            if export_format == 'pdf':
                try:
                    pdf_buffer = self.export_to_pdf(resume_content, title)

                    # In production, save to file storage (S3, etc.)
                    job_data.update({
                        'status': 'completed',
                        'download_url': f"/api/v1/exports/{export_id}/download",
                        'file_size': len(pdf_buffer.getvalue()),
                        'completed_at': datetime.utcnow()
                    })

                    # Store the file content (in production, save to persistent storage)
                    self.export_cache[f"{export_id}_content"] = pdf_buffer.getvalue()

                except Exception as e:
                    job_data.update({
                        'status': 'failed',
                        'error_message': str(e),
                        'completed_at': datetime.utcnow()
                    })

            self.export_cache[export_id] = job_data

            logger.info(f"Created export job: {export_id}")
            return job_data

        except Exception as e:
            logger.error(f"Error creating export job: {e}")
            raise

    def get_export_status(self, export_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of an export job"""
        try:
            job_data = self.export_cache.get(export_id)
            if not job_data:
                return None

            # Check if job has expired
            if datetime.utcnow() > job_data['expires_at']:
                self.cleanup_export_job(export_id)
                return None

            return job_data

        except Exception as e:
            logger.error(f"Error getting export status for {export_id}: {e}")
            return None

    def get_export_file(self, export_id: str) -> Optional[bytes]:
        """Get the exported file content"""
        try:
            job_data = self.get_export_status(export_id)
            if not job_data or job_data['status'] != 'completed':
                return None

            # Get file content from cache
            file_content = self.export_cache.get(f"{export_id}_content")
            return file_content

        except Exception as e:
            logger.error(f"Error getting export file for {export_id}: {e}")
            return None

    def cleanup_export_job(self, export_id: str) -> bool:
        """Clean up export job and associated files"""
        try:
            # Remove job data
            if export_id in self.export_cache:
                del self.export_cache[export_id]

            # Remove file content
            content_key = f"{export_id}_content"
            if content_key in self.export_cache:
                del self.export_cache[content_key]

            logger.info(f"Cleaned up export job: {export_id}")
            return True

        except Exception as e:
            logger.error(f"Error cleaning up export job {export_id}: {e}")
            return False

    def cleanup_expired_jobs(self) -> int:
        """Clean up all expired export jobs"""
        try:
            current_time = datetime.utcnow()
            expired_jobs = []

            for export_id, job_data in self.export_cache.items():
                if isinstance(job_data, dict) and 'expires_at' in job_data:
                    if current_time > job_data['expires_at']:
                        expired_jobs.append(export_id)

            for export_id in expired_jobs:
                self.cleanup_export_job(export_id)

            logger.info(f"Cleaned up {len(expired_jobs)} expired export jobs")
            return len(expired_jobs)

        except Exception as e:
            logger.error(f"Error cleaning up expired jobs: {e}")
            return 0

    def get_supported_formats(self) -> Dict[str, Dict[str, Any]]:
        """Get list of supported export formats"""
        return {
            'pdf': {
                'name': 'PDF Document',
                'description': 'Portable Document Format suitable for printing and sharing',
                'extension': '.pdf',
                'mime_type': 'application/pdf',
                'max_size_mb': 10
            },
            # Future formats can be added here
            # 'docx': {
            #     'name': 'Word Document',
            #     'description': 'Microsoft Word document format',
            #     'extension': '.docx',
            #     'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            #     'max_size_mb': 10
            # },
            # 'html': {
            #     'name': 'HTML Document',
            #     'description': 'Web-ready HTML format',
            #     'extension': '.html',
            #     'mime_type': 'text/html',
            #     'max_size_mb': 5
            # }
        }

    def validate_export_request(
            self,
            resume_content: Dict[str, Any],
            export_format: str
    ) -> tuple[bool, Optional[str]]:
        """Validate export request"""
        try:
            # Check if format is supported
            supported_formats = self.get_supported_formats()
            if export_format not in supported_formats:
                return False, f"Unsupported export format: {export_format}"

            # Check if resume content is valid
            if not resume_content:
                return False, "Resume content is empty"

            # Check required fields
            personal_info = resume_content.get('personal_info', {})
            if not personal_info.get('first_name') or not personal_info.get('last_name'):
                return False, "Personal information (first_name, last_name) is required for export"

            return True, None

        except Exception as e:
            logger.error(f"Error validating export request: {e}")
            return False, f"Validation error: {str(e)}"

    def get_export_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get export statistics"""
        try:
            total_jobs = 0
            completed_jobs = 0
            failed_jobs = 0
            pending_jobs = 0
            user_jobs = 0

            for job_data in self.export_cache.values():
                if isinstance(job_data, dict) and 'status' in job_data:
                    total_jobs += 1

                    if user_id and job_data.get('user_id') == user_id:
                        user_jobs += 1

                    status = job_data['status']
                    if status == 'completed':
                        completed_jobs += 1
                    elif status == 'failed':
                        failed_jobs += 1
                    elif status == 'pending':
                        pending_jobs += 1

            stats = {
                'total_jobs': total_jobs,
                'completed_jobs': completed_jobs,
                'failed_jobs': failed_jobs,
                'pending_jobs': pending_jobs,
                'success_rate': (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            }

            if user_id:
                stats['user_jobs'] = user_jobs

            return stats

        except Exception as e:
            logger.error(f"Error getting export statistics: {e}")
            return {}