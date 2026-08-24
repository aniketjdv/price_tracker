"""
AI Buy / Wait Recommendation Engine.
Produces actionable, explainable BUY NOW or WAIT decisions.
"""
import numpy as np
from .utils import (
    REC_BUY_NOW, REC_WAIT,
    REC_STRONG_BUY, REC_BUY, REC_WAIT_MILD, REC_STRONG_WAIT,
    TREND_INCREASING, TREND_DECREASING, TREND_STABLE, TREND_VOLATILE
)


class PriceRecommendationEngine:
    @staticmethod
    def determine_trend(prices):
        if not prices or len(prices) < 3:
            return TREND_STABLE

        arr = np.array(prices, dtype=float)
        std_p = np.std(arr)
        mean_p = np.mean(arr)
        volatility = (std_p / mean_p * 100.0) if mean_p > 0 else 0.0

        if volatility > 12.0:
            return TREND_VOLATILE

        recent = arr[-14:] if len(arr) >= 14 else arr
        x = np.arange(len(recent))
        slope, _ = np.polyfit(x, recent, 1)
        slope_pct = (slope * len(recent) / recent[0] * 100.0) if recent[0] > 0 else 0.0

        if slope_pct < -2.0:
            return TREND_DECREASING
        elif slope_pct > 2.0:
            return TREND_INCREASING
        return TREND_STABLE

    @classmethod
    def evaluate(cls, current_price, predicted_7d, predicted_14d, predicted_30d,
                 historical_min, historical_avg, historical_max, trend=None, is_anomaly=False):
        curr = float(current_price)
        h_min = float(historical_min or curr)
        h_avg = float(historical_avg or curr)
        h_max = float(historical_max or curr)
        pred_14 = float(predicted_14d or predicted_7d or curr)
        pred_7 = float(predicted_7d or curr)

        exp_drop_14d_pct = ((curr - pred_14) / curr * 100.0) if curr > 0 else 0.0
        exp_drop_7d_pct = ((curr - pred_7) / curr * 100.0) if curr > 0 else 0.0
        diff_from_min_pct = ((curr - h_min) / h_min * 100.0) if h_min > 0 else 0.0
        diff_from_avg_pct = ((curr - h_avg) / h_avg * 100.0) if h_avg > 0 else 0.0

        if curr <= (h_min * 1.02):
            return {
                'recommendation': REC_BUY_NOW,
                'strength': REC_STRONG_BUY,
                'reason': f'Current price (₹{curr:,.0f}) is at or near its all-time historical minimum (₹{h_min:,.0f}). AI models indicate prices are unlikely to drop further and will rebound soon.',
                'expected_change_pct': round(-exp_drop_14d_pct, 2),
            }

        if exp_drop_14d_pct >= 3.5 or (exp_drop_7d_pct >= 3.0 and trend == TREND_DECREASING):
            strength = REC_STRONG_WAIT if exp_drop_14d_pct >= 7.0 else REC_WAIT_MILD
            return {
                'recommendation': REC_WAIT,
                'strength': strength,
                'reason': f'Price is trending downward. The AI forecasting model projects a further {exp_drop_14d_pct:.1f}% decline over the next 14 days (estimated target: ₹{pred_14:,.0f}). Waiting for the bottom is recommended.',
                'expected_change_pct': round(-exp_drop_14d_pct, 2),
            }

        if diff_from_avg_pct <= -5.0 and exp_drop_14d_pct < 2.0:
            return {
                'recommendation': REC_BUY_NOW,
                'strength': REC_BUY,
                'reason': f'The product is currently selling {abs(diff_from_avg_pct):.1f}% below its historical average price (₹{h_avg:,.0f}). AI forecasts indicate price stabilization.',
                'expected_change_pct': round(-exp_drop_14d_pct, 2),
            }

        if diff_from_avg_pct >= 4.0:
            return {
                'recommendation': REC_WAIT,
                'strength': REC_WAIT_MILD,
                'reason': f'Current price (₹{curr:,.0f}) is {diff_from_avg_pct:.1f}% higher than its historical average of ₹{h_avg:,.0f}. Waiting for an upcoming promotional cycle is advised.',
                'expected_change_pct': round(-exp_drop_14d_pct, 2),
            }

        if pred_14 > curr:
            return {
                'recommendation': REC_BUY_NOW,
                'strength': REC_BUY,
                'reason': f'Current price is stable and projected to gradually increase by {abs(exp_drop_14d_pct):.1f}% over the next two weeks. Good time to purchase.',
                'expected_change_pct': round(-exp_drop_14d_pct, 2),
            }
        else:
            return {
                'recommendation': REC_WAIT,
                'strength': REC_WAIT_MILD,
                'reason': f'Prices have plateaued near ₹{curr:,.0f}. A minor softening toward ₹{pred_14:,.0f} is anticipated over the coming weeks.',
                'expected_change_pct': round(-exp_drop_14d_pct, 2),
            }
