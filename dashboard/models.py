from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.contrib.auth.models import User


class Platform(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default="#000000")
    bg_color = models.CharField(max_length=20, blank=True, default="#F5F3FF")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=30, blank=True)
    photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)

    def __str__(self):
        return f"Profile for {self.user.username}"


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    TREND_UP = "up"
    TREND_DOWN = "down"
    TREND_STABLE = "stable"

    TREND_CHOICES = [
        (TREND_UP, "Up"),
        (TREND_DOWN, "Down"),
        (TREND_STABLE, "Stable"),
    ]

    STOCK_IN = "In Stock"
    STOCK_LOW = "Low Stock"
    STOCK_OUT = "Out of Stock"

    STOCK_CHOICES = [
        (STOCK_IN, "In Stock"),
        (STOCK_LOW, "Low Stock"),
        (STOCK_OUT, "Out of Stock"),
    ]

    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="products")
    platform = models.ForeignKey(Platform, on_delete=models.SET_NULL, null=True, related_name="products")
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    lowest_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    discount = models.PositiveSmallIntegerField(default=0)
    trend = models.CharField(max_length=10, choices=TREND_CHOICES, default=TREND_STABLE)
    trend_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    stock = models.CharField(max_length=20, choices=STOCK_CHOICES, default=STOCK_IN)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    reviews = models.PositiveIntegerField(default=0)
    image_url = models.URLField(blank=True)
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    prediction = models.TextField(blank=True)
    wishlisted = models.BooleanField(default=False)
    tracked = models.BooleanField(default=False)
    tracked_by = models.ManyToManyField(User, blank=True, related_name="tracked_products")
    updated = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("product_detail", args=[self.id])

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:255]
        super().save(*args, **kwargs)


class ProductListing(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="listings")
    platform = models.ForeignKey(Platform, on_delete=models.SET_NULL, null=True, related_name="listings")
    external_product_id = models.CharField(max_length=100)
    seller = models.CharField(max_length=150, blank=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    availability = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    review_count = models.PositiveIntegerField(default=0)
    product_url = models.URLField(blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["platform", "external_product_id"], name="unique_platform_external_product")]
        ordering = ["current_price"]

    def __str__(self):
        return f"{self.product.name} - {self.platform}"


class PriceHistory(models.Model):
    product_listing = models.ForeignKey(ProductListing, on_delete=models.CASCADE, related_name="price_history")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    recorded_at = models.DateTimeField()

    class Meta:
        ordering = ["recorded_at"]
        indexes = [models.Index(fields=["product_listing", "recorded_at"])]

    def __str__(self):
        return f"{self.product_listing} - {self.price}"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image_url = models.URLField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Image for {self.product.name}"


class Coupon(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="coupons")
    code = models.CharField(max_length=40)
    description = models.CharField(max_length=255)
    expiry = models.DateField()

    def __str__(self):
        return self.code


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews_data")
    name = models.CharField(max_length=80)
    rating = models.DecimalField(max_digits=2, decimal_places=1)
    date = models.DateField()
    text = models.TextField()

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.name} - {self.product.name}"


class PriceAlert(models.Model):
    STATUS_WATCHING = "watching"
    STATUS_TRIGGERED = "triggered"

    STATUS_CHOICES = [
        (STATUS_WATCHING, "Watching"),
        (STATUS_TRIGGERED, "Triggered"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="price_alerts")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="alerts")
    target_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_WATCHING)
    email_on = models.BooleanField(default=True)
    sms_on = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Alert for {self.product.name}"


class Notification(models.Model):
    TYPE_CHOICES = [
        ("drop", "Price Drop"),
        ("alert", "Alert"),
        ("stock", "Stock"),
        ("coupon", "Coupon"),
        ("offer", "Offer"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="drop")
    title = models.CharField(max_length=120)
    body = models.TextField()
    time = models.CharField(max_length=40, blank=True)
    read = models.BooleanField(default=False)
    color = models.CharField(max_length=7, blank=True, default="#4F46E5")
    bg_color = models.CharField(max_length=20, blank=True, default="#EEF2FF")
    icon = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def icon_class(self):
        if self.type == "drop":
            return "fa-arrow-down"
        if self.type == "alert":
            return "fa-bell"
        if self.type == "stock":
            return "fa-check-circle"
        if self.type == "coupon":
            return "fa-tag"
        if self.type == "offer":
            return "fa-bolt"
        return "fa-info-circle"


class AIPricePrediction(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="ai_predictions")
    prediction_date = models.DateField(auto_now=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    predicted_price_7_days = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    predicted_price_14_days = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    predicted_price_30_days = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    trend = models.CharField(max_length=20, default="STABLE")
    recommendation = models.CharField(max_length=20, default="WAIT")
    recommendation_strength = models.CharField(max_length=30, default="Wait")
    recommendation_reason = models.TextField(blank=True)
    is_anomaly = models.BooleanField(default=False)
    anomaly_reason = models.TextField(blank=True)
    historical_average = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    historical_minimum = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    historical_maximum = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    model_name = models.CharField(max_length=100, default="RandomForestRegressor")
    model_version = models.CharField(max_length=50, default="v1.0")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "AI Price Prediction"
        verbose_name_plural = "AI Price Predictions"

    def __str__(self):
        return f"AI Prediction: {self.product.name} ({self.recommendation})"


class AIModelMetric(models.Model):
    model_name = models.CharField(max_length=100)
    model_type = models.CharField(max_length=50)
    mae = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rmse = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    r2_score = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    trained_samples = models.PositiveIntegerField(default=0)
    trained_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-trained_at"]
        verbose_name = "AI Model Metric"
        verbose_name_plural = "AI Model Metrics"

    def __str__(self):
        return f"{self.model_name} (MAE: {self.mae}, R²: {self.r2_score})"

