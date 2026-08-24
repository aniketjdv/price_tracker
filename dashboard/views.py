import json
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import urlsplit

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import Resolver404, resolve, reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from ai_engine import AIModelManager
from .forms import PriceAlertForm, ProductForm, ProfileForm, SignupForm
from .models import (
    AIModelMetric,
    AIPricePrediction,
    Category,
    Coupon,
    Notification,
    Platform,
    PriceAlert,
    Product,
    ProductImage,
    ProductListing,
    PriceHistory,
    Review,
    UserProfile,
)
from .services import ensure_demo_data


class TrackerLoginView(LoginView):
    template_name = "dashboard/login.html"
    redirect_authenticated_user = True


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard:dashboard_home")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("dashboard:dashboard_home")
    return render(request, "dashboard/signup.html", {"form": form})


def staff_required(view):
    return user_passes_test(lambda user: user.is_active and user.is_staff, login_url="dashboard:login")(view)


@staff_required
def admin_dashboard(request):
    active_tab = request.GET.get("tab", "products")
    product_query = request.GET.get("q", "").strip()
    selected_platform = request.GET.get("platform", "")
    selected_category = request.GET.get("category", "")

    if request.method == "POST":
        action = request.POST.get("action")
        user_id = request.POST.get("user_id")
        if user_id:
            user = get_object_or_404(User, id=user_id)
            if action == "toggle_active" and user != request.user:
                user.is_active = not user.is_active
                user.save(update_fields=["is_active"])
                messages.success(request, f"User '{user.username}' active status updated.")
            elif action == "toggle_staff" and user != request.user:
                user.is_staff = not user.is_staff
                user.save(update_fields=["is_staff"])
                messages.success(request, f"User '{user.username}' staff status updated.")
            elif action == "delete_user" and user != request.user:
                user_name = user.username
                user.delete()
                messages.success(request, f"User '{user_name}' deleted.")
            return redirect(f"{reverse('dashboard:admin_dashboard')}?tab=users")

    products_qs = Product.objects.select_related("category", "platform").all()
    if product_query:
        products_qs = products_qs.filter(Q(name__icontains=product_query) | Q(brand__icontains=product_query))
    if selected_platform:
        products_qs = products_qs.filter(platform__name=selected_platform)
    if selected_category:
        products_qs = products_qs.filter(category__name=selected_category)

    users = User.objects.order_by("-date_joined")
    categories = Category.objects.order_by("name")
    platforms = Platform.objects.order_by("name")

    context = {
        "active_tab": active_tab,
        "product_query": product_query,
        "selected_platform": selected_platform,
        "selected_category": selected_category,
        "products": products_qs[:100],
        "categories": categories,
        "platforms": platforms,
        "users": users,
        "user_count": User.objects.count(),
        "active_user_count": User.objects.filter(is_active=True).count(),
        "product_count": Product.objects.count(),
        "listing_count": ProductListing.objects.count(),
        "history_count": PriceHistory.objects.count(),
        "alert_count": PriceAlert.objects.count(),
    }
    return render(request, "dashboard/admin_dashboard.html", context)


@staff_required
@require_POST
def admin_create_product(request):
    name = request.POST.get("name", "").strip()
    brand = request.POST.get("brand", "").strip()
    category_id = request.POST.get("category")
    platform_id = request.POST.get("platform")
    current_price_raw = request.POST.get("current_price")
    original_price_raw = request.POST.get("original_price")
    lowest_price_raw = request.POST.get("lowest_price")
    discount_raw = request.POST.get("discount")
    stock = request.POST.get("stock", Product.STOCK_IN)
    image_url = request.POST.get("image_url", "").strip()
    url = request.POST.get("url", "").strip()
    description = request.POST.get("description", "").strip()
    prediction = request.POST.get("prediction", "").strip()

    if not name or not current_price_raw:
        messages.error(request, "Product name and current price are required.")
        return redirect(f"{reverse('dashboard:admin_dashboard')}?tab=products")

    try:
        current_price = Decimal(str(current_price_raw))
        original_price = Decimal(str(original_price_raw)) if original_price_raw else current_price
        lowest_price = Decimal(str(lowest_price_raw)) if lowest_price_raw else current_price
        discount = int(discount_raw) if discount_raw else (round((original_price - current_price) * 100 / original_price) if original_price > current_price else 0)
    except (ValueError, TypeError):
        messages.error(request, "Invalid numeric values provided for price or discount.")
        return redirect(f"{reverse('dashboard:admin_dashboard')}?tab=products")

    category = Category.objects.filter(id=category_id).first() if category_id else None
    platform = Platform.objects.filter(id=platform_id).first() if platform_id else None

    product = Product.objects.create(
        name=name,
        brand=brand,
        category=category,
        platform=platform,
        current_price=current_price,
        original_price=original_price,
        lowest_price=lowest_price,
        discount=discount,
        stock=stock,
        image_url=image_url,
        url=url,
        description=description,
        prediction=prediction,
    )

    if platform:
        listing, _ = ProductListing.objects.get_or_create(
            platform=platform,
            external_product_id=f"adm-{product.id}",
            defaults={
                "product": product,
                "seller": platform.name,
                "current_price": current_price,
                "mrp": original_price,
                "discount_percentage": Decimal(str(discount)),
                "availability": stock == Product.STOCK_IN,
                "product_url": url,
            }
        )
        PriceHistory.objects.create(
            product_listing=listing,
            price=current_price,
            recorded_at=timezone.now(),
        )

    messages.success(request, f"Product '{product.name}' was successfully created.")
    return redirect(f"{reverse('dashboard:admin_dashboard')}?tab=products")


