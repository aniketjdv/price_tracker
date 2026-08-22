from django.core.management.base import BaseCommand

from dashboard.services import update_simulated_prices


class Command(BaseCommand):
    help = "Generate a new simulated price and history point for each listing."

    def handle(self, *args, **options):
        count = update_simulated_prices()
        self.stdout.write(self.style.SUCCESS(f"Updated {count} simulated listings."))
