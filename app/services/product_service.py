"""
Product service for search, recommendations, and comparisons.
Optimized for high concurrency with async operations.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select, or_, and_, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.database import get_db_context
from app.services.entity_extractor import ExtractedEntities

logger = logging.getLogger(__name__)


class ProductSearchResult:
    """Container for product search results."""
    
    def __init__(
        self,
        products: List[Product],
        total_count: int,
        page: int = 1,
        page_size: int = 10,
        filters_applied: Dict[str, Any] = None
    ):
        self.products = products
        self.total_count = total_count
        self.page = page
        self.page_size = page_size
        self.filters_applied = filters_applied or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "products": [p.to_summary() for p in self.products],
            "total_count": self.total_count,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": (self.total_count + self.page_size - 1) // self.page_size,
            "filters_applied": self.filters_applied,
        }


class ProductComparison:
    """Container for product comparison results."""
    
    def __init__(
        self,
        products: List[Product],
        comparison_fields: List[str],
        comparison_data: Dict[str, Dict[str, Any]]
    ):
        self.products = products
        self.comparison_fields = comparison_fields
        self.comparison_data = comparison_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "products": [p.to_dict() for p in self.products],
            "comparison_fields": self.comparison_fields,
            "comparison_data": self.comparison_data,
        }


class ProductService:
    """
    Product service for search, filtering, recommendations, and comparisons.
    """
    
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 50
    
    async def search(
        self,
        query: Optional[str] = None,
        entities: Optional[ExtractedEntities] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        tags: Optional[List[str]] = None,
        in_stock_only: bool = False,
        sort_by: str = "relevance",
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE
    ) -> ProductSearchResult:
        """
        Search products with filters.
        
        Args:
            query: Free-text search query
            entities: Extracted entities from user query
            category: Filter by category
            brand: Filter by brand
            min_price: Minimum price filter
            max_price: Maximum price filter
            min_rating: Minimum rating filter
            tags: Filter by tags
            in_stock_only: Only show in-stock items
            sort_by: Sort order (relevance, price_asc, price_desc, rating, newest)
            page: Page number (1-indexed)
            page_size: Results per page
        
        Returns:
            ProductSearchResult with products and pagination info
        """
        page_size = min(page_size, self.MAX_PAGE_SIZE)
        offset = (page - 1) * page_size
        
        # Apply entities if provided
        if entities:
            if entities.categories and not category:
                category = entities.categories[0]
            if entities.brands and not brand:
                brand = entities.brands[0]
            if entities.min_price is not None and min_price is None:
                min_price = entities.min_price
            if entities.max_price is not None and max_price is None:
                max_price = entities.max_price
        
        filters_applied = {}
        
        async with get_db_context() as db:
            # Build base query
            stmt = select(Product)
            conditions = []
            
            # Text search
            if query:
                search_term = f"%{query.lower()}%"
                conditions.append(
                    or_(
                        func.lower(Product.name).like(search_term),
                        func.lower(Product.description).like(search_term),
                        func.lower(Product.brand).like(search_term),
                    )
                )
                filters_applied["query"] = query
            
            # Category filter
            if category:
                conditions.append(func.lower(Product.category) == category.lower())
                filters_applied["category"] = category
            
            # Brand filter
            if brand:
                conditions.append(func.lower(Product.brand) == brand.lower())
                filters_applied["brand"] = brand
            
            # Price filters
            if min_price is not None:
                conditions.append(Product.price >= min_price)
                filters_applied["min_price"] = min_price
            
            if max_price is not None:
                conditions.append(Product.price <= max_price)
                filters_applied["max_price"] = max_price
            
            # Rating filter
            if min_rating is not None:
                conditions.append(Product.rating >= min_rating)
                filters_applied["min_rating"] = min_rating
            
            # Stock filter
            if in_stock_only:
                conditions.append(Product.stock > 0)
                filters_applied["in_stock_only"] = True
            
            # Apply conditions
            if conditions:
                stmt = stmt.where(and_(*conditions))
            
            # Get total count
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total_result = await db.execute(count_stmt)
            total_count = total_result.scalar() or 0
            
            # Apply sorting
            if sort_by == "price_asc":
                stmt = stmt.order_by(asc(Product.price))
            elif sort_by == "price_desc":
                stmt = stmt.order_by(desc(Product.price))
            elif sort_by == "rating":
                stmt = stmt.order_by(desc(Product.rating), desc(Product.review_count))
            elif sort_by == "newest":
                stmt = stmt.order_by(desc(Product.created_at))
            else:  # relevance - default
                if query:
                    # Prioritize exact matches in name
                    stmt = stmt.order_by(
                        desc(func.lower(Product.name).like(f"%{query.lower()}%")),
                        desc(Product.rating),
                        desc(Product.review_count)
                    )
                else:
                    stmt = stmt.order_by(desc(Product.rating), desc(Product.review_count))
            
            # Apply pagination
            stmt = stmt.offset(offset).limit(page_size)
            
            # Execute query
            result = await db.execute(stmt)
            products = list(result.scalars().all())
        
        return ProductSearchResult(
            products=products,
            total_count=total_count,
            page=page,
            page_size=page_size,
            filters_applied=filters_applied,
        )
    
    async def get_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID."""
        async with get_db_context() as db:
            result = await db.execute(
                select(Product).where(Product.id == product_id)
            )
            return result.scalar_one_or_none()
    
    async def get_by_ids(self, product_ids: List[int]) -> List[Product]:
        """Get multiple products by IDs."""
        if not product_ids:
            return []
        
        async with get_db_context() as db:
            result = await db.execute(
                select(Product).where(Product.id.in_(product_ids))
            )
            return list(result.scalars().all())
    
    async def get_similar(
        self,
        product_id: int,
        limit: int = 5
    ) -> List[Product]:
        """Find similar products based on category and brand."""
        product = await self.get_by_id(product_id)
        if not product:
            return []
        
        async with get_db_context() as db:
            result = await db.execute(
                select(Product)
                .where(
                    and_(
                        Product.id != product_id,
                        or_(
                            Product.category == product.category,
                            Product.brand == product.brand,
                        )
                    )
                )
                .order_by(desc(Product.rating))
                .limit(limit)
            )
            return list(result.scalars().all())
    
    async def get_recommendations(
        self,
        preferences: Dict[str, Any],
        discussed_products: List[int] = None,
        limit: int = 5
    ) -> List[Product]:
        """
        Get personalized recommendations based on preferences and history.
        
        Args:
            preferences: User preferences (categories, brands, price_range)
            discussed_products: Previously discussed product IDs
            limit: Number of recommendations
        
        Returns:
            List of recommended products
        """
        async with get_db_context() as db:
            conditions = [Product.stock > 0]  # Only in-stock
            
            # Exclude previously discussed
            if discussed_products:
                conditions.append(Product.id.notin_(discussed_products))
            
            # Apply preferences
            if preferences.get("categories"):
                conditions.append(
                    Product.category.in_(preferences["categories"])
                )
            
            if preferences.get("brands"):
                conditions.append(
                    Product.brand.in_(preferences["brands"])
                )
            
            if preferences.get("max_price"):
                conditions.append(
                    Product.price <= preferences["max_price"]
                )
            
            if preferences.get("min_rating"):
                conditions.append(
                    Product.rating >= preferences["min_rating"]
                )
            
            result = await db.execute(
                select(Product)
                .where(and_(*conditions))
                .order_by(desc(Product.rating), desc(Product.review_count))
                .limit(limit)
            )
            return list(result.scalars().all())
    
    async def compare(
        self,
        product_ids: List[int]
    ) -> ProductComparison:
        """
        Compare multiple products.
        
        Args:
            product_ids: List of product IDs to compare (max 4)
        
        Returns:
            ProductComparison with comparison data
        """
        product_ids = product_ids[:4]  # Limit to 4 products
        products = await self.get_by_ids(product_ids)
        
        if len(products) < 2:
            return ProductComparison(
                products=products,
                comparison_fields=[],
                comparison_data={}
            )
        
        # Standard comparison fields
        comparison_fields = [
            "price",
            "rating",
            "review_count",
            "brand",
            "category",
        ]
        
        # Build comparison data
        comparison_data = {}
        for field in comparison_fields:
            comparison_data[field] = {
                str(p.id): getattr(p, field) for p in products
            }
        
        # Add specs comparison if available
        all_spec_keys = set()
        for p in products:
            if p.specifications:
                all_spec_keys.update(p.specifications.keys())
        
        for spec_key in all_spec_keys:
            comparison_data[f"spec_{spec_key}"] = {
                str(p.id): p.specifications.get(spec_key, "N/A") if p.specifications else "N/A"
                for p in products
            }
            comparison_fields.append(f"spec_{spec_key}")
        
        return ProductComparison(
            products=products,
            comparison_fields=comparison_fields,
            comparison_data=comparison_data,
        )
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all categories with product counts."""
        async with get_db_context() as db:
            result = await db.execute(
                select(
                    Product.category,
                    func.count(Product.id).label("count")
                )
                .group_by(Product.category)
                .order_by(desc(func.count(Product.id)))
            )
            return [
                {"category": row[0], "count": row[1]}
                for row in result.all()
            ]
    
    async def get_brands(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all brands with product counts."""
        async with get_db_context() as db:
            stmt = select(
                Product.brand,
                func.count(Product.id).label("count")
            )
            
            if category:
                stmt = stmt.where(func.lower(Product.category) == category.lower())
            
            stmt = stmt.group_by(Product.brand).order_by(desc(func.count(Product.id)))
            
            result = await db.execute(stmt)
            return [
                {"brand": row[0], "count": row[1]}
                for row in result.all()
            ]


# Singleton instance
_product_service: Optional[ProductService] = None


def get_product_service() -> ProductService:
    """Get or create product service instance."""
    global _product_service
    if _product_service is None:
        _product_service = ProductService()
    return _product_service