@staff_required
@require_POST
def admin_edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    name = request.POST.get("name", "").strip()
    brand = request.POST.get("brand", "").strip()
    category_id = request.POST.get("category")
    platform_id = request.POST.get("platform")
    current_price_raw = request.POST.get("current_price")
    original_price_raw = request.POST.get("original_price")
    lowest_price_raw = request.POST.get("lowest_price")
    discount_raw = request.POST.get("discount")
    stock = request.POST.get("stock", Product.STOCK_IN)
    image_url = request.POST.get("image_url", "").strip()
    url = request.POST.get("url", "").strip()
    description = request.POST.get("description", "").strip()
    prediction = request.POST.get("prediction", "").strip()

    if not name or not current_price_raw:
        messages.error(request, "Product name and current price are required.")
        return redirect(f"{reverse('dashboard:admin_dashboard')}?tab=products")

    try:
        current_price = Decimal(str(current_price_raw))
        original_price = Decimal(str(original_price_raw)) if original_price_raw else None
        lowest_price = Decimal(str(lowest_price_raw)) if lowest_price_raw else current_price
        discount = int(discount_raw) if discount_raw else (round(((original_price or current_price) - current_price) * 100 / (original_price or current_price)) if original_price and original_price > current_price else 0)
    except (ValueError, TypeError):
        messages.error(request, "Invalid numeric values provided.")
        return redirect(f"{reverse('dashboard:admin_dashboard')}?tab=products")

    old_price = product.current_price
    product.name = name
    product.brand = brand
    product.category = Category.objects.filter(id=category_id).first() if category_id else None
    product.platform = Platform.objects.filter(id=platform_id).first() if platform_id else None
    product.current_price = current_price
    product.original_price = original_price
    product.lowest_price = min(lowest_price, current_price)
    product.discount = discount
    product.stock = stock
    product.image_url = image_url
    product.url = url
    product.description = description
    product.prediction = prediction
    product.save()

    # Update listings & price history if price changed
    if product.listings.exists():
        listing = product.listings.first()
        listing.current_price = current_price
        if original_price:
            listing.mrp = original_price
        listing.discount_percentage = Decimal(str(discount))
        listing.availability = (stock == Product.STOCK_IN)
        listing.save(update_fields=["current_price", "mrp", "discount_percentage", "availability", "last_updated"])
        if old_price != current_price:
            PriceHistory.objects.create(
                product_listing=listing,
                price=current_price,
                recorded_at=timezone.now(),
            )

    # Check price alerts for this product
    for alert in product.alerts.all():
        alert.current_price = current_price
        if alert.status == PriceAlert.STATUS_WATCHING and current_price <= alert.target_price:
            alert.status = PriceAlert.STATUS_TRIGGERED
            Notification.objects.create(
                user=alert.user,
                type="alert",
                title="Target Price Reached!",
                body=f"{product.name} reached your target price of ₹{alert.target_price:,.0f} (Current: ₹{product.current_price:,.0f})!",
                time="just now",
                color="#10B981",
                bg_color="#F0FDF4",
            )
        alert.save(update_fields=["current_price", "status"])

    messages.success(request, f"Product '{product.name}' details updated successfully.")
    return redirect(f"{reverse('dashboard:admin_dashboard')}?tab=products")


@staff_required
def admin_delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product_name = product.name
    product.delete()
    messages.success(request, f"Product '{product_name}' was successfully deleted.")
    return redirect(f"{reverse('dashboard:admin_dashboard')}?tab=products")


