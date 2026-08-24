from django.core.management.base import BaseCommand
from ai_engine.model_manager import AIModelManager


class Command(BaseCommand):
    help = "Train price prediction and anomaly detection ML models using historical price data."

    def add_arguments(self, parser):
        parser.add_argument("--verbose", action="store_true", help="Print detailed training logs.")

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("=" * 60))
        self.stdout.write(self.style.NOTICE("   PRICEPULSE AI / ML MODEL TRAINING & EVALUATION"))
        self.stdout.write(self.style.NOTICE("=" * 60))
        self.stdout.write("Loading historical price data from database...")

        result = AIModelManager.train_all_models()

        if not result["success"]:
            self.stdout.write(self.style.ERROR(f"Training failed: {result['message']}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Loaded and processed training dataset ({result['samples_count']} samples)."))
        self.stdout.write("")

        metrics = result["metrics"]
        self.stdout.write(self.style.HTTP_INFO("Model Evaluation Results (Chronological Validation Split):"))
        self.stdout.write("-" * 65)
        self.stdout.write(f"{'Model':<25} | {'MAE':<12} | {'RMSE':<12} | {'R2 Score':<8}")
        self.stdout.write("-" * 65)

        for model_name in ["LinearRegression", "RandomForestRegressor"]:
            if model_name in metrics:
                m = metrics[model_name]
                mae_str = f"Rs. {m['mae']:,.0f}"
                rmse_str = f"Rs. {m['rmse']:,.0f}"
                r2_str = f"{m['r2']:.4f}"
                self.stdout.write(f"{model_name:<25} | {mae_str:<12} | {rmse_str:<12} | {r2_str:<8}")

        self.stdout.write("-" * 65)
        best_model = metrics.get("best_model", "RandomForestRegressor")
        self.stdout.write(self.style.SUCCESS(f"Selected Best Model: {best_model}"))
        self.stdout.write(self.style.SUCCESS("Model serialized and saved to ai_engine/saved_models/"))
        self.stdout.write(self.style.SUCCESS("AIModelMetric database table updated."))
        self.stdout.write(self.style.NOTICE("=" * 65))

