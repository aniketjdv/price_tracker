from django.contrib import admin

from .models import (
    AIModelMetric,
    AIPricePrediction,
    Category,
    Coupon,
    Notification,
    Platform,
    PriceAlert,
    Product,
    ProductListing,
    PriceHistory,
    ProductImage,
    Review,
)


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ["name", "color", "bg_color"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class CouponInline(admin.TabularInline):
    model = Coupon
    extra = 1


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "platform", "category", "current_price", "stock", "wishlisted", "tracked"]
    list_filter = ["platform", "category", "stock", "wishlisted", "tracked"]
    search_fields = ["name", "platform__name", "category__name"]
    inlines = [ProductImageInline, CouponInline, ReviewInline]


@admin.register(ProductListing)
class ProductListingAdmin(admin.ModelAdmin):
    list_display = ["product", "platform", "seller", "current_price", "mrp", "availability", "last_updated"]
    list_filter = ["platform", "availability"]
    search_fields = ["product__name", "external_product_id", "seller"]


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ["product_listing", "price", "recorded_at"]
    list_filter = ["product_listing__platform"]
    search_fields = ["product_listing__product__name", "product_listing__external_product_id"]


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ["product", "target_price", "current_price", "status", "email_on", "sms_on", "created_at"]
    list_filter = ["status", "email_on", "sms_on"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "type", "read", "time", "created_at"]
    list_filter = ["type", "read"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["name", "product", "rating", "date"]


@admin.register(AIPricePrediction)
class AIPricePredictionAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "current_price",
        "predicted_price_7_days",
        "predicted_price_14_days",
        "predicted_price_30_days",
        "trend",
        "recommendation",
        "recommendation_strength",
        "is_anomaly",
        "prediction_date",
    ]
    list_filter = ["trend", "recommendation", "recommendation_strength", "is_anomaly", "prediction_date"]
    search_fields = ["product__name", "recommendation_reason", "anomaly_reason"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(AIModelMetric)
class AIModelMetricAdmin(admin.ModelAdmin):
    list_display = ["model_name", "model_type", "mae", "rmse", "r2_score", "trained_samples", "is_active", "trained_at"]
    list_filter = ["model_type", "is_active"]
    search_fields = ["model_name"]
    readonly_fields = ["trained_at"]

