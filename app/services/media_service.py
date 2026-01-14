"""
Media service for visual aids, tutorials, and product media.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select, or_, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import Media, MediaType, MediaCategory
from app.models.database import get_db_context

logger = logging.getLogger(__name__)


class MediaService:
    """
    Service for managing and retrieving media assets.
    """
    
    async def search(
        self,
        query: Optional[str] = None,
        media_type: Optional[str] = None,
        category: Optional[str] = None,
        product_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Media]:
        """
        Search media assets.
        
        Args:
            query: Free-text search in title/description
            media_type: Filter by type (image, video, document)
            category: Filter by category (tutorial, troubleshoot, etc.)
            product_id: Filter by associated product
            tags: Filter by tags
            limit: Maximum results
        
        Returns:
            List of matching media assets
        """
        async with get_db_context() as db:
            stmt = select(Media)
            conditions = []
            
            if query:
                search_term = f"%{query.lower()}%"
                conditions.append(
                    or_(
                        func.lower(Media.title).like(search_term),
                        func.lower(Media.description).like(search_term),
                    )
                )
            
            if media_type:
                conditions.append(Media.type == media_type)
            
            if category:
                conditions.append(Media.category == category)
            
            # Note: JSON containment varies by database
            # For SQLite, we use string matching
            if product_id is not None:
                conditions.append(
                    func.cast(Media.product_ids, String).like(f"%{product_id}%")
                )
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
            
            stmt = stmt.order_by(desc(Media.created_at)).limit(limit)
            
            result = await db.execute(stmt)
            return list(result.scalars().all())
    
    async def get_by_id(self, media_id: int) -> Optional[Media]:
        """Get media by ID."""
        async with get_db_context() as db:
            result = await db.execute(
                select(Media).where(Media.id == media_id)
            )
            return result.scalar_one_or_none()
    
    async def get_product_media(
        self,
        product_id: int,
        media_type: Optional[str] = None
    ) -> List[Media]:
        """Get all media for a product."""
        async with get_db_context() as db:
            stmt = select(Media).where(
                func.cast(Media.product_ids, String).like(f"%{product_id}%")
            )
            
            if media_type:
                stmt = stmt.where(Media.type == media_type)
            
            stmt = stmt.order_by(Media.type, Media.created_at)
            
            result = await db.execute(stmt)
            return list(result.scalars().all())
    
    async def find_tutorials(
        self,
        product_id: Optional[int] = None,
        category: Optional[str] = None,
        issue: Optional[str] = None,
        limit: int = 5
    ) -> List[Media]:
        """
        Find relevant tutorial videos.
        
        Args:
            product_id: Associated product
            category: Product category
            issue: Issue description for troubleshooting
            limit: Maximum results
        
        Returns:
            List of tutorial media
        """
        async with get_db_context() as db:
            conditions = [
                Media.category.in_([
                    MediaCategory.TUTORIAL.value,
                    MediaCategory.TROUBLESHOOT.value,
                    MediaCategory.GUIDE.value,
                ])
            ]
            
            # Prefer videos
            stmt = select(Media).where(and_(*conditions))
            
            if product_id is not None:
                # First try product-specific
                product_stmt = stmt.where(
                    func.cast(Media.product_ids, String).like(f"%{product_id}%")
                )
                result = await db.execute(product_stmt.limit(limit))
                media = list(result.scalars().all())
                if media:
                    return media
            
            if issue:
                # Search by issue keywords
                search_term = f"%{issue.lower()}%"
                issue_stmt = stmt.where(
                    or_(
                        func.lower(Media.title).like(search_term),
                        func.lower(Media.description).like(search_term),
                        func.cast(Media.related_issues, String).like(search_term),
                        func.cast(Media.keywords, String).like(search_term),
                    )
                )
                result = await db.execute(issue_stmt.limit(limit))
                media = list(result.scalars().all())
                if media:
                    return media
            
            # Fallback to general tutorials
            result = await db.execute(stmt.limit(limit))
            return list(result.scalars().all())
    
    async def get_troubleshoot_media(
        self,
        issue: str,
        product_model: Optional[str] = None,
        limit: int = 3
    ) -> List[Media]:
        """
        Find troubleshooting media for an issue.
        
        Args:
            issue: Issue description
            product_model: Specific product model
            limit: Maximum results
        
        Returns:
            List of troubleshooting media
        """
        async with get_db_context() as db:
            search_terms = issue.lower().split()
            
            conditions = [
                Media.category == MediaCategory.TROUBLESHOOT.value,
            ]
            
            # Search in related_issues, keywords, title, description
            search_conditions = []
            for term in search_terms[:5]:  # Limit terms
                term_pattern = f"%{term}%"
                search_conditions.append(
                    or_(
                        func.lower(Media.title).like(term_pattern),
                        func.lower(Media.description).like(term_pattern),
                        func.cast(Media.related_issues, String).like(term_pattern),
                        func.cast(Media.keywords, String).like(term_pattern),
                    )
                )
            
            if search_conditions:
                conditions.append(or_(*search_conditions))
            
            stmt = select(Media).where(and_(*conditions))
            
            # Prefer videos
            stmt = stmt.order_by(
                desc(Media.type == MediaType.VIDEO.value),
                desc(Media.created_at)
            ).limit(limit)
            
            result = await db.execute(stmt)
            return list(result.scalars().all())
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all media categories with counts."""
        async with get_db_context() as db:
            result = await db.execute(
                select(
                    Media.category,
                    func.count(Media.id).label("count")
                )
                .group_by(Media.category)
                .order_by(desc(func.count(Media.id)))
            )
            return [
                {"category": row[0], "count": row[1]}
                for row in result.all()
            ]


# Import String for type casting
from sqlalchemy import String

# Singleton instance
_media_service: Optional[MediaService] = None


def get_media_service() -> MediaService:
    """Get or create media service instance."""
    global _media_service
    if _media_service is None:
        _media_service = MediaService()
    return _media_service
