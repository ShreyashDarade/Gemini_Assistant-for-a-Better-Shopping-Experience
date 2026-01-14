"""
Media API router.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.media import (
    MediaSchema,
    MediaSummary,
    MediaSearchResponse,
    MediaCategoryResponse,
)
from app.services.media_service import get_media_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["Media"])


@router.get(
    "",
    response_model=MediaSearchResponse,
    summary="Search media",
    description="Search media assets (images, videos, tutorials)"
)
async def search_media(
    query: Optional[str] = Query(default=None, max_length=200),
    type: Optional[str] = Query(
        default=None,
        pattern="^(image|video|document|audio)$"
    ),
    category: Optional[str] = Query(default=None),
    product_id: Optional[int] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50)
):
    """
    Search media assets.
    
    **Media types:**
    - `image`: Product images, infographics
    - `video`: Tutorial videos, demos
    - `document`: PDFs, guides
    - `audio`: Audio guides
    
    **Categories:**
    - `product`: Product-related media
    - `tutorial`: How-to guides
    - `troubleshoot`: Troubleshooting content
    - `promotional`: Marketing content
    """
    try:
        media_service = get_media_service()
        
        media = await media_service.search(
            query=query,
            media_type=type,
            category=category,
            product_id=product_id,
            limit=limit
        )
        
        return MediaSearchResponse(
            media=[MediaSummary(**m.to_summary()) for m in media],
            total_count=len(media)
        )
        
    except Exception as e:
        logger.exception(f"Media search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/categories",
    response_model=List[MediaCategoryResponse],
    summary="Get media categories",
    description="Get all media categories with counts"
)
async def get_categories():
    """Get all media categories."""
    try:
        media_service = get_media_service()
        categories = await media_service.get_categories()
        return [MediaCategoryResponse(**c) for c in categories]
    except Exception as e:
        logger.exception(f"Get media categories error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/tutorials",
    response_model=List[MediaSummary],
    summary="Find tutorials",
    description="Find tutorials and guides"
)
async def find_tutorials(
    issue: Optional[str] = Query(
        default=None,
        max_length=500,
        description="Issue or topic"
    ),
    product_id: Optional[int] = Query(default=None),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20)
):
    """Find relevant tutorials."""
    try:
        media_service = get_media_service()
        
        tutorials = await media_service.find_tutorials(
            issue=issue,
            product_id=product_id,
            category=category,
            limit=limit
        )
        
        return [MediaSummary(**t.to_summary()) for t in tutorials]
        
    except Exception as e:
        logger.exception(f"Find tutorials error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{media_id}",
    response_model=MediaSchema,
    summary="Get media details",
    description="Get full details for a media asset"
)
async def get_media(media_id: int):
    """Get media by ID."""
    try:
        media_service = get_media_service()
        media = await media_service.get_by_id(media_id)
        
        if not media:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Media {media_id} not found"
            )
        
        return MediaSchema(**media.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Get media error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/product/{product_id}",
    response_model=List[MediaSummary],
    summary="Get product media",
    description="Get all media for a specific product"
)
async def get_product_media(
    product_id: int,
    type: Optional[str] = Query(
        default=None,
        pattern="^(image|video|document|audio)$"
    )
):
    """Get all media for a product."""
    try:
        media_service = get_media_service()
        media = await media_service.get_product_media(product_id, type)
        return [MediaSummary(**m.to_summary()) for m in media]
    except Exception as e:
        logger.exception(f"Get product media error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