def ensure_sample_data():
    ensure_demo_data()
    return

    # Legacy presentation fixtures retained below for reference only.
    if Platform.objects.exists():
        return

    platforms = {
        "Amazon": {"color": "#FF9900", "bg_color": "#FFF7ED"},
        "Flipkart": {"color": "#2874F0", "bg_color": "#EFF6FF"},
        "Myntra": {"color": "#FF3F6C", "bg_color": "#FFF1F4"},
        "Ajio": {"color": "#6D28D9", "bg_color": "#F5F3FF"},
        "Croma": {"color": "#00A887", "bg_color": "#F0FDF4"},
        "Reliance Digital": {"color": "#E31837", "bg_color": "#FEF2F2"},
    }

    for name, values in platforms.items():
        Platform.objects.create(name=name, color=values["color"], bg_color=values["bg_color"])

    categories = [
        "Electronics",
        "Smartphones",
        "TVs",
        "Footwear",
        "Home Appliances",
        "Clothing",
    ]
    for category in categories:
        Category.objects.create(name=category)

    product_data = [
        {
            "name": "Sony WH-1000XM5 Wireless Headphones",
            "category": "Electronics",
            "platform": "Amazon",
            "current_price": 24990,
            "original_price": 34990,
            "lowest_price": 22999,
            "discount": 29,
            "trend": "down",
            "trend_pct": -12.4,
            "stock": "In Stock",
            "rating": 4.5,
            "reviews": 2847,
            "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=300&h=300&fit=crop&auto=format",
            "url": "https://www.amazon.in/example-product",
            "description": "Industry-leading noise canceling with Dual Noise Sensor technology. 30-hour battery life with quick charging.",
            "prediction": "Price likely to drop by ₹2,000 in next 2 weeks based on historical trends.",
            "wishlisted": False,
            "tracked": True,
            "updated": "2 hours ago",
            "images": [
                "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&h=600&fit=crop&auto=format",
                "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=600&h=600&fit=crop&auto=format",
            ],
            "coupons": [
                {"code": "SONY10", "description": "Extra 10% off on Sony products", "expiry": date(2026, 7, 10)},
            ],
            "reviews_data": [
                {"name": "Rahul M.", "rating": 5, "date": date(2026, 6, 2), "text": "Excellent noise cancellation. Worth every rupee."},
                {"name": "Sneha K.", "rating": 4, "date": date(2026, 5, 18), "text": "Sound quality is top notch. A bit pricey but worth it."},
            ],
        },
        {
            "name": "Apple iPhone 15 Pro 128GB",
            "category": "Smartphones",
            "platform": "Flipkart",
            "current_price": 119900,
            "original_price": 134900,
            "lowest_price": 109990,
            "discount": 11,
            "trend": "up",
            "trend_pct": 3.2,
            "stock": "In Stock",
            "rating": 4.8,
            "reviews": 12430,
            "image_url": "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=300&h=300&fit=crop&auto=format",
            "url": "https://www.flipkart.com/example-product",
            "description": "A17 Pro chip with 3nm technology. ProRes video recording. Titanium design and Action Button.",
            "prediction": "Price expected to remain stable for next month. May drop during Diwali sale.",
            "wishlisted": True,
            "tracked": True,
            "updated": "30 min ago",
            "images": [
                "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&h=600&fit=crop&auto=format",
                "https://images.unsplash.com/photo-1591337676887-a217a6970a8a?w=600&h=600&fit=crop&auto=format",
            ],
            "coupons": [],
            "reviews_data": [
                {"name": "Arjun S.", "rating": 5, "date": date(2026, 5, 5), "text": "Best phone I've used this year."},
            ],
        },
        {
            "name": "Nike Air Max 270 Running Shoes",
            "category": "Footwear",
            "platform": "Myntra",
            "current_price": 8995,
            "original_price": 12995,
            "lowest_price": 7999,
            "discount": 31,
            "trend": "down",
            "trend_pct": -8.1,
            "stock": "In Stock",
            "rating": 4.2,
            "reviews": 3201,
            "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300&h=300&fit=crop&auto=format",
            "url": "https://www.myntra.com/example-product",
            "description": "270 degrees of Nike Air cushioning for all-day comfort. Breathable mesh upper with dynamic support.",
            "prediction": "Price trending down. Alert set at ₹7,999 — expected to reach target in 1–2 weeks.",
            "wishlisted": True,
            "tracked": False,
            "updated": "5 hours ago",
            "images": [
                "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&h=600&fit=crop&auto=format",
                "https://images.unsplash.com/photo-1460353581641-37baddab0fa2?w=600&h=600&fit=crop&auto=format",
            ],
            "coupons": [
                {"code": "MYNTRA20", "description": "20% off on footwear orders above ₹5,000", "expiry": date(2026, 7, 12)},
            ],
            "reviews_data": [],
        },
    ]

    for item in product_data:
        product = Product.objects.create(
            name=item["name"],
            category=Category.objects.get(name=item["category"]),
            platform=Platform.objects.get(name=item["platform"]),
            current_price=item["current_price"],
            original_price=item["original_price"],
            lowest_price=item["lowest_price"],
            discount=item["discount"],
            trend=item["trend"],
            trend_pct=item["trend_pct"],
            stock=item["stock"],
            rating=item["rating"],
            reviews=item.get("reviews", 0),
            image_url=item["image_url"],
            url=item["url"],
            description=item["description"],
            prediction=item["prediction"],
            wishlisted=item["wishlisted"],
            tracked=item["tracked"],
            updated=item["updated"],
        )

        for index, image_url in enumerate(item["images"]):
            ProductImage.objects.create(product=product, image_url=image_url, order=index)

        for coupon in item["coupons"]:
            Coupon.objects.create(product=product, code=coupon["code"], description=coupon["description"], expiry=coupon["expiry"])

        for review in item.get("reviews_data", []):
            Review.objects.create(product=product, name=review["name"], rating=review["rating"], date=review["date"], text=review["text"])

    PriceAlert.objects.create(product=Product.objects.first(), target_price=22000, current_price=24990, status=PriceAlert.STATUS_WATCHING, email_on=True, sms_on=True)
    PriceAlert.objects.create(product=Product.objects.get(name__contains="Nike"), target_price=7999, current_price=8995, status=PriceAlert.STATUS_TRIGGERED, email_on=True, sms_on=True)

    Notification.objects.create(type="drop", title="Price dropped!", body="Sony WH-1000XM5 dropped ₹2,000 on Amazon", time="10 min ago", read=False, color="#10B981", bg_color="#F0FDF4")
    Notification.objects.create(type="alert", title="Alert triggered", body="Nike Air Max 270 reached your target price on Myntra", time="1 hour ago", read=False, color="#4F46E5", bg_color="#EEF2FF")
    Notification.objects.create(type="stock", title="Back in stock", body="Apple iPad Pro (12.9\") is now available on Flipkart", time="3 hours ago", read=True, color="#10B981", bg_color="#F0FDF4")
    Notification.objects.create(type="coupon", title="Coupon available", body="Use code SAVE15 on Samsung TV at Croma — valid 24 hrs", time="5 hours ago", read=True, color="#F59E0B", bg_color="#FFFBEB")
    Notification.objects.create(type="offer", title="Flash sale alert", body="Flipkart Big Billion Days starts tonight at midnight", time="Yesterday", read=True, color="#EF4444", bg_color="#FEF2F2")


