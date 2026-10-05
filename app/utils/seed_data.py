"""
Data seeder - connects to your actual data source.
Modify this file to load products from your real database/API.
"""

import logging
from typing import Any

from app.models.database import get_db_context
from app.models.media import Media
from app.models.product import Product

logger = logging.getLogger(__name__)


async def seed_from_external_source(
    products: list[dict[str, Any]], media: list[dict[str, Any]] | None = None
):
    """
    Seed database from external data source.

    Call this with your real product data:

    Example:
        products = await fetch_from_your_api()
        await seed_from_external_source(products)

    Args:
        products: List of product dictionaries with keys:
            - name, description, category, brand, price
            - rating, stock, image_url, etc.
        media: Optional list of media dictionaries
    """
    async with get_db_context() as db:
        # Add products
        for product_data in products:
            product = Product(**product_data)
            db.add(product)

        # Add media if provided
        if media:
            for media_data in media:
                m = Media(**media_data)
                db.add(m)

        await db.commit()
        logger.info(f"Seeded {len(products)} products and {len(media) if media else 0} media items")


async def seed_sample_data():
    """
    Called on app startup.
    Connect this to your actual data source.
    """
    # No demo data - connect to your real data source here
    # Example:
    # products = await your_api_client.fetch_products()
    # await seed_from_external_source(products)

    logger.info("No sample data loaded - connect your data source in seed_data.py")
    pass
