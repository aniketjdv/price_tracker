"""
Feature Engineering for Price Forecasting.
Calculates historical lag features, rolling statistics, price changes,
and calendar features without data leakage.
"""
import pandas as pd
import numpy as np


def create_features_for_series(df, is_training=False, target_horizons=[7, 14, 30]):
    if df.empty or len(df) < 2:
        return pd.DataFrame(), {} if is_training else pd.DataFrame()

    df = df.sort_values('recorded_at').copy()
    prices = df['price'].values
    n = len(prices)

    features_list = []
    for i in range(n):
        history = prices[:i+1]
        current = prices[i]

        lag_1 = prices[i-1] if i >= 1 else current
        lag_2 = prices[i-2] if i >= 2 else lag_1
        lag_3 = prices[i-3] if i >= 3 else lag_2
        lag_7 = prices[i-7] if i >= 7 else history[0]

        w7 = history[-7:] if len(history) >= 7 else history
        w14 = history[-14:] if len(history) >= 14 else history
        w30 = history[-30:] if len(history) >= 30 else history

        rolling_mean_7 = float(np.mean(w7))
        rolling_mean_14 = float(np.mean(w14))
        rolling_mean_30 = float(np.mean(w30))

        rolling_std_7 = float(np.std(w7)) if len(w7) > 1 else 0.0
        rolling_std_14 = float(np.std(w14)) if len(w14) > 1 else 0.0

        rolling_min_7 = float(np.min(w7))
        rolling_max_7 = float(np.max(w7))
        rolling_min_30 = float(np.min(w30))
        rolling_max_30 = float(np.max(w30))

        pct_change_1d = ((current - lag_1) / lag_1 * 100.0) if lag_1 > 0 else 0.0
        pct_change_7d = ((current - lag_7) / lag_7 * 100.0) if lag_7 > 0 else 0.0
        diff_from_30d_avg = ((current - rolling_mean_30) / rolling_mean_30 * 100.0) if rolling_mean_30 > 0 else 0.0

        dt = pd.to_datetime(df['recorded_at'].iloc[i])
        day_of_week = dt.dayofweek
        day_of_month = dt.day
        month = dt.month
        days_index = i

        feat = {
            'current_price': current,
            'lag_1': lag_1,
            'lag_2': lag_2,
            'lag_3': lag_3,
            'lag_7': lag_7,
            'rolling_mean_7': rolling_mean_7,
            'rolling_mean_14': rolling_mean_14,
            'rolling_mean_30': rolling_mean_30,
            'rolling_std_7': rolling_std_7,
            'rolling_std_14': rolling_std_14,
            'rolling_min_7': rolling_min_7,
            'rolling_max_7': rolling_max_7,
            'rolling_min_30': rolling_min_30,
            'rolling_max_30': rolling_max_30,
            'pct_change_1d': pct_change_1d,
            'pct_change_7d': pct_change_7d,
            'diff_from_30d_avg': diff_from_30d_avg,
            'day_of_week': day_of_week,
            'day_of_month': day_of_month,
            'month': month,
            'days_index': days_index,
        }

        if is_training:
            for h in target_horizons:
                feat[f'target_{h}d'] = prices[i + h] if (i + h) < n else np.nan

        features_list.append(feat)

    features_df = pd.DataFrame(features_list)
    return features_df


FEATURE_COLUMNS = [
    'current_price',
    'lag_1',
    'lag_2',
    'lag_3',
    'lag_7',
    'rolling_mean_7',
    'rolling_mean_14',
    'rolling_mean_30',
    'rolling_std_7',
    'rolling_std_14',
    'rolling_min_7',
    'rolling_max_7',
    'rolling_min_30',
    'rolling_max_30',
    'pct_change_1d',
    'pct_change_7d',
    'diff_from_30d_avg',
    'day_of_week',
    'day_of_month',
    'month',
    'days_index',
]
