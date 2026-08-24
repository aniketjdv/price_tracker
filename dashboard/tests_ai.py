import json
from decimal import Decimal
from datetime import timedelta
import pandas as pd
import numpy as np

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.management import call_command

from dashboard.models import Product, ProductListing, PriceHistory, Platform, Category, AIPricePrediction, AIModelMetric
from ai_engine.preprocessing import clean_price_series, validate_minimum_data, fetch_product_price_history
from ai_engine.feature_engineering import create_features_for_series, FEATURE_COLUMNS
from ai_engine.price_prediction import PricePredictionModel
from ai_engine.anomaly_detection import PriceAnomalyDetector
from ai_engine.recommendation import PriceRecommendationEngine
from ai_engine.evaluation import evaluate_regression_models
from ai_engine.model_manager import AIModelManager


class AIDataPreprocessingTests(TestCase):
    def test_clean_price_series_sorts_and_filters_invalid_data(self):
        now = timezone.now()
        raw_data = pd.DataFrame([
            {"recorded_at": now - timedelta(days=1), "price": 1000.0, "product_id": 1},
            {"recorded_at": now - timedelta(days=5), "price": -50.0, "product_id": 1},  # invalid
            {"recorded_at": now - timedelta(days=3), "price": 950.0, "product_id": 1},
            {"recorded_at": now - timedelta(days=2), "price": np.nan, "product_id": 1},  # invalid
        ])
        cleaned = clean_price_series(raw_data)
        self.assertEqual(len(cleaned), 2)
        # Should be strictly sorted chronologically
        self.assertLess(cleaned.iloc[0]["recorded_at"], cleaned.iloc[1]["recorded_at"])
        self.assertEqual(cleaned.iloc[0]["price"], 950.0)
        self.assertEqual(cleaned.iloc[1]["price"], 1000.0)

    def test_validate_minimum_data(self):
        few_points = pd.DataFrame([{"recorded_at": timezone.now(), "price": 100.0}])
        valid, msg = validate_minimum_data(few_points, min_points=5)
        self.assertFalse(valid)
        self.assertIn("Insufficient historical data", msg)

        enough_points = pd.DataFrame([{"recorded_at": timezone.now() - timedelta(days=i), "price": 100.0} for i in range(10)])
        valid, msg = validate_minimum_data(enough_points, min_points=5)
        self.assertTrue(valid)


class AIFeatureEngineeringTests(TestCase):
    def test_feature_creation_and_no_lookahead_leakage(self):
        now = timezone.now()
        prices = [50000, 49500, 49000, 48500, 48000, 47500, 47000, 46500, 46000, 45500]
        data = pd.DataFrame([
            {"recorded_at": now - timedelta(days=len(prices) - 1 - i), "price": p}
            for i, p in enumerate(prices)
        ])
        feats = create_features_for_series(data, is_training=True, target_horizons=[7])
        self.assertEqual(len(feats), len(prices))

        # Check all required feature columns exist
        for col in FEATURE_COLUMNS:
            self.assertIn(col, feats.columns)

        # Confirm target_7d is future price at index + 7
        self.assertEqual(feats.iloc[0]["target_7d"], prices[7])
        self.assertTrue(np.isnan(feats.iloc[-1]["target_7d"]))


class AIPricePredictionModelTests(TestCase):
    def test_fit_and_predict_horizons(self):
        np.random.seed(42)
        X = np.random.uniform(30000, 40000, size=(20, len(FEATURE_COLUMNS)))
        y_7 = X[:, 0] * 0.98 + np.random.normal(0, 100, size=20)
        y_14 = X[:, 0] * 0.96 + np.random.normal(0, 100, size=20)
        y_30 = X[:, 0] * 0.94 + np.random.normal(0, 100, size=20)

        y_dict = {"target_7d": y_7, "target_14d": y_14, "target_30d": y_30}

        model = PricePredictionModel(model_type="random_forest")
        model.fit(X, y_dict)
        self.assertTrue(model.is_fitted)

        test_sample = X[0]
        predictions = model.predict_horizons(test_sample, current_price=35000)
        self.assertIn("predicted_price_7_days", predictions)
        self.assertIn("predicted_price_14_days", predictions)
        self.assertIn("predicted_price_30_days", predictions)
        self.assertGreater(predictions["predicted_price_7_days"], 0)


class AIAnomalyDetectionTests(TestCase):
    def test_anomaly_detection_normal_vs_drop(self):
        history = [40000, 39800, 40200, 39900, 40100, 39700, 40300, 39950]
        detector = PriceAnomalyDetector(contamination=0.08)
        detector.fit(history)

        # Normal price
        normal_res = detector.analyze(39900, history)
        self.assertFalse(normal_res["is_anomaly"])
        self.assertEqual(normal_res["anomaly_type"], "NORMAL")

        # Flash drop anomaly
        drop_res = detector.analyze(24000, history)
        self.assertTrue(drop_res["is_anomaly"])
        self.assertEqual(drop_res["anomaly_type"], "FLASH_DROP")
        self.assertIn("Unusually low price", drop_res["reason"])


