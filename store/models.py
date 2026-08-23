"""The storefront intentionally reuses dashboard's shared catalog models.

Keeping Product, ProductListing, and PriceHistory in one place means the store
and the price tracker observe the same prices and history.
"""

from dashboard.models import Category, PriceHistory, Product, ProductListing

__all__ = ["Category", "PriceHistory", "Product", "ProductListing"]
