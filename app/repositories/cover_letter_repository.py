from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, or_
from uuid import UUID
import logging

from app.repositories.base import BaseRepository
from app.models.cover_letter import CoverLetter

logger = logging.getLogger(__name__)


class CoverLetterRepository(BaseRepository[CoverLetter]):
    """Repository for Cover Letter model with specific business logic"""

    def __init__(self, db: Session):
        super().__init__(db, CoverLetter)

    def get_by_user(
            self,
            user_id: UUID,
            page: int = 1,
            size: int = 10,
            is_active: Optional[bool] = None,
            company_name: Optional[str] = None,
            order_by: str = "updated_at",
            order_desc: bool = True
    ) -> List[CoverLetter]:
        """Get all cover letters for a specific user"""
        try:
            filters = {"user_id": user_id}
            if is_active is not None:
                filters["is_active"] = is_active

            skip = (page - 1) * size

            # Build query
            query = self.db.query(CoverLetter).filter(
                CoverLetter.user_id == user_id
            )

            if is_active is not None:
                query = query.filter(CoverLetter.is_active == is_active)

            if company_name:
                query = query.filter(CoverLetter.company_name.ilike(f"%{company_name}%"))

            # Apply ordering
            if hasattr(CoverLetter, order_by):
                order_column = getattr(CoverLetter, order_by)
                if order_desc:
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(order_column)

            return query.offset(skip).limit(size).all()

        except Exception as e:
            logger.error(f"Error getting cover letters for user {user_id}: {e}")
            raise

    def count_by_user(
            self,
            user_id: UUID,
            is_active: Optional[bool] = None,
            company_name: Optional[str] = None
    ) -> int:
        """Count cover letters for a specific user"""
        try:
            query = self.db.query(CoverLetter).filter(
                CoverLetter.user_id == user_id
            )

            if is_active is not None:
                query = query.filter(CoverLetter.is_active == is_active)

            if company_name:
                query = query.filter(CoverLetter.company_name.ilike(f"%{company_name}%"))

            return query.count()

        except Exception as e:
            logger.error(f"Error counting cover letters for user {user_id}: {e}")
            raise

    def get_by_id_and_user(self, cover_letter_id: UUID, user_id: UUID) -> Optional[CoverLetter]:
        """Get cover letter by ID and verify ownership"""
        try:
            return self.db.query(CoverLetter).filter(
                and_(
                    CoverLetter.id == cover_letter_id,
                    CoverLetter.user_id == user_id
                )
            ).first()
        except Exception as e:
            logger.error(f"Error getting cover letter {cover_letter_id} for user {user_id}: {e}")
            raise

    def create_cover_letter(
            self,
            user_id: UUID,
            title: str,
            content: Dict[str, Any],
            job_title: Optional[str] = None,
            company_name: Optional[str] = None,
            hiring_manager_name: Optional[str] = None,
            template_id: str = "professional",
            resume_id: Optional[UUID] = None
    ) -> CoverLetter:
        """Create a new cover letter with automatic version numbering"""
        try:
            # Get the latest version for this user
            latest_version = self.get_latest_version_for_user(user_id)
            new_version = latest_version + 1 if latest_version else 1

            return self.create(
                user_id=user_id,
                title=title,
                job_title=job_title,
                company_name=company_name,
                hiring_manager_name=hiring_manager_name,
                content=content,
                template_id=template_id,
                resume_id=resume_id,
                version=new_version
            )
        except Exception as e:
            logger.error(f"Error creating cover letter for user {user_id}: {e}")
            raise

    def update_cover_letter(
            self,
            cover_letter_id: UUID,
            user_id: UUID,
            update_data: Dict[str, Any]
    ) -> Optional[CoverLetter]:
        """Update cover letter and increment version"""
        try:
            cover_letter = self.get_by_id_and_user(cover_letter_id, user_id)
            if not cover_letter:
                return None

            # Increment version if content is being updated
            if 'content' in update_data:
                update_data['version'] = cover_letter.version + 1

            # Remove None values
            clean_data = {k: v for k, v in update_data.items() if v is not None}

            return self.update(cover_letter_id, clean_data)
        except Exception as e:
            logger.error(f"Error updating cover letter {cover_letter_id} for user {user_id}: {e}")
            raise

    def delete_cover_letter(self, cover_letter_id: UUID, user_id: UUID) -> bool:
        """Delete cover letter after verifying ownership"""
        try:
            cover_letter = self.get_by_id_and_user(cover_letter_id, user_id)
            if not cover_letter:
                return False

            return self.delete(cover_letter_id)
        except Exception as e:
            logger.error(f"Error deleting cover letter {cover_letter_id} for user {user_id}: {e}")
            raise

    def duplicate_cover_letter(
            self,
            cover_letter_id: UUID,
            user_id: UUID,
            new_title: str,
            new_job_title: Optional[str] = None,
            new_company_name: Optional[str] = None
    ) -> Optional[CoverLetter]:
        """Create a copy of existing cover letter"""
        try:
            original = self.get_by_id_and_user(cover_letter_id, user_id)
            if not original:
                return None

            # Create new cover letter with same content
            return self.create_cover_letter(
                user_id=user_id,
                title=new_title,
                job_title=new_job_title or original.job_title,
                company_name=new_company_name or original.company_name,
                hiring_manager_name=original.hiring_manager_name,
                content=original.content,
                template_id=original.template_id,
                resume_id=original.resume_id
            )
        except Exception as e:
            logger.error(f"Error duplicating cover letter {cover_letter_id} for user {user_id}: {e}")
            raise

    def get_latest_version_for_user(self, user_id: UUID) -> Optional[int]:
        """Get the latest version number for user's cover letters"""
        try:
            result = self.db.query(func.max(CoverLetter.version)).filter(
                CoverLetter.user_id == user_id
            ).scalar()
            return result if result is not None else 0
        except Exception as e:
            logger.error(f"Error getting latest version for user {user_id}: {e}")
            raise

    def search_cover_letters(
            self,
            user_id: UUID,
            search_term: str,
            page: int = 1,
            size: int = 10
    ) -> tuple[List[CoverLetter], int]:
        """Search user's cover letters by title, company, or job title"""
        try:
            skip = (page - 1) * size

            # Build base query
            base_query = self.db.query(CoverLetter).filter(
                and_(
                    CoverLetter.user_id == user_id,
                    CoverLetter.is_active == True
                )
            )

            # Add search conditions
            search_conditions = or_(
                CoverLetter.title.ilike(f"%{search_term}%"),
                CoverLetter.job_title.ilike(f"%{search_term}%"),
                CoverLetter.company_name.ilike(f"%{search_term}%"),
                CoverLetter.content.astext.ilike(f"%{search_term}%")
            )

            # Get count for pagination
            total_count = base_query.filter(search_conditions).count()

            # Get results with pagination
            results = base_query.filter(search_conditions) \
                .order_by(desc(CoverLetter.updated_at)) \
                .offset(skip) \
                .limit(size) \
                .all()

            return results, total_count

        except Exception as e:
            logger.error(f"Error searching cover letters for user {user_id}: {e}")
            raise

    def get_cover_letters_by_company(
            self,
            user_id: UUID,
            company_name: str,
            limit: int = 10
    ) -> List[CoverLetter]:
        """Get cover letters for a specific company"""
        try:
            return self.db.query(CoverLetter).filter(
                and_(
                    CoverLetter.user_id == user_id,
                    CoverLetter.company_name.ilike(f"%{company_name}%"),
                    CoverLetter.is_active == True
                )
            ).order_by(desc(CoverLetter.created_at)).limit(limit).all()

        except Exception as e:
            logger.error(f"Error getting cover letters by company for user {user_id}: {e}")
            raise

    def get_cover_letters_by_resume(
            self,
            user_id: UUID,
            resume_id: UUID
    ) -> List[CoverLetter]:
        """Get cover letters associated with a specific resume"""
        try:
            return self.db.query(CoverLetter).filter(
                and_(
                    CoverLetter.user_id == user_id,
                    CoverLetter.resume_id == resume_id,
                    CoverLetter.is_active == True
                )
            ).order_by(desc(CoverLetter.created_at)).all()

        except Exception as e:
            logger.error(f"Error getting cover letters by resume {resume_id} for user {user_id}: {e}")
            raise

    def get_user_cover_letter_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get statistics about user's cover letters"""
        try:
            total_cover_letters = self.count_by_user(user_id)
            active_cover_letters = self.count_by_user(user_id, is_active=True)
            inactive_cover_letters = total_cover_letters - active_cover_letters

            # Get latest cover letter
            latest_cover_letter = self.db.query(CoverLetter).filter(
                and_(
                    CoverLetter.user_id == user_id,
                    CoverLetter.is_active == True
                )
            ).order_by(desc(CoverLetter.updated_at)).first()

            # Get template usage stats
            template_stats = self.db.query(
                CoverLetter.template_id,
                func.count(CoverLetter.id).label('count')
            ).filter(
                and_(
                    CoverLetter.user_id == user_id,
                    CoverLetter.is_active == True
                )
            ).group_by(CoverLetter.template_id).all()

            # Get company stats
            company_stats = self.db.query(
                CoverLetter.company_name,
                func.count(CoverLetter.id).label('count')
            ).filter(
                and_(
                    CoverLetter.user_id == user_id,
                    CoverLetter.is_active == True,
                    CoverLetter.company_name.isnot(None)
                )
            ).group_by(CoverLetter.company_name).order_by(desc('count')).limit(5).all()

            # Get average word count
            cover_letters = self.get_by_user(user_id, page=1, size=100, is_active=True)
            total_words = sum(cl.get_word_count() for cl in cover_letters)
            avg_word_count = int(total_words / len(cover_letters)) if cover_letters else 0

            return {
                "total_cover_letters": total_cover_letters,
                "active_cover_letters": active_cover_letters,
                "inactive_cover_letters": inactive_cover_letters,
                "latest_cover_letter": {
                    "id": str(latest_cover_letter.id),
                    "title": latest_cover_letter.title,
                    "company_name": latest_cover_letter.company_name,
                    "job_title": latest_cover_letter.job_title,
                    "updated_at": latest_cover_letter.updated_at
                } if latest_cover_letter else None,
                "template_usage": [
                    {"template_id": stat.template_id, "count": stat.count}
                    for stat in template_stats
                ],
                "top_companies": [
                    {"company_name": stat.company_name, "count": stat.count}
                    for stat in company_stats
                ],
                "average_word_count": avg_word_count
            }
        except Exception as e:
            logger.error(f"Error getting cover letter stats for user {user_id}: {e}")
            raise

    def get_cover_letters_by_template(self, template_id: str, limit: int = 10) -> List[CoverLetter]:
        """Get cover letters using a specific template"""
        try:
            return self.db.query(CoverLetter).filter(
                and_(
                    CoverLetter.template_id == template_id,
                    CoverLetter.is_active == True
                )
            ).order_by(desc(CoverLetter.created_at)).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting cover letters by template {template_id}: {e}")
            raise

    def bulk_update_template(self, old_template_id: str, new_template_id: str) -> int:
        """Bulk update template for multiple cover letters"""
        try:
            result = self.db.query(CoverLetter).filter(
                CoverLetter.template_id == old_template_id
            ).update({"template_id": new_template_id})

            self.db.commit()
            logger.info(f"Updated {result} cover letters from template {old_template_id} to {new_template_id}")
            return result
        except Exception as e:
            logger.error(f"Error bulk updating template: {e}")
            self.db.rollback()
            raise

    def get_cover_letters_by_date_range(
            self,
            user_id: UUID,
            start_date,
            end_date,
            is_active: Optional[bool] = None
    ) -> List[CoverLetter]:
        """Get cover letters created within date range"""
        try:
            query = self.db.query(CoverLetter).filter(
                and_(
                    CoverLetter.user_id == user_id,
                    CoverLetter.created_at >= start_date,
                    CoverLetter.created_at <= end_date
                )
            )

            if is_active is not None:
                query = query.filter(CoverLetter.is_active == is_active)

            return query.order_by(desc(CoverLetter.created_at)).all()

        except Exception as e:
            logger.error(f"Error getting cover letters by date range for user {user_id}: {e}")
            raise

    def mark_as_template(self, cover_letter_id: UUID, user_id: UUID) -> bool:
        """Mark cover letter as a template for reuse"""
        try:
            cover_letter = self.get_by_id_and_user(cover_letter_id, user_id)
            if not cover_letter:
                return False

            cover_letter.is_template = True
            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error marking cover letter {cover_letter_id} as template: {e}")
            self.db.rollback()
            raise

    def get_user_templates(self, user_id: UUID) -> List[CoverLetter]:
        """Get user's cover letter templates"""
        try:
            return self.db.query(CoverLetter).filter(
                and_(
                    CoverLetter.user_id == user_id,
                    CoverLetter.is_template == True,
                    CoverLetter.is_active == True
                )
            ).order_by(desc(CoverLetter.updated_at)).all()

        except Exception as e:
            logger.error(f"Error getting user templates for user {user_id}: {e}")
            raise