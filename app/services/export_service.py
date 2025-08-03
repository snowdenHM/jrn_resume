from typing import Dict, Any, Optional
from io import BytesIO
import logging
import uuid
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict
import threading
import weakref
import gc

from app.utils.pdf_generator import ResumePDFGenerator
from app.core.config import settings

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting resumes to various formats with improved memory management"""

    def __init__(self):
        self.pdf_generator = ResumePDFGenerator()
        self.export_cache = {}  # In production, use Redis
        self.cache_lock = threading.RLock()  # Use RLock for nested locking
        self.max_cache_size = 100  # Maximum number of cached files
        self.max_file_size = 10 * 1024 * 1024  # 10MB max file size
        self._cleanup_thread = None
        self._start_cleanup_thread()

    def _start_cleanup_thread(self):
        """Start background cleanup thread"""

        def cleanup_worker():
            import time
            while True:
                try:
                    time.sleep(300)  # Run every 5 minutes
                    self.cleanup_expired_jobs()
                    self._cleanup_cache_if_needed()
                    # Force garbage collection
                    gc.collect()
                except Exception as e:
                    logger.error(f"Cleanup thread error: {e}")

        if not self._cleanup_thread or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
            self._cleanup_thread.start()

    def export_to_pdf(
            self,
            resume_content: Dict[str, Any],
            title: str = "Resume",
            template_id: str = "professional"
    ) -> BytesIO:
        """Export resume to PDF format with improved error handling"""
        try:
            logger.info(f"Starting PDF export for resume: {title}")

            # Validate input
            if not resume_content:
                raise ValueError("Resume content cannot be empty")

            if not isinstance(resume_content, dict):
                raise ValueError("Resume content must be a dictionary")

            if not resume_content.get('personal_info'):
                raise ValueError("Resume must contain personal information")

            # Validate personal info has required fields
            personal_info = resume_content['personal_info']
            required_fields = ['first_name', 'last_name']
            missing_fields = [field for field in required_fields if not personal_info.get(field)]
            if missing_fields:
                raise ValueError(f"Missing required personal info fields: {', '.join(missing_fields)}")

            # Sanitize title
            safe_title = self._sanitize_filename(title)

            # Generate PDF with memory-conscious approach
            try:
                pdf_buffer = self.pdf_generator.generate_resume_pdf(
                    resume_content=resume_content,
                    title=safe_title
                )
            except Exception as pdf_error:
                logger.error(f"PDF generation failed: {pdf_error}")
                raise ValueError(f"PDF generation failed: {str(pdf_error)}")

            # Validate generated PDF size
            pdf_size = len(pdf_buffer.getvalue())
            if pdf_size > self.max_file_size:
                pdf_buffer.close()  # Clean up memory
                raise ValueError(f"Generated PDF size ({pdf_size} bytes) exceeds maximum allowed size")

            if pdf_size == 0:
                pdf_buffer.close()
                raise ValueError("Generated PDF is empty")

            logger.info(f"Successfully exported resume to PDF: {title} ({pdf_size} bytes)")
            return pdf_buffer

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error exporting resume to PDF: {e}", exc_info=True)
            raise ValueError(f"PDF export failed: {str(e)}")

    def create_export_job(
            self,
            resume_content: Dict[str, Any],
            title: str = "Resume",
            export_format: str = "pdf",
            user_id: str = None
    ) -> Dict[str, Any]:
        """Create an asynchronous export job with improved error handling"""
        export_id = None
        try:
            export_id = str(uuid.uuid4())

            # Validate input
            if not user_id:
                raise ValueError("User ID is required for export job")

            if export_format not in self.get_supported_formats():
                raise ValueError(f"Unsupported export format: {export_format}")

            # Validate resume content early
            is_valid, error_msg = self.validate_export_request(resume_content, export_format)
            if not is_valid:
                raise ValueError(error_msg)

            job_data = {
                'export_id': export_id,
                'user_id': user_id,
                'resume_title': self._sanitize_filename(title),
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
                self.export_cache[export_id] = job_data.copy()

            # Process export based on format
            try:
                if export_format == 'pdf':
                    self._process_pdf_export(export_id, resume_content, title)
                elif export_format == 'docx':
                    job_data.update({
                        'status': 'failed',
                        'error_message': f"Export format '{export_format}' not yet implemented",
                        'completed_at': datetime.utcnow()
                    })
                elif export_format == 'html':
                    job_data.update({
                        'status': 'failed',
                        'error_message': f"Export format '{export_format}' not yet implemented",
                        'completed_at': datetime.utcnow()
                    })
                else:
                    job_data.update({
                        'status': 'failed',
                        'error_message': f"Export format '{export_format}' not supported",
                        'completed_at': datetime.utcnow()
                    })

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Export job {export_id} failed: {error_msg}")
                job_data.update({
                    'status': 'failed',
                    'error_message': error_msg,
                    'completed_at': datetime.utcnow(),
                    'progress': 0
                })

            # Update job data in cache
            with self.cache_lock:
                if export_id in self.export_cache:
                    self.export_cache[export_id].update(job_data)

            logger.info(f"Created export job: {export_id} with status: {job_data['status']}")
            return job_data

        except Exception as e:
            logger.error(f"Error creating export job: {e}", exc_info=True)
            # Clean up failed job
            if export_id:
                self.cleanup_export_job(export_id)
            raise

    def _process_pdf_export(self, export_id: str, resume_content: Dict[str, Any], title: str):
        """Process PDF export with proper error handling and memory management"""
        try:
            with self.cache_lock:
                if export_id not in self.export_cache:
                    raise ValueError("Export job not found")

                self.export_cache[export_id]['status'] = 'processing'
                self.export_cache[export_id]['progress'] = 25

            # Generate PDF
            pdf_buffer = self.export_to_pdf(resume_content, title)
            file_content = pdf_buffer.getvalue()

            # Close buffer to free memory
            pdf_buffer.close()

            # Validate file size
            if len(file_content) > self.max_file_size:
                raise ValueError("Generated file exceeds size limit")

            with self.cache_lock:
                if export_id in self.export_cache:
                    self.export_cache[export_id].update({
                        'status': 'completed',
                        'download_url': f"/api/v1/export/{export_id}/download",
                        'file_size': len(file_content),
                        'completed_at': datetime.utcnow(),
                        'progress': 100
                    })

                    # Store the file content with weak reference for memory management
                    content_key = f"{export_id}_content"
                    self.export_cache[content_key] = file_content

        except Exception as e:
            logger.error(f"PDF export processing failed for {export_id}: {e}")
            with self.cache_lock:
                if export_id in self.export_cache:
                    self.export_cache[export_id].update({
                        'status': 'failed',
                        'error_message': str(e),
                        'completed_at': datetime.utcnow(),
                        'progress': 0
                    })
            raise

    def get_export_status(self, export_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of an export job with improved error handling"""
        try:
            if not export_id:
                return None

            with self.cache_lock:
                job_data = self.export_cache.get(export_id)

            if not job_data:
                logger.debug(f"Export job not found: {export_id}")
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
        """Get the exported file content with improved error handling"""
        try:
            if not export_id:
                return None

            job_data = self.get_export_status(export_id)
            if not job_data:
                return None

            if job_data['status'] != 'completed':
                logger.warning(f"Export job {export_id} not completed, status: {job_data['status']}")
                return None

            # Get file content from cache
            content_key = f"{export_id}_content"
            with self.cache_lock:
                file_content = self.export_cache.get(content_key)

            if not file_content:
                logger.error(f"Export file content not found for job {export_id}")
                return None

            if not isinstance(file_content, bytes):
                logger.error(f"Invalid file content type for job {export_id}")
                return None

            return file_content

        except Exception as e:
            logger.error(f"Error getting export file for {export_id}: {e}")
            return None

    def cleanup_export_job(self, export_id: str) -> bool:
        """Clean up export job and associated files with improved error handling"""
        try:
            if not export_id:
                return False

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
                logger.debug(f"Cleaned up export job: {export_id}")
                return True
            else:
                logger.debug(f"Export job not found for cleanup: {export_id}")
                return False

        except Exception as e:
            logger.error(f"Error cleaning up export job {export_id}: {e}")
            return False

    def cleanup_expired_jobs(self) -> int:
        """Clean up all expired export jobs with improved error handling"""
        try:
            current_time = datetime.utcnow()
            expired_jobs = []

            with self.cache_lock:
                # Find expired jobs
                for export_id, job_data in list(self.export_cache.items()):
                    if (isinstance(job_data, dict) and
                            'expires_at' in job_data and
                            not export_id.endswith('_content')):
                        try:
                            if current_time > job_data['expires_at']:
                                expired_jobs.append(export_id)
                        except Exception as e:
                            logger.error(f"Error checking expiration for job {export_id}: {e}")
                            expired_jobs.append(export_id)  # Clean up problematic entries

            # Clean up expired jobs
            cleaned_count = 0
            for export_id in expired_jobs:
                try:
                    if self.cleanup_export_job(export_id):
                        cleaned_count += 1
                except Exception as e:
                    logger.error(f"Error cleaning up expired job {export_id}: {e}")

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired export jobs")

            return cleaned_count

        except Exception as e:
            logger.error(f"Error cleaning up expired jobs: {e}")
            return 0

    def _cleanup_cache_if_needed(self):
        """Clean up cache if it exceeds maximum size with improved logic"""
        try:
            current_cache_size = len(self.export_cache)
            if current_cache_size <= self.max_cache_size:
                return

            # Calculate how many entries to remove (remove 30% of oldest)
            jobs_to_remove = max(1, int(current_cache_size * 0.3))

            # Find oldest jobs to remove
            current_time = datetime.utcnow()
            job_ages = []

            for key, data in list(self.export_cache.items()):
                if (isinstance(data, dict) and
                        'created_at' in data and
                        not key.endswith('_content')):
                    try:
                        age = (current_time - data['created_at']).total_seconds()
                        job_ages.append((age, key))
                    except Exception as e:
                        logger.error(f"Error calculating age for job {key}: {e}")
                        job_ages.append((float('inf'), key))  # Mark for removal

            # Sort by age (oldest first) and remove oldest jobs
            job_ages.sort(reverse=True)

            removed_count = 0
            for _, export_id in job_ages[:jobs_to_remove]:
                try:
                    if self.cleanup_export_job(export_id):
                        removed_count += 1
                except Exception as e:
                    logger.error(f"Error removing old job {export_id}: {e}")

            logger.info(f"Cache cleanup removed {removed_count} old export jobs")

        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage"""
        if not filename or not isinstance(filename, str):
            return "resume"

        # Remove or replace problematic characters
        import re
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename.strip())
        sanitized = re.sub(r'\s+', '_', sanitized)
        sanitized = sanitized[:100]  # Limit length

        return sanitized if sanitized else "resume"

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
        """Validate export request with comprehensive checks"""
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

            if not isinstance(personal_info, dict):
                return False, "Personal information must be a dictionary"

            required_personal_fields = ['first_name', 'last_name']
            missing_fields = [field for field in required_personal_fields
                              if not personal_info.get(field)]

            if missing_fields:
                return False, f"Personal information missing required fields: {', '.join(missing_fields)}"

            # Check content size (rough estimate)
            try:
                content_str = str(resume_content)
                content_size = len(content_str.encode('utf-8'))
                if content_size > 1024 * 1024:  # 1MB content limit
                    return False, "Resume content is too large"
            except Exception as e:
                logger.warning(f"Could not estimate content size: {e}")

            return True, None

        except Exception as e:
            logger.error(f"Error validating export request: {e}")
            return False, f"Validation error: {str(e)}"

    def get_export_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get export statistics with improved error handling"""
        try:
            with self.cache_lock:
                total_jobs = 0
                completed_jobs = 0
                failed_jobs = 0
                pending_jobs = 0
                user_jobs = 0
                total_file_size = 0

                for key, job_data in self.export_cache.items():
                    try:
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
                    except Exception as e:
                        logger.error(f"Error processing statistics for key {key}: {e}")

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
            return {
                'total_jobs': 0,
                'completed_jobs': 0,
                'failed_jobs': 0,
                'pending_jobs': 0,
                'success_rate': 0,
                'total_cache_size_mb': 0,
                'cache_utilization': 0
            }

    def get_user_export_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get export history for a specific user with improved error handling"""
        try:
            if not user_id:
                return []

            user_exports = []

            with self.cache_lock:
                for export_id, job_data in self.export_cache.items():
                    try:
                        if (isinstance(job_data, dict) and
                                'user_id' in job_data and
                                job_data['user_id'] == user_id and
                                not export_id.endswith('_content')):
                            export_entry = {
                                'export_id': export_id,
                                'resume_title': job_data.get('resume_title'),
                                'export_format': job_data.get('export_format'),
                                'status': job_data.get('status'),
                                'created_at': job_data.get('created_at'),
                                'file_size': job_data.get('file_size'),
                                'download_url': job_data.get('download_url')
                            }
                            user_exports.append(export_entry)
                    except Exception as e:
                        logger.error(f"Error processing export entry {export_id}: {e}")

            # Sort by creation date (newest first) and limit
            try:
                user_exports.sort(
                    key=lambda x: x.get('created_at', datetime.min),
                    reverse=True
                )
            except Exception as e:
                logger.error(f"Error sorting export history: {e}")

            return user_exports[:limit]

        except Exception as e:
            logger.error(f"Error getting user export history: {e}")
            return []

    def __del__(self):
        """Cleanup when service is destroyed"""
        try:
            if hasattr(self, '_cleanup_thread') and self._cleanup_thread:
                # Note: We can't join the thread here as it's daemon
                pass
        except Exception as e:
            logger.error(f"Error in ExportService destructor: {e}")