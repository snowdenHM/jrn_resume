from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, or_
from uuid import UUID
import logging

from app.repositories.base import BaseRepository
from app.models.resume import Resume

logger = logging.getLogger(__name__)


class ResumeRepository(BaseRepository[Resume]):
    """Repository for Resume model with specific business logic"""

    def __init__(self, db: Session):
        super().__init__(db, Resume)

    def get_by_user(
            self,
            user_id: UUID,
            page: int = 1,
            size: int = 10,
            is_active: Optional[bool] = None,
            order_by: str = "updated_at",
            order_desc: bool = True
    ) -> List[Resume]:
        """Get all resumes for a specific user"""
        try:
            filters = {"user_id": user_id}
            if is_active is not None:
                filters["is_active"] = is_active

            skip = (page - 1) * size

            return self.get_multi(
                skip=skip,
                limit=size,
                filters=filters,
                order_by=order_by,
                order_desc=order_desc
            )
        except Exception as e:
            logger.error(f"Error getting resumes for user {user_id}: {e}")
            raise

    def count_by_user(self, user_id: UUID, is_active: Optional[bool] = None) -> int:
        """Count resumes for a specific user"""
        try:
            filters = {"user_id": user_id}
            if is_active is not None:
                filters["is_active"] = is_active

            return self.count(filters)
        except Exception as e:
            logger.error(f"Error counting resumes for user {user_id}: {e}")
            raise

    def get_by_id_and_user(self, resume_id: UUID, user_id: UUID) -> Optional[Resume]:
        """Get resume by ID and verify ownership"""
        try:
            return self.db.query(Resume).filter(
                and_(
                    Resume.id == resume_id,
                    Resume.user_id == user_id
                )
            ).first()
        except Exception as e:
            logger.error(f"Error getting resume {resume_id} for user {user_id}: {e}")
            raise

    def create_resume(
            self,
            user_id: UUID,
            title: str,
            content: Dict[str, Any],
            template_id: str = "professional"
    ) -> Resume:
        """Create a new resume with automatic version numbering"""
        try:
            # Get the latest version for this user
            latest_version = self.get_latest_version_for_user(user_id)
            new_version = latest_version + 1 if latest_version else 1

            return self.create(
                user_id=user_id,
                title=title,
                content=content,
                template_id=template_id,
                version=new_version
            )
        except Exception as e:
            logger.error(f"Error creating resume for user {user_id}: {e}")
            raise

    def update_resume(
            self,
            resume_id: UUID,
            user_id: UUID,
            update_data: Dict[str, Any]
    ) -> Optional[Resume]:
        """Update resume and increment version"""
        try:
            resume = self.get_by_id_and_user(resume_id, user_id)
            if not resume:
                return None

            # Increment version if content is being updated
            if 'content' in update_data:
                update_data['version'] = resume.version + 1

            # Remove None values
            clean_data = {k: v for k, v in update_data.items() if v is not None}

            return self.update(resume_id, clean_data)
        except Exception as e:
            logger.error(f"Error updating resume {resume_id} for user {user_id}: {e}")
            raise

    def delete_resume(self, resume_id: UUID, user_id: UUID) -> bool:
        """Delete resume after verifying ownership"""
        try:
            resume = self.get_by_id_and_user(resume_id, user_id)
            if not resume:
                return False

            return self.delete(resume_id)
        except Exception as e:
            logger.error(f"Error deleting resume {resume_id} for user {user_id}: {e}")
            raise

    def soft_delete_resume(self, resume_id: UUID, user_id: UUID) -> Optional[Resume]:
        """Soft delete resume after verifying ownership"""
        try:
            resume = self.get_by_id_and_user(resume_id, user_id)
            if not resume:
                return None

            return self.soft_delete(resume_id)
        except Exception as e:
            logger.error(f"Error soft deleting resume {resume_id} for user {user_id}: {e}")
            raise

    def duplicate_resume(
            self,
            resume_id: UUID,
            user_id: UUID,
            new_title: str
    ) -> Optional[Resume]:
        """Create a copy of existing resume"""
        try:
            original = self.get_by_id_and_user(resume_id, user_id)
            if not original:
                return None

            # Create new resume with same content
            return self.create_resume(
                user_id=user_id,
                title=new_title,
                content=original.content,
                template_id=original.template_id
            )
        except Exception as e:
            logger.error(f"Error duplicating resume {resume_id} for user {user_id}: {e}")
            raise

    def get_latest_version_for_user(self, user_id: UUID) -> Optional[int]:
        """Get the latest version number for user's resumes"""
        try:
            result = self.db.query(func.max(Resume.version)).filter(
                Resume.user_id == user_id
            ).scalar()
            return result if result is not None else 0
        except Exception as e:
            logger.error(f"Error getting latest version for user {user_id}: {e}")
            raise

    def get_resume_versions(self, user_id: UUID, base_title: str) -> List[Resume]:
        """Get all versions of resumes with similar title"""
        try:
            return self.db.query(Resume).filter(
                and_(
                    Resume.user_id == user_id,
                    Resume.title.like(f"%{base_title}%")
                )
            ).order_by(desc(Resume.version)).all()
        except Exception as e:
            logger.error(f"Error getting resume versions for user {user_id}: {e}")
            raise

    def search_resumes(
            self,
            user_id: UUID,
            search_term: str,
            page: int = 1,
            size: int = 10
    ) -> tuple[List[Resume], int]:
        """Search user's resumes by title or content with count"""
        try:
            skip = (page - 1) * size

            # Build base query
            base_query = self.db.query(Resume).filter(
                and_(
                    Resume.user_id == user_id,
                    Resume.is_active == True
                )
            )

            # Add search conditions
            search_conditions = or_(
                Resume.title.ilike(f"%{search_term}%"),
                Resume.content.astext.ilike(f"%{search_term}%")
            )

            # Get count for pagination
            total_count = base_query.filter(search_conditions).count()

            # Get results with pagination
            results = base_query.filter(search_conditions)\
                .order_by(desc(Resume.updated_at))\
                .offset(skip)\
                .limit(size)\
                .all()

            return results, total_count

        except Exception as e:
            logger.error(f"Error searching resumes for user {user_id}: {e}")
            raise

    def get_user_resume_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get statistics about user's resumes"""
        try:
            total_resumes = self.count_by_user(user_id)
            active_resumes = self.count_by_user(user_id, is_active=True)
            inactive_resumes = total_resumes - active_resumes

            # Get latest resume
            latest_resume = self.db.query(Resume).filter(
                and_(
                    Resume.user_id == user_id,
                    Resume.is_active == True
                )
            ).order_by(desc(Resume.updated_at)).first()

            # Get template usage stats
            template_stats = self.db.query(
                Resume.template_id,
                func.count(Resume.id).label('count')
            ).filter(
                and_(
                    Resume.user_id == user_id,
                    Resume.is_active == True
                )
            ).group_by(Resume.template_id).all()

            return {
                "total_resumes": total_resumes,
                "active_resumes": active_resumes,
                "inactive_resumes": inactive_resumes,
                "latest_resume": {
                    "id": str(latest_resume.id),
                    "title": latest_resume.title,
                    "updated_at": latest_resume.updated_at
                } if latest_resume else None,
                "template_usage": [
                    {"template_id": stat.template_id, "count": stat.count}
                    for stat in template_stats
                ]
            }
        except Exception as e:
            logger.error(f"Error getting resume stats for user {user_id}: {e}")
            raise

    def get_resumes_by_template(self, template_id: str, limit: int = 10) -> List[Resume]:
        """Get resumes using a specific template"""
        try:
            return self.db.query(Resume).filter(
                and_(
                    Resume.template_id == template_id,
                    Resume.is_active == True
                )
            ).order_by(desc(Resume.created_at)).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting resumes by template {template_id}: {e}")
            raise

    def bulk_update_template(self, old_template_id: str, new_template_id: str) -> int:
        """Bulk update template for multiple resumes"""
        try:
            result = self.db.query(Resume).filter(
                Resume.template_id == old_template_id
            ).update({"template_id": new_template_id})

            self.db.commit()
            logger.info(f"Updated {result} resumes from template {old_template_id} to {new_template_id}")
            return result
        except Exception as e:
            logger.error(f"Error bulk updating template: {e}")
            self.db.rollback()
            raise

    def get_resumes_by_date_range(
            self,
            user_id: UUID,
            start_date,
            end_date,
            is_active: Optional[bool] = None
    ) -> List[Resume]:
        """Get resumes created within date range"""
        try:
            query = self.db.query(Resume).filter(
                and_(
                    Resume.user_id == user_id,
                    Resume.created_at >= start_date,
                    Resume.created_at <= end_date
                )
            )

            if is_active is not None:
                query = query.filter(Resume.is_active == is_active)

            return query.order_by(desc(Resume.created_at)).all()

        except Exception as e:
            logger.error(f"Error getting resumes by date range for user {user_id}: {e}")
            raise