class AIRecommendationEngineTests(TestCase):
    def test_strong_buy_at_all_time_low(self):
        res = PriceRecommendationEngine.evaluate(
            current_price=29999,
            predicted_7d=31000,
            predicted_14d=32000,
            predicted_30d=33000,
            historical_min=29999,
            historical_avg=35000,
            historical_max=40000,
            trend="INCREASING"
        )
        self.assertEqual(res["recommendation"], "BUY NOW")
        self.assertEqual(res["strength"], "Strong Buy")

    def test_wait_when_future_prices_declining(self):
        res = PriceRecommendationEngine.evaluate(
            current_price=50000,
            predicted_7d=48000,
            predicted_14d=45000,
            predicted_30d=42000,
            historical_min=40000,
            historical_avg=49000,
            historical_max=55000,
            trend="DECREASING"
        )
        self.assertEqual(res["recommendation"], "WAIT")
        self.assertIn("Wait", res["strength"])
        self.assertIn("trending downward", res["reason"])


class AIModelEvaluationTests(TestCase):
    def test_evaluation_metrics_calculation(self):
        X_train = np.linspace(100, 500, 20).reshape(-1, 1)
        y_train = X_train.flatten() * 1.5 + 10
        X_test = np.linspace(500, 600, 10).reshape(-1, 1)
        y_test = X_test.flatten() * 1.5 + 10

        results = evaluate_regression_models(X_train, y_train, X_test, y_test)
        self.assertIn("LinearRegression", results)
        self.assertIn("RandomForestRegressor", results)
        self.assertIn("best_model", results)
        self.assertLess(results["LinearRegression"]["mae"], 5.0)


class AIEndToEndModelManagerTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Smartphones")
        self.plat = Platform.objects.create(name="Amazon", color="#FF9900", bg_color="#FFF7ED")
        self.product = Product.objects.create(
            name="AI Test Smartphone Ultra",
            category=self.cat,
            platform=self.plat,
            current_price=Decimal("49999"),
            original_price=Decimal("59999"),
            lowest_price=Decimal("48999"),
            discount=16,
            stock="In Stock"
        )
        self.listing = ProductListing.objects.create(
            product=self.product,
            platform=self.plat,
            external_product_id="TEST-AI-001",
            current_price=Decimal("49999"),
            mrp=Decimal("59999")
        )
        now = timezone.now()
        for i in range(25):
            PriceHistory.objects.create(
                product_listing=self.listing,
                price=Decimal(str(55000 - (i * 200))),
                recorded_at=now - timedelta(days=25 - i)
            )

    def test_analyze_product_end_to_end(self):
        analysis = AIModelManager.analyze_product(self.product)
        self.assertIsNotNone(analysis)
        self.assertTrue(analysis["available"])
        self.assertEqual(analysis["product_id"], self.product.id)
        self.assertIn(analysis["recommendation"], ["BUY NOW", "WAIT"])
        self.assertIsNotNone(analysis["predicted_price_7_days"])
        self.assertIsNotNone(analysis["predicted_price_14_days"])
        self.assertIsNotNone(analysis["predicted_price_30_days"])

        # Check DB record creation
        saved_db = AIPricePrediction.objects.filter(product=self.product).first()
        self.assertIsNotNone(saved_db)
        self.assertEqual(saved_db.recommendation, analysis["recommendation"])


class AIRESTApiEndpointsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat = Category.objects.create(name="Audio")
        self.plat = Platform.objects.create(name="Flipkart", color="#2874F0", bg_color="#EFF6FF")
        self.product = Product.objects.create(
            name="AI Test Wireless Earbuds",
            category=self.cat,
            platform=self.plat,
            current_price=Decimal("2999"),
            original_price=Decimal("4999"),
            lowest_price=Decimal("2899")
        )
        self.listing = ProductListing.objects.create(
            product=self.product,
            platform=self.plat,
            external_product_id="TEST-AI-002",
            current_price=Decimal("2999"),
            mrp=Decimal("4999")
        )
        now = timezone.now()
        for i in range(15):
            PriceHistory.objects.create(
                product_listing=self.listing,
                price=Decimal(str(3500 - (i * 30))),
                recorded_at=now - timedelta(days=15 - i)
            )

    def test_api_ai_analysis_endpoint(self):
        url = reverse("dashboard:api_ai_product_analysis", args=[self.product.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["product_id"], self.product.id)
        self.assertIn("recommendation", data)
        self.assertIn("predicted_price_7_days", data)

    def test_api_ai_prediction_endpoint(self):
        url = reverse("dashboard:api_ai_product_prediction", args=[self.product.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["product_id"], self.product.id)
        self.assertIn("predicted_price_7_days", data)
        self.assertIn("predicted_price_14_days", data)

    def test_api_ai_recommendation_endpoint(self):
        url = reverse("dashboard:api_ai_product_recommendation", args=[self.product.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("recommendation", data)
        self.assertIn("recommendation_reason", data)

    def test_api_ai_anomaly_endpoint(self):
        url = reverse("dashboard:api_ai_product_anomaly", args=[self.product.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("is_anomaly", data)

    def test_api_ai_metrics_endpoint(self):
        url = reverse("dashboard:api_ai_metrics")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("metrics", data)


class AIManagementCommandsTests(TestCase):
    def test_train_price_model_command(self):
        call_command("train_price_model")
        metrics_count = AIModelMetric.objects.count()
        self.assertGreaterEqual(metrics_count, 1)

    def test_generate_ai_predictions_command(self):
        call_command("generate_ai_predictions")
        preds_count = AIPricePrediction.objects.count()
        self.assertGreaterEqual(preds_count, 1)
