from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="product",
            name="brand",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.CreateModel(
            name="ProductListing",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_product_id", models.CharField(max_length=100)),
                ("seller", models.CharField(blank=True, max_length=150)),
                ("current_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("mrp", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("discount_percentage", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("availability", models.BooleanField(default=True)),
                ("rating", models.DecimalField(decimal_places=1, default=0, max_digits=3)),
                ("review_count", models.PositiveIntegerField(default=0)),
                ("product_url", models.URLField(blank=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("platform", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="listings", to="dashboard.platform")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="listings", to="dashboard.product")),
            ],
            options={"ordering": ["current_price"]},
        ),
        migrations.CreateModel(
            name="PriceHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("recorded_at", models.DateTimeField()),
                ("product_listing", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="price_history", to="dashboard.productlisting")),
            ],
            options={"ordering": ["recorded_at"]},
        ),
        migrations.AddConstraint(
            model_name="productlisting",
            constraint=models.UniqueConstraint(fields=("platform", "external_product_id"), name="unique_platform_external_product"),
        ),
        migrations.AddIndex(
            model_name="pricehistory",
            index=models.Index(fields=["product_listing", "recorded_at"], name="dashboard_p_product_ce92b5_idx"),
        ),
    ]