"""
Data Preprocessing Pipeline for the AI/ML Engine.
Extracts price time-series from the database, sorts chronologically,
handles missing/invalid values, and prepares structured DataFrames.
"""
import pandas as pd
import numpy as np
from decimal import Decimal
from django.utils import timezone
from .utils import MIN_HISTORICAL_POINTS


def fetch_product_price_history(product_id_or_product):
    from dashboard.models import Product, PriceHistory

    if isinstance(product_id_or_product, (int, str)):
        product = Product.objects.filter(id=product_id_or_product).first()
    else:
        product = product_id_or_product

    if not product:
        return pd.DataFrame(columns=['recorded_at', 'price', 'product_id', 'marketplace'])

    history_qs = PriceHistory.objects.filter(
        product_listing__product=product
    ).select_related('product_listing', 'product_listing__platform').order_by('recorded_at')

    data = []
    for h in history_qs:
        data.append({
            'recorded_at': pd.to_datetime(h.recorded_at),
            'price': float(h.price),
            'product_id': product.id,
            'marketplace': h.product_listing.platform.name if h.product_listing.platform else 'General',
        })

    if not data and product.current_price:
        data.append({
            'recorded_at': pd.to_datetime(product.created_at or timezone.now()),
            'price': float(product.current_price),
            'product_id': product.id,
            'marketplace': product.platform.name if product.platform else 'General',
        })

    df = pd.DataFrame(data)
    return clean_price_series(df)


def fetch_catalog_price_history():
    from dashboard.models import PriceHistory
    history_qs = PriceHistory.objects.select_related('product_listing__product', 'product_listing__platform').order_by('recorded_at')

    data = []
    for h in history_qs:
        data.append({
            'recorded_at': pd.to_datetime(h.recorded_at),
            'price': float(h.price),
            'product_id': h.product_listing.product_id,
            'marketplace': h.product_listing.platform.name if h.product_listing.platform else 'General',
        })
    df = pd.DataFrame(data)
    return clean_price_series(df)


def clean_price_series(df):
    if df.empty:
        return df

    df = df.copy()
    df['recorded_at'] = pd.to_datetime(df['recorded_at'])
    df = df.sort_values('recorded_at').reset_index(drop=True)

    df = df[df['price'] > 0]
    df = df.dropna(subset=['price', 'recorded_at'])

    if 'product_id' in df.columns:
        df['date'] = df['recorded_at'].dt.date
        df = df.sort_values('recorded_at').groupby(['product_id', 'date']).last().reset_index()
        df['recorded_at'] = pd.to_datetime(df['date'])
        df = df.drop(columns=['date'], errors='ignore')

    return df.sort_values('recorded_at').reset_index(drop=True)


def validate_minimum_data(df, min_points=MIN_HISTORICAL_POINTS):
    if df is None or df.empty or len(df) < min_points:
        return False, f'Insufficient historical data ({len(df) if df is not None else 0}/{min_points} points). At least {min_points} price records are required for reliable AI predictions.'
    return True, 'Data sufficient for AI analysis.'
