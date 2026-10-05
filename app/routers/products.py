"""
Products API router.
"""

import logging

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.product import (
    BrandResponse,
    CategoryResponse,
    ProductCompareRequest,
    ProductCompareResponse,
    ProductSchema,
    ProductSearchResponse,
    ProductSummary,
)
from app.services.product_service import get_product_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "",
    response_model=ProductSearchResponse,
    summary="Search products",
    description="Search and filter products with pagination",
)
async def search_products(
    query: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None),
    brand: str | None = Query(default=None),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    min_rating: float | None = Query(default=None, ge=0, le=5),
    in_stock_only: bool = Query(default=False),
    sort_by: str = Query(
        default="relevance", pattern="^(relevance|price_asc|price_desc|rating|newest)$"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
):
    """
    Search products with filters.

    **Sort options:**
    - `relevance`: Best match (default)
    - `price_asc`: Lowest price first
    - `price_desc`: Highest price first
    - `rating`: Highest rated first
    - `newest`: Most recent first
    """
    try:
        product_service = get_product_service()

        result = await product_service.search(
            query=query,
            category=category,
            brand=brand,
            min_price=min_price,
            max_price=max_price,
            min_rating=min_rating,
            in_stock_only=in_stock_only,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )

        return ProductSearchResponse(
            products=[ProductSummary(**p.to_summary()) for p in result.products],
            total_count=result.total_count,
            page=result.page,
            page_size=result.page_size,
            total_pages=(result.total_count + result.page_size - 1) // result.page_size,
            filters_applied=result.filters_applied,
        )

    except Exception as e:
        logger.exception(f"Product search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error"
        ) from e


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
    summary="Get categories",
    description="Get all product categories with counts",
)
async def get_categories():
    """Get all product categories."""
    try:
        product_service = get_product_service()
        categories = await product_service.get_categories()
        return [CategoryResponse(**c) for c in categories]
    except Exception as e:
        logger.exception(f"Get categories error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error"
        ) from e


@router.get(
    "/brands",
    response_model=list[BrandResponse],
    summary="Get brands",
    description="Get all brands with product counts",
)
async def get_brands(category: str | None = Query(default=None)):
    """Get all brands, optionally filtered by category."""
    try:
        product_service = get_product_service()
        brands = await product_service.get_brands(category)
        return [BrandResponse(**b) for b in brands]
    except Exception as e:
        logger.exception(f"Get brands error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error"
        ) from e


@router.get(
    "/{product_id}",
    response_model=ProductSchema,
    summary="Get product details",
    description="Get full details for a product",
)
async def get_product(product_id: int):
    """Get product by ID."""
    try:
        product_service = get_product_service()
        product = await product_service.get_by_id(product_id)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {product_id} not found"
            )

        return ProductSchema(**product.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Get product error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error"
        ) from e


@router.get(
    "/{product_id}/similar",
    response_model=list[ProductSummary],
    summary="Get similar products",
    description="Get products similar to the specified product",
)
async def get_similar_products(product_id: int, limit: int = Query(default=5, ge=1, le=20)):
    """Get similar products."""
    try:
        product_service = get_product_service()
        similar = await product_service.get_similar(product_id, limit)
        return [ProductSummary(**p.to_summary()) for p in similar]
    except Exception as e:
        logger.exception(f"Get similar products error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error"
        ) from e


@router.post(
    "/compare",
    response_model=ProductCompareResponse,
    summary="Compare products",
    description="Compare 2-4 products side by side",
)
async def compare_products(request: ProductCompareRequest):
    """Compare multiple products."""
    try:
        product_service = get_product_service()
        comparison = await product_service.compare(request.product_ids)

        if len(comparison.products) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Need at least 2 valid products to compare",
            )

        return ProductCompareResponse(
            products=[ProductSchema(**p.to_dict()) for p in comparison.products],
            comparison_fields=comparison.comparison_fields,
            comparison_data=comparison.comparison_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Compare products error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error"
        ) from e
