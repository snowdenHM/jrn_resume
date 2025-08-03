from typing import Dict, Any, Optional
from io import BytesIO
import logging
import uuid
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict
import threading

from app.utils.pdf_generator import ResumePDFGenerator
from app.core.config import settings

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting resumes to various formats"""

    def __init__(self):
        self.pdf_generator = ResumePDFGenerator()
        self.export_cache = {}  # In production, use Redis
        self.cache_lock = threading.Lock()
        self.max_cache_size = 100  # Maximum number of cached files
        self.max_file_size = 10 * 1024 * 1024  # 10MB max file size

    def export_to_pdf(
            self,
            resume_content: Dict[str, Any],
            title: str = "Resume",
            template_id: str = "professional"
    ) -> BytesIO:
        """Export resume to PDF format"""
        try:
            logger.info(f"Starting PDF export for resume: {title}")

            # Validate input
            if not resume_content:
                raise ValueError("Resume content cannot be empty")

            if not resume_content.get('personal_info'):
                raise ValueError("Resume must contain personal information")

            # Generate PDF
            pdf_buffer = self.pdf_generator.generate_resume_pdf(
                resume_content=resume_content,
                title=title
            )

            # Validate generated PDF size
            pdf_size = len(pdf_buffer.getvalue())
            if pdf_size > self.max_file_size:
                raise ValueError(f"Generated PDF size ({pdf_size} bytes) exceeds maximum allowed size")

            if pdf_size == 0:
                raise ValueError("Generated PDF is empty")

            logger.info(f"Successfully exported resume to PDF: {title} ({pdf_size} bytes)")
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

            # Validate input
            if not user_id:
                raise ValueError("User ID is required for export job")

            if export_format not in self.get_supported_formats():
                raise ValueError(f"Unsupported export format: {export_format}")

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
                'error_message': None,
                'progress': 0
            }

            # Store job in cache with thread safety
            with self.cache_lock:
                # Clean cache if it's getting too large
                self._cleanup_cache_if_needed()
                self.export_cache[export_id] = job_data

            # Process export based on format
            try:
                if export_format == 'pdf':
                    job_data['status'] = 'processing'
                    job_data['progress'] = 25

                    pdf_buffer = self.export_to_pdf(resume_content, title)
                    file_content = pdf_buffer.getvalue()

                    # Validate file size
                    if len(file_content) > self.max_file_size:
                        raise ValueError("Generated file exceeds size limit")

                    job_data.update({
                        'status': 'completed',
                        'download_url': f"/api/v1/export/{export_id}/download",
                        'file_size': len(file_content),
                        'completed_at': datetime.utcnow(),
                        'progress': 100
                    })

                    # Store the file content with thread safety
                    with self.cache_lock:
                        self.export_cache[f"{export_id}_content"] = file_content

                else:
                    # Future formats (DOCX, HTML, etc.)
                    job_data.update({
                        'status': 'failed',
                        'error_message': f"Export format '{export_format}' not yet implemented",
                        'completed_at': datetime.utcnow()
                    })

            except Exception as e:
                job_data.update({
                    'status': 'failed',
                    'error_message': str(e),
                    'completed_at': datetime.utcnow(),
                    'progress': 0
                })
                logger.error(f"Export job {export_id} failed: {e}")

            # Update job data in cache
            with self.cache_lock:
                self.export_cache[export_id] = job_data

            logger.info(f"Created export job: {export_id} with status: {job_data['status']}")
            return job_data

        except Exception as e:
            logger.error(f"Error creating export job: {e}")
            raise

    def get_export_status(self, export_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of an export job"""
        try:
            with self.cache_lock:
                job_data = self.export_cache.get(export_id)

            if not job_data:
                logger.warning(f"Export job not found: {export_id}")
                return None

            # Check if job has expired
            if datetime.utcnow() > job_data['expires_at']:
                logger.info(f"Export job expired: {export_id}")
                self.cleanup_export_job(export_id)
                return None

            # Return copy to avoid external modifications
            return job_data.copy()

        except Exception as e:
            logger.error(f"Error getting export status for {export_id}: {e}")
            return None

    def get_export_file(self, export_id: str) -> Optional[bytes]:
        """Get the exported file content"""
        try:
            job_data = self.get_export_status(export_id)
            if not job_data:
                return None

            if job_data['status'] != 'completed':
                logger.warning(f"Export job {export_id} not completed, status: {job_data['status']}")
                return None

            # Get file content from cache
            with self.cache_lock:
                file_content = self.export_cache.get(f"{export_id}_content")

            if not file_content:
                logger.error(f"Export file content not found for job {export_id}")
                return None

            return file_content

        except Exception as e:
            logger.error(f"Error getting export file for {export_id}: {e}")
            return None

    def cleanup_export_job(self, export_id: str) -> bool:
        """Clean up export job and associated files"""
        try:
            with self.cache_lock:
                # Remove job data
                job_removed = export_id in self.export_cache
                if job_removed:
                    del self.export_cache[export_id]

                # Remove file content
                content_key = f"{export_id}_content"
                content_removed = content_key in self.export_cache
                if content_removed:
                    del self.export_cache[content_key]

            if job_removed or content_removed:
                logger.info(f"Cleaned up export job: {export_id}")
                return True
            else:
                logger.warning(f"Export job not found for cleanup: {export_id}")
                return False

        except Exception as e:
            logger.error(f"Error cleaning up export job {export_id}: {e}")
            return False

    def cleanup_expired_jobs(self) -> int:
        """Clean up all expired export jobs"""
        try:
            current_time = datetime.utcnow()
            expired_jobs = []

            with self.cache_lock:
                # Find expired jobs
                for export_id, job_data in list(self.export_cache.items()):
                    if isinstance(job_data, dict) and 'expires_at' in job_data:
                        if current_time > job_data['expires_at']:
                            expired_jobs.append(export_id)

            # Clean up expired jobs
            cleaned_count = 0
            for export_id in expired_jobs:
                if self.cleanup_export_job(export_id):
                    cleaned_count += 1

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired export jobs")

            return cleaned_count

        except Exception as e:
            logger.error(f"Error cleaning up expired jobs: {e}")
            return 0

    def _cleanup_cache_if_needed(self):
        """Clean up cache if it exceeds maximum size"""
        try:
            if len(self.export_cache) <= self.max_cache_size:
                return

            # Find oldest jobs to remove
            current_time = datetime.utcnow()
            job_ages = []

            for key, data in self.export_cache.items():
                if isinstance(data, dict) and 'created_at' in data:
                    age = (current_time - data['created_at']).total_seconds()
                    job_ages.append((age, key))

            # Sort by age (oldest first) and remove oldest jobs
            job_ages.sort(reverse=True)
            jobs_to_remove = int(len(job_ages) * 0.3)  # Remove 30% of oldest jobs

            for _, export_id in job_ages[:jobs_to_remove]:
                if not export_id.endswith('_content'):
                    # This will also remove associated content
                    self.cleanup_export_job(export_id)

            logger.info(f"Cache cleanup removed {jobs_to_remove} old export jobs")

        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")

    def get_supported_formats(self) -> Dict[str, Dict[str, Any]]:
        """Get list of supported export formats"""
        return {
            'pdf': {
                'name': 'PDF Document',
                'description': 'Portable Document Format suitable for printing and sharing',
                'extension': '.pdf',
                'mime_type': 'application/pdf',
                'max_size_mb': 10,
                'supported': True
            },
            'docx': {
                'name': 'Word Document',
                'description': 'Microsoft Word document format',
                'extension': '.docx',
                'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'max_size_mb': 10,
                'supported': False  # Not yet implemented
            },
            'html': {
                'name': 'HTML Document',
                'description': 'Web-ready HTML format',
                'extension': '.html',
                'mime_type': 'text/html',
                'max_size_mb': 5,
                'supported': False  # Not yet implemented
            }
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

            format_info = supported_formats[export_format]
            if not format_info.get('supported', False):
                return False, f"Export format '{export_format}' is not yet implemented"

            # Check if resume content is valid
            if not resume_content:
                return False, "Resume content is empty"

            if not isinstance(resume_content, dict):
                return False, "Resume content must be a dictionary"

            # Check required fields
            personal_info = resume_content.get('personal_info', {})
            if not personal_info:
                return False, "Resume must contain personal information"

            required_personal_fields = ['first_name', 'last_name']
            missing_fields = [field for field in required_personal_fields
                              if not personal_info.get(field)]

            if missing_fields:
                return False, f"Personal information missing required fields: {', '.join(missing_fields)}"

            # Check content size (rough estimate)
            content_size = len(str(resume_content))
            if content_size > 1024 * 1024:  # 1MB content limit
                return False, "Resume content is too large"

            return True, None

        except Exception as e:
            logger.error(f"Error validating export request: {e}")
            return False, f"Validation error: {str(e)}"

    def get_export_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get export statistics"""
        try:
            with self.cache_lock:
                total_jobs = 0
                completed_jobs = 0
                failed_jobs = 0
                pending_jobs = 0
                user_jobs = 0
                total_file_size = 0

                for key, job_data in self.export_cache.items():
                    # Skip content entries
                    if key.endswith('_content'):
                        if isinstance(job_data, bytes):
                            total_file_size += len(job_data)
                        continue

                    if isinstance(job_data, dict) and 'status' in job_data:
                        total_jobs += 1

                        if user_id and job_data.get('user_id') == user_id:
                            user_jobs += 1

                        status = job_data['status']
                        if status == 'completed':
                            completed_jobs += 1
                        elif status == 'failed':
                            failed_jobs += 1
                        elif status in ['pending', 'processing']:
                            pending_jobs += 1

            stats = {
                'total_jobs': total_jobs,
                'completed_jobs': completed_jobs,
                'failed_jobs': failed_jobs,
                'pending_jobs': pending_jobs,
                'success_rate': round((completed_jobs / total_jobs * 100), 2) if total_jobs > 0 else 0,
                'total_cache_size_mb': round(total_file_size / (1024 * 1024), 2),
                'cache_utilization': round((len(self.export_cache) / self.max_cache_size * 100), 2)
            }

            if user_id:
                stats['user_jobs'] = user_jobs

            return stats

        except Exception as e:
            logger.error(f"Error getting export statistics: {e}")
            return {}

    def get_user_export_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get export history for a specific user"""
        try:
            user_exports = []

            with self.cache_lock:
                for export_id, job_data in self.export_cache.items():
                    if (isinstance(job_data, dict) and
                            'user_id' in job_data and
                            job_data['user_id'] == user_id and
                            not export_id.endswith('_content')):
                        user_exports.append({
                            'export_id': export_id,
                            'resume_title': job_data.get('resume_title'),
                            'export_format': job_data.get('export_format'),
                            'status': job_data.get('status'),
                            'created_at': job_data.get('created_at'),
                            'file_size': job_data.get('file_size'),
                            'download_url': job_data.get('download_url')
                        })

            # Sort by creation date (newest first) and limit
            user_exports.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
            return user_exports[:limit]

        except Exception as e:
            logger.error(f"Error getting user export history: {e}")
            return []