from django.core.management.base import BaseCommand

from dashboard.services import seed_simulator_data


class Command(BaseCommand):
    help = "Populate the database with deterministic simulated marketplace data."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=60)
        parser.add_argument("--days", type=int, default=60)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--reset", action="store_true")

    def handle(self, *args, **options):
        count = seed_simulator_data(
            count=options["count"],
            days=options["days"],
            seed=options["seed"],
            reset=options["reset"],
        )
        self.stdout.write(self.style.SUCCESS(f"Seeded {count} simulated products."))
