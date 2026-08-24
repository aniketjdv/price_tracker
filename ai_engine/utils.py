"""
Utility functions, constants, and paths for the AI/ML Engine.
"""
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SAVED_MODELS_DIR = BASE_DIR / 'saved_models'
SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)

MIN_HISTORICAL_POINTS = 5
MIN_TRAIN_POINTS_FOR_FORECAST = 8

PRICE_PREDICTOR_MODEL_PATH = SAVED_MODELS_DIR / 'price_predictor.joblib'
ANOMALY_DETECTOR_MODEL_PATH = SAVED_MODELS_DIR / 'anomaly_detector.joblib'
METRICS_PATH = SAVED_MODELS_DIR / 'model_metrics.json'

TREND_INCREASING = 'INCREASING'
TREND_DECREASING = 'DECREASING'
TREND_STABLE = 'STABLE'
TREND_VOLATILE = 'VOLATILE'

REC_BUY_NOW = 'BUY NOW'
REC_WAIT = 'WAIT'

REC_STRONG_BUY = 'Strong Buy'
REC_BUY = 'Buy'
REC_WAIT_MILD = 'Wait'
REC_STRONG_WAIT = 'Strong Wait'


def format_inr(value):
    if value is None:
        return 'N/A'
    try:
        val = float(value)
        return f'₹{val:,.0f}'
    except (ValueError, TypeError):
        return str(value)


def safe_decimal(value, default=Decimal('0')):
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except Exception:
        return default
