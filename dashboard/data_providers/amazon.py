from .base import EcommerceProvider


class AmazonProvider(EcommerceProvider):
    """Integration point for a future legitimate Amazon API client."""

    def __init__(self, **kwargs):
        self.api_key = kwargs.get("api_key")
        self.api_secret = kwargs.get("api_secret")
        self.partner_tag = kwargs.get("partner_tag")

    def search_products(self, query, **kwargs):
        raise NotImplementedError("Amazon API integration is not configured")

    def get_product(self, product_id):
        raise NotImplementedError("Amazon API integration is not configured")

    def get_price(self, product_id):
        raise NotImplementedError("Amazon API integration is not configured")

    def get_products(self, **kwargs):
        raise NotImplementedError("Amazon API integration is not configured")
