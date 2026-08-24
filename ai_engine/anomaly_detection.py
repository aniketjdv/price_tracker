"""
Price Anomaly Detection.
Combines Isolation Forest and statistical IQR/Z-score bands to detect unusual prices.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


class PriceAnomalyDetector:
    def __init__(self, contamination=0.08):
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.is_fitted = False

    def fit(self, price_history_array):
        prices = np.array(price_history_array).reshape(-1, 1)
        if len(prices) >= 5:
            self.model.fit(prices)
            self.is_fitted = True
        return self

    def analyze(self, current_price, historical_prices):
        if not historical_prices or len(historical_prices) < 3:
            return {
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'anomaly_type': 'NORMAL',
                'reason': 'Insufficient historical points to establish anomalous behavior.'
            }

        arr = np.array(historical_prices, dtype=float)
        mean_p = float(np.mean(arr))
        std_p = float(np.std(arr)) if len(arr) > 1 else 0.0
        median_p = float(np.median(arr))
        q25, q75 = np.percentile(arr, [25, 75])
        iqr = q75 - q25

        current = float(current_price)
        diff_pct = ((current - mean_p) / mean_p * 100.0) if mean_p > 0 else 0.0

        lower_bound = max(0.0, q25 - 1.5 * iqr) if iqr > 0 else (mean_p - 2.0 * std_p)
        upper_bound = (q75 + 1.5 * iqr) if iqr > 0 else (mean_p + 2.0 * std_p)

        iso_flag = False
        try:
            if self.is_fitted:
                pred = self.model.predict([[current]])[0]
                iso_flag = (pred == -1)
        except Exception:
            iso_flag = False

        if current < lower_bound or (iso_flag and current < median_p):
            return {
                'is_anomaly': True,
                'anomaly_score': -0.85,
                'anomaly_type': 'FLASH_DROP',
                'reason': f'Unusually low price detected! Currently ₹{current:,.0f}, which is {abs(diff_pct):.1f}% below the historical average (₹{mean_p:,.0f}). Possible flash sale or clearance.'
            }
        elif current > upper_bound or (iso_flag and current > median_p):
            return {
                'is_anomaly': True,
                'anomaly_score': 0.85,
                'anomaly_type': 'SURGE',
                'reason': f'Unusually high price surge detected! Current price ₹{current:,.0f} is {diff_pct:.1f}% above the normal range (₹{mean_p:,.0f}).'
            }
        else:
            return {
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'anomaly_type': 'NORMAL',
                'reason': f'Price (₹{current:,.0f}) is within normal historical distribution (Avg: ₹{mean_p:,.0f}).'
            }
