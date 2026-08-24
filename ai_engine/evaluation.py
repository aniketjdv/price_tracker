"""
Model Evaluation and Metrics.
Computes Mean Absolute Error (MAE), Root Mean Squared Error (RMSE),
and R-squared (R2) using chronological time-based train/test splits.
"""
import numpy as np
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score


def evaluate_regression_models(X_train, y_train, X_test, y_test):
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor

    results = {}

    # Linear Regression Baseline
    lr = LinearRegression()
    lr.fit(X_train, y_train)
    lr_pred = lr.predict(X_test)

    results['LinearRegression'] = {
        'mae': round(float(mean_absolute_error(y_test, lr_pred)), 2),
        'rmse': round(float(root_mean_squared_error(y_test, lr_pred)), 2),
        'r2': round(float(r2_score(y_test, lr_pred)), 4),
        'model': lr,
    }

    # Random Forest Regressor
    rf = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)

    results['RandomForestRegressor'] = {
        'mae': round(float(mean_absolute_error(y_test, rf_pred)), 2),
        'rmse': round(float(root_mean_squared_error(y_test, rf_pred)), 2),
        'r2': round(float(r2_score(y_test, rf_pred)), 4),
        'model': rf,
    }

    best_model_name = 'RandomForestRegressor' if results['RandomForestRegressor']['mae'] <= results['LinearRegression']['mae'] else 'LinearRegression'
    results['best_model'] = best_model_name

    return results
