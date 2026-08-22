from .base import EcommerceProvider


class FlipkartProvider(EcommerceProvider):
    """Integration point for a future legitimate Flipkart API client."""

    def __init__(self, **kwargs):
        self.api_key = kwargs.get("api_key")
        self.affiliate_id = kwargs.get("affiliate_id")

    def search_products(self, query, **kwargs):
        raise NotImplementedError("Flipkart API integration is not configured")

    def get_product(self, product_id):
        raise NotImplementedError("Flipkart API integration is not configured")

    def get_price(self, product_id):
        raise NotImplementedError("Flipkart API integration is not configured")

    def get_products(self, **kwargs):
        raise NotImplementedError("Flipkart API integration is not configured")
