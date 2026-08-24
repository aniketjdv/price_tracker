from django.core.management.base import BaseCommand
from ai_engine.model_manager import AIModelManager
from dashboard.models import Product


class Command(BaseCommand):
    help = "Generate AI price predictions, anomaly alerts, and Buy/Wait recommendations for products."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, help="Specific product ID to analyze.")

    def handle(self, *args, **options):
        from dashboard.services import ensure_demo_data
        ensure_demo_data()

        pid = options.get("product_id")
        self.stdout.write(self.style.NOTICE("=" * 60))
        self.stdout.write(self.style.NOTICE("   PRICEPULSE AI INFERENCE & RECOMMENDATION GENERATOR"))
        self.stdout.write(self.style.NOTICE("=" * 60))

        if pid:
            product = Product.objects.filter(id=pid).first()
            if not product:
                self.stdout.write(self.style.ERROR(f"Product with ID {pid} not found."))
                return
            products = [product]
        else:
            products = Product.objects.all()

        count = 0
        for p in products:
            res = AIModelManager.analyze_product(p)
            if res and res.get("available"):
                count += 1
                rec = res["recommendation"]
                strength = res["recommendation_strength"]
                curr = res["current_price"]
                p7 = res["predicted_price_7_days"]
                p14 = res["predicted_price_14_days"]
                p30 = res["predicted_price_30_days"]
                anomaly_str = " [UNUSUAL PRICE!]" if res["is_anomaly"] else ""
                self.stdout.write(
                    f"[{p.id:02d}] {p.name[:28]:<28} | Curr: Rs. {curr:,.0f} | 7d: Rs. {p7:,.0f} | 14d: Rs. {p14:,.0f} | 30d: Rs. {p30:,.0f} | {rec} ({strength}){anomaly_str}"
                )

        self.stdout.write("-" * 60)
        self.stdout.write(self.style.SUCCESS(f"Successfully generated and stored AI predictions for {count} products."))
        self.stdout.write(self.style.NOTICE("=" * 60))