def dashboard_home(request):
    ensure_sample_data()
    total_products = Product.objects.count()
    price_drops = Product.objects.filter(trend="down").count() or Product.objects.filter(discount__gt=0).count()
    lowest_price = Product.objects.order_by("lowest_price").first()

    if request.user.is_authenticated:
        active_alerts = PriceAlert.objects.filter(user=request.user, status=PriceAlert.STATUS_WATCHING).count()
        tracked_count = request.user.tracked_products.count()
        candidate_products = list(request.user.tracked_products.all()[:12])
    else:
        active_alerts = PriceAlert.objects.filter(user__isnull=True, status=PriceAlert.STATUS_WATCHING).count()
        tracked_count = Product.objects.filter(tracked=True).count()
        candidate_products = []

    if not candidate_products:
        candidate_products = list(Product.objects.filter(listings__price_history__isnull=False).distinct()[:12])
        if not candidate_products:
            candidate_products = list(Product.objects.all()[:12])

    chart_products = []
    for prod in candidate_products:
        listing = prod.listings.first()
        if listing:
            history_qs = listing.price_history.order_by("recorded_at")
            points = [
                {
                    "date": h.recorded_at.strftime("%Y-%m-%d"),
                    "label": h.recorded_at.strftime("%b %d"),
                    "price": float(h.price),
                }
                for h in history_qs
            ]
            if points:
                chart_products.append({
                    "id": prod.id,
                    "name": prod.name,
                    "platform": prod.platform.name if prod.platform else "",
                    "current_price": float(prod.current_price),
                    "original_price": float(prod.original_price or prod.current_price),
                    "history": points,
                })

    chart_products_json = json.dumps(chart_products)

    recent_drops = Product.objects.filter(trend="down").order_by("-updated_at")[:6]
    if not recent_drops:
        recent_drops = Product.objects.order_by("-discount", "-updated_at")[:6]

    platforms = Platform.objects.all()
    platform_distribution = [
        {"name": platform.name, "color": platform.color, "value": products_per_platform(platform)} for platform in platforms
    ]
    platform_total = sum(item["value"] for item in platform_distribution) or 1
    gradient_parts = []
    curr_deg = 0.0
    for item in platform_distribution:
        item["percent"] = round(item["value"] * 100 / platform_total)
        deg = (item["value"] * 360.0 / platform_total)
        next_deg = curr_deg + deg
        gradient_parts.append(f"{item['color']} {curr_deg:.1f}deg {next_deg:.1f}deg")
        curr_deg = next_deg

    donut_gradient = f"conic-gradient({', '.join(gradient_parts)})" if gradient_parts else ""

    context = {
        "total_products": total_products,
        "tracked_count": tracked_count,
        "price_drops": price_drops,
        "lowest_price": lowest_price.current_price if lowest_price else 0,
        "lowest_product": lowest_price,
        "active_alerts": active_alerts,
        "recent_drops": recent_drops,
        "platform_distribution": platform_distribution,
        "platforms": platforms,
        "donut_gradient": donut_gradient,
        "chart_products": chart_products,
        "chart_products_json": chart_products_json,
    }
    return render(request, "dashboard/dashboard_home.html", context)


def products_per_platform(platform):
    return Product.objects.filter(platform=platform).count()


