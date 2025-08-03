import logging
from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import and_, desc, asc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=declarative_base())


class BaseRepository(Generic[ModelType]):
    """Base repository class with common CRUD operations"""

    def __init__(self, db: Session, model: Type[ModelType]):
        self.db = db
        self.model = model

    def create(self, **kwargs) -> ModelType:
        """Create new record"""
        try:
            db_obj = self.model(**kwargs)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            logger.info(f"Created {self.model.__name__} with ID: {db_obj.id}")
            return db_obj
        except Exception as e:
            logger.error(f"Error creating {self.model.__name__}: {e}")
            self.db.rollback()
            raise

    def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """Get record by ID"""
        try:
            return self.db.query(self.model).filter(self.model.id == id).first()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by ID {id}: {e}")
            raise

    def get_multi(
            self,
            skip: int = 0,
            limit: int = 100,
            filters: Optional[Dict[str, Any]] = None,
            order_by: Optional[str] = None,
            order_desc: bool = False
    ) -> List[ModelType]:
        """Get multiple records with filters and pagination"""
        try:
            query = self.db.query(self.model)

            # Apply filters
            if filters:
                filter_conditions = []
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        if isinstance(value, list):
                            filter_conditions.append(getattr(self.model, key).in_(value))
                        else:
                            filter_conditions.append(getattr(self.model, key) == value)

                if filter_conditions:
                    query = query.filter(and_(*filter_conditions))

            # Apply ordering
            if order_by and hasattr(self.model, order_by):
                order_column = getattr(self.model, order_by)
                if order_desc:
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(asc(order_column))

            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting multiple {self.model.__name__}: {e}")
            raise

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with filters"""
        try:
            query = self.db.query(self.model)

            if filters:
                filter_conditions = []
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        if isinstance(value, list):
                            filter_conditions.append(getattr(self.model, key).in_(value))
                        else:
                            filter_conditions.append(getattr(self.model, key) == value)

                if filter_conditions:
                    query = query.filter(and_(*filter_conditions))

            return query.count()
        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise

    def update(self, id: UUID, update_data: Dict[str, Any]) -> Optional[ModelType]:
        """Update record by ID"""
        try:
            db_obj = self.get_by_id(id)
            if db_obj:
                for key, value in update_data.items():
                    if hasattr(db_obj, key) and value is not None:
                        setattr(db_obj, key, value)

                self.db.commit()
                self.db.refresh(db_obj)
                logger.info(f"Updated {self.model.__name__} with ID: {id}")
            return db_obj
        except Exception as e:
            logger.error(f"Error updating {self.model.__name__} with ID {id}: {e}")
            self.db.rollback()
            raise

    def delete(self, id: UUID) -> bool:
        """Delete record by ID"""
        try:
            db_obj = self.get_by_id(id)
            if db_obj:
                self.db.delete(db_obj)
                self.db.commit()
                logger.info(f"Deleted {self.model.__name__} with ID: {id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting {self.model.__name__} with ID {id}: {e}")
            self.db.rollback()
            raise

    def soft_delete(self, id: UUID) -> Optional[ModelType]:
        """Soft delete record (if model supports is_active field)"""
        if not hasattr(self.model, 'is_active'):
            raise NotImplementedError(f"{self.model.__name__} does not support soft delete")

        return self.update(id, {'is_active': False})

    def exists(self, **kwargs) -> bool:
        """Check if record exists with given criteria"""
        try:
            query = self.db.query(self.model)
            for key, value in kwargs.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)

            return query.first() is not None
        except Exception as e:
            logger.error(f"Error checking existence for {self.model.__name__}: {e}")
            raise

    def get_or_create(self, defaults: Optional[Dict[str, Any]] = None, **kwargs) -> tuple[ModelType, bool]:
        """Get existing record or create new one"""
        try:
            # Try to get existing record
            query = self.db.query(self.model)
            for key, value in kwargs.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)

            instance = query.first()

            if instance:
                return instance, False

            # Create new record
            create_data = {**kwargs}
            if defaults:
                create_data.update(defaults)

            instance = self.create(**create_data)
            return instance, True
        except Exception as e:
            logger.error(f"Error in get_or_create for {self.model.__name__}: {e}")
            raise

    def bulk_create(self, objects_data: List[Dict[str, Any]]) -> List[ModelType]:
        """Bulk create multiple records"""
        try:
            db_objects = [self.model(**data) for data in objects_data]
            self.db.add_all(db_objects)
            self.db.commit()

            for obj in db_objects:
                self.db.refresh(obj)

            logger.info(f"Bulk created {len(db_objects)} {self.model.__name__} records")
            return db_objects
        except Exception as e:
            logger.error(f"Error bulk creating {self.model.__name__}: {e}")
            self.db.rollback()
            raise

    def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """Bulk update multiple records"""
        try:
            updated_count = 0
            for update_data in updates:
                if 'id' in update_data:
                    record_id = update_data.pop('id')
                    if self.update(record_id, update_data):
                        updated_count += 1

            logger.info(f"Bulk updated {updated_count} {self.model.__name__} records")
            return updated_count
        except Exception as e:
            logger.error(f"Error bulk updating {self.model.__name__}: {e}")
            raise
