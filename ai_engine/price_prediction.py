"""
Price Prediction Models.
Implements Linear Regression (baseline) and Random Forest Regressor (ensemble)
for multi-horizon price forecasting (7, 14, 30 days).
"""
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from .feature_engineering import FEATURE_COLUMNS


class PricePredictionModel:
    def __init__(self, model_type="random_forest"):
        self.model_type = model_type
        self.horizons = [7, 14, 30]
        self.models = {}
        for h in self.horizons:
            if model_type == "linear":
                self.models[h] = LinearRegression()
            else:
                self.models[h] = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=6,
                    min_samples_split=2,
                    random_state=42,
                    n_jobs=-1
                )
        self.is_fitted = False

    def fit(self, X, y_dict):
        for h in self.horizons:
            key = f'target_{h}d'
            if key in y_dict and len(y_dict[key]) > 0:
                y = y_dict[key]
                valid_mask = ~np.isnan(y)
                if np.sum(valid_mask) > 3:
                    self.models[h].fit(X[valid_mask], y[valid_mask])
        self.is_fitted = True
        return self

    def predict_horizons(self, x_latest, current_price=None):
        if not self.is_fitted:
            raise ValueError("Model must be trained before predicting.")

        if len(x_latest.shape) == 1:
            x_latest = x_latest.reshape(1, -1)

        curr = current_price if current_price is not None else float(x_latest[0][0])
        predictions = {}

        for h in self.horizons:
            try:
                pred = float(self.models[h].predict(x_latest)[0])
                pred = max(curr * 0.4, min(curr * 1.6, pred))
                predictions[f'predicted_price_{h}_days'] = round(pred, 2)
            except Exception:
                predictions[f'predicted_price_{h}_days'] = round(curr, 2)

        return predictions