def products(request):
    ensure_sample_data()
    query = request.GET.get("q", "")
    platform_filter = request.GET.get("platform", "All")
    sort = request.GET.get("sort", "Lowest Price")
    tracked_only = request.GET.get("tracked") == "1"

    if request.user.is_authenticated:
        user_tracked_ids = set(request.user.tracked_products.values_list("id", flat=True))
        tracked_count = len(user_tracked_ids)
    else:
        user_tracked_ids = set(Product.objects.filter(tracked=True).values_list("id", flat=True))
        tracked_count = len(user_tracked_ids)

    products = Product.objects.all().prefetch_related("ai_predictions")
    if tracked_only:
        if request.user.is_authenticated:
            products = products.filter(tracked_by=request.user)
        else:
            products = products.filter(tracked=True)

    if query:
        products = products.filter(name__icontains=query)
    if platform_filter != "All":
        products = products.filter(platform__name=platform_filter)

    if sort == "Highest Discount":
        products = products.order_by("-discount")
    elif sort == "Newest":
        products = products.order_by("-created_at")
    elif sort == "Recently Updated":
        products = products.order_by("-updated_at")
    else:
        products = products.order_by("current_price")

    return render(request, "dashboard/products.html", {
        "products": products,
        "platforms": Platform.objects.all(),
        "selected_platform": platform_filter,
        "sort": sort,
        "query": query,
        "tracked_only": tracked_only,
        "tracked_count": tracked_count,
        "user_tracked_ids": user_tracked_ids,
    })


def product_detail(request, product_id):
    ensure_demo_data()
    product = get_object_or_404(Product, id=product_id)
    savings = (product.original_price or 0) - product.current_price
    listings = ProductListing.objects.filter(product=product).select_related("platform")
    
    first_listing = product.listings.first()
    raw_history = list(first_listing.price_history.order_by("recorded_at").values("recorded_at", "price")) if first_listing else []
    
    store_compare = [
        {"store": listing.platform.name, "price": listing.current_price, "shipping": "Free", "delivery": "2 days", "in_stock": listing.availability}
        for listing in listings
    ]

    # Run AI Analysis
    ai_analysis = AIModelManager.analyze_product(product)

    # Prepare Historical + Forecast Chart data
    history_labels = []
    history_prices = []
    for point in raw_history[-30:]:  # Last 30 points for crisp visual display
        history_labels.append(point["recorded_at"].strftime("%d %b"))
        history_prices.append(float(point["price"]))

    if not history_prices and product.current_price:
        history_labels.append("Today")
        history_prices.append(float(product.current_price))

    # Forecast points (7d, 14d, 30d)
    last_dt = raw_history[-1]["recorded_at"] if raw_history else timezone.now()
    d7_str = (last_dt + timedelta(days=7)).strftime("%d %b (7d)")
    d14_str = (last_dt + timedelta(days=14)).strftime("%d %b (14d)")
    d30_str = (last_dt + timedelta(days=30)).strftime("%d %b (30d)")

    pred_7 = ai_analysis.get("predicted_price_7_days") or float(product.current_price)
    pred_14 = ai_analysis.get("predicted_price_14_days") or float(product.current_price)
    pred_30 = ai_analysis.get("predicted_price_30_days") or float(product.current_price)

    all_labels = history_labels + [d7_str, d14_str, d30_str]
    actual_dataset = history_prices + [None, None, None]
    forecast_dataset = [None] * (len(history_prices) - 1) + [history_prices[-1], pred_7, pred_14, pred_30]

    if request.user.is_authenticated:
        user_alert = PriceAlert.objects.filter(product=product, user=request.user).first()
        is_tracked = product.tracked_by.filter(id=request.user.id).exists()
    else:
        user_alert = PriceAlert.objects.filter(product=product, user__isnull=True).first()
        is_tracked = product.tracked

    return render(request, "dashboard/product_detail.html", {
        "product": product,
        "savings": savings,
        "price_history": raw_history,
        "store_compare": store_compare,
        "user_alert": user_alert,
        "is_tracked": is_tracked,
        "ai_analysis": ai_analysis,
        "chart_labels_json": json.dumps(all_labels),
        "chart_history_json": json.dumps(actual_dataset),
        "chart_forecast_json": json.dumps(forecast_dataset),
    })



@login_required(login_url="dashboard:login")
def price_alerts(request):
    ensure_sample_data()
    status_filter = request.GET.get("status", "all")
    query = request.GET.get("q", "").strip()

    base_qs = PriceAlert.objects.filter(user=request.user)
    alerts_qs = base_qs.select_related("product", "product__platform", "product__category").prefetch_related("product__ai_predictions")

    if query:
        alerts_qs = alerts_qs.filter(product__name__icontains=query)

    if status_filter == "watching":
        alerts_qs = alerts_qs.filter(status=PriceAlert.STATUS_WATCHING)
    elif status_filter == "triggered":
        alerts_qs = alerts_qs.filter(status=PriceAlert.STATUS_TRIGGERED)

    alerts = list(alerts_qs)
    # Calculate helper properties for each alert
    for alert in alerts:
        alert.diff = alert.current_price - alert.target_price
        alert.is_target_met = alert.current_price <= alert.target_price

    total_count = base_qs.count()
    watching_count = base_qs.filter(status=PriceAlert.STATUS_WATCHING).count()
    triggered_count = base_qs.filter(status=PriceAlert.STATUS_TRIGGERED).count()
    all_products = Product.objects.order_by("name")

    form = PriceAlertForm()
    return render(request, "dashboard/price_alerts.html", {
        "alerts": alerts,
        "form": form,
        "products": all_products,
        "selected_status": status_filter,
        "query": query,
        "total_count": total_count,
        "watching_count": watching_count,
        "triggered_count": triggered_count,
    })


