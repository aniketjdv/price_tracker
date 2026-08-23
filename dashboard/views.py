from datetime import date

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PriceAlertForm, ProductForm, ProfileForm, SignupForm
from .models import (
    Category,
    Coupon,
    Notification,
    Platform,
    PriceAlert,
    Product,
    ProductImage,
    ProductListing,
    PriceHistory,
    PriceAlert,
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
    if request.method == "POST":
        action = request.POST.get("action")
        user_id = request.POST.get("user_id")
        user = get_object_or_404(User, id=user_id)
        if action == "toggle_active" and user != request.user:
            user.is_active = not user.is_active
            user.save(update_fields=["is_active"])
        elif action == "toggle_staff" and user != request.user:
            user.is_staff = not user.is_staff
            user.save(update_fields=["is_staff"])
        elif action == "delete_user" and user != request.user:
            user.delete()
        return redirect("dashboard:admin_dashboard")

    users = User.objects.order_by("-date_joined")
    context = {
        "users": users,
        "user_count": User.objects.count(),
        "active_user_count": User.objects.filter(is_active=True).count(),
        "product_count": Product.objects.count(),
        "listing_count": ProductListing.objects.count(),
        "history_count": PriceHistory.objects.count(),
        "alert_count": PriceAlert.objects.count(),
        "recent_products": Product.objects.order_by("-created_at")[:6],
    }
    return render(request, "dashboard/admin_dashboard.html", context)


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
    price_drops = Product.objects.filter(trend="down").count()
    lowest_price = Product.objects.order_by("lowest_price").first()
    active_alerts = PriceAlert.objects.filter(status=PriceAlert.STATUS_WATCHING).count()
    recent_drops = Product.objects.filter(trend="down").order_by("-updated_at")[:4]
    if not recent_drops:
        recent_drops = Product.objects.order_by("-updated_at")[:4]
    platforms = Platform.objects.all()
    platform_distribution = [
        {"name": platform.name, "color": platform.color, "value": products_per_platform(platform)} for platform in platforms
    ]
    platform_total = sum(item["value"] for item in platform_distribution) or 1
    for item in platform_distribution:
        item["percent"] = round(item["value"] * 100 / platform_total)
    context = {
        "total_products": total_products,
        "price_drops": price_drops,
        "lowest_price": lowest_price.current_price if lowest_price else 0,
        "active_alerts": active_alerts,
        "recent_drops": recent_drops,
        "platform_distribution": platform_distribution,
        "platforms": platforms,
    }
    return render(request, "dashboard/dashboard_home.html", context)


def products_per_platform(platform):
    return Product.objects.filter(platform=platform).count()


def products(request):
    ensure_sample_data()
    query = request.GET.get("q", "")
    platform_filter = request.GET.get("platform", "All")
    sort = request.GET.get("sort", "Lowest Price")
    products = Product.objects.all()
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
    })


def product_detail(request, product_id):
    ensure_demo_data()
    product = get_object_or_404(Product, id=product_id)
    savings = (product.original_price or 0) - product.current_price
    listings = ProductListing.objects.filter(product=product).select_related("platform")
    price_history = list(product.listings.first().price_history.values("recorded_at", "price")) if product.listings.exists() else []
    store_compare = [
        {"store": listing.platform.name, "price": listing.current_price, "shipping": "Free", "delivery": "2 days", "in_stock": listing.availability}
        for listing in listings
    ]
    return render(request, "dashboard/product_detail.html", {
        "product": product,
        "savings": savings,
        "price_history": price_history,
        "store_compare": store_compare,
    })


def price_alerts(request):
    ensure_sample_data()
    alerts = PriceAlert.objects.select_related("product").all()
    form = PriceAlertForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        alert = form.save(commit=False)
        alert.current_price = alert.product.current_price
        alert.save()
        return redirect("dashboard:price_alerts")
    return render(request, "dashboard/price_alerts.html", {"alerts": alerts, "form": form})


def wishlist(request):
    ensure_sample_data()
    items = Product.objects.filter(wishlisted=True)
    return render(request, "dashboard/wishlist.html", {"items": items})


def analytics(request):
    ensure_sample_data()
    saved_total = sum([1500, 6800, 5300, 9100, 7600, 3400])
    return render(request, "dashboard/analytics.html", {"saved_total": saved_total})


def notifications(request):
    ensure_sample_data()
    if request.method == "POST":
        Notification.objects.filter(read=False).update(read=True)
        return redirect("dashboard:notifications")
    notifs = Notification.objects.all()
    return render(request, "dashboard/notifications.html", {"notifs": notifs})


@login_required
def settings_page(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("dashboard:settings")
    return render(request, "dashboard/settings.html", {"form": form})


def add_product(request):
    ensure_sample_data()
    form = ProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        return redirect("dashboard:product_detail", product_id=product.id)
    return render(request, "dashboard/add_product.html", {"form": form})


def track_new(request):
    ensure_sample_data()
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            return redirect("dashboard:product_detail", product_id=product.id)
    else:
        form = ProductForm()
    return render(request, "dashboard/track_new.html", {"form": form})
