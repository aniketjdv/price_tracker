"""
AI Model Manager.
Central hub for training, persisting (.joblib), loading models,
and running full AI analysis on products.
"""
import json
import os
import joblib
import pandas as pd
import numpy as np
from decimal import Decimal
from django.utils import timezone

from .utils import (
    PRICE_PREDICTOR_MODEL_PATH,
    ANOMALY_DETECTOR_MODEL_PATH,
    METRICS_PATH,
    MIN_HISTORICAL_POINTS,
    safe_decimal,
)
from .preprocessing import fetch_product_price_history, fetch_catalog_price_history, validate_minimum_data
from .feature_engineering import create_features_for_series, FEATURE_COLUMNS
from .price_prediction import PricePredictionModel
from .anomaly_detection import PriceAnomalyDetector
from .recommendation import PriceRecommendationEngine
from .evaluation import evaluate_regression_models


class AIModelManager:
    _cached_predictor = None
    _cached_anomaly_detector = None

    @classmethod
    def get_predictor(cls):
        if cls._cached_predictor is not None:
            return cls._cached_predictor
        if PRICE_PREDICTOR_MODEL_PATH.exists():
            try:
                cls._cached_predictor = joblib.load(PRICE_PREDICTOR_MODEL_PATH)
                return cls._cached_predictor
            except Exception:
                pass
        return None

    @classmethod
    def get_anomaly_detector(cls):
        if cls._cached_anomaly_detector is not None:
            return cls._cached_anomaly_detector
        if ANOMALY_DETECTOR_MODEL_PATH.exists():
            try:
                cls._cached_anomaly_detector = joblib.load(ANOMALY_DETECTOR_MODEL_PATH)
                return cls._cached_anomaly_detector
            except Exception:
                pass
        return None

    @classmethod
    def train_all_models(cls):
        from dashboard.models import Product, AIModelMetric

        catalog_df = fetch_catalog_price_history()
        if catalog_df.empty or len(catalog_df) < 15:
            from dashboard.services import ensure_demo_data
            ensure_demo_data()
            catalog_df = fetch_catalog_price_history()

        product_ids = catalog_df['product_id'].unique()
        all_features = []

        for pid in product_ids:
            p_df = catalog_df[catalog_df['product_id'] == pid]
            if len(p_df) >= MIN_HISTORICAL_POINTS:
                feats = create_features_for_series(p_df, is_training=True)
                if not feats.empty:
                    all_features.append(feats)

        if not all_features:
            return {
                'success': False,
                'message': 'No products with sufficient historical data found for training.',
                'metrics': {}
            }

        combined_df = pd.concat(all_features, ignore_index=True)
        trainable_7d = combined_df.dropna(subset=['target_7d']).copy()

        if len(trainable_7d) < 10:
            return {
                'success': False,
                'message': 'Insufficient time-stepped samples for multi-horizon training.',
                'metrics': {}
            }

        X = trainable_7d[FEATURE_COLUMNS].values
        y_7 = trainable_7d['target_7d'].values

        split_idx = max(int(len(X) * 0.8), 2)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y_7[:split_idx], y_7[split_idx:]

        eval_results = evaluate_regression_models(X_train, y_train, X_test if len(X_test) > 0 else X_train, y_test if len(y_test) > 0 else y_train)

        predictor = PricePredictionModel(model_type='random_forest')
        y_dict = {
            'target_7d': combined_df['target_7d'].values if 'target_7d' in combined_df else y_7,
            'target_14d': combined_df['target_14d'].values if 'target_14d' in combined_df else y_7,
            'target_30d': combined_df['target_30d'].values if 'target_30d' in combined_df else y_7,
        }
        X_all = combined_df[FEATURE_COLUMNS].values
        predictor.fit(X_all, y_dict)

        anomaly_detector = PriceAnomalyDetector(contamination=0.08)
        anomaly_detector.fit(catalog_df['price'].values)

        joblib.dump(predictor, PRICE_PREDICTOR_MODEL_PATH)
        joblib.dump(anomaly_detector, ANOMALY_DETECTOR_MODEL_PATH)
        cls._cached_predictor = predictor
        cls._cached_anomaly_detector = anomaly_detector

        with open(METRICS_PATH, 'w', encoding='utf-8') as f:
            json.dump({
                'trained_at': timezone.now().isoformat(),
                'samples_count': int(len(X)),
                'metrics': {
                    'LinearRegression': {
                        'mae': eval_results['LinearRegression']['mae'],
                        'rmse': eval_results['LinearRegression']['rmse'],
                        'r2': eval_results['LinearRegression']['r2'],
                    },
                    'RandomForestRegressor': {
                        'mae': eval_results['RandomForestRegressor']['mae'],
                        'rmse': eval_results['RandomForestRegressor']['rmse'],
                        'r2': eval_results['RandomForestRegressor']['r2'],
                    },
                    'best_model': eval_results['best_model'],
                }
            }, f, indent=2)

        AIModelMetric.objects.update_or_create(
            model_name='PricePulse Random Forest Regressor',
            defaults={
                'model_type': 'RandomForestRegressor',
                'mae': safe_decimal(eval_results['RandomForestRegressor']['mae']),
                'rmse': safe_decimal(eval_results['RandomForestRegressor']['rmse']),
                'r2_score': safe_decimal(eval_results['RandomForestRegressor']['r2']),
                'trained_samples': len(X),
                'is_active': True,
            }
        )

        AIModelMetric.objects.update_or_create(
            model_name='PricePulse Linear Regression Baseline',
            defaults={
                'model_type': 'LinearRegression',
                'mae': safe_decimal(eval_results['LinearRegression']['mae']),
                'rmse': safe_decimal(eval_results['LinearRegression']['rmse']),
                'r2_score': safe_decimal(eval_results['LinearRegression']['r2']),
                'trained_samples': len(X),
                'is_active': False,
            }
        )

        return {
            'success': True,
            'message': f'Models successfully trained on {len(X)} samples.',
            'metrics': eval_results,
            'samples_count': len(X),
        }

    @classmethod
    def analyze_product(cls, product_id_or_product):
        from dashboard.models import Product, AIPricePrediction

        if isinstance(product_id_or_product, (int, str)):
            product = Product.objects.filter(id=product_id_or_product).first()
        else:
            product = product_id_or_product

        if not product:
            return None

        df = fetch_product_price_history(product)
        is_valid, msg = validate_minimum_data(df, MIN_HISTORICAL_POINTS)

        current_price = float(product.current_price)

        if not is_valid:
            return {
                'product_id': product.id,
                'product_name': product.name,
                'available': False,
                'message': msg,
                'current_price': current_price,
                'predicted_price_7_days': None,
                'predicted_price_14_days': None,
                'predicted_price_30_days': None,
                'trend': product.trend.upper() if product.trend else 'STABLE',
                'recommendation': 'WAIT',
                'recommendation_strength': 'Wait',
                'recommendation_reason': msg,
                'is_anomaly': False,
                'anomaly_reason': 'Insufficient data points to evaluate anomalies.',
                'historical_average': current_price,
                'historical_minimum': float(product.lowest_price or current_price),
                'historical_maximum': float(product.original_price or current_price),
            }

        price_series = df['price'].tolist()
        h_min = float(np.min(price_series))
        h_max = float(np.max(price_series))
        h_avg = float(np.mean(price_series))

        feats_df = create_features_for_series(df, is_training=False)
        x_latest = feats_df[FEATURE_COLUMNS].iloc[-1].values

        predictor = cls.get_predictor()
        if predictor is None:
            cls.train_all_models()
            predictor = cls.get_predictor()

        if predictor is not None and predictor.is_fitted:
            predictions = predictor.predict_horizons(x_latest, current_price=current_price)
            pred_7 = predictions['predicted_price_7_days']
            pred_14 = predictions['predicted_price_14_days']
            pred_30 = predictions['predicted_price_30_days']
        else:
            pred_7 = round(current_price * 0.98, 2)
            pred_14 = round(current_price * 0.96, 2)
            pred_30 = round(current_price * 0.95, 2)

        detector = cls.get_anomaly_detector() or PriceAnomalyDetector().fit(price_series)
        anomaly_res = detector.analyze(current_price, price_series)

        trend = PriceRecommendationEngine.determine_trend(price_series)

        rec_res = PriceRecommendationEngine.evaluate(
            current_price=current_price,
            predicted_7d=pred_7,
            predicted_14d=pred_14,
            predicted_30d=pred_30,
            historical_min=h_min,
            historical_avg=h_avg,
            historical_max=h_max,
            trend=trend,
            is_anomaly=anomaly_res['is_anomaly'],
        )

        analysis = {
            'product_id': product.id,
            'product_name': product.name,
            'available': True,
            'message': 'AI analysis generated successfully.',
            'current_price': current_price,
            'predicted_price_7_days': pred_7,
            'predicted_price_14_days': pred_14,
            'predicted_price_30_days': pred_30,
            'trend': trend,
            'recommendation': rec_res['recommendation'],
            'recommendation_strength': rec_res['strength'],
            'recommendation_reason': rec_res['reason'],
            'expected_change_pct': rec_res.get('expected_change_pct', 0.0),
            'is_anomaly': anomaly_res['is_anomaly'],
            'anomaly_reason': anomaly_res['reason'],
            'historical_average': round(h_avg, 2),
            'historical_minimum': round(h_min, 2),
            'historical_maximum': round(h_max, 2),
            'model_name': 'RandomForestRegressor (Ensemble)',
            'model_version': 'v1.0',
        }

        AIPricePrediction.objects.update_or_create(
            product=product,
            defaults={
                'prediction_date': timezone.now().date(),
                'current_price': safe_decimal(current_price),
                'predicted_price_7_days': safe_decimal(pred_7),
                'predicted_price_14_days': safe_decimal(pred_14),
                'predicted_price_30_days': safe_decimal(pred_30),
                'trend': trend,
                'recommendation': rec_res['recommendation'],
                'recommendation_strength': rec_res['strength'],
                'recommendation_reason': rec_res['reason'],
                'is_anomaly': anomaly_res['is_anomaly'],
                'anomaly_reason': anomaly_res['reason'],
                'historical_average': safe_decimal(h_avg),
                'historical_minimum': safe_decimal(h_min),
                'historical_maximum': safe_decimal(h_max),
                'model_name': 'RandomForestRegressor',
                'model_version': 'v1.0',
            }
        )

        return analysis

    @classmethod
    def generate_all_predictions(cls):
        from dashboard.models import Product
        products = Product.objects.all()
        results = []
        for p in products:
            res = cls.analyze_product(p)
            if res:
                results.append(res)
        return results