@login_required(login_url="dashboard:login")
@require_POST
def create_price_alert(request):
    ensure_sample_data()
    product_id = request.POST.get("product") or request.POST.get("product_id")
    target_price_raw = request.POST.get("target_price")
    email_on = request.POST.get("email_on") in ["on", "true", "True", "1", True]
    sms_on = request.POST.get("sms_on") in ["on", "true", "True", "1", True]
    next_url = request.POST.get("next") or "dashboard:price_alerts"

    if not product_id or not target_price_raw:
        messages.error(request, "Please select a product and provide a target price.")
        return redirect(next_url)

    try:
        product = Product.objects.get(id=product_id)
        target_price = Decimal(str(target_price_raw))
    except (Product.DoesNotExist, ValueError, TypeError):
        messages.error(request, "Invalid product or target price.")
        return redirect(next_url)

    current_price = product.current_price
    status = PriceAlert.STATUS_TRIGGERED if current_price <= target_price else PriceAlert.STATUS_WATCHING
    user = request.user

    alert, created = PriceAlert.objects.get_or_create(
        product=product,
        user=user,
        defaults={
            "target_price": target_price,
            "current_price": current_price,
            "status": status,
            "email_on": email_on,
            "sms_on": sms_on,
        }
    )

    if not created:
        alert.target_price = target_price
        alert.current_price = current_price
        alert.status = status
        alert.email_on = email_on
        alert.sms_on = sms_on
        alert.save()
        messages.success(request, f"Updated price alert for {product.name} at ₹{target_price:,.0f}!")
    else:
        messages.success(request, f"Price alert set for {product.name} at target price ₹{target_price:,.0f}!")

    product.tracked_by.add(user)
    product.tracked = True
    product.save()

    if status == PriceAlert.STATUS_TRIGGERED:
        Notification.objects.create(
            user=user,
            type="alert",
            title="Target Price Reached!",
            body=f"{product.name} is currently ₹{current_price:,.0f}, meeting your target price of ₹{target_price:,.0f}!",
            time="just now",
            color="#10B981",
            bg_color="#F0FDF4",
        )

    return redirect(next_url)


@login_required(login_url="dashboard:login")
@require_POST
def edit_price_alert(request, alert_id):
    alert = get_object_or_404(PriceAlert, id=alert_id)
    if alert.user and alert.user != request.user:
        messages.error(request, "You do not have permission to edit this alert.")
        return redirect("dashboard:price_alerts")

    target_price_raw = request.POST.get("target_price")
    next_url = request.POST.get("next") or "dashboard:price_alerts"

    if target_price_raw:
        try:
            alert.target_price = Decimal(str(target_price_raw))
        except (ValueError, TypeError):
            messages.error(request, "Invalid target price.")
            return redirect(next_url)

    alert.email_on = request.POST.get("email_on") in ["on", "true", "True", "1", True]
    alert.sms_on = request.POST.get("sms_on") in ["on", "true", "True", "1", True]

    requested_status = request.POST.get("status")
    if requested_status in [PriceAlert.STATUS_WATCHING, PriceAlert.STATUS_TRIGGERED]:
        alert.status = requested_status
    else:
        if alert.product.current_price <= alert.target_price:
            alert.status = PriceAlert.STATUS_TRIGGERED
        else:
            alert.status = PriceAlert.STATUS_WATCHING

    alert.current_price = alert.product.current_price
    alert.save()
    messages.success(request, f"Price alert for {alert.product.name} updated successfully.")
    return redirect(next_url)


@login_required(login_url="dashboard:login")
def delete_price_alert(request, alert_id):
    alert = get_object_or_404(PriceAlert, id=alert_id)
    if alert.user and alert.user != request.user:
        messages.error(request, "You do not have permission to delete this alert.")
        return redirect("dashboard:price_alerts")

    product_name = alert.product.name
    alert.delete()
    messages.success(request, f"Alert for '{product_name}' has been deleted successfully.")
    next_url = request.POST.get("next") or request.GET.get("next") or "dashboard:price_alerts"
    return redirect(next_url)


