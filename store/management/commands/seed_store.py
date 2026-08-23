from django.core.management.base import BaseCommand

from dashboard.services import seed_simulator_data


class Command(BaseCommand):
    help = "Seed the ShopSphere demo storefront with shared tracker data."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=60)
        parser.add_argument("--days", type=int, default=60)
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        count = seed_simulator_data(count=options["count"], days=options["days"], seed=options["seed"])
        self.stdout.write(self.style.SUCCESS(f"ShopSphere ready with {count} products and shared price history."))
