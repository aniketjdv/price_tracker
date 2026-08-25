
# PricePulse: AI-Powered Price Tracker Dashboard

PricePulse is an intelligent multi-marketplace price tracking, anomaly detection, and future price forecasting web application built with **Django 5** and **Scikit-learn**.

---

## 🚀 Quick Start Guide for New Devices

### 1. Prerequisites
- **Python 3.10+** (Python 3.11, 3.12, or 3.14 supported)
- **Git** (optional)

---

### 2. Setup Virtual Environment & Install Dependencies

#### On Windows:
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
# (or in Command Prompt: .\.venv\Scripts\activate.bat)

# Upgrade pip & install dependencies
pip install -r requirements.txt
```

#### On macOS / Linux:
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip & install dependencies
pip install -r requirements.txt
```

---

### 3. Database Setup & Migrations
```bash
python manage.py migrate
```

---

### 4. Seed Data & Train AI Models
```bash
# 1. Populate initial multi-marketplace catalog with 60 days of historical data:
python manage.py seed_simulator_data

# 2. Train the Random Forest & Linear Regression AI price forecasting models:
python manage.py train_price_model

# 3. Generate catalog-wide AI predictions, anomaly alerts, and Buy/Wait recommendations:
python manage.py generate_ai_predictions
```

---

### 5. Run Automated Tests (53 Tests)
```bash
python manage.py test
```

---

### 6. Start the Development Server
```bash
python manage.py runserver
```

Open your browser at **`http://127.0.0.1:8000/`**.

---

## 🤖 AI / Machine Learning Features (`ai_engine/`)

- **Multi-Horizon Price Forecasting**: Predicts future prices for **7 Days**, **14 Days**, and **30 Days** using Random Forest Regressor.
- **Buy / Wait Recommendation Engine**: Outputs `BUY NOW` or `WAIT` with classified strengths (`Strong Buy`, `Buy`, `Wait`, `Strong Wait`) and explainable reasoning.
- **Price Anomaly Detection**: Uses Isolation Forest and IQR bands to detect flash sales (`FLASH_DROP`) and abnormal price spikes (`SURGE`).
- **Interactive Visualizations**: Chart.js charts displaying historical actual prices alongside future dashed AI forecast trajectories.

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

  