@login_required(login_url="dashboard:login")
@require_POST
def toggle_alert_status(request, alert_id):
    alert = get_object_or_404(PriceAlert, id=alert_id)
    if alert.user and alert.user != request.user:
        messages.error(request, "You do not have permission to modify this alert.")
        return redirect("dashboard:price_alerts")

    if alert.status == PriceAlert.STATUS_TRIGGERED:
        alert.status = PriceAlert.STATUS_WATCHING
        messages.info(request, f"Alert for {alert.product.name} reset to Watching.")
    else:
        alert.status = PriceAlert.STATUS_TRIGGERED
        messages.info(request, f"Alert for {alert.product.name} set to Triggered.")
    alert.save(update_fields=["status"])
    return redirect("dashboard:price_alerts")


@login_required(login_url="dashboard:login")
def wishlist(request):
    ensure_sample_data()
    items = Product.objects.filter(wishlisted=True)
    return render(request, "dashboard/wishlist.html", {"items": items})


def analytics(request):
    ensure_sample_data()
    saved_total = sum([1500, 6800, 5300, 9100, 7600, 3400])
    return render(request, "dashboard/analytics.html", {"saved_total": saved_total})


@login_required(login_url="dashboard:login")
def notifications(request):
    ensure_sample_data()
    notifs_qs = Notification.objects.filter(Q(user=request.user) | Q(user__isnull=True))

    if request.method == "POST":
        notifs_qs.filter(read=False).update(read=True)
        return redirect("dashboard:notifications")
    return render(request, "dashboard/notifications.html", {"notifs": notifs_qs})


