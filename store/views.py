from decimal import Decimal

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from dashboard.models import PriceHistory, Product, ProductListing
from dashboard.services import ensure_demo_data


def _catalog_queryset():
    return Product.objects.select_related("category", "platform").prefetch_related("listings")


def _primary_listing(product):
    return product.listings.select_related("platform").order_by("current_price").first()


def _listing_payload(listing, request=None):
    product = listing.product
    product_url = reverse("store:product_detail", kwargs={"slug": product.slug})
    return {
        "product_id": listing.external_product_id,
        "name": product.name,
        "brand": product.brand,
        "category": product.category.name if product.category else "Uncategorised",
        "price": float(listing.current_price),
        "mrp": float(listing.mrp or product.original_price or listing.current_price),
        "discount_percentage": float(listing.discount_percentage),
        "currency": "INR",
        "availability": listing.availability,
        "product_url": request.build_absolute_uri(product_url) if request else product_url,
        "image_url": product.image_url,
        "seller": listing.seller or "ShopSphere",
        "rating": float(listing.rating),
        "review_count": listing.review_count,
    }


def home(request):
    ensure_demo_data()
    products = _catalog_queryset()
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    brand = request.GET.get("brand", "")
    availability = request.GET.get("availability", "")
    minimum = request.GET.get("min_price", "")
    maximum = request.GET.get("max_price", "")
    rating = request.GET.get("rating", "")
    sort = request.GET.get("sort", "popular")

    if query:
        products = products.filter(Q(name__icontains=query) | Q(brand__icontains=query) | Q(category__name__icontains=query))
    if category:
        products = products.filter(category__name=category)
    if brand:
        products = products.filter(brand=brand)
    if availability == "in_stock":
        products = products.filter(stock__in=[Product.STOCK_IN, Product.STOCK_LOW])
    if rating:
        products = products.filter(rating__gte=rating)
    if minimum.isdigit():
        products = products.filter(current_price__gte=Decimal(minimum))
    if maximum.isdigit():
        products = products.filter(current_price__lte=Decimal(maximum))

    ordering = {
        "price_asc": "current_price",
        "price_desc": "-current_price",
        "newest": "-created_at",
        "discount": "-discount",
        "rating": "-rating",
    }.get(sort, "-reviews")
    products = products.order_by(ordering)
    categories = Product.objects.values_list("category__name", flat=True).distinct().order_by("category__name")
    brands = Product.objects.exclude(brand="").values_list("brand", flat=True).distinct().order_by("brand")
    cart = request.session.get("store_cart", {})
    wishlist = request.session.get("store_wishlist", [])
    return render(request, "store/home.html", {
        "products": products,
        "categories": categories,
        "brands": brands,
        "query": query,
        "selected_category": category,
        "selected_brand": brand,
        "availability": availability,
        "min_price": minimum,
        "max_price": maximum,
        "rating": rating,
        "sort": sort,
        "cart_count": sum(cart.values()),
        "wishlist": [int(item) for item in wishlist],
    })


def product_detail(request, slug):
    ensure_demo_data()
    product = get_object_or_404(_catalog_queryset(), slug=slug)
    listing = _primary_listing(product)
    history = list(PriceHistory.objects.filter(product_listing=listing).order_by("recorded_at").values("price", "recorded_at")) if listing else []
    prices = [point["price"] for point in history]
    context = {
        "product": product,
        "listing": listing,
        "history": history,
        "lowest_price": min(prices) if prices else product.current_price,
        "highest_price": max(prices) if prices else product.current_price,
        "average_price": sum(prices, Decimal("0")) / len(prices) if prices else product.current_price,
        "cart_count": sum(request.session.get("store_cart", {}).values()),
        "is_wishlisted": product.id in [int(item) for item in request.session.get("store_wishlist", [])],
    }
    return render(request, "store/product_detail.html", context)


@require_POST
def add_to_cart(request, product_id):
    get_object_or_404(Product, id=product_id)
    cart = request.session.get("store_cart", {})
    key = str(product_id)
    cart[key] = int(cart.get(key, 0)) + 1
    request.session["store_cart"] = cart
    return redirect(request.POST.get("next") or "store:cart")


@require_POST
def remove_from_cart(request, product_id):
    cart = request.session.get("store_cart", {})
    cart.pop(str(product_id), None)
    request.session["store_cart"] = cart
    return redirect("store:cart")


def cart(request):
    cart_data = request.session.get("store_cart", {})
    products = Product.objects.filter(id__in=cart_data.keys()).select_related("category", "platform")
    items = [{"product": product, "quantity": int(cart_data.get(str(product.id), 1)), "total": product.current_price * int(cart_data.get(str(product.id), 1))} for product in products]
    return render(request, "store/cart.html", {"items": items, "total": sum((item["total"] for item in items), Decimal("0")), "cart_count": sum(cart_data.values())})


@require_POST
def toggle_wishlist(request, product_id):
    get_object_or_404(Product, id=product_id)
    wishlist = [int(item) for item in request.session.get("store_wishlist", [])]
    if product_id in wishlist:
        wishlist.remove(product_id)
    else:
        wishlist.append(product_id)
    request.session["store_wishlist"] = wishlist
    return redirect(request.POST.get("next") or "store:home")


def _api_listings(queryset):
    return [_listing_payload(listing) for listing in queryset.select_related("product", "product__category", "platform")]


def api_products(request):
    ensure_demo_data()
    listings = ProductListing.objects.filter(availability=True)
    query = request.GET.get("q", "").strip()
    if query:
        listings = listings.filter(Q(product__name__icontains=query) | Q(product__brand__icontains=query) | Q(product__category__name__icontains=query))
    return JsonResponse({"source": "shopsphere-demo", "products": _api_listings(listings[:100])})


def api_search(request):
    return api_products(request)


def _get_listing(product_id):
    return get_object_or_404(ProductListing.objects.select_related("product", "product__category", "platform"), external_product_id=product_id)


def api_product(request, product_id):
    ensure_demo_data()
    return JsonResponse(_listing_payload(_get_listing(product_id), request))


def api_price(request, product_id):
    ensure_demo_data()
    listing = _get_listing(product_id)
    return JsonResponse({"product_id": product_id, "price": float(listing.current_price), "currency": "INR", "recorded_at": listing.last_updated.isoformat()})


def api_price_history(request, product_id):
    ensure_demo_data()
    listing = _get_listing(product_id)
    history = PriceHistory.objects.filter(product_listing=listing).values("price", "recorded_at")
    return JsonResponse({"product_id": product_id, "currency": "INR", "history": [{"price": float(point["price"]), "recorded_at": point["recorded_at"].isoformat()} for point in history]})
