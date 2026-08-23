from datetime import timedelta
from decimal import Decimal
import random

from django.utils import timezone

from .base import EcommerceProvider


CATALOG = [
    ("Mobiles", "Samsung Galaxy S24 5G", "Samsung", 74999),
    ("Mobiles", "OnePlus 12 5G", "OnePlus", 64999),
    ("Laptops", "Lenovo IdeaPad Slim 5", "Lenovo", 62990),
    ("Laptops", "Apple MacBook Air M2", "Apple", 99990),
    ("Headphones", "Sony WH-1000XM5 Wireless", "Sony", 34990),
    ("Televisions", "Samsung 55 inch QLED 4K TV", "Samsung", 89990),
    ("Cameras", "Canon EOS R50 Mirrorless Camera", "Canon", 79990),
    ("Smart Watches", "Garmin Venu 3 Smartwatch", "Garmin", 45990),
    ("Gaming", "Sony PlayStation 5 Slim", "Sony", 54990),
    ("Home Appliances", "LG  frost-free double-door refrigerator", "LG", 58990),
    ("Fashion", "Nike Air Max 270 Running Shoes", "Nike", 12995),
    ("Accessories", "Apple AirPods Pro (2nd Generation)", "Apple", 24900),
]
MARKETPLACES = ["Amazon", "Flipkart", "Myntra", "Croma", "Reliance Digital"]
IMAGE_URLS = {
    "Mobiles": "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&h=600&fit=crop&auto=format",
    "Laptops": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&h=600&fit=crop&auto=format",
    "Headphones": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&h=600&fit=crop&auto=format",
    "Televisions": "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=600&h=600&fit=crop&auto=format",
    "Cameras": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=600&h=600&fit=crop&auto=format",
    "Smart Watches": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&h=600&fit=crop&auto=format",
    "Gaming": "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?w=600&h=600&fit=crop&auto=format",
    "Home Appliances": "https://images.unsplash.com/photo-1571175443880-49e1d25b2bc5?w=600&h=600&fit=crop&auto=format",
    "Fashion": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&h=600&fit=crop&auto=format",
    "Accessories": "https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1?w=600&h=600&fit=crop&auto=format",
}


class SimulatorProvider(EcommerceProvider):
    source = "simulator"

    def __init__(self, seed=42):
        self.random = random.Random(seed)

    def _product(self, index, marketplace=None):
        category, base_name, brand, mrp = CATALOG[index % len(CATALOG)]
        name = base_name if index < len(CATALOG) else f"{base_name} - Edition {index + 1:02d}"
        marketplace = marketplace or MARKETPLACES[index % len(MARKETPLACES)]
        external_id = f"SIM-{marketplace[:3].upper()}-{index + 1:03d}"
        discount = self.random.randint(5, 25)
        price = int(mrp * (100 - discount) / 100)
        return {
            "external_id": external_id,
            "name": name,
            "brand": brand,
            "category": category,
            "marketplace": marketplace,
            "price": price,
            "mrp": mrp,
            "discount_percentage": round((mrp - price) * 100 / mrp, 2),
            "currency": "INR",
            "availability": self.random.random() > 0.08,
            "rating": round(self.random.uniform(3.8, 4.8), 1),
            "review_count": self.random.randint(120, 25000),
            "product_url": f"https://example.com/{marketplace.lower().replace(' ', '-')}/product/{external_id}",
            "image_url": IMAGE_URLS[category],
            "seller": f"{marketplace} Marketplace Seller",
        }

    def get_products(self, **kwargs):
        count = min(int(kwargs.get("count", 60)), 100)
        marketplace = kwargs.get("marketplace")
        products = [self._product(index, marketplace) for index in range(count)]
        return {"source": self.source, "marketplace": marketplace or "multiple", "products": products}

    def search_products(self, query, **kwargs):
        response = self.get_products(**kwargs)
        needle = query.lower()
        response["products"] = [item for item in response["products"] if needle in item["name"].lower() or needle in item["brand"].lower()]
        return response

    def get_product(self, product_id):
        parts = product_id.split("-")
        marketplace = next((name for name in MARKETPLACES if name[:3].upper() == parts[1]), None) if len(parts) == 3 else None
        requested_index = int(parts[2]) - 1 if len(parts) == 3 and parts[2].isdigit() else None
        for index in range(100):
            product = self._product(index, marketplace)
            if product["external_id"] == product_id:
                return {"source": self.source, "marketplace": product["marketplace"], "product": product}
            if requested_index is not None and index >= requested_index:
                break
        return None

    def get_price(self, product_id):
        response = self.get_product(product_id)
        return response["product"]["price"] if response else None

    def historical_prices(self, listing, days=60, seed=42):
        rng = random.Random(seed)
        base = Decimal(str(listing["price"]))
        points = []
        price = base * Decimal("1.08")
        for offset in range(days - 1, -1, -1):
            seasonal = Decimal("0.94") if offset in (35, 14, 7) else Decimal("1")
            movement = Decimal(str(rng.uniform(-0.018, 0.018)))
            price = max(Decimal("100"), price * (Decimal("1") + movement) * seasonal)
            points.append({"recorded_at": timezone.now() - timedelta(days=offset), "price": price.quantize(Decimal("0.01"))})
        points[-1]["price"] = base
        return points
