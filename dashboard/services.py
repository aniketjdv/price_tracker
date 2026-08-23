from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .data_providers import get_provider
from .data_providers.simulator import MARKETPLACES
from .models import Category, Notification, Platform, PriceAlert, PriceHistory, Product, ProductListing


PLATFORM_COLORS = {
    "Amazon": ("#FF9900", "#FFF7ED"),
    "Flipkart": ("#2874F0", "#EFF6FF"),
    "Myntra": ("#FF3F6C", "#FFF1F4"),
    "Croma": ("#00A887", "#F0FDF4"),
    "Reliance Digital": ("#E31837", "#FEF2F2"),
}


def detect_price_drop(previous_price, current_price):
    previous = Decimal(str(previous_price))
    current = Decimal(str(current_price))
    amount = max(previous - current, Decimal("0"))
    percentage = (amount * 100 / previous).quantize(Decimal("0.01")) if previous else Decimal("0")
    return {"dropped": current < previous, "amount": amount, "percentage": percentage}


def _platform(name):
    color, bg_color = PLATFORM_COLORS.get(name, ("#000000", "#F5F5F5"))
    platform, _ = Platform.objects.get_or_create(name=name, defaults={"color": color, "bg_color": bg_color})
    return platform


def _sync_legacy_product(product, listing_data, platform):
    product.brand = listing_data["brand"]
    product.category = Category.objects.get_or_create(name=listing_data["category"])[0]
    product.platform = platform
    product.current_price = listing_data["price"]
    product.original_price = listing_data["mrp"]
    product.lowest_price = listing_data["price"]
    product.discount = round(listing_data["discount_percentage"])
    product.rating = listing_data["rating"]
    product.reviews = listing_data["review_count"]
    product.image_url = listing_data["image_url"]
    product.url = listing_data["product_url"]
    product.stock = Product.STOCK_IN if listing_data["availability"] else Product.STOCK_OUT
    product.updated = "just now"
    product.save()


@transaction.atomic
def seed_simulator_data(count=60, days=60, seed=42, reset=False):
    provider = get_provider("simulator")
    if reset:
        PriceHistory.objects.all().delete()
        ProductListing.objects.all().delete()
        Product.objects.all().delete()

    response = provider.get_products(count=count)
    products = response["products"]
    for index, first_listing in enumerate(products):
        product = Product.objects.filter(name=first_listing["name"]).first()
        if not product:
            product = Product(name=first_listing["name"])
        primary_platform = _platform(first_listing["marketplace"])
        _sync_legacy_product(product, first_listing, primary_platform)

        for marketplace in MARKETPLACES:
            listing_data = provider.get_products(count=index + 1, marketplace=marketplace)["products"][-1]
            platform = _platform(marketplace)
            listing, _ = ProductListing.objects.update_or_create(
                platform=platform,
                external_product_id=listing_data["external_id"],
                defaults={
                    "product": product,
                    "seller": listing_data["seller"],
                    "current_price": listing_data["price"],
                    "mrp": listing_data["mrp"],
                    "discount_percentage": listing_data["discount_percentage"],
                    "availability": listing_data["availability"],
                    "rating": listing_data["rating"],
                    "review_count": listing_data["review_count"],
                    "product_url": listing_data["product_url"],
                },
            )
            if not listing.price_history.exists():
                PriceHistory.objects.bulk_create([
                    PriceHistory(product_listing=listing, price=point["price"], recorded_at=point["recorded_at"])
                    for point in provider.historical_prices(listing_data, days=days, seed=seed + index)
                ])
        product.lowest_price = product.listings.order_by("current_price").values_list("current_price", flat=True).first()
        product.save(update_fields=["lowest_price", "updated_at"])

    if not PriceAlert.objects.exists() and Product.objects.exists():
        product = Product.objects.first()
        PriceAlert.objects.create(product=product, target_price=product.lowest_price or product.current_price, current_price=product.current_price)
    if not Notification.objects.exists():
        Notification.objects.create(type="drop", title="Simulation ready", body="Demo prices are provided by the local simulator.", time="just now", color="#10B981", bg_color="#F0FDF4")
    return len(products)


def ensure_demo_data():
    if not ProductListing.objects.exists():
        seed_simulator_data()


def update_simulated_prices(seed=None):
    provider = get_provider("simulator")
    listings = ProductListing.objects.select_related("product", "platform")
    updated = 0
    updated_products = set()
    for listing in listings:
        product_data = provider.get_product(listing.external_product_id)
        if not product_data:
            continue
        new_price = Decimal(str(product_data["product"]["price"]))
        previous = listing.current_price
        change = detect_price_drop(previous, new_price)
        listing.current_price = new_price
        listing.discount_percentage = ((listing.mrp - new_price) * 100 / listing.mrp).quantize(Decimal("0.01")) if listing.mrp else 0
        listing.last_updated = timezone.now()
        listing.save(update_fields=["current_price", "discount_percentage", "last_updated"])
        PriceHistory.objects.create(product_listing=listing, price=new_price, recorded_at=timezone.now())
        if change["dropped"] and listing.product.tracked:
            Notification.objects.create(type="drop", title="Price dropped", body=f"{listing.product.name} dropped by ₹{change['amount']:.0f} on {listing.platform.name}", time="just now")
        
        # Keep product current price in sync with primary or lowest listing
        product = listing.product
        if product.id not in updated_products:
            lowest = product.listings.order_by("current_price").values_list("current_price", flat=True).first() or new_price
            product.current_price = new_price
            product.lowest_price = min(product.lowest_price or lowest, lowest)
            product.save(update_fields=["current_price", "lowest_price", "updated_at"])
            updated_products.add(product.id)

            # Check and trigger any active price alerts
            for alert in product.alerts.all():
                alert.current_price = product.current_price
                if alert.status == PriceAlert.STATUS_WATCHING and product.current_price <= alert.target_price:
                    alert.status = PriceAlert.STATUS_TRIGGERED
                    Notification.objects.create(
                        type="alert",
                        title="Target Price Reached!",
                        body=f"{product.name} reached your target price of ₹{alert.target_price:,.0f} (Current: ₹{product.current_price:,.0f})!",
                        time="just now",
                        color="#10B981",
                        bg_color="#F0FDF4",
                    )
                alert.save(update_fields=["current_price", "status"])

        updated += 1
    return updated
