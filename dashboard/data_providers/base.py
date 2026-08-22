from abc import ABC, abstractmethod


class EcommerceProvider(ABC):
    """Provider contract shared by simulated and real marketplace integrations."""

    @abstractmethod
    def search_products(self, query, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def get_product(self, product_id):
        raise NotImplementedError

    @abstractmethod
    def get_price(self, product_id):
        raise NotImplementedError

    @abstractmethod
    def get_products(self, **kwargs):
        raise NotImplementedError