@login_required
def settings_page(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile information has been updated successfully.")
        return redirect("dashboard:settings")
    return render(request, "dashboard/settings.html", {"form": form, "profile": profile})


def add_product(request):
    ensure_sample_data()
    form = ProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        return redirect("dashboard:product_detail", product_id=product.id)
    return render(request, "dashboard/add_product.html", {"form": form})


def _resolve_product_from_url(source_url):
    if not source_url:
        return None
    source_url = source_url.strip()

    # 1. Try URL resolution via Django url resolver
    try:
        path = urlsplit(source_url).path or source_url.split("?", 1)[0]
        paths_to_try = [path]
        if not path.endswith("/"):
            paths_to_try.append(path + "/")

        for p in paths_to_try:
            try:
                match = resolve(p)
                if match.url_name == "product_detail" and match.namespace == "store":
                    product = Product.objects.filter(slug=match.kwargs.get("slug")).first()
                    if product:
                        return product
                if match.url_name == "product_detail" and match.namespace == "dashboard":
                    product = Product.objects.filter(id=match.kwargs.get("product_id")).first()
                    if product:
                        return product
            except (Resolver404, KeyError, ValueError):
                continue
    except Exception:
        pass

    # 2. Regex fallback for /store/product/<slug>/ or /product/<id>/
    import re
    store_match = re.search(r'/store/product/([a-zA-Z0-9_-]+)', source_url)
    if store_match:
        slug = store_match.group(1).rstrip("/")
        product = Product.objects.filter(slug=slug).first()
        if product:
            return product

    dash_match = re.search(r'/product/(\d+)', source_url)
    if dash_match:
        product_id = dash_match.group(1)
        product = Product.objects.filter(id=product_id).first()
        if product:
            return product

    # 3. Match against exact product URL or listing URLs
    product = Product.objects.filter(url=source_url).first()
    if product:
        return product
    listing = ProductListing.objects.filter(product_url=source_url).first()
    if listing:
        return listing.product

    # 4. Slug or name match
    cleaned = source_url.strip("/").split("/")[-1]
    product = Product.objects.filter(slug=cleaned).first()
    if product:
        return product

    return None


@login_required(login_url="dashboard:login")
def track_new(request):
    ensure_sample_data()
    source_url = request.POST.get("url", "") if request.method == "POST" else request.GET.get("url", "")
    store_product = _resolve_product_from_url(source_url) if source_url else None

    # Calculate suggested target price
    suggested_target_price = None
    if store_product:
        suggested_target_price = store_product.lowest_price or round(store_product.current_price * Decimal("0.9"))

    if request.method == "POST":
        if store_product:
            user = request.user
            store_product.tracked_by.add(user)
            store_product.tracked = True
            store_product.url = source_url
            store_product.save(update_fields=["tracked", "url", "updated_at"])

            target_price_raw = request.POST.get("target_price")
            if target_price_raw:
                try:
                    target_price = Decimal(str(target_price_raw))
                except (ValueError, TypeError):
                    target_price = suggested_target_price or store_product.current_price
            else:
                target_price = suggested_target_price or store_product.current_price

            email_on = request.POST.get("email_on") in ["on", "true", "True", "1", True] if "email_on" in request.POST else True
            sms_on = request.POST.get("sms_on") in ["on", "true", "True", "1", True]

            current_price = store_product.current_price
            status = PriceAlert.STATUS_TRIGGERED if current_price <= target_price else PriceAlert.STATUS_WATCHING

            alert, created = PriceAlert.objects.get_or_create(
                product=store_product,
                user=user,
                defaults={
                    "target_price": target_price,
                    "current_price": current_price,
                    "status": status,
                    "email_on": email_on,
                    "sms_on": sms_on,
                }
            )
            if not created:
                alert.target_price = target_price
                alert.current_price = current_price
                alert.status = status
                alert.email_on = email_on
                alert.sms_on = sms_on
                alert.save()
                messages.success(request, f"Tracking started! Updated price alert for {store_product.name} at target price ₹{target_price:,.0f}.")
            else:
                messages.success(request, f"Tracking started! Price alert is now active for {store_product.name} at target price ₹{target_price:,.0f}.")

            if status == PriceAlert.STATUS_TRIGGERED:
                Notification.objects.create(
                    user=user,
                    type="alert",
                    title="Target Price Reached!",
                    body=f"{store_product.name} is currently ₹{current_price:,.0f}, meeting your target price of ₹{target_price:,.0f}!",
                    time="just now",
                    color="#10B981",
                    bg_color="#F0FDF4",
                )

            return redirect("dashboard:price_alerts")
        else:
            messages.error(request, "That URL was not recognized. Please paste a valid product link from the store.")

    sample_products = Product.objects.all()[:4]

    return render(request, "dashboard/track_new.html", {
        "source_url": source_url,
        "store_product": store_product,
        "suggested_target_price": suggested_target_price,
        "url_error": bool(request.method == "POST" and not store_product),
        "sample_products": sample_products,
    })


# ==========================================
# AI / ML REST JSON API ENDPOINTS
# ==========================================

def api_ai_product_analysis(request, product_id):
    """
    GET /api/ai/products/<product_id>/analysis/
    Returns full comprehensive AI analysis payload.
    """
    product = get_object_or_404(Product, id=product_id)
    analysis = AIModelManager.analyze_product(product)
    return JsonResponse(analysis, json_dumps_params={"indent": 2})


def api_ai_product_prediction(request, product_id):
    """
    GET /api/ai/products/<product_id>/prediction/
    Returns 7-day, 14-day, and 30-day predicted price points.
    """
    product = get_object_or_404(Product, id=product_id)
    analysis = AIModelManager.analyze_product(product)
    return JsonResponse({
        "product_id": product.id,
        "product_name": product.name,
        "current_price": float(product.current_price),
        "predicted_price_7_days": analysis.get("predicted_price_7_days"),
        "predicted_price_14_days": analysis.get("predicted_price_14_days"),
        "predicted_price_30_days": analysis.get("predicted_price_30_days"),
        "trend": analysis.get("trend"),
        "model_name": analysis.get("model_name"),
        "model_version": analysis.get("model_version"),
        "available": analysis.get("available", True),
        "message": analysis.get("message", ""),
    }, json_dumps_params={"indent": 2})


def api_ai_product_recommendation(request, product_id):
    """
    GET /api/ai/products/<product_id>/recommendation/
    Returns BUY NOW / WAIT recommendation with dynamic reasoning.
    """
    product = get_object_or_404(Product, id=product_id)
    analysis = AIModelManager.analyze_product(product)
    return JsonResponse({
        "product_id": product.id,
        "product_name": product.name,
        "current_price": float(product.current_price),
        "recommendation": analysis.get("recommendation"),
        "recommendation_strength": analysis.get("recommendation_strength"),
        "recommendation_reason": analysis.get("recommendation_reason"),
        "expected_change_pct": analysis.get("expected_change_pct"),
        "historical_minimum": analysis.get("historical_minimum"),
        "historical_average": analysis.get("historical_average"),
    }, json_dumps_params={"indent": 2})


def api_ai_product_anomaly(request, product_id):
    """
    GET /api/ai/products/<product_id>/anomaly/
    Returns whether current price is anomalous compared to normal distribution.
    """
    product = get_object_or_404(Product, id=product_id)
    analysis = AIModelManager.analyze_product(product)
    return JsonResponse({
        "product_id": product.id,
        "product_name": product.name,
        "current_price": float(product.current_price),
        "is_anomaly": analysis.get("is_anomaly", False),
        "anomaly_reason": analysis.get("anomaly_reason", ""),
        "historical_average": analysis.get("historical_average"),
        "historical_minimum": analysis.get("historical_minimum"),
        "historical_maximum": analysis.get("historical_maximum"),
    }, json_dumps_params={"indent": 2})


def api_ai_metrics(request):
    """
    GET /api/ai/metrics/
    Returns the latest model training and evaluation metrics.
    """
    metrics = AIModelMetric.objects.all()
    data = [
        {
            "model_name": m.model_name,
            "model_type": m.model_type,
            "mae": float(m.mae) if m.mae else None,
            "rmse": float(m.rmse) if m.rmse else None,
            "r2_score": float(m.r2_score) if m.r2_score else None,
            "trained_samples": m.trained_samples,
            "is_active": m.is_active,
            "trained_at": m.trained_at.isoformat() if m.trained_at else None,
        }
        for m in metrics
    ]
    return JsonResponse({"metrics": data, "count": len(data)}, json_dumps_params={"indent": 2})

