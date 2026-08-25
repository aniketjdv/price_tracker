
  # Price Tracker Dashboard
# PricePulse: AI-Powered Price Tracker Dashboard

  This project is a Django-based price tracking dashboard with SQLite persistence.
PricePulse is an intelligent multi-marketplace price tracking, anomaly detection, and future price forecasting web application built with **Django 5** and **Scikit-learn**.

  ## Running the code
---

  1. Create and activate your Python virtual environment, if not already active:
     - Windows PowerShell: `python -m venv .venv` and `.\.venv\Scripts\Activate.ps1`
     - Windows Command Prompt: `python -m venv .venv` and `.\.venv\Scripts\activate.bat`
## 🚀 Quick Start Guide for New Devices

  2. Install dependencies:
     - `pip install -r requirements.txt`
### 1. Prerequisites
- **Python 3.10+** (Python 3.11, 3.12, or 3.14 supported)
- **Git** (optional)

  3. Apply database migrations:
     - `python manage.py migrate`
---

  4. Run the development server:
     - `python manage.py runserver`
### 2. Setup Virtual Environment & Install Dependencies

  5. Open the app in your browser at `http://127.0.0.1:8000/`.
#### On Windows:
```powershell
# Create virtual environment
python -m venv .venv

  ## Notes
# Activate virtual environment
.\.venv\Scripts\Activate.ps1
# (or in Command Prompt: .\.venv\Scripts\activate.bat)

  - The React/Vite frontend has been removed and replaced with Django templates using Bootstrap.
  - The app stores data in `db.sqlite3`.
# Upgrade pip & install dependencies
pip install -r requirements.txt
```

   ## Simulated provider
#### On macOS / Linux:
```bash
# Create virtual environment
python3 -m venv .venv

   The default provider is a deterministic local simulator. Its responses use the same provider contract as future marketplace integrations and are clearly marked with `source: simulator`; they are not data from Amazon, Flipkart, or any other real store.
# Activate virtual environment
source .venv/bin/activate

   Seed 60 products, five marketplace listings per product, and 60 days of history:
# Upgrade pip & install dependencies
pip install -r requirements.txt
```

   `python manage.py seed_simulator_data`
---

   Optional controls are `--count`, `--days`, `--seed`, and `--reset`.
### 3. Database Setup & Migrations
```bash
python manage.py migrate
```

   Generate a new price and history point for every listing:
---

   `python manage.py update_simulated_prices`
### 4. Seed Data & Train AI Models
```bash
# 1. Populate initial multi-marketplace catalog with 60 days of historical data:
python manage.py seed_simulator_data

   ## ShopSphere demo storefront
# 2. Train the Random Forest & Linear Regression AI price forecasting models:
python manage.py train_price_model

   The independent `store` app provides an original simulated e-commerce storefront backed by the same `Product`, `ProductListing`, and `PriceHistory` records used by the tracker. It is available at `http://127.0.0.1:8000/store/` and exposes JSON endpoints under `/store/api/products/`.
# 3. Generate catalog-wide AI predictions, anomaly alerts, and Buy/Wait recommendations:
python manage.py generate_ai_predictions
```

   Prepare or refresh the catalog with:
---

   `python manage.py seed_store`
### 5. Run Automated Tests (53 Tests)
```bash
python manage.py test
```

   Add a product to the cart or wishlist from the storefront, open its product page to show the shared price history, then run:
---

   `python manage.py simulate_price_changes`
### 6. Start the Development Server
```bash
python manage.py runserver
```

   Refresh the store and PricePulse dashboard to demonstrate the new shared history point and any generated price-drop notification. The store does not process real orders or payments.
Open your browser at **`http://127.0.0.1:8000/`**.

   ## Provider configuration
---

   Copy `.env.example` to `.env` and set `ECOMMERCE_PROVIDER=simulator`. The Django settings read future Amazon and Flipkart credentials from environment variables only. To add a real integration, implement the four methods in `AmazonProvider` or `FlipkartProvider`; the models, services, templates, and views consume the shared provider interface.
## 🤖 AI / Machine Learning Features (`ai_engine/`)

   ## Data model
- **Multi-Horizon Price Forecasting**: Predicts future prices for **7 Days**, **14 Days**, and **30 Days** using Random Forest Regressor.
- **Buy / Wait Recommendation Engine**: Outputs `BUY NOW` or `WAIT` with classified strengths (`Strong Buy`, `Buy`, `Wait`, `Strong Wait`) and explainable reasoning.
- **Price Anomaly Detection**: Uses Isolation Forest and IQR bands to detect flash sales (`FLASH_DROP`) and abnormal price spikes (`SURGE`).
- **Interactive Visualizations**: Chart.js charts displaying historical actual prices alongside future dashed AI forecast trajectories.

   `Product` stores the shared catalog item. `ProductListing` stores marketplace-specific IDs, sellers, URLs, availability, and current prices. `PriceHistory` stores timestamped prices for each listing, which keeps comparison and ML inputs independent from the provider implementation.
---

## 🌐 Key URLs & REST APIs

| Page / API | URL Path |
| :--- | :--- |
| **Home Dashboard** | `http://127.0.0.1:8000/` |
| **Products Catalog** | `http://127.0.0.1:8000/products/` |
| **Product Detail & AI Forecast** | `http://127.0.0.1:8000/product/<id>/` |
| **Price Alerts** | `http://127.0.0.1:8000/alerts/` |
| **Track New Product** | `http://127.0.0.1:8000/track-new/` |
| **Admin Control Center** | `http://127.0.0.1:8000/site-admin/` |
| **Django Admin** | `http://127.0.0.1:8000/admin/` |
| **AI Analysis API (JSON)** | `http://127.0.0.1:8000/api/ai/products/<id>/analysis/` |
| **AI Prediction API (JSON)** | `http://127.0.0.1:8000/api/ai/products/<id>/prediction/` |
| **AI Recommendation API (JSON)** | `http://127.0.0.1:8000/api/ai/products/<id>/recommendation/` |
| **AI Anomaly API (JSON)** | `http://127.0.0.1:8000/api/ai/products/<id>/anomaly/` |
| **AI Metrics API (JSON)** | `http://127.0.0.1:8000/api/ai/metrics/` |

  